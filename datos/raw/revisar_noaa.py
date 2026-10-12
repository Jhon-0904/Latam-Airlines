import csv
import glob
import os
from collections import Counter

archivos = sorted(glob.glob("noaa/estaciones/*.psv"))

if not archivos:
    print("No se encontraron archivos NOAA.")
    raise SystemExit(1)

for archivo in archivos:
    meses = Counter()
    fechas = []

    with open(archivo, "r", encoding="utf-8", errors="replace", newline="") as f:
        lector = csv.DictReader(f, delimiter="|")

        if not lector.fieldnames or "DATE" not in lector.fieldnames:
            print(f"\nERROR: no se encontró la columna DATE: {archivo}")
            continue

        for fila in lector:
            fecha = (fila.get("DATE") or "").strip()
            if len(fecha) >= 7:
                fechas.append(fecha)
                meses[fecha[:7]] += 1

    print(f"\nArchivo: {os.path.basename(archivo)}")
    print(f"Primera fecha: {min(fechas) if fechas else 'Sin datos'}")
    print(f"Última fecha:  {max(fechas) if fechas else 'Sin datos'}")
    print(f"Registros:     {sum(meses.values()):,}")
    print("Registros por mes:")
    for mes, cantidad in sorted(meses.items()):
        if mes in ("2025-12", "2026-01"):
            print(f"  {mes}: {cantidad:,}")
