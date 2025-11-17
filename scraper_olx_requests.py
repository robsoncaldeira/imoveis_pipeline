#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scraper direto para OLX usando requests + BeautifulSoup
Evita problemas com Selenium/Chrome
"""

import sys
import sqlite3
import json
import re
import time
import csv
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

DB_PATH = Path(__file__).parent / "imoveis.db"
OUTPUT_DIR = Path(__file__).parent / "output"

# Headers para simular navegador
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def fetch_olx_listing(url, session=None):
    """Fetch página de anúncio do OLX"""
    if session is None:
        session = requests.Session()
    
    try:
        logger.info(f"Fetching: {url}")
        response = session.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.warning(f"Erro ao buscar {url}: {e}")
        return None

def extract_olx_data(html, url):
    """Extrai dados da página OLX"""
    if not html:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Tenta extrair dados estruturados (JSON-LD)
        scripts = soup.find_all('script', {'type': 'application/ld+json'})
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and ('BreadcrumbList' in str(data) or 'Thing' in str(data)):
                    continue
                
                # Se encontrar listing schema
                if isinstance(data, dict):
                    titulo = data.get('name') or data.get('headline')
                    preco = None
                    metragem = None
                    quartos = None
                    banheiros = None
                    descricao = data.get('description')
                    endereco = None
                    cidade = None
                    estado = None
                    cep = None
                    contato = None
                    
                    # Extrai preço de offers
                    offers = data.get('offers', {})
                    if isinstance(offers, dict):
                        preco = offers.get('price')
                    elif isinstance(offers, list) and len(offers) > 0:
                        preco = offers[0].get('price')
                    
                    # Extrai endereço
                    address = data.get('address', {})
                    if isinstance(address, dict):
                        endereco = address.get('streetAddress')
                        cidade = address.get('addressLocality')
                        estado = address.get('addressRegion')
                        cep = address.get('postalCode')
                    
                    # Contato
                    contact = data.get('contactPoint')
                    if isinstance(contact, dict):
                        contato = contact.get('telephone')
                    
                    if titulo or preco or endereco:
                        return {
                            'titulo': titulo,
                            'preco': f"R$ {preco}" if preco else None,
                            'metragem': metragem,
                            'quartos': quartos,
                            'banheiros': banheiros,
                            'descricao': descricao,
                            'endereco': endereco,
                            'cidade': cidade,
                            'estado': estado,
                            'cep': cep,
                            'contato': contato,
                        }
            except json.JSONDecodeError:
                continue
        
        # Fallback: extrai com regex
        titulo_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        titulo = titulo_match.group(1) if titulo_match else None
        
        # Preço
        price_match = re.search(r'R\$\s*([\d\.,]+)', html)
        preco = f"R$ {price_match.group(1)}" if price_match else None
        
        # Descrição
        desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html)
        descricao = desc_match.group(1) if desc_match else None
        
        # CEP
        cep_match = re.search(r'(\d{5})-(\d{3})', html)
        cep = f"{cep_match.group(1)}-{cep_match.group(2)}" if cep_match else None
        
        # Telefone
        phone_match = re.search(r'\(\d{2}\)\s*\d{4,5}-\d{4}', html)
        contato = phone_match.group(0) if phone_match else None
        
        if titulo or preco:
            return {
                'titulo': titulo,
                'preco': preco,
                'metragem': None,
                'quartos': None,
                'banheiros': None,
                'descricao': descricao,
                'endereco': None,
                'cidade': None,
                'estado': None,
                'cep': cep,
                'contato': contato,
            }
    
    except Exception as e:
        logger.warning(f"Erro ao extrair dados: {e}")
    
    return None

def process_worker(url_batch, session):
    """Worker que processa URLs"""
    results = []
    for url in url_batch:
        html = fetch_olx_listing(url, session)
        data = extract_olx_data(html, url)
        if data:
            results.append((url, data))
        time.sleep(2)  # Delay para não sobrecarregar OLX
    return results

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get pending links
    c.execute("SELECT url FROM links WHERE status = 'pending' LIMIT 72")
    urls = [row[0] for row in c.fetchall()]
    logger.info(f"📊 Processando {len(urls)} links")
    
    if not urls:
        logger.info("❌ Nenhum link pendente")
        return
    
    # Processa URLs
    all_results = []
    session = requests.Session()
    batch_size = 6
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i+batch_size]
            futures.append(executor.submit(process_worker, batch, session))
        
        for future in as_completed(futures):
            try:
                results = future.result()
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"Erro em worker: {e}")
    
    # Salva no banco
    logger.info(f"💾 Salvando {len(all_results)} registros...")
    for url, data in all_results:
        try:
            imovel_id = re.search(r'/vi/(\d+)', url).group(1)
            c.execute("""
                INSERT OR REPLACE INTO imoveis 
                (id, link, titulo, preco, metragem, quartos, banheiros, 
                 descricao, endereco, cidade, estado, cep, contato, fonte, data_coleta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OLX', ?)
            """, (
                imovel_id,
                url,
                data.get('titulo'),
                data.get('preco'),
                data.get('metragem'),
                data.get('quartos'),
                data.get('banheiros'),
                data.get('descricao'),
                data.get('endereco'),
                data.get('cidade'),
                data.get('estado'),
                data.get('cep'),
                data.get('contato'),
                datetime.now().isoformat(),
            ))
            
            # Mark link as done
            c.execute("UPDATE links SET status = 'done' WHERE url = ?", (url,))
        except Exception as e:
            logger.warning(f"Erro ao salvar {url}: {e}")
    
    conn.commit()
    
    # Export CSV
    logger.info("📄 Exportando CSV...")
    c.execute("""
        SELECT id, titulo, preco, metragem, quartos, banheiros, descricao,
               endereco, cidade, estado, cep, contato, link, fonte, data_coleta
        FROM imoveis
        ORDER BY data_coleta DESC
    """)
    
    csv_file = OUTPUT_DIR / f"imoveis_olx_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Título', 'Preço', 'Metragem', 'Quartos', 'Banheiros',
                        'Descrição', 'Endereço', 'Cidade', 'Estado', 'CEP', 'Contato',
                        'Link', 'Fonte', 'Data Coleta'])
        for row in c.fetchall():
            writer.writerow(row)
    
    logger.info(f"✅ CSV salvo em: {csv_file}")
    
    # Stats
    c.execute("SELECT COUNT(*) FROM imoveis WHERE preco IS NOT NULL")
    com_preco = c.fetchone()[0]
    logger.info(f"📊 Total: {len(all_results)}, Com preço: {com_preco}")
    
    conn.close()

if __name__ == '__main__':
    main()
