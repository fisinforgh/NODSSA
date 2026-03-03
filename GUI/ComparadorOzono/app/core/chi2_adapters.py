# -*- coding: utf-8 -*-
from __future__ import annotations
import numpy as np
import pandas as pd
from .chi2 import linear_model_chi2, interpret_coeffs

def chi2_from_binned(df_bins: pd.DataFrame, alpha: float = 0.05) -> dict:
    """
    Drop-in para tu pipeline actual.
    Espera columnas: 'sun_bin_center', 'y_mean', 'sigma', y opcionalmente 'occ' o 'n'.
    NO modifica tu lógica: sólo toma lo que ya produces y calcula χ².
    """
    x = df_bins["sun_bin_center"].to_numpy(float)
    y = df_bins["y_mean"].to_numpy(float)
    s = df_bins["sigma"].to_numpy(float)
    
    # Extraer número total de observaciones si está disponible
    n_obs = None
    if "occ" in df_bins.columns:
        n_obs = int(df_bins["occ"].sum())
    elif "n" in df_bins.columns:
        n_obs = int(df_bins["n"].sum())
    
    res = linear_model_chi2(x, y, s, alpha=alpha, n_obs=n_obs)
    res["interpretacion"] = interpret_coeffs(res["a0"], res["a1"])
    return res

def to_row(lat: float, lon: float, res: dict, min_occ: int = 1, pct_reduction: float = 0.0) -> dict:
    """Devuelve un renglón con el formato de tu tabla 'Test–χ²–g.l.–p' (sin corte)."""
    return dict(
        lat=float(lat), lon=float(lon),
        N=int(res.get("N", 0)), nu=int(res.get("nu", 0)),
        chi2=float(res.get("chi2", float("nan"))),
        chi2_red=float(res.get("chi2_red", float("nan"))),
        p_value=float(res.get("p_value", float("nan"))),
        p_cdf=float(res.get("p_cdf", float("nan"))),
        chi2_lo=float(res.get("chi2_lo", float("nan"))),
        chi2_hi=float(res.get("chi2_hi", float("nan"))),
        veredict_chi=res.get("veredict_chi", "NO PASA"),
        veredict_tutor=res.get("veredict_tutor", "NO PASA"),
        a0=float(res.get("a0", float("nan"))),
        a1=float(res.get("a1", float("nan"))),
        sigma_a0=float(res.get("sigma_a0", float("nan"))),
        sigma_a1=float(res.get("sigma_a1", float("nan"))),
        min_occ=int(min_occ), pct_reduction=float(pct_reduction)
    )
