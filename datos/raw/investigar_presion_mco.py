import csv
import glob
import os
from collections import Counter, defaultdict

archivos = glob.glob(
    "noaa/procesados/GHCNh_USW00012815_*.psv"
)

if not archivos:
    raise SystemExit("No se encontró el archivo NOAA de MCO.")

total = 0
con_presion = 0
por_mes = defaultdict(lambda: Counter())
por_reporte = defaultdict(lambda: Counter())
por_fuente = defaultdict(lambda: Counter())
calidad = Counter()
valores = []
fechas = []

with open(archivos[0], encoding="utf-8-sig", newline="") as f:
    lector = csv.DictReader(f, delimiter="|")
    columnas = lector.fieldnames or []

    print("Columnas relacionadas con presión, fuente o reporte:")
    for columna in columnas:
        if any(x in columna.lower() for x in (
            "sea_level_pressure", "report_type",
            "source", "station_id"
        )):
            print(" ", columna)

    for fila in lector:
        total += 1

        fecha = (fila.get("DATE") or "").strip()
        mes = fecha[:7] if fecha else "SIN_FECHA"
        presion = (fila.get("sea_level_pressure") or "").strip()

        reporte = (
            fila.get("REPORT_TYPE")
            or fila.get("REPORT_TYPE_SOURCE")
            or "NO_DISPONIBLE"
        ).strip()

        fuente = (
            fila.get("SOURCE")
            or fila.get("SOURCE_CODE")
            or "NO_DISPONIBLE"
        ).strip()

        estacion_origen = (
            fila.get("SOURCE_STATION_ID")
            or fila.get("SOURCE_ID")
            or "NO_DISPONIBLE"
        ).strip()

        por_mes[mes]["total"] += 1
        por_reporte[reporte]["total"] += 1
        por_fuente[fuente]["total"] += 1

        if presion:
            con_presion += 1
            por_mes[mes]["con_presion"] += 1
            por_reporte[reporte]["con_presion"] += 1
            por_fuente[fuente]["con_presion"] += 1

            qc = (
                fila.get("sea_level_pressure_Quality_Code") or ""
            ).strip()
            calidad[qc if qc else "(vacío)"] += 1

            try:
                valores.append(float(presion))
            except ValueError:
                pass

            if fecha:
                fechas.append(fecha)

print("\nRESUMEN GENERAL MCO")
print("=" * 65)
print("Archivo:", os.path.basename(archivos[0]))
print("Registros:", total)
print("Registros con presión:", con_presion)
print("Cobertura de presión:", round(100 * con_presion / total, 2), "%")
print("Códigos de calidad:", dict(calidad))

if valores:
    print("Presión mínima observada:", min(valores))
    print("Presión máxima observada:", max(valores))

if fechas:
    print("Primera fecha con presión:", min(fechas))
    print("Última fecha con presión:", max(fechas))

print("\nPOR MES")
for mes, c in sorted(por_mes.items()):
    pct = 100 * c["con_presion"] / c["total"] if c["total"] else 0
    print(f"{mes}: {c['con_presion']}/{c['total']} ({pct:.2f}%)")

print("\nPOR TIPO DE REPORTE")
for nombre, c in sorted(
    por_reporte.items(),
    key=lambda x: x[1]["total"],
    reverse=True
):
    pct = 100 * c["con_presion"] / c["total"] if c["total"] else 0
    print(f"{nombre}: {c['con_presion']}/{c['total']} ({pct:.2f}%)")

print("\nPOR FUENTE")
for nombre, c in sorted(
    por_fuente.items(),
    key=lambda x: x[1]["total"],
    reverse=True
):
    pct = 100 * c["con_presion"] / c["total"] if c["total"] else 0
    print(f"{nombre}: {c['con_presion']}/{c['total']} ({pct:.2f}%)")
