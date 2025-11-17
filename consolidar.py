#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consolidador de CSVs de múltiplas buscas
Combina todos os imoveis_scraper_escalavel_*.csv em um único arquivo
"""

import sys
from pathlib import Path
from datetime import datetime

try:
    import pandas as pd
except ImportError:
    print("❌ pandas não instalado. Execute:")
    print("   pip install pandas")
    sys.exit(1)


def consolidar_csvs(output_dir="output"):
    """Consolida todos os CSVs de scraper em um único arquivo."""
    
    output_path = Path(output_dir)
    csv_files = sorted(output_path.glob("imoveis_scraper_escalavel_*.csv"))
    
    if not csv_files:
        print("❌ Nenhum CSV encontrado em output/")
        return False
    
    print(f"📁 Consolidando {len(csv_files)} arquivo(s)...")
    
    # Ler todos os CSVs
    dfs = []
    total_rows = 0
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, encoding='utf-8')
            dfs.append(df)
            total_rows += len(df)
            print(f"  ✓ {csv_file.name}: {len(df)} linhas")
        except Exception as e:
            print(f"  ❌ Erro ao ler {csv_file.name}: {e}")
            continue
    
    if not dfs:
        print("❌ Erro ao ler CSVs")
        return False
    
    # Concatenar
    df_consolidated = pd.concat(dfs, ignore_index=True)
    
    # Remover duplicatas por link
    df_consolidated = df_consolidated.drop_duplicates(subset=['link'], keep='first')
    
    # Ordenar por data_coleta
    df_consolidated['data_coleta'] = pd.to_datetime(df_consolidated['data_coleta'], errors='coerce')
    df_consolidated = df_consolidated.sort_values('data_coleta', ascending=False)
    
    # Salvar
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_path / f"imoveis_consolidado_{timestamp}.csv"
    
    df_consolidated.to_csv(output_file, index=False, encoding='utf-8')
    
    print(f"\n{'='*70}")
    print(f"✅ CONSOLIDAÇÃO CONCLUÍDA")
    print(f"{'='*70}")
    print(f"Arquivo: {output_file.name}")
    print(f"Total de linhas originais: {total_rows}")
    print(f"Total após remover duplicatas: {len(df_consolidated)}")
    print(f"Domínios: {df_consolidated['fonte'].nunique()}")
    print(f"\nPor domínio:")
    for fonte, count in df_consolidated['fonte'].value_counts().items():
        print(f"  {fonte}: {count}")
    
    print(f"\nCobertura de dados:")
    for col in ['preco', 'endereco', 'cidade', 'cep', 'contato']:
        filled = (df_consolidated[col].notna() & (df_consolidated[col] != '')).sum()
        pct = (filled / len(df_consolidated) * 100) if len(df_consolidated) > 0 else 0
        print(f"  {col}: {pct:.1f}% ({filled}/{len(df_consolidated)})")
    
    return True


if __name__ == '__main__':
    consolidar_csvs()
