#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consulta dados salvos no banco de dados imoveis.db
"""

import sqlite3
from pathlib import Path
import json

# Banco sempre na raiz do projeto
DB_PATH = Path(__file__).resolve().parent / "imoveis.db"

def query_all_imoveis():
    """Consulta todos os imóveis do banco"""
    if not DB_PATH.exists():
        print("❌ Banco de dados não encontrado")
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Contar total
    c.execute('SELECT COUNT(*) FROM imoveis')
    total = c.fetchone()[0]
    
    print(f"\n{'='*80}")
    print(f"📊 IMÓVEIS SALVOS NO BANCO DE DADOS")
    print(f"{'='*80}")
    print(f"Total de imóveis: {total}\n")
    
    if total == 0:
        print("❌ Nenhum imóvel no banco")
        conn.close()
        return
    
    # Buscar todos
    c.execute('SELECT id, titulo, preco, cidade, estado, link FROM imoveis ORDER BY id')
    
    for i, row in enumerate(c.fetchall(), 1):
        id_prop, titulo, preco, cidade, estado, link = row
        print(f"{i}. [{id_prop}]")
        print(f"   📍 {titulo}")
        print(f"   💰 {preco}")
        print(f"   🏙️  {cidade}, {estado}")
        print(f"   🔗 {link}")
        print()
    
    # Estatísticas
    print(f"{'='*80}")
    c.execute('SELECT estado, COUNT(*) as qtd FROM imoveis GROUP BY estado ORDER BY qtd DESC')
    print("📈 Distribuição por Estado:")
    for estado, qtd in c.fetchall():
        print(f"   {estado}: {qtd} imóvei(s)")
    
    c.execute('SELECT cidade, COUNT(*) as qtd FROM imoveis GROUP BY cidade ORDER BY qtd DESC')
    print("\n📈 Top Cidades:")
    for cidade, qtd in c.fetchall()[:5]:
        print(f"   {cidade}: {qtd} imóvei(s)")
    
    c.execute('SELECT MIN(CAST(REPLACE(preco, "R$ ", "") as REAL)), MAX(CAST(REPLACE(preco, "R$ ", "") as REAL)) FROM imoveis')
    min_preco, max_preco = c.fetchone()
    if min_preco and max_preco:
        print(f"\n💵 Faixa de Preços:")
        print(f"   Mínimo: R$ {min_preco:,.0f}")
        print(f"   Máximo: R$ {max_preco:,.0f}")
    
    print(f"{'='*80}\n")
    
    conn.close()

if __name__ == '__main__':
    query_all_imoveis()
