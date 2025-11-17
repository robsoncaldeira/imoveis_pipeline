#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Busca múltiplas palavras-chave em sequência e consolida os resultados em um único JSON.
Usa busca_ampla.py internamente.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from busca_ampla import BroadSearcher, save_results

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Palavras-chave padrão para busca
PALAVRAS_CHAVE_PADRAO = [
    "apartamento curitiba",
    "casa curitiba",
    "imóvel curitiba",
    "apartamento sao paulo",
    "casa sao paulo",
]

def rodar_multiplas_buscas(palavras_chave, headless=False, slow_wait=2):
    """
    Roda múltiplas buscas em sequência e consolida resultados.
    
    Args:
        palavras_chave: lista de strings (ex: ["apartamento curitiba", "casa sp"])
        headless: bool - rodar navegador em headless mode
        slow_wait: int - tempo de espera entre requisições
    
    Returns:
        lista deduplicada de resultados
    """
    todos_resultados = []
    vistos_ids = set()
    
    print("="*70)
    print("BUSCA MÚLTIPLA DE IMÓVEIS")
    print("="*70)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"Palavras-chave: {len(palavras_chave)}\n")
    
    buscador = BroadSearcher(headless=headless, slow_wait=slow_wait)
    
    for idx, palavra_chave in enumerate(palavras_chave, 1):
        print(f"\n[{idx}/{len(palavras_chave)}] Buscando: '{palavra_chave}'")
        print("-" * 70)
        
        try:
            resultados = buscador.search(palavra_chave)
            
            # Deduplicar por ID
            for item in resultados:
                item_id = item.get("id")
                if item_id not in vistos_ids:
                    vistos_ids.add(item_id)
                    todos_resultados.append(item)
            
            print(f"✓ {len(resultados)} resultado(s) coletado(s)")
        
        except Exception as e:
            print(f"✗ Erro ao buscar '{palavra_chave}': {e}")
    
    print(f"\n{'='*70}")
    print(f"RESUMO FINAL")
    print(f"{'='*70}")
    print(f"Total de resultados únicos: {len(todos_resultados)}")
    
    return todos_resultados


def salvar_consolidado(resultados, prefix="imoveis_consolidado"):
    """Salva todos os resultados em um único JSON consolidado."""
    if not resultados:
        print("\n❌ Nenhum resultado para salvar")
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nome = f"{prefix}_{timestamp}.json"
    caminho = OUTPUT_DIR / nome
    
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ {len(resultados)} resultado(s) consolidado(s) em: {caminho.name}")
    print(f"📁 Caminho completo: {caminho}")
    
    # Mostrar resumo
    print(f"\n{'='*70}")
    print("PRIMEIROS 10 RESULTADOS:")
    print(f"{'='*70}")
    for i, im in enumerate(resultados[:10], 1):
        print(f"\n{i}. {im.get('titulo', 'N/A')[:80]}")
        print(f"   💰 {im.get('preco', 'N/A')}")
        print(f"   📐 {im.get('metragem', 'N/A')}")
        print(f"   🛏️ {im.get('quartos', 'N/A')}")
    
    if len(resultados) > 10:
        print(f"\n   ... e {len(resultados) - 10} mais resultados")
    
    return caminho


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Busca múltiplas palavras-chave de imóveis e consolida resultados"
    )
    parser.add_argument(
        "-k", "--keywords",
        nargs="*",
        help="Palavras-chave para busca (ex: -k 'apartamento curitiba' 'casa sp')"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Rodar navegador em headless mode (padrão: visível para debug)"
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=2,
        help="Tempo de espera entre requisições em segundos (padrão: 2)"
    )
    
    args = parser.parse_args()
    
    # Usar palavras-chave fornecidas ou padrão
    if args.keywords and args.keywords[0]:
        palavras_chave = args.keywords
    else:
        print("Usando palavras-chave padrão...")
        palavras_chave = PALAVRAS_CHAVE_PADRAO
    
    # Rodar buscas
    resultados = rodar_multiplas_buscas(
        palavras_chave,
        headless=args.headless,
        slow_wait=args.wait
    )
    
    # Salvar consolidado
    if resultados:
        salvar_consolidado(resultados)
    else:
        print("\n⚠️ Nenhum resultado encontrado em nenhuma busca.")


if __name__ == "__main__":
    main()
