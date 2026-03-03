#!/usr/bin/env python3
"""
features_sunspots.py

Genera variables rezagadas (lags) de SunspotNumber y guarda
data/processed/sunspots_2005_2025_lags.parquet.
"""
import pandas as pd
import os

def add_lags(df, col="SunspotNumber", max_lag=365):
    df = df.copy().set_index("Date")
    for lag in range(1, max_lag+1):
        df[f"{col}_lag{lag}"] = df[col].shift(lag)
    return df.reset_index()

# 1) Leer limpio
df = pd.read_parquet("../data/processed/sunspots_2005_2025_clean.parquet")

# 2) Generar lags diarios (p.ej. 365 para un año)
df_lags = add_lags(df, col="SunspotNumber", max_lag=365)

# 3) Guardar
out_dir = "../data/processed"
os.makedirs(out_dir, exist_ok=True)
df_lags.to_parquet(f"{out_dir}/sunspots_2005_2025_lags.parquet", index=False)
print(f"💾 Sunspots lags guardados en {out_dir}/sunspots_2005_2025_lags.parquet")

