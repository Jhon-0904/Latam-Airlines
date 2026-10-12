import csv
import math
from pathlib import Path
from collections import Counter

base = Path.home() / "aviacion_bigdata" / "datos" / "raw"

archivos = [
    base / "bts/extraidos/2025_12/On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)_2025_12.csv",
    base / "bts/extraidos/2026_01/On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)_2026_1.csv",
]

conteo = Counter()

for archivo in archivos:
    print("Leyendo:", archivo.name)
    with archivo.open(encoding="utf-8-sig", newline="") as f:
        for fila in csv.DictReader(f):
            origen = (fila.get("Origin") or "").strip()
            if origen:
                conteo[origen] += 1

aeropuertos = {}

with (base / "noaa/catalogo/airports.csv").open(
    encoding="utf-8-sig", newline=""
) as f:
    for fila in csv.DictReader(f):
        if fila.get("iso_country") != "US":
            continue
        codigo = (fila.get("iata_code") or "").strip()
        try:
            lat = float(fila["latitude_deg"])
            lon = float(fila["longitude_deg"])
        except (ValueError, KeyError):
            continue
        if codigo:
            aeropuertos[codigo] = (
                lat, lon, fila.get("name", "Sin nombre")
            )

estaciones = []

with (base / "noaa/catalogo/ghcnh-station-list.txt").open(
    encoding="utf-8", errors="replace"
) as f:
    for linea in f:
        partes = linea.split()
        if len(partes) < 4 or partes[-1] != "US":
            continue
        try:
            sid = partes[0]
            lat = float(partes[1])
            lon = float(partes[2])
        except ValueError:
            continue
        nombre = " ".join(partes[4:-1])
        estaciones.append((sid, lat, lon, nombre))

def distancia_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))

print("\n10 AEROPUERTOS CON MÁS VUELOS Y ESTACIONES CERCANAS\n")

mostrados = 0

for codigo, cantidad in conteo.most_common():
    if codigo not in aeropuertos:
        continue

    lat, lon, nombre = aeropuertos[codigo]
    cercana = min(
        estaciones,
        key=lambda e: distancia_km(lat, lon, e[1], e[2]),
        default=None,
    )

    print(f"{codigo} | {cantidad:,} vuelos | {nombre}")

    if cercana:
        km = distancia_km(lat, lon, cercana[1], cercana[2])
        print(f"  Estación cercana: {cercana[0]} | {km:.1f} km")
    else:
        print("  No se encontraron estaciones NOAA de EE. UU.")

    mostrados += 1
    if mostrados >= 10:
        break

print(f"\nEstaciones NOAA de EE. UU. leídas: {len(estaciones)}")
print("Proceso terminado.")
