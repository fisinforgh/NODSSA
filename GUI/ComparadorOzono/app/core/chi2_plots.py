# -*- coding: utf-8 -*-
from __future__ import annotations

import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Tuple, Union

# Adaptador del pipeline de χ² sobre datos binned
from .chi2_adapters import chi2_from_binned


# ========================== Helpers genéricos ==========================

def _pick(cols_map: dict, *names) -> str | None:
    for n in names:
        if n.lower() in cols_map:
            return cols_map[n.lower()]
    return None


# ====================== 3.1 Comparativos locales ======================

def _ensure_local_arrays(df_bins: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Devuelve (x, y, sigma) a partir de un DataFrame binned con nombres flexibles.
    Soporta:
      - x:  S_bin | sun_bin_center | sun_bin | S
      - y:  y_mean | ozone_mean | mean | y
      - σ:  sigma | sigma_cal | stderr | se
      - si no hay σ: usa y_std / sqrt(n) con piso conservador (8 DU)
    """
    if df_bins.empty:
        return np.array([]), np.array([]), np.array([])

    c = {k.lower(): k for k in df_bins.columns}
    cx = _pick(c, "S_bin", "sun_bin_center", "sun_bin", "S")
    cy = _pick(c, "y_mean", "ozone_mean", "mean", "y")
    cs = _pick(c, "sigma", "sigma_cal", "stderr", "se")

    if not cx or not cy:
        return np.array([]), np.array([]), np.array([])

    x = df_bins[cx].to_numpy(float)
    y = df_bins[cy].to_numpy(float)

    if cs:
        s = df_bins[cs].to_numpy(float)
    else:
        cy_std = _pick(c, "y_std", "ozone_std", "std")
        cn = _pick(c, "n", "occ", "count")
        if cy_std and cn:
            se = df_bins[cy_std].to_numpy(float) / np.sqrt(
                df_bins[cn].replace(0, np.nan).to_numpy(float)
            )
            s = np.maximum(se, 8.0)  # piso recomendado
        elif cy_std:
            s = np.maximum(df_bins[cy_std].to_numpy(float), 8.0)
        else:
            # último recurso
            s = np.full_like(y, 8.0, dtype=float)

    # limpia NaN e inf
    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(s) & (s > 0)
    x, y, s = x[m], y[m], s[m]

    # orden
    order = np.argsort(x)
    return x[order], y[order], s[order]


def plot_local(df_bins: pd.DataFrame, title: str, out_path: str, alpha: float = 0.05):
    """
    df_bins: un solo sitio ya binned (columnas flexibles).
    Grafica puntos con barras de error, recta ajustada y caja de métricas (χ², ν, χ²_red, p, críticos, veredictos, a0/a1).
    """
    x, y, s = _ensure_local_arrays(df_bins)
    if x.size < 2:
        fig = plt.figure()
        plt.text(0.5, 0.5, "Sin datos", ha="center", va="center")
        plt.title(title)
        fig.savefig(out_path, dpi=200)
        plt.close(fig)
        return

    # Usa el adaptador general (aplica WLS + test de χ²)
    res = chi2_from_binned(df_bins, alpha=alpha)
    yhat = res["a0"] + res["a1"] * x

    fig = plt.figure()
    ax = plt.gca()
    ax.errorbar(x, y, yerr=s, fmt="o", label="Bins (ȳ ± σ)")
    ax.plot(x, yhat, "-", label="Ajuste lineal")
    ax.set_xlabel("Manchas solares (bin)")
    ax.set_ylabel("O₃ (DU)")
    ax.set_title(title)
    ax.legend(loc="best")
    txt = (
        f"a₀={res['a0']:.2f}±{res['sigma_a0']:.2f} DU  |  "
        f"a₁={res['a1']:.3f}±{res['sigma_a1']:.3f} DU/uMS\n"
        f"χ²={res['chi2']:.2f}, ν={res['nu']}, χ²_red={res['chi2_red']:.2f}, "
        f"p={res['p_value']:.3f}, CDF={res['p_cdf']:.3f}\n"
        f"críticos: [{res['chi2_lo']:.2f}, {res['chi2_hi']:.2f}]  "
        f"veredicto(χ²)={res['veredict_chi']}  tutor={res['veredict_tutor']}"
    )
    ax.text(0.02, 0.02, txt, transform=ax.transAxes, fontsize=8, va="bottom")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


# ================== 3.2 Curva de justificación (sweep) ==================

def plot_sweep(sweep_df: pd.DataFrame, chosen_min_occ: int, out_path: str):
    """
    sweep_df: columnas min_occ, chi2_red_mean (y opcional pct_reduction).
    """
    fig = plt.figure()
    ax = plt.gca()

    # Banda de referencia ~1.2–1.3 si te sirve como guía visual
    ax.axhspan(1.2, 1.3, alpha=0.08)

    ax.plot(sweep_df["min_occ"], sweep_df["chi2_red_mean"], marker="o")
    if "pct_reduction" in sweep_df.columns:
        for _, r in sweep_df.iterrows():
            ax.annotate(
                f"{r['pct_reduction']:.0f}%",
                (r["min_occ"], r["chi2_red_mean"]),
                fontsize=7,
                xytext=(4, 4),
                textcoords="offset points",
            )
    ax.axvline(chosen_min_occ, linestyle="--")
    ax.set_xlabel("min_occ")
    ax.set_ylabel("χ²/ν (promedio global)")
    ax.set_title("Justificación del umbral por ocurrencias")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


# ======= 3.3 Superficies globales (χ²_red sobre rejilla a0–a1 o lat–lon) =======

def load_surface_grid_csv(path: Union[str, Path]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Carga un CSV de superficies y devuelve ejes normalizados y matriz Z.
    Acepta cualquiera de estas combinaciones:
      - x, y, chi2_red
      - a0_norm, a1_norm, chi2_red
      - a0, a1, chi2_red  (se normalizan 0..1)
      - lat, lon, chi2_red (se pivotan sin normalizar; devolvemos ejes en su escala)
    """
    df = pd.read_csv(path)
    cols = {c.lower(): c for c in df.columns}

    def pick(*names):
        return _pick(cols, *names)

    # Caso lat/lon mapeable (pivot tradicional)
    clat, clon = pick("lat"), pick("lon")
    cz = pick("chi2_red", "chi2red", "chi2")
    if clat and clon and cz:
        pv = df.pivot_table(index=cols[clat], columns=cols[clon], values=cols[cz], aggfunc="mean")
        if pv.empty:
            return np.array([]), np.array([]), np.array([[]])
        x = pv.columns.values.astype(float)  # lon
        y = pv.index.values.astype(float)    # lat
        Z = pv.values.astype(float)
        return x, y, Z  # NOTA: aquí NO están normalizados (mapa físico)

    # Caso “a0–a1” con normalizados o x/y
    cx = pick("x", "a0_norm")
    cy = pick("y", "a1_norm")
    cz = pick("chi2_red", "chi2red", "chi2")

    if cx and cy and cz:
        x = df[cols[cx]].astype(float).to_numpy()
        y = df[cols[cy]].astype(float).to_numpy()
        z = df[cols[cz]].astype(float).to_numpy()
    else:
        # Normalizar desde a0/a1 crudos
        ca0, ca1, cz = pick("a0"), pick("a1"), pick("chi2_red", "chi2red", "chi2")
        if not (ca0 and ca1 and cz):
            return np.array([]), np.array([]), np.array([[]])
        a0 = df[cols[ca0]].astype(float).to_numpy()
        a1 = df[cols[ca1]].astype(float).to_numpy()
        z = df[cols[cz]].astype(float).to_numpy()
        a0r = np.nanmax(a0) - np.nanmin(a0)
        a1r = np.nanmax(a1) - np.nanmin(a1)
        x = (a0 - np.nanmin(a0)) / (a0r if a0r > 0 else 1.0)
        y = (a1 - np.nanmin(a1)) / (a1r if a1r > 0 else 1.0)

    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    x, y, z = x[m], y[m], z[m]

    gx = np.unique(x)
    gy = np.unique(y)
    if gx.size == 0 or gy.size == 0:
        return np.array([]), np.array([]), np.array([[]])

    Z = np.full((gy.size, gx.size), np.nan)
    ix = {v: i for i, v in enumerate(gx)}
    iy = {v: i for i, v in enumerate(gy)}
    for xx, yy, zz in zip(x, y, z):
        Z[iy[yy], ix[xx]] = zz
    return gx, gy, Z


def plot_surface(
    diag: Union[pd.DataFrame, str, Path],
    title: str,
    out_path: str,
    chi2_min_display: float = 0.0,
    chi2_max_display: float | None = 100.0,
):
    """
    Puede recibir:
      - DataFrame con columnas (lat,lon,chi2_red) o (x,y,chi2_red) o (a0_norm,a1_norm,chi2_red) o (a0,a1,chi2_red)
      - Ruta a CSV con el mismo formato.
    Dibuja la superficie y guarda PNG. También exporta proyecciones XZ/YZ.
    """
    # 1) Normaliza entrada a (X, Y, Z)
    if isinstance(diag, (str, Path)):
        X, Y, Z = load_surface_grid_csv(diag)
    elif isinstance(diag, pd.DataFrame):
        # Para reutilizar la misma lógica, volcamos a temp y reutilizamos
        from io import StringIO
        buf = StringIO()
        diag.to_csv(buf, index=False)
        buf.seek(0)
        df = pd.read_csv(buf)
        tmp = Path(out_path).with_suffix(".tmp.csv")
        df.to_csv(tmp, index=False)
        X, Y, Z = load_surface_grid_csv(tmp)
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
    else:
        X, Y, Z = np.array([]), np.array([]), np.array([[]])

    if Z.size == 0:
        fig = plt.figure()
        plt.text(0.5, 0.5, "Sin datos", ha="center", va="center")
        plt.title(title)
        fig.savefig(out_path, dpi=200)
        plt.close(fig)
        return

    # 2) Render
    fig = plt.figure()
    ax = plt.gca()

    # Aplicamos máscara “laxa” por si χ²_red está alto
    Zplot = Z.copy().astype(float)
    mask_nan = ~np.isfinite(Zplot)
    if chi2_max_display is not None:
        mask_bad = mask_nan | (Zplot < chi2_min_display) | (Zplot > chi2_max_display)
    else:
        mask_bad = mask_nan | (Zplot < chi2_min_display)
    Zm = np.ma.masked_where(mask_bad, Zplot)

    # ¿Ejes normalizados (0..1) o físicos (lat/lon)? Lo inferimos por el rango:
    extent = [float(np.nanmin(X)), float(np.nanmax(X)), float(np.nanmin(Y)), float(np.nanmax(Y))]
    im = ax.imshow(Zm, origin="lower", extent=extent, aspect="auto")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(r"$\chi^2_\nu$")

    # Etiquetas heurísticas
    if (extent[0] >= 0 and extent[1] <= 1) and (extent[2] >= 0 and extent[3] <= 1):
        ax.set_xlabel("a0 (normalizado)")
        ax.set_ylabel("a1 (normalizado)")
    else:
        ax.set_xlabel("Lon")
        ax.set_ylabel("Lat")

    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)

    # 3) Proyecciones XZ / YZ
    lat_me = np.nanmean(Z, axis=1)  # YZ (promedio por X)
    lon_me = np.nanmean(Z, axis=0)  # XZ (promedio por Y)

    # XZ (eje Y contra promedio por columnas, i.e. “a1/lat”)
    fig = plt.figure()
    plt.plot(Y, lat_me, marker="o")
    plt.xlabel(ax.get_ylabel())
    plt.ylabel(r"$\chi^2_\nu$ medio (XZ)")
    plt.title(title + " — proyección XZ")
    fig.tight_layout()
    fig.savefig(out_path.replace(".png", "_XZ.png"), dpi=200)
    plt.close(fig)

    # YZ (eje X contra promedio por filas, i.e. “a0/lon”)
    fig = plt.figure()
    plt.plot(X, lon_me, marker="o")
    plt.xlabel(ax.get_xlabel())
    plt.ylabel(r"$\chi^2_\nu$ medio (YZ)")
    plt.title(title + " — proyección YZ")
    fig.tight_layout()
    fig.savefig(out_path.replace(".png", "_YZ.png"), dpi=200)
    plt.close(fig)


def plot_occurrences_vs_sigma(
    df: pd.DataFrame, 
    min_occ: int, 
    col_sigma: str = "Ozone_std", 
    col_count: str = "Count",
    ymax: Optional[int] = None
) -> plt.Figure:
    """
    Genera un scatter plot de Ocurrencias vs Sigma (Figura 30 del libro).
    NOTA: La 'Sigma' del libro se refiere al Error Estándar (StdDev / sqrt(N)),
    ya que muestra cómo el error disminuye al aumentar las ocurrencias.
    ymax: Límite superior manual para el eje Y.
    """
    fig = plt.figure(figsize=(6, 4), dpi=100)
    ax = plt.gca()
    
    # Extraer datos
    if col_sigma in df.columns and col_count in df.columns:
        # Calcular Error Estándar: sigma / sqrt(n)
        sigma_raw = df[col_sigma].astype(float)
        count = df[col_count].astype(float)
        
        # Evitar división por cero
        x = sigma_raw / np.sqrt(count.replace(0, np.nan))
        y = count
        
        # Scatter plot
        # Separar puntos aceptados y rechazados
        mask_accepted = y >= min_occ
        mask_rejected = ~mask_accepted
        
        # Puntos aceptados (negros)
        ax.scatter(x[mask_accepted], y[mask_accepted], s=8, c='black', alpha=0.7, label='Aceptados', edgecolors='none')
        # Puntos rechazados (gris claro o rojo tenue)
        ax.scatter(x[mask_rejected], y[mask_rejected], s=8, c='gray', alpha=0.4, label='Rechazados', edgecolors='none')
        
        # Línea de corte
        ax.axhline(min_occ, color='red', linestyle='--', linewidth=1.5, label=f'min_occ={min_occ}')
        
        # Estética similar al libro (Ticks internos, caja completa)
        ax.set_xlabel(r"$\sigma_{O_3}^{OBS}$ (UD)")
        ax.set_ylabel("Ocurrencias")
        ax.set_title(rf"Estudio de ocurrencias en función de $\sigma$ (min_occ={min_occ})")
        
        # Configurar ticks hacia adentro y en los 4 lados
        ax.tick_params(direction='in', top=True, right=True, which='both')
        ax.minorticks_on()
        ax.grid(True, linestyle=':', alpha=0.5)
        
        # Leyenda simple
        # ax.legend() # El libro no parece tener leyenda explícita, pero la dejamos por claridad o la quitamos si molesta
        
        # Debug: Imprimir cuántos puntos se están graficando
        valid_points = x.notna() & y.notna()
        n_plotted = valid_points.sum()
        print(f"[DEBUG] Plot Ocurrencias vs Sigma: Total filas={len(df)}, Puntos válidos={n_plotted}")
        
        # Ajustar rangos
        if not x.empty:
            ax.set_xlim(left=0)
            
            # Definir límite superior Y
            if ymax is not None and ymax > 0:
                y_top = ymax
            else:
                # Default: mostrar todo o al menos 30
                y_top = max(30, y.max() * 1.05)
                
            ax.set_ylim(bottom=0, top=y_top)
            
    else:
        ax.text(0.5, 0.5, "Datos insuficientes para graficar\nOcurrencias vs Sigma", 
                ha="center", va="center")
    
    fig.tight_layout()
    return fig

from scipy.stats import chi2

def plot_chi2_probability(nu: int, chi2_val: float) -> plt.Figure:
    """
    Genera un gráfico de la distribución Chi-cuadrado con nu grados de libertad.
    Sombrea el intervalo de confianza del 95% (2.5% - 97.5%) y marca el valor observado.
    """
    fig = plt.figure(figsize=(6, 4), dpi=100)
    ax = plt.gca()

    # Rango X: desde 0 hasta un poco más allá del crítico superior o del valor observado
    crit_hi = chi2.ppf(0.999, df=nu)
    x_max = max(crit_hi, chi2_val * 1.1, nu * 2) # Asegurar que se vea todo
    x = np.linspace(0, x_max, 500)
    y = chi2.pdf(x, df=nu)

    # Plot PDF
    ax.plot(x, y, 'b-', label=f'$\chi^2$ PDF (ν={nu})')

    # Sombrear área de confianza 95% (0.025 a 0.975)
    # Colas de rechazo: < 0.025 y > 0.975
    # El usuario pidió "colas entre 0.275 y 0.975" -> asumo que quiere ver la zona de aceptación
    # o las colas de rechazo. Lo estándar es sombrear la zona de aceptación o marcar los límites.
    # Voy a marcar los límites críticos y sombrear la zona de aceptación (95%).
    
    crit_lo = chi2.ppf(0.025, df=nu)
    crit_hi_95 = chi2.ppf(0.975, df=nu)
    
    mask_conf = (x >= crit_lo) & (x <= crit_hi_95)
    ax.fill_between(x, y, where=mask_conf, color='green', alpha=0.2, label='Zona Aceptación (95%)')
    
    # Línea del valor observado
    p_cdf = chi2.cdf(chi2_val, df=nu)
    ax.axvline(chi2_val, color='red', linestyle='-', linewidth=2, label=f'$\chi^2_{{obs}}$={chi2_val:.2f}\nAUC (CDF)={p_cdf:.4f}')
    
    # Líneas críticas
    ax.axvline(crit_lo, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(crit_hi_95, color='gray', linestyle='--', alpha=0.5)
    
    # Textos
    ax.text(crit_lo, max(y)/2, f'2.5%\n{crit_lo:.1f}', ha='right', va='center', fontsize=8, color='gray')
    ax.text(crit_hi_95, max(y)/2, f'97.5%\n{crit_hi_95:.1f}', ha='left', va='center', fontsize=8, color='gray')

    # Mostrar valor de AUC en el gráfico también
    ax.text(chi2_val, max(y)*0.8, f'AUC={p_cdf:.4f}', ha='right' if p_cdf > 0.5 else 'left', va='bottom', color='red', fontsize=9, fontweight='bold')

    ax.set_xlabel(r'$\chi^2$')
    ax.set_ylabel('Densidad de Probabilidad')
    ax.set_title(f'Distribución $\chi^2$ (ν={nu})')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    return fig
