import csv
import glob
import os

archivos = sorted(glob.glob("noaa/procesados/*.psv"))

if not archivos:
    print("ERROR: no se encontraron archivos NOAA procesados.")
    raise SystemExit(1)

# Basta con inspeccionar la primera estación para conocer el esquema.
archivo = archivos[0]

print("Archivo:", os.path.basename(archivo))

with open(archivo, "r", encoding="utf-8", errors="replace", newline="") as f:
    lector = csv.reader(f, delimiter="|")
    cabecera = next(lector, [])
    primera_fila = next(lector, [])

print(f"\nTotal de columnas NOAA: {len(cabecera)}")
print("\nColumnas y valores de la primera observación:")

for i, nombre in enumerate(cabecera):
    valor = primera_fila[i] if i < len(primera_fila) else ""
    print(f"{i:3} | {nombre} | {valor}")

print("\nEstaciones procesadas:", len(archivos))
