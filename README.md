# Prototipo de alerta temprana de demoras de vuelos

## 1. Descripción

Proyecto académico de Big Data y analítica de datos para estudiar patrones asociados a las demoras de salida de vuelos y evaluar un modelo experimental de alerta temprana.

Se integran registros de puntualidad de vuelos del Bureau of Transportation Statistics (BTS) con observaciones meteorológicas históricas de NOAA.

**Importante:** los datos corresponden a vuelos de Estados Unidos. Se utilizan como base experimental y no representan operaciones reales de LATAM Airlines.

## 2. Objetivos

- Integrar información de vuelos y observaciones meteorológicas.
- Analizar patrones de demoras por aeropuerto, hora y visibilidad.
- Evaluar un modelo experimental para identificar demoras de salida de al menos 15 minutos.
- Medir el rendimiento de almacenamiento y lectura de Parquet frente a CSV.

## 3. Fuentes de datos

- BTS TranStats: https://www.transtats.bts.gov/
- NOAA Global Hourly: https://www.ncei.noaa.gov/products/land-based-station/global-hourly

Periodo analizado: diciembre de 2025 y enero de 2026.

El inventario de archivos, tamaños y hashes SHA-256 está en `outputs/evidencias/entrega_semana7/ficha_procedencia_datos.csv`. Las fechas de descarga no registradas y las condiciones de uso pendientes de verificación deben declararse como limitaciones.

## 4. Tecnologías

- Python
- pandas y NumPy
- scikit-learn
- matplotlib
- PyArrow y Parquet

El pipeline implementado utiliza pandas y scikit-learn. PySpark está instalado en el entorno, pero no forma parte del procesamiento ejecutado.

## 5. Estructura del proyecto

```text
aviacion_bigdata/
├── datos/
│   ├── raw/
│   │   ├── bts/
│   │   └── noaa/
│   └── processed/
│       └── integrated/
├── scripts/
├── outputs/
│   ├── metrics/
│   └── figures/
├── documentacion/
│   ├── arquitectura.md
│   └── fichas_procedencia_datos.md
├── requirements.txt
└── README.md
```

## 6. Preparación del entorno

Se recomienda Python 3.9 o una versión compatible con las dependencias registradas en `requirements.txt`.

Crear y activar un entorno virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Los archivos originales deben estar ubicados en las rutas descritas en las fichas de procedencia.

## 7. Ejecución del pipeline

Desde la raíz del repositorio:

```bash
python scripts/pipeline_semana7.py 2>&1 | tee outputs/metrics/ejecucion_pipeline_semana7.log
```

El pipeline integra los datos, genera el dataset procesado y registra resultados de la ejecución.

## 8. Resultados registrados

En la ejecución documentada se obtuvieron:

- 316,622 vuelos integrados.
- 40 columnas en el dataset final.
- 79,127 observaciones meteorológicas cargadas.
- 99.82% de coincidencia temporal meteorológica.
- 34.99% de vuelos con las variables meteorológicas principales completas.
- Tasa de demoras de al menos 15 minutos: 24.44%.

Dataset completo: `datos/processed/integrated/dataset_integrado_semana7.parquet`.

Los resultados pueden variar si cambian los datos, el entorno o las versiones de las herramientas.

## 9. Evidencias

- Métricas y resultados: `outputs/metrics/`
- Gráficos exploratorios: `outputs/figures/`
- Ficha de procedencia: `outputs/evidencias/entrega_semana7/ficha_procedencia_datos.csv`
- Arquitectura: `documentacion/arquitectura.md`
- Comparación Parquet y CSV: `outputs/metrics/benchmark_formatos.log`
- Prueba de escalabilidad: `outputs/metrics/prueba_escalabilidad_semana7.csv`

## 10. Limitaciones

El modelo evaluado es experimental y todavía presenta capacidad predictiva limitada. No debe utilizarse para tomar decisiones operativas reales sin validación adicional.

La prueba de escalabilidad disponible mide lecturas repetidas y agregaciones sobre Parquet; no representa una ejecución distribuida ni una medición completa del pipeline a escala 100 veces mayor.

## 11. Reproducibilidad y uso de IA

Las versiones de las dependencias se registran en `requirements.txt`. La declaración de uso de IA generativa se conservará como documento independiente y deberá ser revisada y firmada por todos los integrantes del equipo.