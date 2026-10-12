import csv
import glob
import os
from collections import Counter

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

salida = "noaa/procesados/auditoria_calidad_noaa.csv"
resultados = []

for archivo in sorted(glob.glob("noaa/procesados/GHCNh_*.psv")):
    nombre = os.path.basename(archivo)

    with open(archivo, encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f, delimiter="|")
        columnas = set(lector.fieldnames or [])

        variables_archivo = [
            v for v in VARIABLES if v in columnas
        ]

        total = 0
        contadores = {
            v: {
                "con_valor": 0,
                "numericos": 0,
                "vacios": 0,
                "codigos_calidad": Counter(),
                "valores_especiales": 0,
            }
            for v in variables_archivo
        }

        for fila in lector:
            total += 1

            for v in variables_archivo:
                dato = (fila.get(v) or "").strip()
                calidad = (
                    fila.get(v + "_Quality_Code") or ""
                ).strip()

                c = contadores[v]

                if dato == "":
                    c["vacios"] += 1
                    continue

                c["con_valor"] += 1

                if calidad:
                    c["codigos_calidad"][calidad] += 1

                try:
                    numero = float(dato)
                    c["numericos"] += 1

                    # 999 significa dirección del viento variable
                    # o no informada; no es un ángulo válido.
                    if v == "wind_direction" and numero == 999:
                        c["valores_especiales"] += 1

                except ValueError:
                    pass

        for v, c in contadores.items():
            resultados.append({
                "archivo": nombre,
                "estacion": nombre.split("_")[1],
                "variable": v,
                "registros_totales": total,
                "registros_con_valor": c["con_valor"],
                "registros_vacios": c["vacios"],
                "porcentaje_con_valor": round(
                    100 * c["con_valor"] / total, 2
                ) if total else 0,
                "registros_numericos": c["numericos"],
                "valores_especiales_conocidos": c["valores_especiales"],
                "distribucion_codigos_calidad": ";".join(
                    f"{codigo}:{cantidad}"
                    for codigo, cantidad
                    in sorted(c["codigos_calidad"].items())
                ),
            })

os.makedirs(os.path.dirname(salida), exist_ok=True)

with open(salida, "w", encoding="utf-8", newline="") as f:
    campos = list(resultados[0].keys()) if resultados else []
    escritor = csv.DictWriter(f, fieldnames=campos)
    escritor.writeheader()
    escritor.writerows(resultados)

print("\nAUDITORÍA DE CALIDAD NOAA")
print("=" * 90)

for r in resultados:
    print(
        f"{r['estacion']} | {r['variable']:<24} | "
        f"con valor: {r['porcentaje_con_valor']:6.2f}% | "
        f"vacíos: {r['registros_vacios']:6} | "
        f"especiales conocidos: {r['valores_especiales_conocidos']:5}"
    )

print("\nArchivo generado:", salida)
print("Total de combinaciones estación-variable:", len(resultados))
print("\nNota: tener un valor no significa que haya superado los controles")
print("de calidad. Los códigos se conservan para interpretar sus reglas.")
