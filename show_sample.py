#!/usr/bin/env python3
import csv

with open('output/imoveis_olx_extratos_20251116_221732.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    dados = list(reader)

print('\n' + '='*80)
print('📋 AMOSTRA DOS DADOS EXTRAÍDOS'.center(80))
print('='*80 + '\n')

for i, row in enumerate(dados[:5], 1):
    print(f'{i}. {row["titulo"][:60]}')
    print(f'   💰 Preço: {row["preco"]:>15}  |  🏙️ {row["cidade"]}/{row["estado"].upper()}')
    print(f'   🔗 Link: {row["ad_url"][:55]}...')
    print()

print('...\n' + '='*80 + '\n')
