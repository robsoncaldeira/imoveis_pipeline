#!/usr/bin/env python3
import json

with open('output/network_www.olx.com.br_20251114_120445.json', encoding='utf-8') as f:
    data = json.load(f)
    print(f'Total de entradas: {len(data)}')
    for i, entry in enumerate(data[:2]):
        print(f'\nEntrada {i}:')
        print(f'  Status: {entry.get("status")}')
        text = entry.get('text', '')
        print(f'  Tamanho do text: {len(text)}')
        if text and len(text) > 100:
            if 'GalleryGroup' in text:
                print(f'  ✓ Contém GalleryGroup')
            print(f'  Preview: {text[:200]}...')
