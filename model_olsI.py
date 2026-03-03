#!/usr/bin/env python3
"""
model_ols.py

Ajusta un modelo OLS múltiple de la columna total de ozono usando lags de ozono y la serie de manchas solares.
Genera métricas, residuos, diagnósticos estadísticos y guarda resultados.
"""
import pandas as pd
import statsmodels.api as sm
from diagnosticos import correr_tests
from scipy.stats import shapiro
from statsmodels.stats.diagnostic import het_breuschpagan, acorr_ljungbox
import os

# 1) Cargar datos de ozono con lags y de manchas solares limpias
df_oz = pd.read_parquet("../data/processed/ozone_2005_2025_lags.parquet")
df_sp = pd.read_parquet("../data/processed/sunspots_2005_2025_clean.parquet")

# 2) Fusionar por fecha
# Asegura que ambas tablas tengan la columna 'Date'
df = pd.merge(df_oz, df_sp, on="Date").dropna()

# 3) Definir predictores (lags ozono 1–12 + SunspotNumber)
lags = [f"Ozone_lag{lag}" for lag in range(1, 13)]
predictors = lags + ["SunspotNumber"]
X = df[predictors]
X = sm.add_constant(X)
y = df["Ozone"]

# 4) Ajustar modelo OLS
model = sm.OLS(y, X).fit()
print(model.summary())

# 5) Diagnósticos de supuestos (normalidad, homocedasticidad, independencia)
print("\n--- Diagnósticos de supuestos ---")
# Normalidad (Shapiro–Wilk)
st_sw, p_sw = shapiro(model.resid)
print(f"Shapiro–Wilk p-valor = {p_sw:.3f}")
# Homocedasticidad (Breusch–Pagan)
bp_stat, bp_p, _, _ = het_breuschpagan(model.resid, model.model.exog)
print(f"Breusch–Pagan p-valor = {bp_p:.3f}")
# Independencia (Ljung–Box lag=10)
lb = acorr_ljungbox(model.resid, lags=[10], return_df=True)
print(lb)
# Durbin–Watson
dw = sm.stats.stattools.durbin_watson(model.resid)
print(f"Durbin–Watson = {dw:.3f}")

# 6) Guardar resultados (fitted, residuos)
os.makedirs("../data/processed", exist_ok=True)
df_out = df.assign(fitted=model.fittedvalues, resid=model.resid)
df_out.to_parquet("../data/processed/ols_results_with_solar.parquet", index=False)
print("💾 Resultados OLS guardados en data/processed/ols_results_with_solar.parquet")

# 7) Pruebas de batería y guardar diagnósticos
df_diag = correr_tests(y=model.resid, exog=df[predictors])
df_diag.to_csv("../data/processed/diagnostics_OLS_with_solar.csv", index=False)
print("💾 Diagnósticos OLS guardados en data/processed/diagnostics_OLS_with_solar.csv")

