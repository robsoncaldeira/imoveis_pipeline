#!/usr/bin/env python3
import csv
import glob

# Ler CSV - encontrar o mais recente
csv_files = glob.glob('output/imoveis_olx_extratos*.csv')
csv_file = max(csv_files) if csv_files else None

if not csv_file:
    print("Nenhum arquivo CSV encontrado")
    exit(1)

with open(csv_file, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    dados = list(reader)

print('=' * 60)
print('RESUMO FINAL - EXTRAÇÃO DE IMÓVEIS OLX')
print('=' * 60)
print(f'\n✅ Total de imóveis extraídos: {len(dados)}')
print(f'\n📊 Dados por Estado:')
estados = {}
for row in dados:
    estado = row['estado'].upper()
    estados[estado] = estados.get(estado, 0) + 1
for estado, count in sorted(estados.items()):
    print(f'  {estado}: {count} imóveis')

print(f'\n🏙️ Dados por Cidade:')
cidades = {}
for row in dados:
    cidade = row['cidade']
    cidades[cidade] = cidades.get(cidade, 0) + 1
for cidade, count in sorted(cidades.items(), key=lambda x: -x[1])[:5]:
    print(f'  {cidade}: {count} imóveis')

print(f'\n💰 Preços:')
precos = []
for row in dados:
    try:
        preco_str = row['preco'].replace('R$ ', '').replace('.', '').replace(',', '.')
        precos.append(float(preco_str))
    except:
        pass
if precos:
    print(f'  Mínimo: R$ {min(precos):,.0f}')
    print(f'  Máximo: R$ {max(precos):,.0f}')
    print(f'  Média: R$ {sum(precos)/len(precos):,.0f}')

print(f'\n📋 Campos disponíveis: {list(dados[0].keys())}')
print(f'\n📁 Arquivo salvo em: {csv_file}')
print('=' * 60)
