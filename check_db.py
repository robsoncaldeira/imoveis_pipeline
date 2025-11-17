#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('imoveis.db')
c = conn.cursor()

# Ver estrutura da tabela
c.execute("PRAGMA table_info(imoveis)")
print('📋 Estrutura da tabela imoveis:')
for row in c.fetchall():
    print(f'  {row}')

# Ver dados
c.execute('SELECT COUNT(*) FROM imoveis')
count = c.fetchone()[0]
print(f'\n📊 Total de registros: {count}')

if count > 0:
    c.execute('SELECT id, titulo, preco FROM imoveis LIMIT 3')
    print(f'\n📝 Primeiros 3 registros:')
    for row in c.fetchall():
        print(f'  ID: {row[0]}, Título: {row[1][:40]}, Preço: {row[2]}')

conn.close()
