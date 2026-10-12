import csv
import glob
import os
from collections import Counter

archivos = sorted(glob.glob("noaa/procesados/*.psv"))

if not archivos:
    raise SystemExit("ERROR: no se encontraron archivos NOAA procesados.")

variables = [
    "temperature",
    "dew_point_temperature",
    "relative_humidity",
    "wind_speed",
    "wind_direction",
    "wind_gust",
    "visibility",
    "sea_level_pressure",
    "precipitation",
    "sky_condition",
]

print("AUDITORÍA DE CALIDAD NOAA")
print("=" * 75)

total_general = 0

for archivo in archivos:
    filas = 0
    vacios = Counter()
    ejemplos = {v: Counter() for v in variables}
    fechas = []
    columnas = None

    with open(archivo, "r", encoding="utf-8",
              errors="replace", newline="") as f:
        lector = csv.DictReader(f, delimiter="|")
        columnas = lector.fieldnames or []

        for fila in lector:
            filas += 1

            if fila.get("DATE") and len(fechas) < 2:
                fechas.append(fila["DATE"])

            for variable in variables:
                valor = (fila.get(variable) or "").strip()

                if not valor:
                    vacios[variable] += 1
                elif len(ejemplos[variable]) < 8:
                    ejemplos[variable][valor] += 1

    total_general += filas

    print(f"\nArchivo: {os.path.basename(archivo)}")
    print(f"Filas: {filas:,}")
    print(f"Columnas: {len(columnas)}")
    print(f"Fechas de ejemplo: {fechas}")

    print("\nVariable | Vacíos (%) | Ejemplos de valores")
    for variable in variables:
        porcentaje = (vacios[variable] / filas * 100) if filas else 0
        muestra = ", ".join(ejemplos[variable].keys()) or "Sin valores"
        print(f"{variable} | {porcentaje:.1f}% | {muestra}")

print("\n" + "=" * 75)
print(f"TOTAL DE OBSERVACIONES NOAA: {total_general:,}")
print(f"TOTAL DE ARCHIVOS: {len(archivos)}")
