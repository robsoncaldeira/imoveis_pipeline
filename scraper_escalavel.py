#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema escalável para scraping de 100k+ imóveis usando:
- SQLite para armazenamento (mais eficiente que JSON)
- Cache de links (evita re-buscar)
- Workers paralelos (múltiplos navegadores simultâneos)
- Retry com backoff exponencial
- Checkpoint automático
"""

import sys
import sqlite3
import json
import re
import time
import hashlib
import threading
import csv
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from tqdm import tqdm
import undetected_chromedriver as uc
import random
from net_utils import load_proxies, load_user_agents, pick_random, configure_chrome_options

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

DB_PATH = Path(__file__).parent / "imoveis.db"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

TARGET_DOMAINS = [
    "vivareal.com.br",
    "imovelweb.com.br",
    "olx.com.br",
    "zapimoveis.com.br",
    "mercadolivre.com.br",
]

# Limites
LINKS_PER_DOMAIN = 20  # links a extrair por domínio
MAX_WORKERS = 3  # número de navegadores paralelos
BATCH_SIZE = 100  # processar em lotes
RETRY_MAX = 3
RETRY_BACKOFF_FACTOR = 2  # 1s, 2s, 4s


# ============================================================================
# BANCO DE DADOS
# ============================================================================

class ImovelDB:
    """Gerencia banco SQLite para armazenar imóveis e metadados."""
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_schema()
    
    def _init_schema(self):
        """Cria tabelas se não existirem."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS imoveis (
                    id TEXT PRIMARY KEY,
                    titulo TEXT NOT NULL,
                    preco TEXT,
                    metragem TEXT,
                    quartos TEXT,
                    banheiros TEXT,
                    descricao TEXT,
                    endereco TEXT,
                    cidade TEXT,
                    estado TEXT,
                    cep TEXT,
                    contato TEXT,
                    link TEXT,
                    fonte TEXT,
                    data_coleta TEXT,
                    raw_text TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS links (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL UNIQUE,
                    domain TEXT,
                    keyword TEXT,
                    status TEXT DEFAULT 'pending',
                    tentativas INTEGER DEFAULT 0,
                    data_add TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoint (
                    id INTEGER PRIMARY KEY,
                    keyword TEXT,
                    domain TEXT,
                    total_links INTEGER,
                    processados INTEGER,
                    data_inicio TEXT,
                    data_ultimo_checkpoint TEXT
                )
            """)
            conn.commit()
    
    def add_link(self, url, domain, keyword):
        """Adiciona link para processar (se não existir)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                link_id = hashlib.md5(url.encode()).hexdigest()
                conn.execute("""
                    INSERT OR IGNORE INTO links (id, url, domain, keyword, data_add)
                    VALUES (?, ?, ?, ?, ?)
                """, (link_id, url, domain, keyword, datetime.now().isoformat()))
                conn.commit()
        except Exception as e:
            print(f"Erro ao add_link: {e}")
    
    def add_imovel(self, titulo, preco=None, metragem=None, quartos=None, 
                   banheiros=None, descricao=None, endereco=None, cidade=None, estado=None, cep=None, contato=None, link=None, fonte=None, raw_text=None):
        """Adiciona imóvel ao banco (deduplicado por ID)."""
        try:
            imovel_id = hashlib.md5(f"{titulo}{preco}{link}".encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO imoveis 
                    (id, titulo, preco, metragem, quartos, banheiros, descricao, endereco, cidade, estado, cep, contato, link, fonte, data_coleta, raw_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (imovel_id, titulo, preco, metragem, quartos, banheiros, descricao, endereco, cidade, estado, cep, contato, link, fonte,
                      datetime.now().isoformat(), raw_text[:500] if raw_text else None))
                conn.commit()
            return imovel_id
        except Exception as e:
            print(f"Erro ao add_imovel: {e}")
            return None
    
    def mark_link_processed(self, url, status='done'):
        """Marca link como processado."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                link_id = hashlib.md5(url.encode()).hexdigest()
                conn.execute("""
                    UPDATE links SET status = ? WHERE id = ?
                """, (status, link_id))
                conn.commit()
        except Exception as e:
            print(f"Erro ao mark_link_processed: {e}")
    
    def increment_tentativas(self, url):
        """Incrementa contador de tentativas."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                link_id = hashlib.md5(url.encode()).hexdigest()
                conn.execute("""
                    UPDATE links SET tentativas = tentativas + 1 WHERE id = ?
                """, (link_id,))
                conn.commit()
        except Exception as e:
            print(f"Erro ao increment_tentativas: {e}")
    
    def get_pending_links(self, domain=None, limit=BATCH_SIZE):
        """Retorna links ainda não processados."""
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT url FROM links WHERE status = 'pending' AND tentativas < ?"
            params = [RETRY_MAX]
            if domain:
                query += " AND domain = ?"
                params.append(domain)
            query += f" LIMIT {limit}"
            cursor = conn.execute(query, params)
            return [row[0] for row in cursor.fetchall()]
    
    def get_stats(self):
        """Retorna estatísticas do banco."""
        with sqlite3.connect(self.db_path) as conn:
            total_imoveis = conn.execute("SELECT COUNT(*) FROM imoveis").fetchone()[0]
            total_links = conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]
            links_done = conn.execute("SELECT COUNT(*) FROM links WHERE status = 'done'").fetchone()[0]
            links_error = conn.execute("SELECT COUNT(*) FROM links WHERE status = 'error'").fetchone()[0]
        return {
            'imoveis': total_imoveis,
            'links_total': total_links,
            'links_done': links_done,
            'links_pending': total_links - links_done - links_error,
            'links_error': links_error,
        }
    
    def export_json(self, limite=None):
        """Exporta imóveis para JSON."""
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT id, titulo, preco, metragem, quartos, banheiros, descricao, endereco, cidade, estado, cep, contato, link, fonte, data_coleta FROM imoveis"
            if limite:
                query += f" LIMIT {limite}"
            cursor = conn.execute(query)
            imoveis = []
            for row in cursor.fetchall():
                imoveis.append({
                    'id': row[0],
                    'titulo': row[1],
                    'preco': row[2],
                    'metragem': row[3],
                    'quartos': row[4],
                    'banheiros': row[5],
                    'descricao': row[6],
                    'endereco': row[7],
                    'cidade': row[8],
                    'estado': row[9],
                    'cep': row[10],
                    'contato': row[11],
                    'link': row[12],
                    'fonte': row[13],
                    'data_coleta': row[14],
                })
            return imoveis


# ============================================================================
# RETRY DECORATOR
# ============================================================================

def retry_exponential(max_attempts=RETRY_MAX, backoff_factor=RETRY_BACKOFF_FACTOR):
    """Retry com exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                    wait_time = backoff_factor ** (attempt - 1)
                    print(f"  ⏳ Tentativa {attempt}: aguardando {wait_time}s...")
                    time.sleep(wait_time)
            return None
        return wrapper
    return decorator


# ============================================================================
# EXTRAÇÃO DE DADOS
# ============================================================================

price_re = re.compile(r"R\$\s*[\d\.\,]+")
area_re = re.compile(r"(\d{2,4})\s*m[²2]", re.IGNORECASE)
rooms_re = re.compile(r"(\d+)\s*(?:quarto|quartos|q|qt)\b", re.IGNORECASE)
baths_re = re.compile(r"(\d+)\s*(?:banheiro|banheiros|b\.)\b", re.IGNORECASE)
cep_re = re.compile(r"\b\d{5}-\d{3}\b")
phone_re = re.compile(r"\(?\d{2,3}\)?\s*\d{4,5}-\d{4}")


def _extract_jsonld(html):
    """Parse JSON-LD blocks and return list of dicts."""
    objs = []
    for m in re.finditer(r"<script[^>]*type=\"application/ld\+json\"[^>]*>(.*?)</script>", html, re.I | re.S):
        try:
            txt = m.group(1).strip()
            # Some pages include multiple JSON objects concatenated
            if txt.startswith('['):
                data = json.loads(txt)
                if isinstance(data, list):
                    objs.extend(data)
            else:
                data = json.loads(txt)
                objs.append(data)
        except Exception:
            continue
    return objs


def extrair_dados(html, url=None):
    """Extrai dados de imóvel da página HTML."""
    if not html or len(html) < 100:
        return None
    
    text = re.sub(r"\s+", " ", html)

    # Try JSON-LD first
    try:
        jsonlds = _extract_jsonld(html)
        for obj in jsonlds:
            # Look for real estate listing structures
            if isinstance(obj, dict):
                # common fields: name, description, offers, address, telephone
                titulo = obj.get('name') or obj.get('headline')
                descricao = obj.get('description')
                price = None
                metragem = None
                quartos = None
                banheiros = None
                endereco = None
                cidade = None
                estado = None
                cep = None
                contato = None

                # offers may contain price
                offers = obj.get('offers')
                if isinstance(offers, dict):
                    price = offers.get('price') or offers.get('priceSpecification', {}).get('price')
                # address
                address = obj.get('address') or {}
                if isinstance(address, dict):
                    endereco = address.get('streetAddress')
                    cidade = address.get('addressLocality')
                    estado = address.get('addressRegion')
                    cep = address.get('postalCode')
                # contact
                contato = obj.get('telephone') or (obj.get('contactPoint', {}) or {}).get('telephone')

                if titulo or price or endereco:
                    return {
                        'titulo': titulo or (text[:150] if text else None),
                        'preco': f"R$ {price}" if price and not isinstance(price, str) and price else (price if isinstance(price, str) else None),
                        'metragem': metragem,
                        'quartos': quartos,
                        'banheiros': banheiros,
                        'descricao': descricao,
                        'endereco': endereco,
                        'cidade': cidade,
                        'estado': estado,
                        'cep': cep,
                        'contato': contato,
                        'link': url,
                    }
    except Exception:
        pass

    # Try to find embedded JSON-like keys (addressLocality, postalCode) anywhere in the HTML
    try:
        m_city = re.search(r'"addressLocality"\s*:\s*"([^"]{2,100})"', html)
        m_region = re.search(r'"addressRegion"\s*:\s*"([A-Z]{2})"', html)
        m_postal = re.search(r'"postalCode"\s*:\s*"(\d{5}-\d{3})"', html)
        if m_city and not cidade:
            cidade = m_city.group(1)
        if m_region and not estado:
            estado = m_region.group(1)
        if m_postal and not cep:
            cep = m_postal.group(1)
    except Exception:
        pass

    # Fallback heuristics from raw text
    preco = None
    m = price_re.search(text)
    if m:
        preco = m.group(0)

    metragem = None
    m = area_re.search(text)
    if m:
        metragem = f"{m.group(1)} m²"

    quartos = None
    m = rooms_re.search(text)
    if m:
        quartos = f"{m.group(1)} Q"

    banheiros = None
    m = baths_re.search(text)
    if m:
        banheiros = f"{m.group(1)} B"

    descricao = None
    # meta description
    m = re.search(r"<meta\s+name=[\"']description[\"']\s+content=[\"']([^\"']+)[\"']", html, re.I)
    if m:
        descricao = m.group(1)
    else:
        # try og:description
        m = re.search(r"<meta\s+property=[\"']og:description[\"']\s+content=[\"']([^\"']+)[\"']", html, re.I)
        if m:
            descricao = m.group(1)

    endereco = None
    cidade = None
    estado = None
    cep = None
    contato = None

    # cep
    m = cep_re.search(text)
    if m:
        cep = m.group(0)

    # phone
    m = phone_re.search(text)
    if m:
        contato = m.group(0)

    # try tel: links
    if not contato:
        m = re.search(r"href=['\"]tel:(\+?[0-9\-\(\)\s]+)['\"]", html, re.I)
        if m:
            contato = m.group(1)

    # data attributes (some sites store phone in data-phone)
    if not contato:
        m = re.search(r"data-phone=['\"]([^'\"]+)['\"]", html, re.I)
        if m:
            contato = m.group(1)

    # try to extract an address line
    m = re.search(r'([A-Za-z0-9\s\.,\-]+\b)(?:,\s*)([A-Za-z\s]+)\s*-\s*([A-Z]{2})', text)
    if m:
        endereco = m.group(1).strip()
        cidade = m.group(2).strip()
        estado = m.group(3).strip()

    # title from <title> tag or first heading
    titulo = None
    m = re.search(r'<title>(.*?)</title>', html, re.I)
    if m:
        titulo = m.group(1).strip()
    else:
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.I | re.S)
        if m:
            titulo = re.sub(r'<[^>]+>', '', m.group(1)).strip()

    if not (titulo or preco or metragem):
        return None

    return {
        'titulo': titulo,
        'preco': preco,
        'metragem': metragem,
        'quartos': quartos,
        'banheiros': banheiros,
        'descricao': descricao,
        'endereco': endereco,
        'cidade': cidade,
        'estado': estado,
        'cep': cep,
        'contato': contato,
        'link': url,
    }


# ============================================================================
# SCRAPER COM WORKERS
# ============================================================================

class ScraperEscalavel:
    def __init__(self, headless=True, max_workers=MAX_WORKERS, proxy_file=None, ua_file=None):
        self.headless = headless
        self.max_workers = max_workers
        self.db = ImovelDB()
        self.drivers = []
        self.proxy_list = load_proxies(proxy_file)
        self.ua_list = load_user_agents(ua_file)
    
    def _get_driver(self):
        """Cria um navegador undetected com suporte a proxy/UA rotation."""
        try:
            options = uc.ChromeOptions()
            # pick proxy and ua
            proxy = pick_random(self.proxy_list)
            ua = pick_random(self.ua_list)
            configure_chrome_options(options, proxy=proxy, user_agent=ua, headless=self.headless)
            try:
                driver = uc.Chrome(options=options, version_main=None)
            except TypeError:
                # fallback
                driver = uc.Chrome(options=options)
            return driver
        except Exception as e:
            print(f"Erro ao criar driver: {e}")
            return None
    
    @retry_exponential(max_attempts=RETRY_MAX)
    def processar_link(self, url, driver):
        """Processa um único link (extrai dados)."""
        if not driver:
            driver = self._get_driver()
        
        driver.get(url)
        time.sleep(1.5)
        
        # Scroll
        try:
            driver.execute_script("window.scrollBy(0, window.innerHeight);")
        except:
            pass
        
        html = driver.page_source
        dados = extrair_dados(html, url)
        
        if dados:
            fonte = None
            for domain in TARGET_DOMAINS:
                if domain in url:
                    fonte = domain.split('.')[0].upper()
                    break
            
            self.db.add_imovel(
                titulo=dados['titulo'],
                preco=dados['preco'],
                metragem=dados['metragem'],
                quartos=dados['quartos'],
                banheiros=dados['banheiros'],
                link=url,
                fonte=fonte,
                raw_text=html[:500]
            )
            return True
        return False
    
    def processar_batch_paralelo(self, links):
        """Processa um lote de links em paralelo com múltiplos drivers."""
        drivers = [self._get_driver() for _ in range(min(self.max_workers, len(links)))]
        drivers = [d for d in drivers if d]
        
        if not drivers:
            print("Erro: não foi possível criar drivers")
            return 0
        
        processed = 0
        with ThreadPoolExecutor(max_workers=len(drivers)) as executor:
            futures = {}
            for link, driver in zip(links, drivers):
                future = executor.submit(self.processar_link, link, driver)
                futures[future] = (link, driver)
            
            for future in tqdm(as_completed(futures), total=len(futures), desc="Processando links"):
                link, driver = futures[future]
                try:
                    if future.result():
                        self.db.mark_link_processed(link, 'done')
                        processed += 1
                    else:
                        self.db.mark_link_processed(link, 'retry')
                        self.db.increment_tentativas(link)
                except Exception as e:
                    print(f"Erro ao processar {link}: {e}")
                    self.db.mark_link_processed(link, 'error')
                    self.db.increment_tentativas(link)
        
        # Fechar drivers
        for driver in drivers:
            try:
                driver.quit()
            except:
                pass
        
        return processed
    
    def processar_tudo(self, domain=None):
        """Processa todos os links pendentes em batches."""
        print(f"\n{'='*70}")
        print("SCRAPER ESCALÁVEL - INICIANDO PROCESSAMENTO")
        print(f"{'='*70}")
        
        while True:
            links = self.db.get_pending_links(domain=domain, limit=BATCH_SIZE)
            if not links:
                break
            
            print(f"\n📦 Processando batch com {len(links)} links...")
            self.processar_batch_paralelo(links)
            
            stats = self.db.get_stats()
            print(f"\n📊 Status: {stats['imoveis']} imóveis, {stats['links_done']}/{stats['links_total']} links processados")
        
        print("\n✅ Processamento concluído!")
    
    def exportar_resultados(self):
        """Exporta resultados para JSON."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        imoveis = self.db.export_json()
        
        if not imoveis:
            print("Nenhum imóvel para exportar")
            return
        
        arquivo = OUTPUT_DIR / f"imoveis_scraper_escalavel_{timestamp}.json"
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(imoveis, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ {len(imoveis)} imóvel(is) exportado(s) para: {arquivo.name}")
        return arquivo

    def exportar_csv(self, limite=None):
        """Exporta resultados para CSV (planilha simples)."""
        import csv
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        imoveis = self.db.export_json(limite)
        if not imoveis:
            print("Nenhum imóvel para exportar")
            return
        arquivo = OUTPUT_DIR / f"imoveis_scraper_escalavel_{timestamp}.csv"
        keys = ['id','titulo','preco','metragem','quartos','banheiros','descricao','endereco','cidade','estado','cep','contato','link','fonte','data_coleta']
        with open(arquivo, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in imoveis:
                writer.writerow({k: row.get(k) for k in keys})
        print(f"\n✅ {len(imoveis)} imóvel(is) exportado(s) para CSV: {arquivo.name}")
        return arquivo


# ============================================================================
# CLI
# ============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Scraper escalável para 100k+ imóveis"
    )
    parser.add_argument(
        "-k", "--keywords",
        nargs="*",
        help="Palavras-chave para busca inicial"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=MAX_WORKERS,
        help=f"Número de workers paralelos (padrão: {MAX_WORKERS})"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Rodar em headless mode"
    )
    parser.add_argument(
        "--links-per-domain",
        type=int,
        default=LINKS_PER_DOMAIN,
        help=f"Número de links por domínio a coletar (padrão: {LINKS_PER_DOMAIN})"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Mostrar estatísticas e sair"
    )
    parser.add_argument(
        "--proxy-file",
        type=str,
        default=None,
        help="Arquivo com proxies (uma por linha)"
    )
    parser.add_argument(
        "--ua-file",
        type=str,
        default=None,
        help="Arquivo com user-agents (uma por linha)"
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Exportar resultados para JSON"
    )
    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="Exportar resultados para CSV"
    )
    
    args = parser.parse_args()
    
    scraper = ScraperEscalavel(headless=args.headless, max_workers=args.workers, proxy_file=args.proxy_file, ua_file=args.ua_file)
    db = scraper.db
    
    if args.stats:
        stats = db.get_stats()
        print(f"{'='*70}")
        print("ESTATÍSTICAS DO BANCO")
        print(f"{'='*70}")
        print(f"Total de imóveis: {stats['imoveis']}")
        print(f"Links processados: {stats['links_done']}/{stats['links_total']}")
        print(f"Links pendentes: {stats['links_pending']}")
        print(f"Links com erro: {stats['links_error']}")
    elif args.export:
        scraper.exportar_resultados()
    elif args.keywords:
        from busca_ampla import BroadSearcher
        print(f"Iniciando busca por: {args.keywords}")
        buscador = BroadSearcher(headless=args.headless, slow_wait=1)
        if not buscador.start_driver():
            print("❌ Não foi possível iniciar o driver do navegador. Abortando.")
            sys.exit(1)
        
        try:
            for keyword in args.keywords:
                print(f"\n🔍 Buscando: {keyword}")
                for domain in TARGET_DOMAINS:
                    links = buscador.bing_site_search_browser(keyword, domain, limit=args.links_per_domain)
                    for link in links:
                        db.add_link(link, domain, keyword)
                    print(f"  ✓ {len(links)} links adicionados de {domain}")
        finally:
            try:
                buscador.driver.quit()
            except:
                pass
        
        scraper.processar_tudo()
        if args.export_csv:
            scraper.exportar_csv()
        elif args.export:
            scraper.exportar_resultados()
        else:
            print('Execução concluída. Use --export ou --export-csv para exportar os resultados.')
    else:
        scraper.processar_tudo()
