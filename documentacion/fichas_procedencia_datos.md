# Fichas de procedencia de datos

## Fuente 1: BTS TranStats
- Proveedor: Bureau of Transportation Statistics.
- URL: https://www.transtats.bts.gov/
- Uso: registros de vuelos, horarios y demoras.
- Periodos utilizados: diciembre de 2025 y enero de 2026.
- Formatos de origen: archivos ZIP y CSV.
- Limitación: datos públicos de vuelos de Estados Unidos; no son registros internos de LATAM Airlines.

## Fuente 2: NOAA GHCNh
- Proveedor: NOAA National Centers for Environmental Information.
- URL: https://www.ncei.noaa.gov/products/land-based-station/global-hourly
- Uso: observaciones meteorológicas históricas de estaciones asociadas con nueve aeropuertos.
- Formato de procesamiento: PSV delimitado por |.
- Limitación: las observaciones históricas no equivalen a pronósticos meteorológicos disponibles operativamente.

## Inventario y trazabilidad
El inventario detallado de archivos, rutas relativas, formatos, tamaños en bytes y hashes SHA-256 se encuentra en:

`outputs/evidencias/entrega_semana7/ficha_procedencia_datos.csv`

La fecha original de descarga no quedó registrada de forma verificable para todos los archivos. No se infiere a partir de las fechas de modificación.

## Estaciones NOAA
| Aeropuerto | Estación |
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
