#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de integração: busca_ampla → SQLite → scraper_escalavel → CSV
1. Lê links coletados do JSON de busca_ampla
2. Insere no banco de dados SQLite
3. Processa com workers paralelos
4. Exporta para CSV
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Adicionar diretório ao path para importar módulos locais
sys.path.insert(0, str(Path(__file__).parent))

from scraper_escalavel import ScraperEscalavel, ImovelDB


def integrar_busca_ampla_para_db():
    """
    Lê o JSON mais recente de busca_ampla e insere os links no banco.
    """
    output_dir = Path(__file__).parent / "output"
    
    # Encontrar o arquivo JSON mais recente de busca_ampla
    json_files = sorted(output_dir.glob("imoveis_busca_ampla_*.json"), reverse=True)
    if not json_files:
        print("❌ Nenhum arquivo JSON de busca_ampla encontrado em output/")
        print("   Execute: python busca_ampla.py \"sua busca\"")
        return False
    
    json_file = json_files[0]
    print(f"📖 Lendo links de: {json_file.name}")
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            resultados = json.load(f)
    except Exception as e:
        print(f"❌ Erro ao ler JSON: {e}")
        return False
    
    db = ImovelDB()
    
    # Extrair domínio do link e inserir no banco
    links_adicionados = 0
    dominios = {}
    
    for item in resultados:
        link = item.get('link')
        if not link:
            continue
        
        # Determinar domínio
        domain = None
        if 'vivareal.com.br' in link:
            domain = 'vivareal.com.br'
        elif 'imovelweb.com.br' in link:
            domain = 'imovelweb.com.br'
        elif 'olx.com.br' in link:
            domain = 'olx.com.br'
        elif 'zapimoveis.com.br' in link:
            domain = 'zapimoveis.com.br'
        elif 'mercadolivre.com.br' in link:
            domain = 'mercadolivre.com.br'
        else:
            domain = 'outro'
        
        # Adicionar link ao banco
        db.add_link(link, domain, 'busca_ampla')
        links_adicionados += 1
        dominios[domain] = dominios.get(domain, 0) + 1
    
    print(f"\n✅ {links_adicionados} links adicionados ao banco:")
    for dom, count in dominios.items():
        print(f"   {dom}: {count}")
    
    return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Integração: busca_ampla → DB → Scraper → CSV"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=3,
        help="Número de workers paralelos (padrão: 3)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Rodar em headless mode"
    )
    parser.add_argument(
        "--skip-search",
        action="store_true",
        help="Pular leitura de busca_ampla, usar links já no banco"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("INTEGRAÇÃO: BUSCA_AMPLA → DB → SCRAPER → CSV")
    print("=" * 70)
    
    # Passo 1: Integrar links de busca_ampla
    if not args.skip_search:
        print("\n[1/3] Lendo links de busca_ampla...")
        if not integrar_busca_ampla_para_db():
            sys.exit(1)
    else:
        print("\n[1/3] Pulando leitura de busca_ampla...")
    
    # Passo 2: Processar com workers
    print("\n[2/3] Processando links com workers paralelos...")
    scraper = ScraperEscalavel(headless=args.headless, max_workers=args.workers)
    scraper.processar_tudo()
    
    # Passo 3: Exportar CSV
    print("\n[3/3] Exportando para CSV...")
    csv_file = scraper.exportar_csv()
    
    if csv_file:
        print(f"\n{'='*70}")
        print(f"✅ SUCESSO! Dados exportados para: {csv_file.name}")
        print(f"{'='*70}")
    else:
        print("\n❌ Erro ao exportar CSV")
        sys.exit(1)


if __name__ == '__main__':
    main()
