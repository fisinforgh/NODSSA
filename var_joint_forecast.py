#!/usr/bin/env python3
"""
var_joint_forecast.py
Pronóstico conjunto Ozono–Manchas Solares (mensual) con VAR.
- Usa datos diarios limpios (2005–2025) y los agrega a mensual (media).
- Ajusta VAR (en niveles o diferencias según ADF), selecciona lags por AIC.
- Pronostica 2026–2036 (132 meses) y exporta:
    data/processed/var_joint_forecast_monthly.parquet (.csv)
    docs/figs/var/var_forecast.png
    docs/figs/var/var_irf.png
    docs/figs/var/ozone_periodogram.png
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import adfuller
from scipy.signal import periodogram

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
FIGS = ROOT / "docs" / "figs" / "var"
FIGS.mkdir(parents=True, exist_ok=True)

OZ_PATH = DATA / "ozone_2005_2025_clean.parquet"
SP_PATH = DATA / "sunspots_2005_2025_clean.parquet"

# ---------- 1) Cargar y pasar a mensual ----------
oz = pd.read_parquet(OZ_PATH)
sp = pd.read_parquet(SP_PATH)

ozm = (oz.set_index("Date")
         .resample("MS")  # inicio de mes
         .mean()
         .rename(columns={"Ozone":"Ozone"}))

spm = (sp.set_index("Date")
         .resample("MS")
         .mean()
         .rename(columns={"SunspotNumber":"SunspotNumber"}))

dfm = (ozm.join(spm, how="inner")
          .dropna()
          .copy())

# ---------- 2) ADF y diferencia si hace falta ----------
def adf_p(series):
    return adfuller(series, autolag="AIC")[1]

p_o3 = adf_p(dfm["Ozone"])
p_sn = adf_p(dfm["SunspotNumber"])
print(f"ADF p-value Ozone (mensual): {p_o3:.4f}")
print(f"ADF p-value SunspotNumber (mensual): {p_sn:.4f}")

use_diff = (p_o3 > 0.05) or (p_sn > 0.05)

if use_diff:
    df_train = dfm.diff().dropna()
    last_levels = dfm.iloc[-1].copy()
    diff_flag = 1
    print("→ No estacionario: usando VAR en diferencias (d=1).")
else:
    df_train = dfm.copy()
    diff_flag = 0
    print("→ Estacionario: usando VAR en niveles.")

# ---------- 3) Selección de rezagos (AIC) y ajuste ----------
maxlags = 24  # hasta 2 años
model = VAR(df_train)
sel = model.select_order(maxlags=maxlags)
p = int(sel.aic or 6)
print(f"Lag seleccionado por AIC: p={p}")

res = model.fit(p)
print(res.summary())

# ---------- 4) Pronóstico 2026–2036 (132 meses) ----------
h = 11 * 12  # meses
fc = res.forecast(df_train.values[-p:], steps=h)
fc = pd.DataFrame(fc, columns=df_train.columns)

# reconstruir niveles si se ajustó en diferencias
if diff_flag == 1:
    # suma acumulada de diferencias + último nivel observado
    start = dfm.iloc[-1].values.reshape(1, -1)
    levels = np.vstack([start, start + np.cumsum(fc.values, axis=0)])
    levels = levels[1:]  # quitar fila inicial
    fc_levels = pd.DataFrame(levels, columns=df_train.columns)
else:
    fc_levels = fc.copy()

# índice de fechas mensuales futuras
start_date = dfm.index[-1] + pd.offsets.MonthBegin(1)
future_idx = pd.date_range(start_date, periods=h, freq="MS")
fc_levels.index = future_idx

out = (fc_levels
       .rename(columns={"Ozone":"Ozone_pred", "SunspotNumber":"SunspotNumber_pred"})
       .reset_index()
       .rename(columns={"index":"Date"}))

# ---------- 5) Guardar ----------
os.makedirs(DATA, exist_ok=True)
out.to_parquet(DATA / "var_joint_forecast_monthly.parquet", index=False)
out.to_csv(DATA / "var_joint_forecast_monthly.csv", index=False)
print("💾 Guardado: data/processed/var_joint_forecast_monthly.parquet (.csv)")

# ---------- 6) Graficar forecast ----------
plt.figure(figsize=(11,5))
plt.plot(dfm.index, dfm["Ozone"], label="Ozone (hist.)", linewidth=1.4)
plt.plot(out["Date"], out["Ozone_pred"], label="Ozone (forecast VAR)", linewidth=1.6)
plt.title("Pronóstico mensual de Ozono (VAR conjunto con SunspotNumber)")
plt.xlabel("Fecha"); plt.ylabel("DU")
plt.legend(); plt.tight_layout()
plt.savefig(FIGS / "var_forecast.png", dpi=150)

# ---------- 7) IRF (impulso-respuesta) ----------
# horizonte 24 meses: respuesta de O3 ante shock en Sunspots y viceversa
irf = res.irf(24)
fig = irf.plot(orth=False)
fig.suptitle("Funciones Impulso–Respuesta (VAR, 24 meses)", y=1.02)
fig.tight_layout()
plt.savefig(FIGS / "var_irf.png", dpi=150)

# ---------- 8) Espectro mensual de ozono (histórico) ----------
# periodograma simple (frecuencia en ciclos/mes)
f, Pxx = periodogram(dfm["Ozone"], fs=1.0)  # 1 muestra/mes
# evitar f=0 (media)
mask = f > 0
f, Pxx = f[mask], Pxx[mask]

plt.figure(figsize=(10,4))
plt.semilogy(f, Pxx)
plt.xlabel("Frecuencia (ciclos/mes)"); plt.ylabel("Densidad espectral (log)")
plt.title("Periodograma de Ozono mensual (picos: ~12 meses, baja-frecuencia)")
plt.tight_layout()
plt.savefig(FIGS / "ozone_periodogram.png", dpi=150)

print("✅ Listo: gráficos en docs/figs/var/")

