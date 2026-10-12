from pathlib import Path
import csv
import hashlib

BASE = Path(".")
SALIDA = BASE / "outputs/evidencias/entrega_semana7/ficha_procedencia_datos.csv"

FUENTES = [
    {
        "directorio": BASE / "datos/raw/bts",
        "proveedor": "Bureau of Transportation Statistics (BTS)",
        "url": "https://www.transtats.bts.gov/",
        "uso": "Datos de vuelos y demoras; periodos diciembre de 2025 y enero de 2026.",
    },
    {
        "directorio": BASE / "datos/raw/noaa",
        "proveedor": "NOAA National Centers for Environmental Information (NCEI)",
        "url": "https://www.ncei.noaa.gov/",
        "uso": "Observaciones meteorológicas históricas GHCNh de estaciones asociadas a los aeropuertos.",
    },
]

def sha256_archivo(ruta):
    digest = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()

SALIDA.parent.mkdir(parents=True, exist_ok=True)
filas = []

for fuente in FUENTES:
    directorio = fuente["directorio"]
    if not directorio.exists():
        continue

    for ruta in sorted(directorio.rglob("*")):
        if not ruta.is_file():
            continue

        filas.append({
            "proveedor": fuente["proveedor"],
            "url_fuente": fuente["url"],
            "uso_en_proyecto": fuente["uso"],
            "ruta_relativa": str(ruta),
            "formato": ruta.suffix.lower() or "sin extensión",
            "tamano_bytes": ruta.stat().st_size,
            "sha256": sha256_archivo(ruta),
            "fecha_descarga": "No registrada; pendiente de documentar",
        })

campos = [
    "proveedor", "url_fuente", "uso_en_proyecto", "ruta_relativa",
    "formato", "tamano_bytes", "sha256", "fecha_descarga"
]

with SALIDA.open("w", newline="", encoding="utf-8-sig") as archivo:
    escritor = csv.DictWriter(archivo, fieldnames=campos)
    escritor.writeheader()
    escritor.writerows(filas)

print(f"Ficha generada: {SALIDA}")
print(f"Archivos inventariados: {len(filas)}")
print("La fecha de descarga queda explícitamente pendiente cuando no existe evidencia.")
