# -*- coding: utf-8 -*-
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np

# SciPy opcional: exacto si está disponible; si no, Wilson–Hilferty
try:
    from scipy.stats import chi2 as _chi2  # type: ignore
    _HAVE_SCIPY = True
except Exception:
    _HAVE_SCIPY = False

ALPHA_DEFAULT = 0.05
SIGMA_FLOOR_DU_DEFAULT = 4.0  # piso recomendado por el tutor

# ----------------- utilidades χ² -----------------
def _normal_ppf_approx(p: float) -> float:
    """Aproximación de la inversa de la CDF normal (Acklam)."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
          4.374664141464968e+00,  2.938163982698783e+00]
    d = [ 7.784695709041462e-03,  3.224671290700398e-01,
          2.445134137142996e+00,  3.754408661907416e+00]
    plow = 0.02425; phigh = 1 - plow
    if p < plow:
        q = math.sqrt(-2*math.log(p))
        return (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
               ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
    elif p > phigh:
        q = math.sqrt(-2*math.log(1-p))
        return -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
                 ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
    else:
        q = p - 0.5; r = q*q
        return (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5]) * q / \
               (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1)

def chi2_quantiles(df: int, alpha: float) -> Tuple[float, float]:
    """Cuantiles inferior/superior (prueba bilateral al nivel alpha)."""
    if df <= 0:
        return (float("nan"), float("nan"))
    if _HAVE_SCIPY:
        return float(_chi2.ppf(alpha/2.0, df)), float(_chi2.ppf(1.0 - alpha/2.0, df))
    # Wilson–Hilferty (aprox)
    mu = 1 - 2/(9*df); sigma = math.sqrt(2/(9*df))
    def approx_ppf(p: float) -> float:
        z = _normal_ppf_approx(p); t = mu + sigma*z
        return df * (t**3)
    return approx_ppf(alpha/2.0), approx_ppf(1.0 - alpha/2.0)

def chi2_cdf(x: float, df: int) -> float:
    """CDF de χ² (acumulada desde la izquierda)."""
    if df <= 0 or not math.isfinite(x):
        return float("nan")
    if _HAVE_SCIPY:
        return float(_chi2.cdf(x, df))
    if x <= 0:
        return 0.0
    t = (x/df)**(1/3); mu = 1 - 2/(9*df); sigma = math.sqrt(2/(9*df))
    z = (t - mu)/sigma
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))

# ----------------- ajuste lineal ponderado -----------------
@dataclass
class FitResult:
    a0: float
    a1: float
    sigma_a0: float
    sigma_a1: float

def weighted_linear_fit(x: np.ndarray, y: np.ndarray, sigma: np.ndarray) -> FitResult:
    """
    WLS para y ≈ a0 + a1*x con pesos 1/sigma^2.
    """
    x = np.asarray(x, float); y = np.asarray(y, float); sigma = np.asarray(sigma, float)
    if x.size != y.size or y.size != sigma.size:
        raise ValueError("x, y y sigma deben tener la misma longitud.")
    if np.any(sigma <= 0) or x.size < 2:
        raise ValueError("sigma > 0 y al menos dos puntos.")

    w = 1.0 / (sigma**2)
    X = np.vstack([np.ones_like(x), x]).T
    # Evita W densa: usa multiplicaciones elementales
    XtWX = X.T @ (w[:, None] * X)
    XtWy = X.T @ (w * y)
    try:
        cov = np.linalg.inv(XtWX)
    except np.linalg.LinAlgError:
        cov = np.linalg.pinv(XtWX)

    beta = cov @ XtWy
    a0, a1 = float(beta[0]), float(beta[1])

    yhat = a0 + a1*x
    resid = y - yhat
    N = y.size; dof = max(N - 2, 1)   # k=2
    chi2 = float(np.sum((resid/sigma)**2))
    s2 = chi2 / dof
    var_params = np.diag(cov) * s2
    return FitResult(a0, a1, float(np.sqrt(var_params[0])), float(np.sqrt(var_params[1])))

# ----------------- test χ² (dos colas) -----------------
def chi2_test(y: np.ndarray, yhat: np.ndarray, sigma: np.ndarray,
              alpha: float = ALPHA_DEFAULT, n_obs: int | None = None) -> Dict[str, float | int | str]:
    """
    Prueba bilateral al 95% (por defecto).
    p_value reportado es **bilateral**: 2*min(CDF, 1-CDF).
    'valor tutor' (p_cdf en [0.025, 0.975]) decide PASA/NO PASA adicional.
    
    Args:
        n_obs: Número total de observaciones (si se trabaja con bins, es la suma de ocurrencias).
               Si None, usa y.size (número de bins).
    """
    y = np.asarray(y, float); yhat = np.asarray(yhat, float); sigma = np.asarray(sigma, float)
    N = n_obs if n_obs is not None else y.size
    nu = N - 2
    if nu <= 0:
        return dict(N=N, nu=nu, chi2=float("nan"), chi2_red=float("nan"),
                    p_value=float("nan"), p_cdf=float("nan"),
                    chi2_lo=float("nan"), chi2_hi=float("nan"),
                    side="NA", veredict_chi="NO PASA", veredict_tutor="NO PASA")

    chi2 = float(np.sum(((y - yhat)/sigma)**2))
    chi2_lo, chi2_hi = chi2_quantiles(nu, alpha)
    chi2_red = chi2 / nu
    p_cdf = chi2_cdf(chi2, nu)
    p_two = 2.0 * min(p_cdf, 1.0 - p_cdf)   # bilateral

    # lado para diagnóstico visual (no afecta veredicto)
    side = "OK"
    veredict_chi = "PASA" if (chi2_lo <= chi2 <= chi2_hi) else "NO PASA"
    if chi2 < chi2_lo: side = "izquierda"
    elif chi2 > chi2_hi: side = "derecha"

    # Criterio práctico del tutor: PASA si CDF está en la banda central (2.5%–97.5%)
    veredict_tutor = "PASA" if (0.025 < p_cdf < 0.975) else "NO PASA"

    return dict(N=int(N), nu=int(nu), chi2=float(chi2), chi2_red=float(chi2_red),
                p_value=float(p_two), p_cdf=float(p_cdf),
                chi2_lo=float(chi2_lo), chi2_hi=float(chi2_hi),
                side=side, veredict_chi=veredict_chi, veredict_tutor=veredict_tutor)

def interpret_coeffs(a0: float, a1: float) -> str:
    trend = "aumenta" if a1 > 0 else "disminuye"
    return (f"a₀≈{a0:.1f} DU (línea base con manchas=0); "
            f"a₁≈{a1:.3f} DU/uMS: por cada unidad de mancha el ozono {trend} {abs(a1):.3f} DU.")

def linear_model_chi2(x: np.ndarray, y: np.ndarray, sigma: np.ndarray,
                      alpha: float = ALPHA_DEFAULT, n_obs: int | None = None) -> Dict[str, float | int | str]:
    """
    Pipeline completo desde (x,y,σ): WLS + χ² + veredictos.
    
    Args:
        n_obs: Número total de observaciones (si se trabaja con bins, es la suma de ocurrencias).
               Si None, usa y.size (número de bins).
    """
    order = np.argsort(x)
    x = np.asarray(x, float)[order]; y = np.asarray(y, float)[order]; sigma = np.asarray(sigma, float)[order]
    fit = weighted_linear_fit(x, y, sigma)
    yhat = fit.a0 + fit.a1 * x
    tt = chi2_test(y, yhat, sigma, alpha=alpha, n_obs=n_obs)
    out = dict(a0=fit.a0, a1=fit.a1, sigma_a0=fit.sigma_a0, sigma_a1=fit.sigma_a1)
    out.update(tt)
    return out

# ----------------- helpers para trabajar con BINS -----------------
def sigma_from_bin_floor(y_std: np.ndarray,
                         sigma_floor_du: float = SIGMA_FLOOR_DU_DEFAULT) -> np.ndarray:
    """
    σ por bin = desviación estándar del bin (dispersión física) con piso en DU.
    """
    s = np.asarray(y_std, float)
    s = np.where(np.isfinite(s) & (s > 0), s, sigma_floor_du)
    s = np.maximum(s, sigma_floor_du)
    return s

def chi2_from_binned(df_binned: "pd.DataFrame",
                     sigma_floor_du: float = SIGMA_FLOOR_DU_DEFAULT) -> dict:
    """
    Ejecuta χ²/χ²_red sobre datos binned. Acepta columnas:
      - S_bin (o sun_bin_center, sun_bin)
      - y_mean (o Ozone_mean)
      - sigma  (o sigma_cal, stderr, se)  [preferido]
      - y_std  (opcional; si no hay sigma y hay n -> usa y_std/sqrt(n)]
      - n      (opcional; número total de observaciones por bin para calcular SE y grados de libertad correctos)
      - occ    (alias de n)
    """
    import numpy as np
    try:
        import pandas as pd  # noqa: F401
    except Exception:
        pass

    cols = {c.lower(): c for c in df_binned.columns}
    def pick(*names):
        for n in names:
            if n.lower() in cols:
                return cols[n.lower()]
        return None

    c_sbin  = pick("S_bin","sun_bin_center","sun_bin","s")
    c_ymean = pick("y_mean","ozone_mean","mean","y")
    c_sigma = pick("sigma","sigma_cal","stderr","se")
    c_ystd  = pick("y_std","ozone_std","std")
    c_n     = pick("n","occ","count","num")

    faltan = []
    if not c_sbin:  faltan.append("S_bin")
    if not c_ymean: faltan.append("y_mean")
    if not (c_sigma or c_ystd):
        faltan.append("sigma o y_std")
    if faltan:
        raise ValueError(f"Faltan columnas en binned: {', '.join(faltan)}")

    x = df_binned[c_sbin].to_numpy(float)
    y = df_binned[c_ymean].to_numpy(float)

    if c_sigma:
        sigma = df_binned[c_sigma].to_numpy(float)
    else:
        ystd = df_binned[c_ystd].to_numpy(float)
        if c_n:
            n = df_binned[c_n].replace(0, np.nan).to_numpy(float)
            se = ystd / np.sqrt(n)
        else:
            # sin n, usa y_std como cota superior del error
            se = ystd.copy()
        sigma = np.maximum(se, float(sigma_floor_du))

    # Evita ceros o NaN
    sigma = np.where(~np.isfinite(sigma) | (sigma <= 0), np.nan, sigma)
    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(sigma)
    x, y, sigma = x[m], y[m], sigma[m]
    if x.size < 2:
        raise ValueError("No hay suficientes bins válidos (≥2) para el ajuste.")

    # Calcular número total de observaciones si está disponible
    n_obs = None
    if c_n:
        n_array = df_binned[c_n].to_numpy(float)[m]
        n_obs = int(np.sum(n_array))

    return linear_model_chi2(x, y, sigma, n_obs=n_obs)

