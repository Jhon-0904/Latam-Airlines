from pathlib import Path
import json
import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix
)

entrada = Path("datos/processed/integrated/dataset_integrado_semana7.parquet")
salida = Path("outputs/metrics")
salida.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(entrada)
df["FlightDate"] = df["FlightDate"].astype(str)

# Mismo criterio temporal del pipeline: diciembre entrena, enero prueba.
df = df[df["has_weather_match"] == 1].copy()
train = df[df["FlightDate"].str.startswith("2025-12")].copy()
test = df[df["FlightDate"].str.startswith("2026-01")].copy()

numeric = [
    "DayOfWeek", "dep_hour_local", "is_weekend", "Distance",
    "temperature", "dew_point", "relative_humidity", "wind_speed",
    "wind_direction", "visibility", "pressure_for_model",
    "weather_age_minutes"
]
categorical = ["Reporting_Airline", "Origin", "Dest"]
target = "dep_delay_minutes"

required = numeric + categorical + [target, "delay_15"]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Faltan columnas necesarias: {missing}")

train = train.dropna(subset=[target, "delay_15"])
test = test.dropna(subset=[target, "delay_15"])

preprocessor = ColumnTransformer([
    ("num", Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler())
    ]), numeric),
    ("cat", Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(
            handle_unknown="ignore", sparse_output=False
        ))
    ]), categorical)
])

model = Pipeline([
    ("preprocessor", preprocessor),
    ("regressor", HistGradientBoostingRegressor(
        max_iter=180,
        learning_rate=0.06,
        max_leaf_nodes=31,
        l2_regularization=0.1,
        random_state=42
    ))
])

X_train = train[numeric + categorical]
y_train = train[target].astype(float)
X_test = test[numeric + categorical]
y_test = test[target].astype(float)

print(f"Filas de entrenamiento: {len(train):,}")
print(f"Filas de prueba: {len(test):,}")
print("Entrenando modelo...")
model.fit(X_train, y_train)

pred = np.maximum(model.predict(X_test), 0)
real_alert = test["delay_15"].astype(int).to_numpy()
pred_alert = (pred >= 15).astype(int)

# Evidencia por vuelo: valores reales y predicción.
columnas = [
    c for c in [
        "FlightDate", "Reporting_Airline", "Origin", "Dest",
        "CRSDepTime", "dep_delay_minutes", "delay_15",
        "weather_age_minutes"
    ] if c in test.columns
]
evidencia = test[columnas].copy()
evidencia["predicted_delay_minutes"] = np.round(pred, 2)
evidencia["predicted_alert_15min"] = pred_alert
evidencia["alert_result"] = np.select(
    [
        (real_alert == 1) & (pred_alert == 1),
        (real_alert == 0) & (pred_alert == 1),
        (real_alert == 1) & (pred_alert == 0)
    ],
    ["verdadero positivo", "falsa alerta", "demora no detectada"],
    default="verdadero negativo"
)

archivo_pred = salida / "predicciones_vuelos_enero_2026.csv"
evidencia.to_csv(archivo_pred, index=False)

mae = mean_absolute_error(y_test, pred)
rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
r2 = r2_score(y_test, pred)
tn, fp, fn, tp = confusion_matrix(
    real_alert, pred_alert, labels=[0, 1]
).ravel()

metricas = {
    "periodo_prueba": "2026-01",
    "filas_entrenamiento": int(len(train)),
    "filas_prueba": int(len(test)),
    "mae_minutos": round(float(mae), 4),
    "rmse_minutos": round(rmse, 4),
    "r2": round(float(r2), 4),
    "accuracy_alerta": round(float(accuracy_score(real_alert, pred_alert)), 4),
    "precision_alerta": round(float(precision_score(real_alert, pred_alert, zero_division=0)), 4),
    "recall_alerta": round(float(recall_score(real_alert, pred_alert, zero_division=0)), 4),
    "f1_alerta": round(float(f1_score(real_alert, pred_alert, zero_division=0)), 4),
    "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    "umbral_alerta_minutos": 15
}

(salida / "metricas_predicciones_enero_2026.json").write_text(
    json.dumps(metricas, indent=2, ensure_ascii=False),
    encoding="utf-8"
)
pd.DataFrame(
    [[tn, fp], [fn, tp]],
    index=["Real sin demora >=15", "Real con demora >=15"],
    columns=["Predicción sin alerta", "Predicción con alerta"]
).to_csv(salida / "matriz_confusion_enero_2026.csv")

print("\nMÉTRICAS DE ESTA EJECUCIÓN")
print(json.dumps(metricas, indent=2, ensure_ascii=False))
print("\nArchivos generados:")
print(archivo_pred)
print(salida / "metricas_predicciones_enero_2026.json")
print(salida / "matriz_confusion_enero_2026.csv")
print("\nMuestra de predicciones:")
print(evidencia.head(10).to_string(index=False))
