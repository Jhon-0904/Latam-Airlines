from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from statistics import median

import pandas as pd

parquet = Path("datos/processed/integrated/dataset_integrado_semana7.parquet")

if not parquet.exists():
    raise FileNotFoundError(f"No se encontró: {parquet}")

print("=" * 55)
print("BENCHMARK: PARQUET VS CSV")
print("=" * 55)

tiempos_parquet = []

for _ in range(3):
    inicio = perf_counter()
    df = pd.read_parquet(parquet)
    tiempos_parquet.append(perf_counter() - inicio)

filas, columnas = df.shape
tam_parquet = parquet.stat().st_size

print(f"Dataset: {filas:,} filas x {columnas} columnas")
print(f"Tamaño Parquet: {tam_parquet / 1024**2:.2f} MiB")
print(f"Lecturas Parquet: {[round(t, 3) for t in tiempos_parquet]} s")

with TemporaryDirectory() as tmp:
    csv = Path(tmp) / "dataset_completo.csv"
    parquet_temp = Path(tmp) / "dataset_completo.parquet"

    inicio = perf_counter()
    df.to_csv(csv, index=False)
    tiempo_escritura_csv = perf_counter() - inicio

    inicio = perf_counter()
    df.to_parquet(parquet_temp, index=False)
    tiempo_escritura_parquet = perf_counter() - inicio

    tiempos_csv = []

    for _ in range(3):
        inicio = perf_counter()
        df_csv = pd.read_csv(csv, low_memory=False)
        tiempos_csv.append(perf_counter() - inicio)
        del df_csv

    tam_csv = csv.stat().st_size

    print(f"\nTamaño CSV: {tam_csv / 1024**2:.2f} MiB")
    print(f"Escritura CSV: {tiempo_escritura_csv:.3f} s")
    print(f"Escritura Parquet: {tiempo_escritura_parquet:.3f} s")
    print(f"Lecturas CSV: {[round(t, 3) for t in tiempos_csv]} s")

    print("\nRESUMEN")
    print(f"Mediana lectura Parquet: {median(tiempos_parquet):.3f} s")
    print(f"Mediana lectura CSV: {median(tiempos_csv):.3f} s")
    print(f"Relación de tamaño CSV/Parquet: {tam_csv / tam_parquet:.2f}x")
    print(f"Ahorro de espacio con Parquet: {(1 - tam_parquet / tam_csv) * 100:.1f}%")

    print("\nLos archivos temporales se eliminarán automáticamente.")

print("\nBenchmark terminado.")
