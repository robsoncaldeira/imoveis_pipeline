#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrai dados completos dos imóveis direto do capture network
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

# Caminho absoluto para o banco na raiz do projeto
DB_PATH = Path(__file__).resolve().parent / "imoveis.db"
CAPTURE_FILE = Path("output/network_www.olx.com.br_20251114_120445.json")
OUTPUT_DIR = Path("output")

def extract_data_from_capture():
    """Extrai dados direto do capture"""
    logger.info(f"📂 Lendo capture: {CAPTURE_FILE}")
    
    with open(CAPTURE_FILE, encoding='utf-8') as f:
        capture_data = json.load(f)
    
    imoveis = []
    
    # Processa cada resposta de fetch
    for entry in capture_data:
        if entry.get('status') != 200 or not entry.get('text'):
            continue
        
        text = entry['text']
        
        # Usa regex para encontrar padrões de imóveis
        import re
        pattern = r'"list_id":(\d+).*?"ad_url":"([^"]+)".*?"price":"([^"]+)".*?"subject":"([^"]+)".*?"municipality":"([^"]+)".*?"state_uf":"([^"]+)"'
        
        matches = re.finditer(pattern, text, re.DOTALL)
        for match in matches:
            try:
                imovel = {
                    'list_id': match.group(1),
                    'ad_url': match.group(2),
                    'preco': match.group(3),
                    'titulo': match.group(4),
                    'cidade': match.group(5),
                    'estado': match.group(6),
                    'bairro': '',
                    'categoria': '',
                }
                imoveis.append(imovel)
            except:
                continue
    
    # Remove duplicatas
    seen = set()
    unique_imoveis = []
    for im in imoveis:
        key = im['list_id']
        if key not in seen:
            seen.add(key)
            unique_imoveis.append(im)
    
    logger.info(f"✅ Extraídos {len(unique_imoveis)} imóveis únicos do capture")
    return unique_imoveis

def save_to_db(imoveis):
    """Salva no banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Cria tabela se não existir
    c.execute("""
        CREATE TABLE IF NOT EXISTS imoveis (
            id TEXT PRIMARY KEY,
            link TEXT,
            titulo TEXT,
            preco TEXT,
            cidade TEXT,
            estado TEXT,
            endereco TEXT,
            descricao TEXT,
            fonte TEXT,
            data_coleta TEXT
        )
    """)
    
    logger.info(f"💾 Salvando {len(imoveis)} imóveis no banco...")
    
    for im in imoveis:
        try:
            c.execute("""
                INSERT OR REPLACE INTO imoveis 
                (id, link, titulo, preco, cidade, estado, endereco, descricao, fonte, data_coleta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(im['list_id']),
                im['ad_url'],
                im['titulo'],
                im['preco'],
                im['cidade'],
                im['estado'].upper() if im['estado'] else None,
                im['bairro'],
                f"Categoria: {im['categoria']}",
                'OLX',
                datetime.now().isoformat(),
            ))
        except Exception as e:
            logger.warning(f"Erro ao salvar {im['list_id']}: {e}")
    
    conn.commit()
    conn.close()
    logger.info("✅ Salvamento concluído")

def main():
    # Extrai dados
    imoveis = extract_data_from_capture()
    
    if not imoveis:
        logger.error("❌ Nenhum imóvel extraído")
        return
    
    # Salva no DB
    save_to_db(imoveis)
    
    # Estatísticas
    com_preco = sum(1 for im in imoveis if im['preco'])
    logger.info(f"\n📊 Resumo:")
    logger.info(f"  Total: {len(imoveis)}")
    logger.info(f"  Com preço: {com_preco}")
    logger.info(f"  Cidades: {len(set(im['cidade'] for im in imoveis))}")
    
    # Sample
    logger.info(f"\n📋 Sample (primeiros 5):")
    for im in imoveis[:5]:
        logger.info(f"  {im['titulo'][:50]} - {im['preco']} - {im['cidade']}/{im['estado'].upper()}")

if __name__ == '__main__':
    main()
