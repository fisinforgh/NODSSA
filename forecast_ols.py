#!/usr/bin/env python3
"""
forecast_ols.py

Pronóstico 2026–2036 de columna total de ozono usando OLS con rezagos,
tendencia, Fourier y solar. Incertidumbre vía bootstrap robusto
(param & block residual). Exporta trayectorias y grafica paths opcionales.
"""

import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
import numpy as np
from datetime import timedelta
import os
import warnings
warnings.filterwarnings("ignore", message="Conversion of an array with ndim")

# ---------------- Parámetros ----------------
BOOTSTRAPS = 500
ALPHA = 0.05
LAGS = [1, 7, 14, 30, 365]     # ajusta a tu frecuencia real
T_SEASON = 365
HARMONICS = [1, 2, 3]
BLOCK_LEN = 7                  # longitud de bloque para bootstrap circular

SHOW_PATHS = True              # === NUEVO: dibujar trayectorias individuales
N_PATHS_TO_SHOW = 20

SAVE_TRAJ = True               # === NUEVO: exportar todas las trayectorias
SAVE_LONG = True               # también versión larga (Date, bootstrap_id, value)

# ---------------- 1) Datos -------------------
df_oz = pd.read_parquet('../data/processed/ozone_2005_2025_clean.parquet')
df_sp = pd.read_parquet('../data/processed/sunspots_2005_2025_clean.parquet')
data = pd.merge(df_oz, df_sp, on='Date').sort_values('Date').reset_index(drop=True)

# ---------------- 2) Variables X -------------
data['t'] = np.arange(len(data))
for k in HARMONICS:
    data[f'sin{k}'] = np.sin(2 * np.pi * k * data['t'] / T_SEASON)
    data[f'cos{k}'] = np.cos(2 * np.pi * k * data['t'] / T_SEASON)
for lag in LAGS:
    data[f'Ozone_lag{lag}'] = data['Ozone'].shift(lag)
data = data.dropna().reset_index(drop=True)

# ---------------- 3) OLS ---------------------
features = [f'Ozone_lag{lag}' for lag in LAGS] + ['SunspotNumber', 't']
for k in HARMONICS:
    features += [f'sin{k}', f'cos{k}']
X = sm.add_constant(data[features], has_constant='add')
y = data['Ozone']
model = sm.OLS(y, X).fit()
print(model.summary())

beta_hat = model.params.values
cov_beta = model.cov_params().values
resid = model.resid.values

# ---------------- 4) Horizonte ----------------
d_end = data['Date'].iloc[-1]
forecast_dates = pd.date_range(d_end + timedelta(days=1), periods=365*11, freq='D')
start_t = data['t'].iloc[-1] + 1

# --------------- Funciones auxiliares --------
def draw_block_residuals(resid_array, n, block_len):
    """Bootstrap circular por bloques."""
    m = int(np.ceil(n / block_len))
    starts = np.random.randint(0, len(resid_array), size=m)
    out = np.concatenate([
        resid_array[s:(s+block_len)] if s+block_len <= len(resid_array)
        else np.r_[resid_array[s:], resid_array[:(s+block_len-len(resid_array))]]
        for s in starts
    ])
    return out[:n]

def iterative_forecast(beta_vec, history, solar_series, start_t, resid_vec=None):
    preds = []
    hist = history.copy()
    t_cur = start_t
    for i, date in enumerate(forecast_dates):
        vals = {f'Ozone_lag{lag}': hist['Ozone'].iloc[-lag] for lag in LAGS}
        vals['SunspotNumber'] = solar_series.get(date, solar_series.iloc[-1])
        vals['t'] = t_cur
        for k in HARMONICS:
            vals[f'sin{k}'] = np.sin(2 * np.pi * k * t_cur / T_SEASON)
            vals[f'cos{k}'] = np.cos(2 * np.pi * k * t_cur / T_SEASON)

        exog = sm.add_constant(pd.DataFrame([vals]), has_constant='add')[X.columns]
        mu = float(exog.values @ beta_vec)

        y_next = mu + (resid_vec[i] if resid_vec is not None else 0.0)
        preds.append(y_next)
        hist.loc[date] = y_next
        t_cur += 1
    return np.array(preds)

# --------------- 6) Bootstrap robusto --------
history_init = data.set_index('Date')['Ozone'].to_frame()
solar_series = df_sp.set_index('Date')['SunspotNumber']

preds_mat = np.zeros((BOOTSTRAPS, len(forecast_dates)), dtype=float)

for b in range(BOOTSTRAPS):
    beta_draw = np.random.multivariate_normal(beta_hat, cov_beta)
    eps_h = draw_block_residuals(resid, len(forecast_dates), BLOCK_LEN)
    preds_mat[b, :] = iterative_forecast(beta_draw, history_init, solar_series, start_t, resid_vec=eps_h)

print(f"✅ Bootstrap robusto completado con {BOOTSTRAPS} réplicas.")

# --------------- 7) Estadísticos -------------
pct_lo = 100 * ALPHA/2
pct_hi = 100 * (1 - ALPHA/2)
mean_fc = preds_mat.mean(axis=0)
lo = np.percentile(preds_mat, pct_lo, axis=0)
hi = np.percentile(preds_mat, pct_hi, axis=0)

df_fc = pd.DataFrame({'Date': forecast_dates,
                      'Ozone_pred': mean_fc,
                      'lower': lo,
                      'upper': hi})

# -------------- 7bis) Exportar trayectorias ---
if SAVE_TRAJ:
    traj_df = pd.DataFrame(preds_mat.T, columns=[f'boot_{i}' for i in range(BOOTSTRAPS)])
    traj_df.insert(0, 'Date', forecast_dates)
    traj_df.to_parquet('../data/processed/forecast_ols_traj.parquet', index=False)
    traj_df.to_csv('../data/processed/forecast_ols_traj.csv', index=False)

    if SAVE_LONG:
        traj_long = traj_df.melt('Date', var_name='bootstrap_id', value_name='Ozone_pred')
        traj_long.to_parquet('../data/processed/forecast_ols_traj_long.parquet', index=False)
        traj_long.to_csv('../data/processed/forecast_ols_traj_long.csv', index=False)

# --------------- 8) Guardar resumen ----------
os.makedirs('../data/processed', exist_ok=True)
df_fc.to_parquet('../data/processed/forecast_ols.parquet', index=False)

# --------------- 9) Gráficos -----------------
# Media + banda
plt.figure(figsize=(10,4))
plt.plot(data['Date'], data['Ozone'], label='Histórico')
plt.plot(df_fc['Date'], df_fc['Ozone_pred'], label='Pronóstico')
plt.fill_between(df_fc['Date'], df_fc['lower'], df_fc['upper'], alpha=0.2,
                 label=f'{int((1-ALPHA)*100)}% banda')
plt.legend()
plt.title('Forecast Ozone 2026–2036 con Fourier Armónicos (Bootstrap robusto)')
plt.tight_layout()
plt.savefig('../data/processed/forecast_ols.png')

# Trayectorias individuales (opcional)
if SHOW_PATHS:
    idx = np.random.choice(BOOTSTRAPS, size=min(N_PATHS_TO_SHOW, BOOTSTRAPS), replace=False)
    plt.figure(figsize=(10,4))
    plt.plot(data['Date'], data['Ozone'], label='Histórico', linewidth=1.2)
    for j in idx:
        plt.plot(forecast_dates, preds_mat[j, :], alpha=0.15, linewidth=0.8)
    plt.plot(forecast_dates, mean_fc, label='Media pronóstico', linewidth=1.5)
    plt.fill_between(forecast_dates, lo, hi, alpha=0.2, label='95% banda')
    plt.legend()
    plt.title('Trayectorias bootstrap del pronóstico de Ozono')
    plt.tight_layout()
    plt.savefig('../data/processed/forecast_ols_paths.png')

print('💾 Forecast robusto y trayectorias guardados.')

