import csv
import glob
import os

archivos = sorted(glob.glob("bts/extraidos/*/*.csv"))

if not archivos:
    print("ERROR: No se encontraron archivos CSV en bts/extraidos/")
    raise SystemExit(1)

claves = [
    "FlightDate",
    "Reporting_Airline",
    "Origin",
    "Dest",
    "CRSDepTime",
    "DepTime",
    "DepDelay",
    "ArrDelay",
    "Cancelled",
    "Diverted",
]

for archivo in archivos:
    print("\n" + "=" * 70)
    print("ARCHIVO:", os.path.basename(archivo))

    with open(archivo, "r", encoding="utf-8-sig", newline="") as f:
        lector = csv.reader(f)
        cabecera = next(lector, None)

        if not cabecera:
            print("Archivo vacío.")
            continue

        indices = {
            nombre.strip(): i
            for i, nombre in enumerate(cabecera)
        }

        print("\nColumnas relevantes encontradas:")
        encontradas = []

        for clave in claves:
            if clave in indices:
                encontradas.append(clave)
                print(f"  {clave}")

        print(f"\nTotal de columnas: {len(cabecera)}")
        print("\nPrimeros 2 registros (solo columnas relevantes):")

        for numero, fila in enumerate(lector, start=1):
            if numero > 2:
                break

            for columna in encontradas:
                i = indices[columna]
                valor = fila[i] if i < len(fila) else ""
                print(f"  {columna}: {valor}")

print("\nRevisión terminada.")
