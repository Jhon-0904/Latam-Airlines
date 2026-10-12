import csv
import glob
import os
from collections import Counter

archivos = sorted(
    glob.glob("bts/extraidos/**/*.csv", recursive=True)
)

if not archivos:
    raise SystemExit(
        "ERROR: no se encontraron CSV en bts/extraidos/"
    )

campos_interes = [
    "FlightDate",
    "Reporting_Airline",
    "Origin",
    "Dest",
    "CRSDepTime",
    "DepTime",
    "DepDelay",
    "Cancelled",
    "Diverted",
]

total = 0
aeropuertos = Counter()
horas = Counter()
fechas = Counter()
cancelados = 0
desviados = 0
sin_retraso = 0
horas_invalidas = 0
muestras = []

for archivo in archivos:
    print(f"\nArchivo: {os.path.basename(archivo)}")

    with open(
        archivo, "r", encoding="utf-8-sig",
        errors="replace", newline=""
    ) as f:
        lector = csv.DictReader(f)
        columnas = lector.fieldnames or []

        faltantes = [
            c for c in campos_interes if c not in columnas
        ]
        if faltantes:
            print("Columnas no encontradas:", faltantes)
            continue

        filas_archivo = 0

        for fila in lector:
            total += 1
            filas_archivo += 1

            origen = (fila.get("Origin") or "").strip()
            fecha = (fila.get("FlightDate") or "").strip()
            hora = (fila.get("CRSDepTime") or "").strip()

            if origen:
                aeropuertos[origen] += 1
            if fecha:
                fechas[fecha[:7]] += 1

            if hora:
                try:
                    h = int(hora)
                    if h < 0 or h > 2359 or h % 100 >= 60:
                        horas_invalidas += 1
                    else:
                        horas[(hora.zfill(4)[:2])] += 1
                except ValueError:
                    horas_invalidas += 1
            else:
                horas_invalidas += 1

            try:
                cancelados += float(fila["Cancelled"] or 0) != 0
            except ValueError:
                pass

            try:
                desviados += float(fila["Diverted"] or 0) != 0
            except ValueError:
                pass

            if not (fila.get("DepDelay") or "").strip():
                sin_retraso += 1

            if origen in {
                "DEN", "DFW", "MCO", "ATL", "CLT",
                "LAS", "LAX", "PHX", "SEA"
            } and len(muestras) < 12:
                muestras.append({
                    c: fila.get(c, "") for c in campos_interes
                })

        print(f"Filas leídas: {filas_archivo:,}")
        print(f"Columnas: {len(columnas)}")

print("\n" + "=" * 65)
print("RESUMEN BTS")
print("=" * 65)
print(f"Total de vuelos: {total:,}")
print("Meses:", dict(sorted(fechas.items())))
print(f"Vuelos cancelados: {cancelados:,}")
print(f"Vuelos desviados: {desviados:,}")
print(f"Vuelos sin DepDelay: {sin_retraso:,}")
print(f"CRSDepTime vacío o inválido: {horas_invalidas:,}")

print("\nAeropuertos mapeados:")
for aeropuerto in [
    "DEN", "DFW", "MCO", "ATL", "CLT",
    "LAS", "LAX", "PHX", "SEA"
]:
    print(f"  {aeropuerto}: {aeropuertos[aeropuerto]:,} vuelos")

print("\nEjemplos de vuelos mapeados:")
for fila in muestras:
    print(fila)
