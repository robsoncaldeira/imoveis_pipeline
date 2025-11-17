#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mostrar estatísticas do banco SQLite"""

import sqlite3
from pathlib import Path

# Caminho absoluto do banco na raiz do projeto
db_path = Path(__file__).resolve().parent / 'imoveis.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Estatísticas gerais
cursor.execute('SELECT COUNT(*) FROM imoveis')
total = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM links')
links_total = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM links WHERE status = ?', ('pending',))
pending = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM links WHERE status = ?', ('success',))
success = cursor.fetchone()[0]

print(f'📊 BANCO DE DADOS - ESTATÍSTICAS')
print(f'════════════════════════════════════════════')
print(f'Total de imóveis coletados: {total}')
print(f'Total de links no banco: {links_total}')
print(f'  - Processados com sucesso: {success}')
print(f'  - Pendentes: {pending}')
print()

# Top domínios
cursor.execute('SELECT fonte, COUNT(*) as count FROM imoveis GROUP BY fonte ORDER BY count DESC')
print('📍 Top domínios coletados:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}')
print()

# Dados coletados por campo
cursor.execute('SELECT COUNT(*) FROM imoveis WHERE preco IS NOT NULL AND preco != ""')
com_preco = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM imoveis WHERE endereco IS NOT NULL AND endereco != ""')
com_endereco = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM imoveis WHERE cep IS NOT NULL AND cep != ""')
com_cep = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM imoveis WHERE contato IS NOT NULL AND contato != ""')
com_contato = cursor.fetchone()[0]

print('📋 Cobertura de dados (% dos imóveis):')
pct_preco = (com_preco / total * 100) if total > 0 else 0
pct_endereco = (com_endereco / total * 100) if total > 0 else 0
pct_cep = (com_cep / total * 100) if total > 0 else 0
pct_contato = (com_contato / total * 100) if total > 0 else 0

print(f'  Preço: {pct_preco:.1f}% ({com_preco}/{total})')
print(f'  Endereço: {pct_endereco:.1f}% ({com_endereco}/{total})')
print(f'  CEP: {pct_cep:.1f}% ({com_cep}/{total})')
print(f'  Contato: {pct_contato:.1f}% ({com_contato}/{total})')
print()

# Amostra de dados coletados
print('📝 Amostra de dados coletados (primeiros 3):')
cursor.execute('''SELECT titulo, preco, endereco, cidade, estado, cep, link 
                  FROM imoveis WHERE link NOT LIKE "%bing.com%"
                  LIMIT 3''')
for idx, row in enumerate(cursor.fetchall(), 1):
    print(f'\n  {idx}. {row[0][:50]}...')
    print(f'     Preço: {row[1] or "N/A"}')
    print(f'     Local: {row[2] or "N/A"}')
    print(f'     {row[3] or ""}, {row[4] or ""} - {row[5] or ""}')
    print(f'     Link: {row[6][:60]}...')

conn.close()
