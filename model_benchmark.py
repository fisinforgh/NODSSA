#!/usr/bin/env python3
"""
model_benchmark.py

Compara modelos OLS vs SARIMAX vs VAR (con manchas solares) y consolida métricas.
Entradas:
  data/processed/ozone_2005_2025_clean.parquet
  data/processed/sunspots_2005_2025_clean.parquet

Salidas:
  data/processed/model_compare_summary.csv
  data/processed/model_compare_residuals.parquet
  docs/figs/bench/compare_test.png
  docs/figs/bench/pred_vs_obs.png

Modo rápido:
  python python/model_benchmark.py --fast
Ejecución normal:
  python python/model_benchmark.py
"""

from __future__ import annotations
import os, time, warnings, argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import statsmodels.api as sm
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.api import VAR
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# ---------------- Configuración global ----------------
warnings.filterwarnings("ignore")
np.random.seed(42)

# ---------------- Argumentos CLI ----------------------
parser = argparse.ArgumentParser(description="Benchmark OLS vs SARIMAX vs VAR")
parser.add_argument("--fast", action="store_true",
                    help="Usa grid pequeño de SARIMAX y rezagos VAR reducidos para ejecución rápida.")
args = parser.parse_args()

# ---------------- Rutas -------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
FIGS = ROOT / "docs" / "figs" / "bench"
FIGS.mkdir(parents=True, exist_ok=True)

OZ_PATH = DATA / "ozone_2005_2025_clean.parquet"
SP_PATH = DATA / "sunspots_2005_2025_clean.parquet"

# ---------------- Utilidades --------------------------
def add_fourier(t: np.ndarray, period: int = 365, K: int = 3) -> pd.DataFrame:
    """Senos y cosenos para estacionalidad (Fourier)."""
    out = {}
    for k in range(1, K + 1):
        ang = 2 * np.pi * k * t / period
        out[f"sin{k}"] = np.sin(ang)
        out[f"cos{k}"] = np.cos(ang)
    return pd.DataFrame(out, index=None)

def add_lags(df: pd.DataFrame, col: str, lags: list[int]) -> pd.DataFrame:
    """Crea columnas de rezagos de 'col'."""
    out = pd.DataFrame(index=df.index)
    for L in lags:
        out[f"{col}_lag{L}"] = df[col].shift(L)
    return out

def mape(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    # Evita divisiones por cero
    eps = 1e-8
    return np.mean(np.abs((y_true - y_pred) / (np.abs(y_true) + eps))) * 100.0

def diebold_mariano(e1: np.ndarray, e2: np.ndarray) -> float:
    """Estadístico DM aprox. normal para h=1 y pérdida cuadrática."""
    d = e1 ** 2 - e2 ** 2
    dbar = d.mean()
    # Newey-West con lag=1
    gamma0 = np.var(d, ddof=1)
    gamma1 = np.cov(d[1:], d[:-1], ddof=1)[0, 1]
    var_d = gamma0 + 2 * gamma1
    return dbar / np.sqrt(var_d / len(d)) if var_d > 0 else np.nan

def summarize_metrics(name: str, y_true: pd.Series, y_pred: pd.Series, aic=np.nan, bic=np.nan) -> dict:
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae  = float(mean_absolute_error(y_true, y_pred))
    r2   = float(r2_score(y_true, y_pred))
    mm   = float(mape(y_true, y_pred))
    return {"Model": name, "RMSE": rmse, "MAE": mae, "MAPE_%": mm, "R2": r2, "AIC": aic, "BIC": bic}

# ---------------- 1) Cargar datos ---------------------
t0 = time.time()
oz = pd.read_parquet(OZ_PATH)
sp = pd.read_parquet(SP_PATH)
df = (pd.merge(oz, sp, on="Date")
        .sort_values("Date")
        .reset_index(drop=True))
df["t"] = np.arange(len(df))
print(f"✓ Datos cargados ({len(df)} filas) en {time.time()-t0:.2f}s")

# Train/Test split crono (80/20)
split_idx = int(len(df) * 0.8)
df_train = df.iloc[:split_idx].copy()
df_test  = df.iloc[split_idx:].copy()

# ---------------- 2) OLS ------------------------------
t1 = time.time()
LAGS = [1, 2, 3, 11, 12]  # parsimonioso y efectivo
Xtr = pd.concat([
    add_lags(df_train, "Ozone", LAGS),
    add_fourier(df_train["t"].values, 365, 3),
    df_train[["SunspotNumber"]],
], axis=1)
Xtr = sm.add_constant(Xtr, has_constant="add")

Xte = pd.concat([
    add_lags(df, "Ozone", LAGS).iloc[split_idx:],
    add_fourier(df_test["t"].values, 365, 3),
    df_test[["SunspotNumber"]],
], axis=1)
Xte = sm.add_constant(Xte, has_constant="add")

# Alinear y dropear NaN por lags
valid_tr = Xtr.dropna().index
ytr = df_train.loc[valid_tr, "Ozone"]
Xtr = Xtr.loc[valid_tr]

valid_te = Xte.dropna().index
Xte = Xte.loc[valid_te]
yte = df.loc[valid_te, "Ozone"]

ols_fit = sm.OLS(ytr, Xtr).fit()
yhat_ols = ols_fit.predict(Xte)
print(f"✓ OLS listo en {time.time()-t1:.2f}s  (params={len(ols_fit.params)})")

# ---------------- 3) SARIMAX --------------------------
t2 = time.time()

if args.fast:
    orders    = [(1,1,1)]
    seasonals = [(1,1,1,365)]
    maxiter   = 150
else:
    orders    = [(1,1,1), (1,1,2), (2,1,1)]
    seasonals = [(0,1,1,365), (1,1,0,365), (1,1,1,365)]
    maxiter   = 250

best_aic = np.inf
best_mod = None

exog_tr = pd.concat([add_fourier(df_train["t"].values, 365, 3),
                     df_train[["SunspotNumber"]]], axis=1)

for order in orders:
    for seasonal_order in seasonals:
        try:
            mod = SARIMAX(
                df_train["Ozone"],
                order=order,
                seasonal_order=seasonal_order,
                exog=exog_tr,
                enforce_stationarity=False,
                enforce_invertibility=False
            )
            res = mod.fit(disp=False, maxiter=maxiter)
            if res.aic < best_aic:
                best_aic = res.aic
                best_mod = (mod, res, order, seasonal_order)
        except Exception:
            continue

if best_mod is None:
    raise RuntimeError("No se pudo ajustar ningún SARIMAX del grid.")

sarimax_mod, sarimax_res, order_best, seas_best = best_mod
exog_te = pd.concat([add_fourier(df_test["t"].values, 365, 3),
                     df_test[["SunspotNumber"]]], axis=1)
yhat_sarimax = sarimax_res.get_forecast(steps=len(df_test), exog=exog_te).predicted_mean
yhat_sarimax = pd.Series(yhat_sarimax, index=df_test.index)
print(f"✓ SARIMAX {order_best}x{seas_best} listo en {time.time()-t2:.2f}s  (AIC={sarimax_res.aic:.1f})")

# ---------------- 4) VAR (bivariado, en diferencias) ---
t3 = time.time()
df_var = df[["Ozone", "SunspotNumber"]].copy()
df_var_diff = df_var.diff().dropna()

# Split ajustado por diff (pierde 1 fila)
split_idx_var = max(split_idx, 1)
train_var = df_var_diff.iloc[:split_idx_var-1]

maxlags = 12 if args.fast else 30
model_var = VAR(train_var)
sel = model_var.select_order(maxlags=maxlags)
p = int(sel.aic or 5)
p = max(1, min(p, maxlags))
var_res = model_var.fit(p)

# Forecast de diferencias y reconstrucción a niveles
steps = len(df) - split_idx
fc_diff = var_res.forecast(train_var.values[-p:], steps=steps)
fc_diff = pd.DataFrame(fc_diff, index=df.index[split_idx:], columns=train_var.columns)

# nivel base al final del train original
y0 = df_var.iloc[split_idx-1]
fc_levels = fc_diff.cumsum() + y0.values
yhat_var = pd.Series(fc_levels["Ozone"].values, index=df.index[split_idx:])
print(f"✓ VAR(p={p}) listo en {time.time()-t3:.2f}s")

# ---------------- 5) Métricas y consolidación ----------
common_idx = yte.index  # ya está alineado con Xte
preds = {
    "OLS":     yhat_ols.reindex(common_idx),
    "SARIMAX": yhat_sarimax.reindex(common_idx),
    "VAR":     yhat_var.reindex(common_idx),
}

rows = []
rows.append(summarize_metrics("OLS",     yte, preds["OLS"],     aic=ols_fit.aic,      bic=ols_fit.bic))
rows.append(summarize_metrics("SARIMAX", yte, preds["SARIMAX"], aic=sarimax_res.aic,  bic=sarimax_res.bic))
rows.append(summarize_metrics("VAR",     yte, preds["VAR"]))

summary = pd.DataFrame(rows).sort_values("RMSE").reset_index(drop=True)
summary_path = DATA / "model_compare_summary.csv"
summary.to_csv(summary_path, index=False)
print(f"💾 Métricas guardadas en {summary_path}")

# Guardar residuos para análisis posterior
resids = pd.DataFrame({
    "Date": df.loc[common_idx, "Date"].values,
    "y_test": yte.values,
    "e_OLS": (yte - preds["OLS"]).values,
    "e_SARIMAX": (yte - preds["SARIMAX"]).values,
    "e_VAR": (yte - preds["VAR"]).values,
})
resids_path = DATA / "model_compare_residuals.parquet"
resids.to_parquet(resids_path, index=False)
print(f"💾 Residuos guardados en {resids_path}")

# ---------------- 6) Diebold-Mariano -------------------
try:
    dm_os = diebold_mariano(resids["e_OLS"].values,     resids["e_SARIMAX"].values)
    dm_ov = diebold_mariano(resids["e_OLS"].values,     resids["e_VAR"].values)
    dm_sv = diebold_mariano(resids["e_SARIMAX"].values, resids["e_VAR"].values)
    print(f"DM(OLS vs SARIMAX) ~ N(0,1): {dm_os:.2f}")
    print(f"DM(OLS vs VAR)     ~ N(0,1): {dm_ov:.2f}")
    print(f"DM(SARIMAX vs VAR) ~ N(0,1): {dm_sv:.2f}")
except Exception as e:
    print(f"⚠️  DM no calculado: {e}")

# ---------------- 7) Gráficas --------------------------
plt.figure(figsize=(11,4))
plt.plot(df.loc[common_idx, "Date"], yte, label="Observado", linewidth=1.5)
for name, yhat in preds.items():
    plt.plot(df.loc[common_idx, "Date"], yhat, label=name, alpha=0.9)
plt.title("Comparación de modelos (test)")
plt.xlabel("Fecha"); plt.ylabel("Ozone (DU)")
plt.legend(); plt.tight_layout()
fig1p = FIGS / "compare_test.png"
plt.savefig(fig1p, dpi=150)

plt.figure(figsize=(11,4))
plt.plot(df.loc[common_idx, "Date"], resids["e_OLS"],     label="e_OLS",     alpha=0.9)
plt.plot(df.loc[common_idx, "Date"], resids["e_SARIMAX"], label="e_SARIMAX", alpha=0.9)
plt.plot(df.loc[common_idx, "Date"], resids["e_VAR"],     label="e_VAR",     alpha=0.9)
plt.axhline(0, color='k', linewidth=0.8)
plt.title("Residuos en test")
plt.xlabel("Fecha"); plt.ylabel("Error (DU)")
plt.legend(); plt.tight_layout()
fig2p = FIGS / "pred_vs_obs.png"
plt.savefig(fig2p, dpi=150)

print(f"🖼  Figuras guardadas en:\n   - {fig1p}\n   - {fig2p}")
print(f"✅ Benchmark completado en {time.time()-t0:.2f}s")

