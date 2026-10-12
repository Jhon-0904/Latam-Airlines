import csv
import glob
import os
from collections import Counter

entrada = "noaa/estaciones"
salida = "noaa/procesados"

archivos = sorted(glob.glob(f"{entrada}/GHCNh_*_202[56].psv"))
estaciones = {}

for archivo in archivos:
    nombre = os.path.basename(archivo)
    estacion = nombre.split("_")[1]
    anio = nombre.split("_")[-1].split(".")[0]
    estaciones.setdefault(estacion, {})[anio] = archivo

meses_objetivo = {"2025-12", "2026-01"}

for estacion, archivos_anio in sorted(estaciones.items()):
    destino = os.path.join(
        salida, f"GHCNh_{estacion}_2025-12_2026-01.psv"
    )
    total = 0
    conteo_meses = Counter()
    cabecera_escrita = False

    with open(destino, "w", encoding="utf-8", newline="") as out:
        escritor = csv.writer(out, delimiter="|", lineterminator="\n")

        for anio in ("2025", "2026"):
            archivo = archivos_anio.get(anio)
            if not archivo:
                continue

            with open(
                archivo, "r", encoding="utf-8",
                errors="replace", newline=""
            ) as f:
                lector = csv.reader(f, delimiter="|")
                cabecera = next(lector, None)

                if not cabecera or "DATE" not in cabecera:
                    print(f"ERROR: no se encontró DATE en {archivo}")
                    continue

                indice_fecha = cabecera.index("DATE")

                if not cabecera_escrita:
                    escritor.writerow(cabecera)
                    cabecera_escrita = True

                for fila in lector:
                    if len(fila) <= indice_fecha:
                        continue

                    fecha = fila[indice_fecha].strip()
                    mes = fecha[:7]

                    if mes in meses_objetivo:
                        escritor.writerow(fila)
                        total += 1
                        conteo_meses[mes] += 1

    print(
        f"{estacion}: {total:,} registros | "
        f"diciembre 2025: {conteo_meses['2025-12']:,} | "
        f"enero 2026: {conteo_meses['2026-01']:,}"
    )
    print(f"  Archivo: {destino}")

print("\nProceso terminado.")
