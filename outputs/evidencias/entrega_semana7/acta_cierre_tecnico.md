# Acta de cierre técnico — Semana 7

## Proyecto
Big Data y Analítica de Datos para la alerta temprana de demoras de salida mediante integración de vuelos y observaciones meteorológicas.

## Entorno y ejecución
- Ejecución local en macOS ARM64.
- Python 3.9.6.
- pandas 2.3.3.
- scikit-learn 1.6.1.
- PyArrow 21.0.0.
- psutil 7.2.2.
- Procesamiento ejecutado con pandas y scikit-learn; no se afirma ejecución distribuida con Spark/Hadoop ni despliegue en AWS.

## Resultados oficiales de integración
- Dataset integrado: 316,622 filas y 40 columnas.
- Vuelos con observación meteorológica asociada T−2: 316,038 (99.82%).
- Vuelos con ocho variables meteorológicas principales completas: 110,784 (34.99%).
- Vuelos con demora de al menos 15 minutos: 77,398 (24.44%).

## Benchmark de formatos
- CSV: 69.80 MiB; lectura mediana 0.566 s; escritura 1.640 s.
- Parquet: 6.06 MiB; lectura mediana 0.027 s; escritura 0.121 s.
- Reducción de tamaño: 91.3%.
- La comparación mide operaciones de lectura y escritura, no una aceleración equivalente de todas las etapas del pipeline.

## Evaluación del modelo
- Entrenamiento: diciembre de 2025, 165,941 registros.
- Prueba temporal: enero de 2026, 150,097 registros.
- Modelo: HistGradientBoostingRegressor.
- MAE: 21.5186 minutos.
- RMSE: 49.8488 minutos.
- R²: 0.0106.
- Precisión de alertas: 28.60%.
- Recall de alertas: 62.35%.
- F1: 39.21%.

El MAE es peor que el baseline de mediana (15.259 minutos). El modelo presenta capacidad predictiva limitada y no se recomienda para decisiones operativas sin mejoras y validación adicional.

## Escalabilidad y rendimiento
Existen pruebas de lectura y agregación Parquet a factores 1x, 10x y 100x. La prueba de réplicas físicas registró aproximadamente 316,622, 3,166,220 y 31,662,200 filas. Esta evidencia describe lectura y agregación; no representa una ejecución completa del pipeline a esos volúmenes ni una prueba distribuida.

## Limitaciones y pendientes explícitos
1. La procedencia de los archivos está inventariada, pero la fecha de descarga no se registró de forma verificable para todos los archivos.
2. La cobertura de observación temporal (99.82%) no implica completitud de todas las variables meteorológicas (34.99%).
3. Los datos son públicos y corresponden a vuelos de Estados Unidos; no son datos internos de LATAM Airlines.
4. No se ha desplegado una solución operacional ni una infraestructura AWS.
5. La declaración de uso de IA debe revisarse y firmarse por las personas que realmente corresponda según las instrucciones del curso.
6. La asignación individual de responsabilidades, si difiere del trabajo grupal esperado, debe comunicarse al docente; no se presume aprobación sin confirmación.

## Evidencias
- `outputs/evidencias/entrega_semana7/metricas_semana7.json`
- `outputs/evidencias/entrega_semana7/metricas_predicciones_enero_2026.json`
- `outputs/evidencias/entrega_semana7/ejecucion_modelo_base_20261011_210001.log`
- `outputs/evidencias/entrega_semana7/benchmark_formatos.log`
- `outputs/evidencias/entrega_semana7/resultados_escalabilidad.csv`
- `outputs/evidencias/entrega_semana7/metricas_demoras_escalabilidad.csv`
- `outputs/evidencias/entrega_semana7/ficha_procedencia_datos.csv`
