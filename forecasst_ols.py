#!/usr/bin/env python3
"""
forecast_ols.py

Genera un pronóstico prospectivo de la columna total de ozono para 2026–2036
usando el modelo OLS entrenado con datos 2005–2025.

Salida:
  data/processed/forecast_ols.parquet
  data/processed/forecast_ols.png
"""
import pandas as pd
import numpy as np
import statsmodels.api as sm
import matplotlib.pyplot as plt
from datetime import timedelta
import os

# 1) Cargar datos completos hasta 2025
df_oz = pd.read_parquet('../data/processed/ozone_2005_2025_clean.parquet')
# Incluye lag features y solar predictor
df_full = pd.read_parquet('../data/processed/ols_results_with_solar.parquet')

# 2) Re-entrenar OLS sobre todo el periodo
df_train = pd.merge(
    df_oz, pd.read_parquet('../data/processed/sunspots_2005_2025_clean.parquet'),
    on='Date'
).dropna()
# Generar lags de ozono
for lag in range(1, 13):
    df_train[f'Ozone_lag{lag}'] = df_train['Ozone'].shift(lag)
df_train = df_train.dropna()
predictors = [f'Ozone_lag{lag}' for lag in range(1,13)] + ['SunspotNumber']
X_train = sm.add_constant(df_train[predictors])
y_train = df_train['Ozone']
model = sm.OLS(y_train, X_train).fit()

# 3) Preparar horizonte diario 2026-2036
start_date = df_train['Date'].max() + timedelta(days=1)
horizon = 365 * 11  # 11 años
future_dates = pd.date_range(start_date, periods=horizon, freq='D')

# 4) Cargar solar para 2026-2036 (interpolado o estimado manualmente)
df_sp_future = pd.read_parquet('../data/processed/sunspots_2005_2025_clean.parquet')
# Asumimos repetición ciclo: usar valores 2014-2024 recurrentes para 2026-2036
# (Implementa tu modelo solar aquí)

# 5) Iterative forecast
df_hist = df_train.set_index('Date')
forecast = []
for date in future_dates:
    # Generar vector de predictores
ing_keys = {}
    for lag in range(1,13):
        ing_keys[f'Ozone_lag{lag}'] = df_hist['Ozone'].iloc[-lag]
    ing_keys['SunspotNumber'] = df_sp_future.set_index('Date').loc[date,'SunspotNumber']
    vec = [ing_keys[col] for col in predictors]
    vec = sm.add_constant(pd.DataFrame([vec], columns=predictors))
    yhat = model.predict(vec)[0]
    forecast.append({'Date': date, 'Ozone_pred': yhat})
    # Añadir predicción al histórico para siguientes lags
    df_hist.loc[date] = [None]*len(df_hist.columns)
    df_hist.at[date,'Ozone'] = yhat

# 6) Guardar resultados
df_fc = pd.DataFrame(forecast)
os.makedirs('../data/processed', exist_ok=True)
df_fc.to_parquet('../data/processed/forecast_ols.parquet', index=False)
# 7) Graficar
plt.figure(figsize=(10,4))
plt.plot(df_train['Date'], df_train['Ozone'], label='Histórico')
plt.plot(df_fc['Date'], df_fc['Ozone_pred'], label='Pronóstico')
plt.legend()
plt.title('Forecast Ozone 2026–2036 (OLS)')
plt.tight_layout()
plt.savefig('../data/processed/forecast_ols.png')
print(f"💾 Forecast guardado en data/processed/forecast_ols.parquet y .png")


