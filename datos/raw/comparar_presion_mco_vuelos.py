import csv
import glob
from bisect import bisect_right
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ESTACION = "USW00012815"
ZONA = ZoneInfo("America/New_York")
VARIABLES = ["sea_level_pressure", "altimeter"]
MAX_EDAD = timedelta(minutes=60)

archivo_noaa = glob.glob(
    f"noaa/procesados/GHCNh_{ESTACION}_*.psv"
)[0]

observaciones = {v: [] for v in VARIABLES}

with open(archivo_noaa, encoding="utf-8-sig", newline="") as f:
    for fila in csv.DictReader(f, delimiter="|"):
        fecha = (fila.get("DATE") or "").strip()
        if not fecha:
            continue

        instante = datetime.fromisoformat(fecha).replace(
            tzinfo=timezone.utc
        )

        for variable in VARIABLES:
            valor = (fila.get(variable) or "").strip()
            if valor:
                observaciones[variable].append(
                    (instante, valor)
                )

for variable in VARIABLES:
    observaciones[variable].sort(key=lambda x: x[0])

tiempos = {
    v: [registro[0] for registro in observaciones[v]]
    for v in VARIABLES
}

resultados = defaultdict(
    lambda: {
        "vuelos": 0,
        "sea_level_pressure": 0,
        "altimeter": 0,
    }
)

archivos_bts = glob.glob(
    "bts/extraidos/**/*.csv", recursive=True
)

for archivo in archivos_bts:
    with open(archivo, encoding="utf-8-sig", newline="") as f:
        for fila in csv.DictReader(f):
            if fila.get("Origin", "").strip() != "MCO":
                continue

            if fila.get("Cancelled", "").strip() not in ("0", "0.0", "0.00"):
                continue
            if fila.get("Diverted", "").strip() not in ("0", "0.0", "0.00"):
                continue
            if not (fila.get("DepDelay") or "").strip():
                continue

            fecha = (fila.get("FlightDate") or "").strip()
            hora = (fila.get("CRSDepTime") or "").strip()

            if not fecha or not hora:
                continue

            try:
                hora = hora.zfill(4)
                salida_local = datetime.strptime(
                    fecha + hora, "%Y-%m-%d%H%M"
                ).replace(tzinfo=ZONA)

                corte = (
                    salida_local - timedelta(hours=2)
                ).astimezone(timezone.utc)
            except ValueError:
                continue

            mes = fecha[:7]
            resultados[mes]["vuelos"] += 1

            for variable in VARIABLES:
                lista_tiempos = tiempos[variable]
                posicion = bisect_right(lista_tiempos, corte) - 1

                if posicion < 0:
                    continue

                edad = corte - lista_tiempos[posicion]

                if timedelta(0) <= edad <= MAX_EDAD:
                    resultados[mes][variable] += 1

print("COBERTURA DE PRESIÓN EN VUELOS MCO")
print("Criterio: última observación anterior al corte, máximo 60 min")
print("=" * 78)

totales = defaultdict(int)

for mes in sorted(resultados):
    r = resultados[mes]
    n = r["vuelos"]
    if not n:
        continue

    print(f"\n{mes} | vuelos evaluados: {n}")

    for variable in VARIABLES:
        cantidad = r[variable]
        porcentaje = 100 * cantidad / n
        print(f"  {variable}: {cantidad}/{n} ({porcentaje:.2f}%)")
        totales[variable] += cantidad

n_total = sum(r["vuelos"] for r in resultados.values())
print(f"\nTOTAL | vuelos evaluados: {n_total}")

for variable in VARIABLES:
    cantidad = totales[variable]
    porcentaje = 100 * cantidad / n_total if n_total else 0
    print(f"  {variable}: {cantidad}/{n_total} ({porcentaje:.2f}%)")
