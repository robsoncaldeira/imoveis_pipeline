import re
import json
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class WebScraperImovelWeb:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9",
            "Referer": "https://www.imovelweb.com.br"
        })

    def coletar_imoveis(self, url):
        """Coleta imóveis do site ImóvelWeb"""
        try:
            print(f"  → Acessando: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            imoveis = self._extrair_imoveis(soup, url)
            
            if imoveis:
                print(f"  ✓ {len(imoveis)} imóvel(is) encontrado(s)")
            else:
                print(f"  ℹ Nenhum imóvel encontrado")
            
            return imoveis
            
        except requests.exceptions.Timeout:
            print(f"  ✗ Timeout ao acessar")
            return []
        except requests.exceptions.ConnectionError:
            print(f"  ✗ Erro de conexão")
            return []
        except Exception as e:
            print(f"  ✗ Erro: {type(e).__name__}")
            return []

    def _extrair_imoveis(self, soup, url_base):
        """Extrai dados dos imóveis do HTML"""
        imoveis = []
        
        # Procurar por cartões de imóvel (estrutura comum de sites de imóveis)
        # Testando múltiplos seletores possíveis
        seletores = [
            "div[data-listing-id]",
            "article[data-listing]",
            "div.listing-item",
            "div.property-card",
            "li.search-result",
            "div.home-card",
            "div[class*='card']",
            "div[class*='listing']",
        ]
        
        cards = []
        for seletor in seletores:
            cards = soup.select(seletor)
            if cards:
                print(f"  → Encontrado seletor: {seletor} ({len(cards)} cards)")
                break
        
        if not cards:
            print("  ℹ Nenhum padrão de card encontrado")
            return imoveis
        
        for card in cards[:10]:  # Limitar a 10 por página
            try:
                imovel = self._extrair_imovel_do_card(card, url_base)
                if imovel:
                    imoveis.append(imovel)
            except Exception as e:
                continue
        
        return imoveis

    def _extrair_imovel_do_card(self, card, url_base):
        """Extrai dados de um card individual"""
        
        # Tentar extrair título
        titulo = None
        for tag in ["h2", "h3", "a.property-name", "[class*='title']"]:
            elem = card.select_one(tag)
            if elem:
                titulo = elem.get_text(strip=True)
                break
        
        if not titulo:
            return None
        
        # Extrair preço
        preco = None
        preco_pattern = re.compile(r"r\$\s*[\d.,]+", re.IGNORECASE)
        card_text = card.get_text(" ", strip=True)
        match = preco_pattern.search(card_text.lower())
        if match:
            preco = match.group().upper()
        
        # Extrair metragem
        metragem = None
        area_pattern = re.compile(r"(\d+)\s*(m²|m2)", re.IGNORECASE)
        match = area_pattern.search(card_text)
        if match:
            metragem = f"{match.group(1)} m²"
        
        # Extrair localização/bairro
        bairro = None
        for tag in ["span[class*='location']", "span[class*='city']", "[class*='neighborhood']"]:
            elem = card.select_one(tag)
            if elem:
                bairro = elem.get_text(strip=True)
                break
        
        # Extrair link
        link = None
        link_elem = card.select_one("a[href]")
        if link_elem:
            href = link_elem.get("href", "")
            link = urljoin(url_base, href) if href else None
        
        # Gerar ID único
        raw = f"{titulo}{preco}{link or url_base}"
        uid = hashlib.md5(raw.encode()).hexdigest()
        
        imovel = {
            "id": uid,
            "titulo": titulo,
            "preco": preco,
            "metragem": metragem,
            "bairro": bairro,
            "descricao": card_text[:150],
            "link": link,
            "data_coleta": datetime.now().isoformat()
        }
        
        # Retornar apenas se tiver preço e título
        if titulo and preco:
            return imovel
        
        return None

    def salvar(self, imoveis):
        """Salva resultados em JSON"""
        if not imoveis:
            print("\n❌ Nenhum imóvel para salvar")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"imovelweb_{timestamp}.json"
        caminho = OUTPUT_DIR / nome_arquivo
        
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(imoveis, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ {len(imoveis)} imóvel(is) salvo em: {caminho}")
        return str(caminho)

    def close(self):
        """Fecha a sessão"""
        if self.session:
            self.session.close()


def main():
    print("="*70)
    print("WEB SCRAPER IMÓVELWEB - COLETA DE IMÓVEIS")
    print("="*70)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    
    # URLs para coletar
    urls = [
        "https://www.imovelweb.com.br/",
        "https://www.imovelweb.com.br/imoveis-venda-curitiba-pr.html",
    ]
    
    scraper = WebScraperImovelWeb()
    todos_imoveis = []
    
    try:
        for idx, url in enumerate(urls, 1):
            print(f"\n[{idx}/{len(urls)}] Processando...")
            imoveis = scraper.coletar_imoveis(url)
            todos_imoveis.extend(imoveis)
        
        print("\n" + "="*70)
        
        if todos_imoveis:
            print(f"\n✓ ENCONTRADOS {len(todos_imoveis)} IMÓVEL(IS)")
            print("="*70)
            
            for i, im in enumerate(todos_imoveis, 1):
                print(f"\n{i}. {im['titulo']}")
                print(f"   💰 Preço: {im['preco']}")
                print(f"   📐 Metragem: {im['metragem']}")
                print(f"   📍 Bairro: {im.get('bairro', 'N/A')}")
            
            scraper.salvar(todos_imoveis)
        else:
            print("\n❌ Nenhum imóvel encontrado")
            print("\n💡 Dicas:")
            print("   • O site pode estar bloqueando o scraper")
            print("   • Tente acessar o site manualmente primeiro")
            print("   • Verifique sua conexão com a internet")
    
    except KeyboardInterrupt:
        print("\n\n⏹️ Execução cancelada")
    except Exception as e:
        print(f"\n❌ Erro: {type(e).__name__} - {str(e)[:100]}")
    
    finally:
        scraper.close()
        print("\n✓ Encerrando...")


if __name__ == "__main__":
    main()
