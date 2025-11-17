#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orquestrador para rodar múltiplas buscas e processar tudo mantendo tudo no DB.
1. Recebe um arquivo com palavras-chave (uma por linha) ou lista pela CLI
2. Para cada keyword, usa BroadSearcher (busca_ampla) para coletar links (headful)
3. Insere links na tabela `links` do DB
4. Depois de todas as buscas, executa ScraperEscalavel.processar_tudo() para extrair os dados

Uso:
    python orquestrador.py --keywords-file keywords.txt --workers 5

Observação: as buscas são feitas em modo "headful" por padrão (para permitir resolver CAPTCHAs).
"""

import argparse
from pathlib import Path
import sys
from scraper_escalavel import ImovelDB, ScraperEscalavel
from busca_ampla import BroadSearcher


def load_keywords(file_path):
    p = Path(file_path)
    if not p.exists():
        return []
    return [l.strip() for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]


def main():
    parser = argparse.ArgumentParser(description='Orquestrador de buscas + processamento')
    parser.add_argument('--keywords-file', '-f', type=str, required=True, help='Arquivo com keywords (uma por linha)')
    parser.add_argument('--workers', '-w', type=int, default=3, help='Workers para processamento')
    parser.add_argument('--headless-search', action='store_true', help='Rodar busca em headless (não recomendado)')
    parser.add_argument('--proxy-file', type=str, default=None, help='Arquivo de proxies (opcional)')
    parser.add_argument('--ua-file', type=str, default=None, help='Arquivo de user agents (opcional)')
    args = parser.parse_args()

    keywords = load_keywords(args.keywords_file)
    if not keywords:
        print('Nenhuma keyword encontrada no arquivo')
        sys.exit(1)

    db = ImovelDB()

    print(f'Iniciando buscas para {len(keywords)} keywords...')
    buscador = BroadSearcher(headless=not args.headless_search, slow_wait=1)
    if not buscador.start_driver():
        print('Erro ao iniciar driver do BroadSearcher')
        sys.exit(1)

    try:
        for kw in keywords:
            print(f'\n🔍 Buscando: {kw}')
            for domain in buscador.TARGET_DOMAINS if hasattr(buscador, 'TARGET_DOMAINS') else ['imovelweb.com.br','vivareal.com.br','olx.com.br','zapimoveis.com.br','mercadolivre.com.br']:
                links = buscador.bing_site_search_browser(kw, domain, limit=20)
                for link in links:
                    db.add_link(link, domain, kw)
                print(f'  ✓ {len(links)} links adicionados de {domain} para {kw}')
    finally:
        try:
            buscador.driver.quit()
        except:
            pass

    print('\n✓ Busca concluída. Iniciando processamento de todos os links no DB...')
    scraper = ScraperEscalavel(headless=True, max_workers=args.workers, proxy_file=args.proxy_file, ua_file=args.ua_file)
    scraper.processar_tudo()
    print('\n✓ Orquestração completa. Use scraper.exportar_csv() ou consolidar.py para gerar CSVs.')

if __name__ == '__main__':
    main()
