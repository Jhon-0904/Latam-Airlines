from pathlib import Path
import time
import os

import pandas as pd
import psutil

BASE = Path("datos/processed/integrated/dataset_integrado_semana7.parquet")
SALIDA = Path("outputs/metrics/prueba_escalabilidad_semana7.csv")

COLUMNAS = ["delay_15", "dep_delay_minutes", "has_weather_match"]
FACTORES = [1, 10, 100]

if not BASE.exists():
    raise FileNotFoundError(f"No existe el dataset: {BASE}")

proceso = psutil.Process(os.getpid())
resultados = []

print("=" * 70)
print("PRUEBA DE ESCALABILIDAD REPRODUCIBLE")
print("Método: lectura y agregación repetida del Parquet real")
print("Nota: no equivale a ejecutar 100 veces todo el pipeline BTS + NOAA.")
print("=" * 70)

# Una lectura inicial para validar columnas y obtener el tamaño real.
base = pd.read_parquet(BASE, columns=COLUMNAS)
n = len(base)
if n == 0:
    raise ValueError("El dataset no contiene filas.")

print(f"Filas del dataset real: {n:,}")
print(f"Columnas medidas: {', '.join(COLUMNAS)}")
del base

for factor in FACTORES:
    inicio = time.perf_counter()
    filas = 0
    demoras = 0
    suma_demora = 0.0
    vuelos_con_clima = 0

    for _ in range(factor):
        df = pd.read_parquet(BASE, columns=COLUMNAS)

        filas += len(df)
        demoras += int(df["delay_15"].fillna(0).sum())
        suma_demora += float(df["dep_delay_minutes"].fillna(0).sum())
        vuelos_con_clima += int(df["has_weather_match"].fillna(False).astype(bool).sum())

        del df

    segundos = time.perf_counter() - inicio
    memoria_gb = proceso.memory_info().rss / (1024 ** 3)

    resultado = {
        "factor": factor,
        "filas_logicas_procesadas": filas,
        "lecturas_dataset": factor,
        "tiempo_segundos": round(segundos, 3),
        "memoria_proceso_gb_fin": round(memoria_gb, 3),
        "tasa_demora_15": round(100 * demoras / filas, 2),
        "demora_promedio": round(suma_demora / filas, 2),
        "clima_t_2h": round(100 * vuelos_con_clima / filas, 2),
        "metodo": "lectura_parquet_y_agregacion_repetida"
    }
    resultados.append(resultado)

    print(
        f"Factor {factor:>3}x | "
        f"filas lógicas: {filas:,} | "
        f"tiempo: {segundos:.3f} s | "
        f"RAM final: {memoria_gb:.3f} GB"
    )

SALIDA.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(resultados).to_csv(SALIDA, index=False)

print("\nResultados guardados en:", SALIDA)
print("\nCSV generado:")
print(pd.DataFrame(resultados).to_string(index=False))
