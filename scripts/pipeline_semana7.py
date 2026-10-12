from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import timedelta
import zipfile
import re
import time
import json
import warnings

import numpy as np
import pandas as pd
import psutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import HistGradientBoostingRegressor

warnings.filterwarnings("ignore")

BASE = Path(".")
RAW_BTS = BASE / "datos" / "raw" / "bts"
RAW_NOAA_PROCESADOS = BASE / "datos" / "raw" / "noaa" / "procesados"
OUT_DATA = BASE / "datos" / "processed" / "integrated"
OUT_FIG = BASE / "outputs" / "figures"
OUT_METRICS = BASE / "outputs" / "metrics"

AIRPORTS = {
    "ATL": {"station": "USW00013874", "tz": "America/New_York"},
    "CLT": {"station": "USW00013881", "tz": "America/New_York"},
    "DEN": {"station": "USW00003017", "tz": "America/Denver"},
    "DFW": {"station": "USW00003927", "tz": "America/Chicago"},
    "LAS": {"station": "USW00023169", "tz": "America/Los_Angeles"},
    "LAX": {"station": "USW00023174", "tz": "America/Los_Angeles"},
    "MCO": {"station": "USW00012815", "tz": "America/New_York"},
    "PHX": {"station": "USW00023183", "tz": "America/Phoenix"},
    "SEA": {"station": "USW00024233", "tz": "America/Los_Angeles"},
}

BTS_USECOLS = [
    "Year", "Quarter", "Month", "DayofMonth", "DayOfWeek", "FlightDate",
    "Reporting_Airline", "Tail_Number", "Flight_Number_Reporting_Airline",
    "Origin", "OriginCityName", "Dest", "DestCityName",
    "CRSDepTime", "DepDelay", "DepDelayMinutes", "DepDel15",
    "Cancelled", "Diverted", "Distance", "DistanceGroup"
]

def log(msg):
    print(msg, flush=True)

def mem_gb():
    return round(psutil.Process().memory_info().rss / (1024 ** 3), 3)

def read_bts_zip(zip_path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as z:
        csv_names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not csv_names:
            raise FileNotFoundError(f"No se encontró CSV dentro de {zip_path}")
        csv_name = csv_names[0]
        log(f"Leyendo BTS: {zip_path.name} -> {csv_name}")
        df = pd.read_csv(
            z.open(csv_name),
            usecols=lambda c: c in BTS_USECOLS,
            low_memory=False
        )
    missing = sorted(set(BTS_USECOLS) - set(df.columns))
    if missing:
        raise ValueError(f"Columnas BTS faltantes en {zip_path.name}: {missing}")
    return df

def parse_crs_time(value):
    if pd.isna(value):
        return None
    try:
        value = int(float(value))
    except Exception:
        return None
    hour = value // 100
    minute = value % 100
    if hour == 24:
        hour = 0
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return hour, minute

def local_to_utc(row):
    hm = parse_crs_time(row["CRSDepTime"])
    if hm is None:
        return pd.NaT
    hour, minute = hm
    origin = row["Origin"]
    tz_name = AIRPORTS[origin]["tz"]
    dt = pd.to_datetime(row["FlightDate"], errors="coerce")
    if pd.isna(dt):
        return pd.NaT
    local_dt = dt.to_pydatetime().replace(hour=hour, minute=minute, second=0, microsecond=0, tzinfo=ZoneInfo(tz_name))
    return pd.Timestamp(local_dt.astimezone(ZoneInfo("UTC"))).tz_localize(None)

def normalize_noaa_columns(df):
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df

def choose_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

def read_noaa_file(path: Path) -> pd.DataFrame:
    station_match = re.search(r"GHCNh_(USW\d+)_", path.name)
    station_from_file = station_match.group(1) if station_match else None

    df = pd.read_csv(path, sep="|", low_memory=False)
    df = normalize_noaa_columns(df)

    date_col = choose_col(df, ["date", "datetime", "timestamp"])
    if date_col is None:
        raise ValueError(f"No se encontró columna de fecha en {path.name}")

    station_col = choose_col(df, ["station", "station_id", "id"])
    if station_col is None:
        df["station"] = station_from_file
    else:
        df["station"] = df[station_col].astype(str).str.strip()

    df["weather_time_utc"] = pd.to_datetime(df[date_col], errors="coerce", utc=True).dt.tz_convert(None)

    desired_candidates = {
        "temperature": ["temperature", "temp", "tmp", "air_temperature"],
        "dew_point": ["dew_point", "dew_point_temperature", "dewpoint", "dew", "dewp"],
        "relative_humidity": ["relative_humidity", "rh", "humidity"],
        "wind_speed": ["wind_speed", "wind_speed_rate", "wnd_speed"],
        "wind_direction": ["wind_direction", "wind_dir", "wnd_direction"],
        "visibility": ["visibility", "vis"],
        "sea_level_pressure": ["sea_level_pressure", "slp"],
        "altimeter": ["altimeter", "altimeter_setting"],
        "precipitation": ["precipitation", "precip", "precipitation_1_hour"],
        "wind_gust": ["wind_gust", "gust"],
        "sky_ceiling": ["sky_ceiling", "ceiling_height"]
    }

    out = df[["station", "weather_time_utc"]].copy()
    for final_col, candidates in desired_candidates.items():
        col = choose_col(df, candidates)
        if col is not None:
            out[final_col] = pd.to_numeric(df[col], errors="coerce")
        else:
            out[final_col] = np.nan

    out = out.dropna(subset=["station", "weather_time_utc"])

    # Controles de rango físico. Las unidades originales se conservan:
    # temperatura en °C, presión en hPa, visibilidad en km,
    # velocidad del viento en m/s y altura del techo nuboso en metros.
    limits = {
        "temperature": (-90, 60),
        "dew_point": (-100, 50),
        "relative_humidity": (0, 100),
        "wind_speed": (0, 100),
        "wind_direction": (0, 360),
        "visibility": (0, 100),
        "sea_level_pressure": (800, 1100),
        "altimeter": (800, 1100),
        "precipitation": (0, 1000),
        "wind_gust": (0, 150),
        "sky_ceiling": (0, 30000),
    }
    for col, (lo, hi) in limits.items():
        out.loc[~out[col].between(lo, hi), col] = np.nan

    out = out.drop_duplicates(subset=["station", "weather_time_utc"])
    return out

def main():
    start_total = time.perf_counter()
    log("=" * 80)
    log("PIPELINE SEMANA 7 - INTEGRACION BTS + NOAA/GHCNh")
    log("=" * 80)
    log(f"RAM inicial del proceso: {mem_gb()} GB")

    bts_files = sorted(RAW_BTS.glob("vuelos_*.zip"))
    if not bts_files:
        raise FileNotFoundError("No se encontraron ZIP de BTS en datos/raw/bts")

    bts_parts = []
    for f in bts_files:
        bts_parts.append(read_bts_zip(f))
    bts = pd.concat(bts_parts, ignore_index=True)

    bts_total = len(bts)
    bts_selected = bts[bts["Origin"].isin(AIRPORTS.keys())].copy()

    for col in ["Cancelled", "Diverted", "DepDelayMinutes", "DepDel15", "Distance", "CRSDepTime"]:
        bts_selected[col] = pd.to_numeric(bts_selected[col], errors="coerce")

    selected_before_clean = len(bts_selected)
    cancelled = int((bts_selected["Cancelled"] == 1).sum())
    diverted = int((bts_selected["Diverted"] == 1).sum())

    bts_selected = bts_selected[
        (bts_selected["Cancelled"] == 0) &
        (bts_selected["Diverted"] == 0) &
        (bts_selected["DepDelayMinutes"].notna()) &
        (bts_selected["DepDel15"].notna()) &
        (bts_selected["CRSDepTime"].notna())
    ].copy()

    duplicates = int(bts_selected.duplicated(
        subset=["FlightDate", "Reporting_Airline", "Flight_Number_Reporting_Airline", "Origin", "Dest", "CRSDepTime", "Tail_Number"]
    ).sum())
    bts_selected = bts_selected.drop_duplicates(
        subset=["FlightDate", "Reporting_Airline", "Flight_Number_Reporting_Airline", "Origin", "Dest", "CRSDepTime", "Tail_Number"]
    )

    log(f"BTS total: {bts_total}")
    log(f"BTS aeropuertos seleccionados antes de limpieza: {selected_before_clean}")
    log(f"Cancelados excluidos: {cancelled}")
    log(f"Desviados excluidos: {diverted}")
    log(f"Duplicados excluidos: {duplicates}")
    log(f"Vuelos elegibles BTS: {len(bts_selected)}")
    log(f"RAM luego de BTS: {mem_gb()} GB")

    log("Convirtiendo hora local programada a UTC y creando alerta T-2h...")
    bts_selected["scheduled_dep_utc"] = bts_selected.apply(local_to_utc, axis=1)
    bts_selected = bts_selected.dropna(subset=["scheduled_dep_utc"]).copy()
    bts_selected["alert_time_utc"] = bts_selected["scheduled_dep_utc"] - pd.Timedelta(hours=2)
    bts_selected["origin_station"] = bts_selected["Origin"].map(lambda x: AIRPORTS[x]["station"])
    bts_selected["dep_hour_local"] = pd.to_numeric(bts_selected["CRSDepTime"], errors="coerce").fillna(0).astype(int) // 100
    bts_selected["is_weekend"] = bts_selected["DayOfWeek"].isin([6, 7]).astype(int)

    noaa_files = sorted(RAW_NOAA_PROCESADOS.glob("GHCNh_*_2025-12_2026-01.psv"))
    if not noaa_files:
        raise FileNotFoundError("No se encontraron archivos NOAA/GHCNh procesados")

    noaa_parts = []
    for f in noaa_files:
        log(f"Leyendo NOAA/GHCNh: {f.name}")
        noaa_parts.append(read_noaa_file(f))
    noaa = pd.concat(noaa_parts, ignore_index=True)
    noaa = noaa.drop_duplicates(subset=["station", "weather_time_utc"])
    log(f"Observaciones NOAA/GHCNh cargadas: {len(noaa)}")
    log(f"RAM luego de NOAA: {mem_gb()} GB")

    log("Integrando vuelos con la última observación meteorológica disponible antes de la alerta...")
    merged_parts = []
    for station in sorted(set(AIRPORTS[a]["station"] for a in AIRPORTS)):
        left = bts_selected[bts_selected["origin_station"] == station].sort_values("alert_time_utc")
        right = noaa[noaa["station"] == station].sort_values("weather_time_utc")
        if left.empty:
            continue
        if right.empty:
            tmp = left.copy()
            for col in noaa.columns:
                if col not in tmp.columns:
                    tmp[col] = np.nan
            merged_parts.append(tmp)
            continue
        tmp = pd.merge_asof(
            left,
            right,
            left_on="alert_time_utc",
            right_on="weather_time_utc",
            direction="backward",
            tolerance=pd.Timedelta(minutes=60)
        )
        merged_parts.append(tmp)

    integrated = pd.concat(merged_parts, ignore_index=True)
    integrated["weather_age_minutes"] = (
        integrated["alert_time_utc"] - integrated["weather_time_utc"]
    ).dt.total_seconds() / 60

    integrated["has_weather_match"] = integrated["weather_time_utc"].notna().astype(int)
    integrated["delay_15"] = (integrated["DepDel15"] == 1).astype(int)
    integrated["dep_delay_minutes"] = integrated["DepDelayMinutes"].astype(float).clip(lower=0)

    key_weather = [
        "temperature", "dew_point", "relative_humidity", "wind_speed",
        "wind_direction", "visibility", "sea_level_pressure", "altimeter"
    ]
    for col in key_weather:
        if col not in integrated.columns:
            integrated[col] = np.nan

    integrated["has_all_core_weather"] = integrated[key_weather].notna().all(axis=1).astype(int)
    integrated["pressure_for_model"] = integrated["sea_level_pressure"]
    integrated.loc[integrated["pressure_for_model"].isna(), "pressure_for_model"] = integrated.loc[
        integrated["pressure_for_model"].isna(), "altimeter"
    ]

    cols_out = [
        "Year", "Month", "DayofMonth", "DayOfWeek", "FlightDate",
        "Reporting_Airline", "Tail_Number", "Flight_Number_Reporting_Airline",
        "Origin", "OriginCityName", "Dest", "DestCityName",
        "CRSDepTime", "scheduled_dep_utc", "alert_time_utc",
        "origin_station", "weather_time_utc", "weather_age_minutes",
        "DepDelayMinutes", "DepDel15", "dep_delay_minutes", "delay_15",
        "Distance", "DistanceGroup", "dep_hour_local", "is_weekend",
        "temperature", "dew_point", "relative_humidity", "wind_speed",
        "wind_direction", "visibility", "sea_level_pressure", "altimeter",
        "pressure_for_model", "precipitation", "wind_gust", "sky_ceiling",
        "has_weather_match", "has_all_core_weather"
    ]
    cols_out = [c for c in cols_out if c in integrated.columns]
    final = integrated[cols_out].copy()

    parquet_path = OUT_DATA / "dataset_integrado_semana7.parquet"
    csv_sample_path = OUT_DATA / "dataset_integrado_muestra_5000.csv"
    final.to_parquet(parquet_path, index=False)
    final.head(5000).to_csv(csv_sample_path, index=False)

    log(f"Dataset integrado guardado: {parquet_path}")
    log(f"Muestra CSV guardada: {csv_sample_path}")
    log(f"Filas dataset integrado: {len(final)}")
    log(f"Columnas dataset integrado: {len(final.columns)}")

    # Metricas de calidad e integracion
    quality = {
        "bts_total_registros": int(bts_total),
        "bts_aeropuertos_seleccionados": int(selected_before_clean),
        "cancelados_excluidos": int(cancelled),
        "desviados_excluidos": int(diverted),
        "duplicados_excluidos": int(duplicates),
        "vuelos_elegibles_integrados": int(len(final)),
        "vuelos_con_clima_t_2h": int(final["has_weather_match"].sum()),
        "porcentaje_con_clima_t_2h": round(float(final["has_weather_match"].mean() * 100), 2),
        "vuelos_con_clima_core_completo": int(final["has_all_core_weather"].sum()),
        "porcentaje_con_clima_core_completo": round(float(final["has_all_core_weather"].mean() * 100), 2),
        "tasa_demora_15_total": round(float(final["delay_15"].mean() * 100), 2),
        "demora_promedio_total": round(float(final["dep_delay_minutes"].mean()), 2),
        "demora_mediana_total": round(float(final["dep_delay_minutes"].median()), 2),
        "demora_promedio_demorados_15": round(float(final.loc[final["delay_15"] == 1, "dep_delay_minutes"].mean()), 2),
        "ram_gb_fin_integracion": mem_gb()
    }

    coverage_by_airport = final.groupby("Origin").agg(
        vuelos=("Origin", "size"),
        tasa_demora_15=("delay_15", "mean"),
        clima_t_2h=("has_weather_match", "mean"),
        clima_core_completo=("has_all_core_weather", "mean"),
        demora_promedio=("dep_delay_minutes", "mean")
    ).reset_index()
    coverage_by_airport["tasa_demora_15"] = (coverage_by_airport["tasa_demora_15"] * 100).round(2)
    coverage_by_airport["clima_t_2h"] = (coverage_by_airport["clima_t_2h"] * 100).round(2)
    coverage_by_airport["clima_core_completo"] = (coverage_by_airport["clima_core_completo"] * 100).round(2)
    coverage_by_airport["demora_promedio"] = coverage_by_airport["demora_promedio"].round(2)

    coverage_by_airport.to_csv(OUT_METRICS / "calidad_por_aeropuerto.csv", index=False)

    # EDA
    sns.set_theme(style="whitegrid")

    fig1 = coverage_by_airport.sort_values("tasa_demora_15", ascending=False)
    plt.figure(figsize=(10, 5))
    sns.barplot(data=fig1, x="Origin", y="tasa_demora_15", color="#2E77BB")
    plt.title("Tasa de vuelos con demora de salida >= 15 minutos por aeropuerto")
    plt.xlabel("Aeropuerto de origen")
    plt.ylabel("Tasa de demora >= 15 min (%)")
    plt.tight_layout()
    plt.savefig(OUT_FIG / "figura_1_demora_por_aeropuerto.png", dpi=180)
    plt.close()

    by_hour = final.groupby("dep_hour_local").agg(
        vuelos=("dep_hour_local", "size"),
        tasa_demora_15=("delay_15", "mean"),
        demora_promedio=("dep_delay_minutes", "mean")
    ).reset_index()
    by_hour["tasa_demora_15"] = by_hour["tasa_demora_15"] * 100

    plt.figure(figsize=(10, 5))
    sns.lineplot(data=by_hour, x="dep_hour_local", y="tasa_demora_15", marker="o", color="#C44E52")
    plt.title("Tasa de demora >= 15 minutos según hora programada de salida")
    plt.xlabel("Hora local programada")
    plt.ylabel("Tasa de demora >= 15 min (%)")
    plt.xticks(range(0, 24, 2))
    plt.tight_layout()
    plt.savefig(OUT_FIG / "figura_2_demora_por_hora.png", dpi=180)
    plt.close()

    eda_weather = final.copy()
    eda_weather["visibility_bucket"] = pd.cut(
        eda_weather["visibility"],
        bins=[-np.inf, 1, 3, 5, 10, np.inf],
        labels=["<=1 km", "1-3 km", "3-5 km", "5-10 km", ">10 km"]
    )
    by_vis = eda_weather.groupby("visibility_bucket", observed=True).agg(
        vuelos=("visibility_bucket", "size"),
        tasa_demora_15=("delay_15", "mean")
    ).reset_index()
    by_vis["tasa_demora_15"] = by_vis["tasa_demora_15"] * 100

    plt.figure(figsize=(9, 5))
    sns.barplot(data=by_vis, x="visibility_bucket", y="tasa_demora_15", color="#55A868")
    plt.title("Relación entre visibilidad y demora de salida >= 15 minutos")
    plt.xlabel("Rango de visibilidad")
    plt.ylabel("Tasa de demora >= 15 min (%)")
    plt.tight_layout()
    plt.savefig(OUT_FIG / "figura_3_demora_por_visibilidad.png", dpi=180)
    plt.close()

    by_hour.to_csv(OUT_METRICS / "eda_demora_por_hora.csv", index=False)
    by_vis.to_csv(OUT_METRICS / "eda_demora_por_visibilidad.csv", index=False)

    # Modelo base: entrenamiento temporal diciembre -> prueba enero
    model_data = final[final["has_weather_match"] == 1].copy()
    train = model_data[model_data["FlightDate"].astype(str).str.startswith("2025-12")].copy()
    test = model_data[model_data["FlightDate"].astype(str).str.startswith("2026-01")].copy()

    numeric_features = [
        "DayOfWeek", "dep_hour_local", "is_weekend", "Distance",
        "temperature", "dew_point", "relative_humidity", "wind_speed",
        "wind_direction", "visibility", "pressure_for_model",
        "weather_age_minutes"
    ]
    numeric_features = [c for c in numeric_features if c in model_data.columns]

    categorical_features = ["Reporting_Airline", "Origin", "Dest"]
    categorical_features = [c for c in categorical_features if c in model_data.columns]

    X_train = train[numeric_features + categorical_features]
    y_train = train["dep_delay_minutes"]
    X_test = test[numeric_features + categorical_features]
    y_test = test["dep_delay_minutes"]
    y_test_alert = test["delay_15"]

    median_train = float(y_train.median())
    y_pred_median = np.full(shape=len(y_test), fill_value=median_train)

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler())
            ]), numeric_features),
            ("cat", Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
            ]), categorical_features)
        ],
        remainder="drop"
    )

    model = HistGradientBoostingRegressor(
        max_iter=180,
        learning_rate=0.06,
        max_leaf_nodes=31,
        l2_regularization=0.1,
        random_state=42
    )

    pipe = Pipeline([
        ("prep", preprocessor),
        ("model", model)
    ])

    log("Entrenando modelo base con diciembre 2025 y evaluando en enero 2026...")
    model_start = time.perf_counter()
    pipe.fit(X_train, y_train)
    model_seconds = round(time.perf_counter() - model_start, 2)

    y_pred = pipe.predict(X_test)
    y_pred = np.clip(y_pred, 0, None)

    y_alert_pred = (y_pred >= 15).astype(int)
    y_alert_median = (y_pred_median >= 15).astype(int)

    def regression_metrics(y_true, y_hat):
        rmse = mean_squared_error(y_true, y_hat) ** 0.5
        return {
            "MAE": round(float(mean_absolute_error(y_true, y_hat)), 3),
            "RMSE": round(float(rmse), 3),
            "R2": round(float(r2_score(y_true, y_hat)), 4)
        }

    def alert_metrics(y_true, y_hat):
        cm = confusion_matrix(y_true, y_hat, labels=[0, 1])
        return {
            "Accuracy": round(float(accuracy_score(y_true, y_hat)), 4),
            "Precision": round(float(precision_score(y_true, y_hat, zero_division=0)), 4),
            "Recall": round(float(recall_score(y_true, y_hat, zero_division=0)), 4),
            "F1": round(float(f1_score(y_true, y_hat, zero_division=0)), 4),
            "TN": int(cm[0, 0]),
            "FP": int(cm[0, 1]),
            "FN": int(cm[1, 0]),
            "TP": int(cm[1, 1])
        }

    metrics = {
        "periodo_entrenamiento": "2025-12",
        "periodo_prueba": "2026-01",
        "filas_train": int(len(train)),
        "filas_test": int(len(test)),
        "features_numericas": numeric_features,
        "features_categoricas": categorical_features,
        "mediana_entrenamiento_minutos": round(median_train, 3),
        "referencia_mediana_regresion": regression_metrics(y_test, y_pred_median),
        "modelo_base": "HistGradientBoostingRegressor",
        "modelo_base_regresion": regression_metrics(y_test, y_pred),
        "referencia_mediana_alerta_15": alert_metrics(y_test_alert, y_alert_median),
        "modelo_base_alerta_15": alert_metrics(y_test_alert, y_alert_pred),
        "segundos_entrenamiento_modelo": model_seconds,
        "ram_gb_fin_modelado": mem_gb()
    }

    with open(OUT_METRICS / "metricas_semana7.json", "w", encoding="utf-8") as f:
        json.dump({"calidad_integracion": quality, "modelo": metrics}, f, indent=2, ensure_ascii=False)

    summary_lines = []
    summary_lines.append("=" * 80)
    summary_lines.append("RESULTADOS FINALES SEMANA 7")
    summary_lines.append("=" * 80)
    summary_lines.append("CALIDAD E INTEGRACION")
    for k, v in quality.items():
        summary_lines.append(f"{k}: {v}")
    summary_lines.append("")
    summary_lines.append("MODELO BASE")
    summary_lines.append(f"Entrenamiento: {metrics['periodo_entrenamiento']} | filas: {metrics['filas_train']}")
    summary_lines.append(f"Prueba: {metrics['periodo_prueba']} | filas: {metrics['filas_test']}")
    summary_lines.append(f"Referencia mediana entrenamiento: {metrics['mediana_entrenamiento_minutos']} minutos")
    summary_lines.append(f"Referencia mediana regresion: {metrics['referencia_mediana_regresion']}")
    summary_lines.append(f"Modelo base regresion: {metrics['modelo_base_regresion']}")
    summary_lines.append(f"Referencia mediana alerta >=15: {metrics['referencia_mediana_alerta_15']}")
    summary_lines.append(f"Modelo base alerta >=15: {metrics['modelo_base_alerta_15']}")
    summary_lines.append(f"Tiempo entrenamiento modelo: {model_seconds} segundos")
    summary_lines.append("")
    summary_lines.append("ARCHIVOS GENERADOS")
    summary_lines.append(str(parquet_path))
    summary_lines.append(str(csv_sample_path))
    summary_lines.append(str(OUT_METRICS / "metricas_semana7.json"))
    summary_lines.append(str(OUT_METRICS / "calidad_por_aeropuerto.csv"))
    summary_lines.append(str(OUT_FIG / "figura_1_demora_por_aeropuerto.png"))
    summary_lines.append(str(OUT_FIG / "figura_2_demora_por_hora.png"))
    summary_lines.append(str(OUT_FIG / "figura_3_demora_por_visibilidad.png"))

    summary = "\n".join(summary_lines)
    print("\n" + summary)

    with open(OUT_METRICS / "resumen_semana7.txt", "w", encoding="utf-8") as f:
        f.write(summary)

    log(f"Tiempo total del pipeline: {round(time.perf_counter() - start_total, 2)} segundos")
    log(f"RAM final del proceso: {mem_gb()} GB")

if __name__ == "__main__":
    main()
