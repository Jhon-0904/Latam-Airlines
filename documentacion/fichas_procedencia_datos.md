# Fichas de procedencia de las fuentes de datos

**Proyecto:** Prototipo de alerta temprana de demoras de salida de vuelos  
**Periodo analizado:** diciembre de 2025 y enero de 2026  
**Fecha de registro de la ficha:** 11 de octubre de 2026  
**Entorno de procesamiento:** macOS, Python, pandas y scikit-learn  
**Almacenamiento procesado:** Parquet

## 1. Fuente BTS: operaciones y puntualidad de vuelos

| Campo | Descripción |
|---|---|
| Nombre de la fuente | On-Time Reporting Carrier / On-Time Performance |
| Organismo | Bureau of Transportation Statistics (BTS), Estados Unidos |
| Portal oficial | https://www.transtats.bts.gov/ |
| Periodo descargado | Diciembre de 2025 y enero de 2026 |
| Archivos originales comprimidos | `datos/raw/bts/vuelos_2025_12.zip` y `datos/raw/bts/vuelos_2026_1.zip` |
| Formato original | ZIP con archivos CSV |
| Tamaño de los ZIP | Aproximadamente 29 MB y 26 MB |
| Tamaño de los CSV extraídos | Aproximadamente 252 MB y 233 MB |
| Filas leídas en la ejecución del pipeline | 1,126,307 |
| Filas de vuelos en los aeropuertos seleccionados | 326,448 |
| Uso en el proyecto | Características del vuelo y construcción de la variable objetivo de demora |
| Diccionario de datos | Archivos `readme.html` incluidos junto a los CSV extraídos |

### Uso y transformación

Se seleccionaron registros de nueve aeropuertos de Estados Unidos. Se excluyeron vuelos cancelados y desviados, además de eliminar duplicados si existían. Se calcularon variables temporales y se construyó una etiqueta que identifica demoras de salida de al menos 15 minutos.

Resultados de la ejecución registrada:

- Registros leídos: 1,126,307.
- Registros de los aeropuertos seleccionados: 326,448.
- Vuelos cancelados excluidos: 9,027.
- Vuelos desviados excluidos: 799.
- Duplicados excluidos: 0.
- Registros elegibles integrados: 316,622.

**Limitación:** estos datos describen vuelos reportados en Estados Unidos y se utilizan como base experimental. No representan operaciones reales de LATAM Airlines.

## 2. Fuente NOAA: observaciones meteorológicas

| Campo | Descripción |
|---|---|
| Nombre de la fuente | Global Hourly / GHCNh |
| Organismo | National Centers for Environmental Information (NCEI), NOAA |
| Portal oficial | https://www.ncei.noaa.gov/products/land-based-station/global-hourly |
| Periodo utilizado | Diciembre de 2025 y enero de 2026 |
| Formato de los archivos procesados | PSV, campos separados por `|` |
| Archivos originales | Observaciones anuales por estación, bajo `datos/raw/noaa/estaciones/` |
| Archivos preparados para integración | `datos/raw/noaa/procesados/` |
| Observaciones cargadas por el pipeline | 79,127 |
| Uso en el proyecto | Incorporar observaciones meteorológicas disponibles antes del instante de alerta |

### Estaciones asociadas a los aeropuertos

| Aeropuerto | Código de estación NOAA |
|---|---|
| DEN | USW00003017 |
| DFW | USW00003927 |
| MCO | USW00012815 |
| ATL | USW00013874 |
| CLT | USW00013881 |
| LAS | USW00023169 |
| LAX | USW00023174 |
| PHX | USW00023183 |
| SEA | USW00024233 |

El archivo `datos/raw/noaa/procesados/mapeo_aeropuerto_estacion.csv` registra la asociación utilizada por el proyecto.

### Uso y transformación

Se seleccionaron observaciones de las estaciones asociadas a los nueve aeropuertos. Se normalizaron nombres de campos, se aplicaron controles de rangos físicos y se eliminaron duplicados por estación y marca temporal.

Para cada vuelo se definió un instante de alerta dos horas antes de la salida programada. Se vinculó la observación más reciente que no fuera posterior a dicho instante, con una tolerancia máxima de 60 minutos.

El pipeline generó un dataset integrado de 316,622 vuelos y 40 columnas.

Resultados de cobertura:

- Vuelos con coincidencia temporal meteorológica: 316,038 (99.82%).
- Vuelos con variables meteorológicas principales completas: 110,784 (34.99%).

**Limitación:** la existencia de una observación temporal no garantiza que todas sus mediciones estén disponibles. Las variables meteorológicas tienen diferentes porcentajes de valores faltantes.

## 3. Resultado integrado y trazabilidad

| Elemento | Ubicación |
|---|---|
| Dataset integrado completo | `datos/processed/integrated/dataset_integrado_semana7.parquet` |
| Muestra CSV de 5,000 filas | `datos/processed/integrated/dataset_integrado_muestra_5000.csv` |
| Log de ejecución | `outputs/metrics/ejecucion_pipeline_semana7.log` |
| Auditoría meteorológica | `datos/raw/noaa/procesados/auditoria_calidad_noaa.csv` |
| Cobertura de alerta meteorológica | `datos/raw/noaa/procesados/cobertura_alerta_2h.csv` |
| Calidad por aeropuerto | `outputs/metrics/calidad_por_aeropuerto.csv` |
| Métricas del modelo | `outputs/metrics/metricas_semana7.json` |

## 4. Licencia, acceso y condiciones de uso

Las fuentes son portales oficiales de organismos del Gobierno de Estados Unidos. Antes de redistribuir los archivos, se deben revisar las condiciones de uso y avisos aplicables publicados por cada organismo. Esta ficha no constituye una determinación legal de licencia.

- BTS: consultar las condiciones y documentación del portal oficial de TranStats.
- NOAA/NCEI: consultar la información de acceso, uso y atribución del portal Global Hourly.

## 5. Reproducibilidad y limitaciones

- Los archivos originales se conservan en la zona `datos/raw/`.
- Los datos transformados se guardan en `datos/processed/`.
- Las métricas, auditorías y evidencias se conservan en `outputs/metrics/`.
- La ejecución y las versiones del entorno deben documentarse en el README del repositorio.
- El prototipo no debe presentarse como un sistema desplegado en LATAM ni como un modelo listo para producción.
