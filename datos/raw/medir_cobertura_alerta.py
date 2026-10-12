import csv
import glob
import os
from bisect import bisect_right
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc
MAX_ANTIGUEDAD_MIN = 60

ESTACIONES = {
    "DEN": "USW00003017",
    "DFW": "USW00003927",
    "MCO": "USW00012815",
    "ATL": "USW00013874",
    "CLT": "USW00013881",
    "LAS": "USW00023169",
    "LAX": "USW00023174",
    "PHX": "USW00023183",
    "SEA": "USW00024233",
}

ZONAS = {
    "DEN": "America/Denver",
    "DFW": "America/Chicago",
    "MCO": "America/New_York",
    "ATL": "America/New_York",
    "CLT": "America/New_York",
    "LAS": "America/Los_Angeles",
    "LAX": "America/Los_Angeles",
    "PHX": "America/Phoenix",
    "SEA": "America/Los_Angeles",
}

VARIABLES = [
    "temperature",
    "dew_point_temperature",
    "relative_humidity",
    "wind_speed",
    "wind_direction",
    "visibility",
    "sea_level_pressure",
    "precipitation",
    "wind_gust",
    "sky_condition",
]

VARIABLES_CLAVE = [
    "temperature",
    "dew_point_temperature",
    "wind_speed",
    "visibility",
    "sea_level_pressure",
]

def numero(valor):
    try:
        return float((valor or "").strip())
    except (ValueError, TypeError):
        return None

def fecha_noaa(valor):
    valor = (valor or "").strip()
    if not valor:
        return None
    dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)

def hora_programada(fecha, hora, zona):
    fecha = (fecha or "").strip()
    hora = (hora or "").strip()

    if not fecha or not hora:
        return None

    # BTS normalmente usa HHMM; también toleramos valores como 700.00.
    if hora.endswith(".00"):
        hora = hora[:-3]
    hora = hora.zfill(4)

    try:
        hh = int(hora[:-2])
        mm = int(hora[-2:])

        dia = datetime.strptime(fecha, "%Y-%m-%d").date()

        # Algunas fuentes representan medianoche como 2400.
        if hh == 24 and mm == 0:
            dia += timedelta(days=1)
            hh = 0

        if hh > 23 or mm > 59:
            return None

        local = datetime(
            dia.year, dia.month, dia.day, hh, mm,
            tzinfo=ZoneInfo(zona)
        )
        return local
    except (ValueError, OverflowError):
        return None

# 1. Cargar observaciones meteorológicas por estación y variable.
# Se conservan valores no vacíos; los códigos de calidad aún no se filtran.
clima = defaultdict(lambda: {"tiempos": [], "valores": []})

archivos_noaa = sorted(
    glob.glob("noaa/procesados/GHCNh_*.psv")
)

print("Cargando observaciones NOAA...")

for archivo in archivos_noaa:
    nombre = os.path.basename(archivo)
    partes = nombre.split("_")
    if len(partes) < 2:
        continue

    estacion = partes[1]

    with open(archivo, encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f, delimiter="|")

        for fila in lector:
            dt = fecha_noaa(fila.get("DATE"))
            if dt is None:
                continue

            for variable in VARIABLES:
                valor = (fila.get(variable) or "").strip()
                if not valor:
                    continue

                # 999 no es una dirección válida del viento.
                if variable == "wind_direction" and numero(valor) == 999:
                    continue

                clave = (estacion, variable)
                clima[clave]["tiempos"].append(dt)
                clima[clave]["valores"].append(valor)

# Ordenar cada serie temporal para búsquedas eficientes.
for serie in clima.values():
    pares = sorted(zip(serie["tiempos"], serie["valores"]))
    serie["tiempos"] = [p[0] for p in pares]
    serie["valores"] = [p[1] for p in pares]

print("Estaciones NOAA cargadas:", len(archivos_noaa))

# 2. Recorrer los vuelos con aeropuerto, horario y target utilizables.
archivos_bts = sorted(
    glob.glob(
        "bts/extraidos/**/*.csv",
        recursive=True
    )
)

if not archivos_bts:
    raise SystemExit("ERROR: no se encontraron CSV BTS.")

conteos = defaultdict(lambda: {
    "vuelos": 0,
    "con_alguna_variable": 0,
    "con_todas_variables_clave": 0,
    "por_variable": defaultdict(int),
})

total_vuelos = 0
total_con_alguna = 0
total_con_todas = 0
total_por_variable = defaultdict(int)
saltados_horario = 0
saltados_target = 0

print("Midiendo cobertura de vuelos...")

for archivo in archivos_bts:
    print("Procesando:", os.path.basename(archivo))

    with open(archivo, encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)

        for fila in lector:
            origen = (fila.get("Origin") or "").strip().upper()

            if origen not in ESTACIONES:
                continue

            # Excluir cancelados, desviados y vuelos sin target disponible.
            cancelado = numero(fila.get("Cancelled"))
            desviado = numero(fila.get("Diverted"))
            retraso = numero(fila.get("DepDelay"))

            if (
                cancelado != 0
                or desviado != 0
                or retraso is None
            ):
                saltados_target += 1
                continue

            local = hora_programada(
                fila.get("FlightDate"),
                fila.get("CRSDepTime"),
                ZONAS[origen],
            )

            if local is None:
                saltados_horario += 1
                continue

            # La alerta se emite dos horas antes de la salida programada.
            corte_utc = (local - timedelta(hours=2)).astimezone(UTC)
            estacion = ESTACIONES[origen]

            disponibles = {}

            for variable in VARIABLES:
                serie = clima.get((estacion, variable))
                if not serie:
                    disponibles[variable] = False
                    continue

                tiempos = serie["tiempos"]
                i = bisect_right(tiempos, corte_utc) - 1

                if i < 0:
                    disponibles[variable] = False
                    continue

                antiguedad = (
                    corte_utc - tiempos[i]
                ).total_seconds() / 60

                disponibles[variable] = (
                    0 <= antiguedad <= MAX_ANTIGUEDAD_MIN
                )

            total_vuelos += 1
            conteos[origen]["vuelos"] += 1

            tiene_alguna = any(disponibles.values())
            tiene_clave = all(
                disponibles[v] for v in VARIABLES_CLAVE
            )

            if tiene_alguna:
                total_con_alguna += 1
                conteos[origen]["con_alguna_variable"] += 1

            if tiene_clave:
                total_con_todas += 1
                conteos[origen]["con_todas_variables_clave"] += 1

            for variable, disponible in disponibles.items():
                if disponible:
                    total_por_variable[variable] += 1
                    conteos[origen]["por_variable"][variable] += 1

# 3. Guardar resumen por aeropuerto y variable.
salida = "noaa/procesados/cobertura_alerta_2h.csv"
filas_salida = []

for aeropuerto in sorted(conteos):
    c = conteos[aeropuerto]
    n = c["vuelos"]

    filas_salida.append({
        "aeropuerto": aeropuerto,
        "estacion_noaa": ESTACIONES[aeropuerto],
        "vuelos_evaluados": n,
        "con_alguna_variable": c["con_alguna_variable"],
        "porcentaje_con_alguna_variable": round(
            100 * c["con_alguna_variable"] / n, 2
        ) if n else 0,
        "con_todas_variables_clave": c["con_todas_variables_clave"],
        "porcentaje_con_todas_variables_clave": round(
            100 * c["con_todas_variables_clave"] / n, 2
        ) if n else 0,
        **{
            "pct_" + v: round(
                100 * c["por_variable"][v] / n, 2
            ) if n else 0
            for v in VARIABLES
        }
    })

if filas_salida:
    with open(salida, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(
            f, fieldnames=list(filas_salida[0].keys())
        )
        escritor.writeheader()
        escritor.writerows(filas_salida)

print("\nCOBERTURA NOAA EN EL INSTANTE DE ALERTA")
print("=" * 100)
print("Vuelos evaluados:", f"{total_vuelos:,}")
print("Vuelos sin target usable o cancelados/desviados:", f"{saltados_target:,}")
print("Vuelos omitidos por horario inválido:", f"{saltados_horario:,}")

if total_vuelos:
    print(
        "Con al menos una variable:",
        f"{total_con_alguna:,}",
        f"({100 * total_con_alguna / total_vuelos:.2f}%)"
    )
    print(
        "Con todas las variables clave:",
        f"{total_con_todas:,}",
        f"({100 * total_con_todas / total_vuelos:.2f}%)"
    )

print("\nCobertura por variable:")
for v in VARIABLES:
    n = total_por_variable[v]
    print(
        f"  {v:<25} {n:>9,} "
        f"({100 * n / total_vuelos:.2f}%)"
        if total_vuelos else f"  {v:<25} 0"
    )

print("\nCobertura por aeropuerto:")
for r in filas_salida:
    print(
        f"  {r['aeropuerto']} | vuelos={r['vuelos_evaluados']:,} | "
        f"alguna={r['porcentaje_con_alguna_variable']:.2f}% | "
        f"todas las clave={r['porcentaje_con_todas_variables_clave']:.2f}%"
    )

print("\nArchivo generado:", salida)
print(
    "\nIMPORTANTE: cobertura preliminar por presencia del valor y antigüedad. "
    "Todavía no aplica todos los controles de calidad NOAA."
)
print(
    "Las alertas cercanas al inicio de diciembre pueden no tener observaciones "
    "porque los archivos actuales empiezan en diciembre."
)
