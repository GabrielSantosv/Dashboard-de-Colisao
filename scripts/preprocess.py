"""
Script de pré-processamento — roda UMA VEZ antes de iniciar o dashboard.

Uso:
    python scripts/preprocess.py

O que faz:
    Lê os CSVs brutos, executa todo o pipeline de limpeza e transformação,
    e salva o resultado em data/processed/accidents.parquet.

Na próxima vez que o dashboard iniciar, ele lê o parquet (~0.1s)
em vez de reprocessar os CSVs (~14s).
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from traffic_accidents.data import load_raw_accidents

OUTPUT = ROOT / "data" / "processed" / "accidents.parquet"


def main():
    print("Iniciando pré-processamento...")
    start = time.time()

    df = load_raw_accidents()
    elapsed_load = time.time() - start
    print(f"Pipeline concluído em {elapsed_load:.1f}s — {len(df):,} registros, {len(df.columns)} colunas")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    df_save = df.copy()
    for col in df_save.select_dtypes(["category"]).columns:
        df_save[col] = df_save[col].astype(str)

    df_save.to_parquet(OUTPUT, index=False, engine="pyarrow", compression="snappy")

    size_mb = OUTPUT.stat().st_size / 1024**2
    total = time.time() - start
    print(f"Salvo em: {OUTPUT}")
    print(f"Tamanho: {size_mb:.1f} MB")
    print(f"Tempo total: {total:.1f}s")
    print()
    print("Pronto! Na próxima inicialização o dashboard vai carregar em menos de 1 segundo.")


if __name__ == "__main__":
    main()
