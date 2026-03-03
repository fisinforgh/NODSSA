# python/GUI/ComparadorOzono/app/core/chi2_bins.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple
import math
import numpy as np
import pandas as pd
from scipy.stats import chi2 as chi2dist
from matplotlib.figure import Figure

@dataclass
class Chi2BinsResult:
    N: int
    nu: int
    chi2: float
    chi2_red: float
    p_two_sided: float
    p_cdf: float
    chi2_lo: float
    chi2_hi: float
    a0: float
    a1: float
    sigma_a0: float
    sigma_a1: float
    min_occ: Optional[int]
    pct_reduction: float
    veredict_chi: bool
    veredict_tutor: bool

REQ_BINS = {"sun_bin", "o3_mean", "sigma", "occ"}

def _wls_fit(x: np.ndarray, y: np.ndarray, s: np.ndarray):
    """Ajuste lineal ponderado: O3 = a0 + a1*x con pesos 1/sigma^2."""
    w = 1.0 / np.maximum(s, 1e-9) ** 2
    X = np.vstack([np.ones_like(x), x]).T
    XT_W = X.T * w
    cov = np.linalg.inv(XT_W @ X)
    beta = cov @ (XT_W @ y)
    return beta, cov

def compute_chi2_from_bins(bins: pd.DataFrame, min_occ: Optional[int]=None, alpha: float=0.05):
    """
    Calcula χ², ν, χ²/ν, p-values y veredictos para bins de O3 vs 'sun_bin'.
    bins requiere: ['sun_bin','o3_mean','sigma','occ'].
    """
    if not REQ_BINS.issubset(bins.columns):
        raise ValueError(f"Faltan columnas: {REQ_BINS - set(bins.columns)}")
    data = bins if min_occ is None else bins[bins["occ"] >= int(min_occ)]
    N = len(data)
    if N < 3:
        raise ValueError("Muy pocos bins tras el filtro (N<3).")

    x = data["sun_bin"].to_numpy(float)
    y = data["o3_mean"].to_numpy(float)
    s = data["sigma"].to_numpy(float)

    (a0, a1), cov = _wls_fit(x, y, s)
    yhat = a0 + a1 * x

    chi2 = float(np.sum(((y - yhat) / np.maximum(s, 1e-12)) ** 2))
    nu = max(N - 2, 1)
    chi2_red = chi2 / nu

    cdf = float(chi2dist.cdf(chi2, df=nu))
    lo  = float(chi2dist.ppf(alpha/2.0, df=nu))
    hi  = float(chi2dist.ppf(1.0 - alpha/2.0, df=nu))
    p_two = 2.0 * min(cdf, 1.0 - cdf)

    ver_chi   = (chi2 >= lo) and (chi2 <= hi)
    ver_tutor = (cdf < 0.975)  # criterio práctico del tutor

    pct = 0.0 if min_occ is None else 100.0 * (1.0 - (len(data) / len(bins)))

    # Figura informativa
    fig = Figure(constrained_layout=True)
    ax = fig.add_subplot(111)
    ax.errorbar(x, y, yerr=s, fmt="o", alpha=0.85, label="Promedio O₃ por bin")
    xs = np.linspace(x.min(), x.max(), 200)
    ax.plot(xs, a0 + a1 * xs, lw=2.0, label="Ajuste ponderado O₃ = a₀ + a₁·S")
    ax.set_xlabel("Manchas solares (bin)")
    ax.set_ylabel("O₃ (DU)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    ax.text(
        0.02, 0.98,
        (f"N={N}, ν={nu}\n"
         f"χ²={chi2:.3f}, χ²/ν={chi2_red:.3f}\n"
         f"a₀={a0:.3f} ± {math.sqrt(max(cov[0,0],0)):.3f} DU\n"
         f"a₁={a1:.5f} ± {math.sqrt(max(cov[1,1],0)):.5f} DU/mancha\n"
         f"p(two)={p_two:.4f}, CDF={cdf:.4f}\n"
         f"IC χ²[2.5%,97.5%]=[{lo:.2f},{hi:.2f}]\n"
         f"Prob={p_two:.4e}\n"
         f"min_occ={min_occ if min_occ is not None else '-'}, %↓={pct:.1f}%"),
        transform=ax.transAxes, va="top", ha="left",
        fontsize=9, family="monospace",
        bbox=dict(facecolor="white", alpha=0.85, edgecolor="#ccc")
    )

    res = Chi2BinsResult(
        N=N, nu=nu, chi2=chi2, chi2_red=chi2_red, p_two_sided=p_two, p_cdf=cdf,
        chi2_lo=lo, chi2_hi=hi, a0=a0, a1=a1,
        sigma_a0=math.sqrt(max(cov[0,0],0)), sigma_a1=math.sqrt(max(cov[1,1],0)),
        min_occ=min_occ, pct_reduction=pct,
        veredict_chi=ver_chi, veredict_tutor=ver_tutor
    )
    return res, fig

def sweep_min_occ(bins: pd.DataFrame, occ_values: Iterable[int]=range(3,21), alpha: float=0.05):
    """Barrido de min_occ para justificar umbral (χ²_red vs min_occ)."""
    rows = []
    for m in occ_values:
        try:
            r, _ = compute_chi2_from_bins(bins, min_occ=m, alpha=alpha)
            rows.append({"min_occ": m, "chi2_red": r.chi2_red, "N": r.N, "nu": r.nu,
                         "pct_reduction": r.pct_reduction, "p_two_sided": r.p_two_sided,
                         "p_cdf": r.p_cdf, "veredict_chi": r.veredict_chi,
                         "veredict_tutor": r.veredict_tutor})
        except Exception:
            rows.append({"min_occ": m, "chi2_red": np.nan, "N": 0, "nu": 0,
                         "pct_reduction": np.nan, "p_two_sided": np.nan, "p_cdf": np.nan,
                         "veredict_chi": False, "veredict_tutor": False})
    df = pd.DataFrame(rows)

    fig = Figure(constrained_layout=True)
    ax = fig.add_subplot(111)
    ax.plot(df["min_occ"], df["chi2_red"], marker="o")
    ax.axhspan(1.2, 1.3, alpha=0.08, label="Zona ~1.2–1.3")
    ax.set_xlabel("min_occ")
    ax.set_ylabel("χ²/ν")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    return df, fig

# Convertidores de entrada para "solo reales"
def from_monthly_real(df_monthly: pd.DataFrame) -> pd.DataFrame:
    """
    A partir de: Year,Month,Ozone_mean,Ozone_std,Count
    -> bins ('sun_bin','o3_mean','sigma','occ').
    """
    req = {"Year","Month","Ozone_mean","Ozone_std","Count"}
    if not req.issubset(df_monthly.columns):
        raise ValueError(f"Faltan columnas: {req - set(df_monthly.columns)}")
    sigma = df_monthly["Ozone_std"].astype(float) / np.sqrt(df_monthly["Count"].clip(lower=1).astype(float))
    out = pd.DataFrame({
        "sun_bin": df_monthly["Month"].astype(float).to_numpy(),
        "o3_mean": df_monthly["Ozone_mean"].astype(float).to_numpy(),
        "sigma": sigma.to_numpy(),
        "occ": df_monthly["Count"].astype(int).to_numpy(),
    })
    return out.replace([np.inf, -np.inf], np.nan).dropna()

def from_binned_generic(df_bins: pd.DataFrame) -> pd.DataFrame:
    """
    A partir de: sun_bin_center,y_mean,sigma[,occ]
    -> bins ('sun_bin','o3_mean','sigma','occ').
    """
    req = {"sun_bin_center","y_mean","sigma"}
    if not req.issubset(df_bins.columns):
        raise ValueError(f"Faltan columnas: {req - set(df_bins.columns)}")
    occ = df_bins["occ"].astype(int).to_numpy() if "occ" in df_bins.columns else np.ones(len(df_bins), int)
    out = pd.DataFrame({
        "sun_bin": df_bins["sun_bin_center"].astype(float).to_numpy(),
        "o3_mean": df_bins["y_mean"].astype(float).to_numpy(),
        "sigma": df_bins["sigma"].astype(float).to_numpy(),
        "occ": occ,
    })
    return out.replace([np.inf, -np.inf], np.nan).dropna()
