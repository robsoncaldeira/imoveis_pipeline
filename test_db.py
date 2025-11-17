#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste para verificar inserção no DB
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("imoveis.db")

def check_db():
    """Verifica conteúdo do DB"""
    if not DB_PATH.exists():
        print("❌ DB não existe ainda")
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        c.execute('SELECT COUNT(*) FROM imoveis')
        count = c.fetchone()[0]
        
        print(f"\n📊 Status do Banco de Dados:")
        print(f"   Arquivo: {DB_PATH.absolute()}")
        print(f"   Total de imóveis: {count}")
        
        if count > 0:
            c.execute('SELECT id, titulo, preco, cidade FROM imoveis LIMIT 5')
            print(f"\n   Últimos 5 registros:")
            for row in c.fetchall():
                print(f"     • [{row[0]}] {row[1][:40]:40} | {row[2]:12} | {row[3]}")
        
        conn.close()
        return count
    except Exception as e:
        print(f"❌ Erro ao consultar: {e}")
        conn.close()
        return 0

if __name__ == '__main__':
    print("🔍 Verificando banco de dados...")
    
    # Conta inicial
    count_antes = check_db()
    
    print(f"\n➡️  Rodando extração...")
    import subprocess
    result = subprocess.run(['.venv\\Scripts\\python.exe', 'extract_from_capture.py'], 
                          capture_output=False)
    
    print(f"\n🔍 Verificando banco após extração...")
    
    # Conta final
    count_depois = check_db()
    
    # Resumo
    print(f"\n📈 Resultado:")
    print(f"   Antes:  {count_antes} imóveis")
    print(f"   Depois: {count_depois} imóveis")
    print(f"   Adicionados: {count_depois - count_antes} imóveis ✅" if count_depois > count_antes else f"   Sem alteração ❌")
