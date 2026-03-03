#!/usr/bin/env python3
"""
chi2_suite.py

Calcula una batería de diagnósticos sobre residuos de modelos:
- Chi2 Global (bondad de ajuste global de residuos)
- Shapiro–Wilk (normalidad)
- Breusch–Pagan (homocedasticidad)
- Durbin–Watson (autocorrelación de orden 1)
- Ljung–Box (autocorrelación conjunta a varios rezagos)

Dos modos de uso:
1) Ajustar OLS y diagnosticar:
   - 'basic': OLS simple Ozone ~ SunspotNumber
   - 'aug'  : OLS con lags de Ozone + armónicos de Fourier + SunspotNumber
   Ejemplo:
   python chi2_suite.py --fit-ols aug \
     --ozone ../data/processed/ozone_2005_2025_clean.parquet \
     --sunspots ../data/processed/sunspots_2005_2025_clean.parquet \
     --oz-lags 1 2 3 11 12 --fourier-K 3 --fourier-period 365 \
     --lags-lb 10 20 --out-csv ../data/processed/chi2_diagnostics_aug.csv

2) Cargar residuos ya calculados:
   python chi2_suite.py --residuals ../data/processed/model_compare_residuals.parquet \
     --resid-col e_OLS --lags-lb 10 20 \
     --out-csv ../data/processed/chi2_diagnostics_from_resid.csv
"""

import argparse
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from pathlib import Path
from typing import List, Tuple, Optional

from statsmodels.stats.diagnostic import het_breuschpagan, acorr_ljungbox
from statsmodels.stats.stattools import durbin_watson
from scipy.stats import shapiro, chi2
import matplotlib.pyplot as plt


# ---------------- Utilidades ----------------

def add_fourier(t: np.ndarray, period: int = 365, K: int = 3) -> pd.DataFrame:
    """Genera armónicos de Fourier sin/cos hasta K para periodo 'period'."""
    out = {}
    for k in range(1, K + 1):
        out[f"sin{k}"] = np.sin(2 * np.pi * k * t / period)
        out[f"cos{k}"] = np.cos(2 * np.pi * k * t / period)
    return pd.DataFrame(out)


def add_lags(series: pd.Series, lags: List[int]) -> pd.DataFrame:
    """Crea columnas con rezagos de 'series'."""
    df = pd.DataFrame(index=series.index)
    for L in lags:
        df[f"{series.name}_lag{L}"] = series.shift(L)
    return df


def chi2_global(residuals: np.ndarray) -> Tuple[float, int, float]:
    """
    Chi2 global: suma(resid^2 / var(resid)) ~ Chi2(df=n) si residuos ~ N(0, sigma^2).
    Devuelve (estadístico, gl, p-valor).
    """
    resid = np.asarray(residuals, dtype=float)
    n = resid.size
    var = np.var(resid, ddof=1)
    if not np.isfinite(var) or var <= 0:
        return np.nan, n, np.nan
    stat = np.sum((resid ** 2) / var)
    p = 1 - chi2.cdf(stat, df=n)
    return float(stat), n, float(p)


def run_diagnostics(residuals: np.ndarray, X_for_BP: Optional[pd.DataFrame],
                    lags_lb: List[int]) -> pd.DataFrame:
    """
    Ejecuta pruebas sobre residuos y devuelve tabla con: Test, Estadístico, g.l., p-valor.
    X_for_BP puede ser None; en ese caso BP no se calcula (o se usa sólo constante).
    """
    rows = []

    # 1) Chi2 Global
    stat, df_, p = chi2_global(residuals)
    rows.append(["Chi2 Global", stat, df_, p])

    # 2) Shapiro–Wilk (nota: para N>5000 SciPy advierte sobre p)
    try:
        sw_stat, sw_p = shapiro(residuals)
        rows.append(["Shapiro–Wilk", sw_stat, "-", sw_p])
    except Exception:
        rows.append(["Shapiro–Wilk", np.nan, "-", np.nan])

    # 3) Breusch–Pagan
    try:
        Xbp = X_for_BP if X_for_BP is not None else pd.DataFrame({"const": 1}, index=np.arange(len(residuals)))
        if "const" not in Xbp.columns:
            Xbp = sm.add_constant(Xbp, has_constant='add')
        bp_stat, bp_p, _, _ = het_breuschpagan(residuals, Xbp)
        gl = Xbp.shape[1] - 1  # grados de libertad aproximados
        rows.append(["Breusch–Pagan", bp_stat, gl, bp_p])
    except Exception:
        rows.append(["Breusch–Pagan", np.nan, "-", np.nan])

    # 4) Durbin–Watson
    try:
        dw = durbin_watson(residuals)
        rows.append(["Durbin–Watson", dw, "-", "-"])
    except Exception:
        rows.append(["Durbin–Watson", np.nan, "-", "-"])

    # 5) Ljung–Box
    for L in lags_lb:
        try:
            lb = acorr_ljungbox(residuals, lags=[L], return_df=True).iloc[0]
            rows.append([f"Ljung–Box (lag={L})", float(lb["lb_stat"]), L, float(lb["lb_pvalue"])])
        except Exception:
            rows.append([f"Ljung–Box (lag={L})", np.nan, L, np.nan])

    return pd.DataFrame(rows, columns=["Test", "Estadístico", "g.l.", "p-valor"])


def fit_ols(mode: str,
            oz_path: Path,
            sp_path: Path,
            oz_lags: List[int],
            fourier_K: int,
            fourier_period: int):
    """
    Ajusta OLS en modo:
      - 'basic': Ozone ~ SunspotNumber
      - 'aug'  : Ozone ~ [Ozone_lags, Fourier, SunspotNumber]
    Devuelve (residuals, X_para_BP, resumen_modelo(str))
    """
    oz = pd.read_parquet(oz_path)
    sp = pd.read_parquet(sp_path)
    df = pd.merge(oz, sp, on="Date").sort_values("Date").reset_index(drop=True)
    df["t"] = np.arange(len(df))

    if mode == "basic":
        X = sm.add_constant(df[["SunspotNumber"]], has_constant='add')
        y = df["Ozone"]
        res = sm.OLS(y, X).fit()
        return res.resid.values, X, res.summary().as_text()

    elif mode == "aug":
        X_parts = []
        # lags de ozono
        if oz_lags:
            X_parts.append(add_lags(df["Ozone"], oz_lags))
        # armónicos
        if fourier_K and fourier_K > 0:
            X_parts.append(add_fourier(df["t"].values, period=fourier_period, K=fourier_K))
        # solar
        X_parts.append(df[["SunspotNumber"]])
        X = pd.concat(X_parts, axis=1)
        X = sm.add_constant(X, has_constant='add')

        valid = X.dropna().index
        y = df.loc[valid, "Ozone"]
        X = X.loc[valid]

        res = sm.OLS(y, X).fit()
        return res.resid.values, X, res.summary().as_text()

    else:
        raise ValueError("mode debe ser 'basic' o 'aug'")


def quick_plot(residuals: np.ndarray, out_fig: Optional[Path] = None):
    """Histograma y serie temporal de residuos (rápido)."""
    fig, ax = plt.subplots(1, 2, figsize=(10, 3))
    ax[0].plot(residuals, lw=0.6)
    ax[0].set_title("Residuos (serie)")
    ax[0].axhline(0, color='k', lw=0.8)

    ax[1].hist(residuals, bins=40)
    ax[1].set_title("Residuos (histograma)")

    plt.tight_layout()
    if out_fig:
        out_fig.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_fig, dpi=150)
    plt.close(fig)


# ------------------- Main ---------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fit-ols", choices=["basic", "aug"], help="Ajustar OLS y diagnosticar")
    p.add_argument("--residuals", type=str, help="Ruta a CSV/Parquet con residuos (o varias columnas)")
    p.add_argument("--ozone", type=str, help="Parquet de ozono si usas --fit-ols")
    p.add_argument("--sunspots", type=str, help="Parquet de manchas si usas --fit-ols")
    p.add_argument("--oz-lags", nargs="+", type=int, default=[1, 2, 3, 11, 12], help="Lags para modo 'aug'")
    p.add_argument("--fourier-K", type=int, default=3, help="Número de armónicos de Fourier")
    p.add_argument("--fourier-period", type=int, default=365, help="Periodo para Fourier")
    p.add_argument("--resid-col", type=str, default=None, help="Columna con residuos si pasas archivo con varias columnas")
    p.add_argument("--lags-lb", nargs="+", type=int, default=[10, 20], help="Lags para Ljung–Box")
    p.add_argument("--out-csv", type=str, help="Ruta CSV de salida")
    p.add_argument("--out-json", type=str, help="Ruta JSON de salida")
    p.add_argument("--out-fig", type=str, help="PNG rápido de residuos")
    args = p.parse_args()

    # Determinar modo de trabajo
    if args.fit_ols:
        if not args.ozone or not args.sunspots:
            p.error("--ozone y --sunspots son requeridos cuando se usa --fit-ols")
        residuals, X_bp, summary_txt = fit_ols(
            mode=args.fit_ols,
            oz_path=Path(args.ozone),
            sp_path=Path(args.sunspots),
            oz_lags=args.oz_lags,
            fourier_K=args.fourier_K,
            fourier_period=args.fourier_period
        )
        print("\n=== Resumen OLS ===")
        print(summary_txt)

    elif args.residuals:
        path = Path(args.residuals)
        if path.suffix.lower() == ".parquet":
            df_res = pd.read_parquet(path)
        else:
            df_res = pd.read_csv(path)
        if args.resid_col:
            residuals = df_res[args.resid_col].values
        else:
            # Toma la primera columna numérica
            candidates = df_res.select_dtypes(include=[np.number]).columns
            if len(candidates) == 0:
                raise ValueError("No se encontraron columnas numéricas de residuos.")
            residuals = df_res[candidates[0]].values
        X_bp = None  # sin regresores originales
        summary_txt = None
    else:
        p.error("Debes especificar --fit-ols (basic/aug) o --residuals <archivo>.")

    # Diagnósticos
    tabla = run_diagnostics(residuals, X_bp, args.lags_lb)
    print("\n=== Diagnósticos ===")
    print(tabla.to_string(index=False))

    # Salidas
    if args.out_csv:
        Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
        tabla.to_csv(args.out_csv, index=False)
        print(f"💾 Guardado CSV: {args.out_csv}")

    if args.out_json:
        outj = Path(args.out_json)
        outj.parent.mkdir(parents=True, exist_ok=True)
        outj.write_text(json.dumps(tabla.to_dict(orient="records"), ensure_ascii=False, indent=2))
        print(f"💾 Guardado JSON: {outj}")

    if args.out_fig:
        quick_plot(residuals, Path(args.out_fig))
        print(f"🖼️  Figura de residuos: {args.out_fig}")


if __name__ == "__main__":
    main()

