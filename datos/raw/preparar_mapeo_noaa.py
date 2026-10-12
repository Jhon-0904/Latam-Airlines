import csv
import glob
import os
from datetime import datetime
from statistics import median

# Aeropuerto BTS -> estación NOAA más cercana seleccionada
mapeo = [
    ("DEN", "USW00003017"),
    ("DFW", "USW00003927"),
    ("MCO", "USW00012815"),
    ("ATL", "USW00013874"),
    ("CLT", "USW00013881"),
    ("LAS", "USW00023169"),
    ("LAX", "USW00023174"),
    ("PHX", "USW00023183"),
    ("SEA", "USW00024233"),
]

ruta_mapeo = "noaa/procesados/mapeo_aeropuerto_estacion.csv"

with open(ruta_mapeo, "w", newline="", encoding="utf-8") as f:
    escritor = csv.writer(f)
    escritor.writerow(["Origin", "STATION"])
    escritor.writerows(mapeo)

print("MAPEO AEROPUERTO-ESTACIÓN")
print("=" * 60)
for aeropuerto, estacion in mapeo:
    print(f"{aeropuerto} -> {estacion}")
print(f"\nArchivo creado: {ruta_mapeo}")

print("\nAUDITORÍA DE INTERVALOS ENTRE OBSERVACIONES")
print("=" * 60)

archivos = sorted(glob.glob("noaa/procesados/GHCNh_*.psv"))

for archivo in archivos:
    if "mapeo_" in os.path.basename(archivo):
        continue

    fechas = []
    with open(archivo, "r", encoding="utf-8",
              errors="replace", newline="") as f:
        lector = csv.DictReader(f, delimiter="|")
        for fila in lector:
            fecha = (fila.get("DATE") or "").strip()
            if fecha:
                try:
                    fechas.append(datetime.fromisoformat(fecha))
                except ValueError:
                    pass

    fechas.sort()
    intervalos = [
        (fechas[i] - fechas[i-1]).total_seconds() / 60
        for i in range(1, len(fechas))
    ]

    if intervalos:
        dentro_60 = sum(x <= 60 for x in intervalos)
        dentro_90 = sum(x <= 90 for x in intervalos)
        print(f"\n{os.path.basename(archivo)}")
        print(f"  Observaciones: {len(fechas):,}")
        print(f"  Intervalo mediano: {median(intervalos):.1f} minutos")
        print(f"  Intervalos <= 60 min: {dentro_60 / len(intervalos) * 100:.1f}%")
        print(f"  Intervalos <= 90 min: {dentro_90 / len(intervalos) * 100:.1f}%")
