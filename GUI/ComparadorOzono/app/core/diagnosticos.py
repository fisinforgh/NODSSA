# -*- coding: utf-8 -*-
"""
Diagnósticos estadísticos para comparación de series (Real vs Predicho).

Incluye:
- Carga de datos CSV (Date, Ozone)
- Cálculo de residuales (real - predicho)
- Pruebas: Chi² Global, Shapiro–Wilk, Breusch–Pagan, Durbin–Watson,
  Ljung–Box (10 y 20)
- Gráficos: Histograma + curva Gauss, Q–Q plot, ACF, Scatter y
  Serie temporal Real vs Predicho
- Conclusión automática: 80% de pruebas OK -> "Modelo adecuado"

Requisitos: numpy, pandas, scipy, statsmodels, matplotlib
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm

from scipy.stats import norm, shapiro
from statsmodels.stats.diagnostic import het_breuschpagan, acorr_ljungbox
from statsmodels.stats.stattools import durbin_watson
from statsmodels.tsa.stattools import acf as acf_func


# ===========================
# Constantes de configuración
# ===========================

SIGNIFICANCE_LEVEL: float = 0.05
DW_LOWER_BOUND: float = 1.5
DW_UPPER_BOUND: float = 2.5

MAX_SHAPIRO_SAMPLES: int = 5000

PLOT_FIGSIZE: Tuple[float, float] = (7.0, 4.5)
PLOT_DPI: int = 150
DEFAULT_BINS: int = 30
ACF_LAGS: int = 30


# ====================
# Modelos de resultado
# ====================

@dataclass
class ResultadoPrueba:
    nombre: str
    estadistico: Optional[float]
    grados_libertad: Optional[int]
    p_valor: Optional[float]
    es_exitoso: bool
    descripcion: str = ""


@dataclass
class ResultadosDiagnosticos:
    pruebas: List[ResultadoPrueba]
    total_exitosas: int
    porcentaje_exitosas: float
    conclusion: str
    residuales: np.ndarray
    rutas_graficos: Dict[str, Path]


# =========================
# Clase de Implementación
# =========================

class DiagnosticosEstadisticos:
    """
    Clase para ejecutar diagnósticos y generar gráficos
    para una comparación Real vs Predicho.
    """

    def __init__(self) -> None:
        self.df: Optional[pd.DataFrame] = None
        self.y_real: Optional[np.ndarray] = None
        self.y_pred: Optional[np.ndarray] = None
        self.residuales: Optional[np.ndarray] = None

    # -------------------------
    # Carga y preprocesamiento
    # -------------------------
    def cargar_datos_csv(self, path_real: str | Path, path_pred: str | Path) -> None:
        """
        Carga dos CSV con columnas: Date, Ozone; alinea por Date y calcula residuales.
        """
        df_r = pd.read_csv(path_real)
        df_p = pd.read_csv(path_pred)

        for d in (df_r, df_p):
            if "Date" not in d.columns or "Ozone" not in d.columns:
                raise ValueError("Cada CSV debe incluir columnas: Date, Ozone")
            d["Date"] = pd.to_datetime(d["Date"], errors="coerce")

        df = (
            pd.merge(
                df_r[["Date", "Ozone"]].rename(columns={"Ozone": "Ozone_real"}),
                df_p[["Date", "Ozone"]].rename(columns={"Ozone": "Ozone_pred"}),
                on="Date",
                how="inner",
            )
            .dropna()
            .sort_values("Date")
            .reset_index(drop=True)
        )

        if df.empty:
            raise ValueError("No hay fechas comunes entre los archivos.")

        self.df = df
        self.y_real = df["Ozone_real"].to_numpy(float)
        self.y_pred = df["Ozone_pred"].to_numpy(float)
        self.residuales = self.y_real - self.y_pred

    # -----------------------
    # Pruebas estadísticas
    # -----------------------
    @staticmethod
    def chi2_global(residuals: np.ndarray, bins: Optional[int] = None) -> Tuple[float, int, float]:
        """
        Chi² de bondad de ajuste comparando el histograma de residuales con N(μ,σ).
        Devuelve: (chi2_stat, grados_libertad, pvalue)
        """
        r = np.asarray(residuals, dtype=float)
        r = r[np.isfinite(r)]
        n = len(r)
        if n < 10:
            return np.nan, 0, np.nan

        mu = float(np.mean(r))
        sd = float(np.std(r, ddof=1))
        if not np.isfinite(sd) or sd <= 0:
            return np.nan, 0, np.nan

        if bins is None:
            iqr = np.subtract(*np.percentile(r, [75, 25]))
            if iqr <= 0:
                bins = int(np.sqrt(n))
            else:
                h = 2 * iqr * (n ** (-1 / 3))
                bins = max(8, int(np.ceil((r.max() - r.min()) / max(h, 1e-9))))
        bins = int(np.clip(bins, 8, 60))

        counts, edges = np.histogram(r, bins=bins)
        cdf_vals = norm.cdf(edges, loc=mu, scale=sd)
        expected_probs = np.diff(cdf_vals)
        expected_counts = np.maximum(expected_probs * n, 1e-9)
        chi2_stat = float(np.sum((counts - expected_counts) ** 2 / expected_counts))
        dof = int(bins - 1 - 2)  # restamos 2 parámetros (μ, σ)

        from scipy.stats import chi2 as chi2_dist
        pvalue = float(1 - chi2_dist.cdf(chi2_stat, dof)) if dof > 0 else np.nan
        return chi2_stat, dof, pvalue

    def ejecutar_todas_las_pruebas(self) -> List[ResultadoPrueba]:
        """
        Ejecuta todas las pruebas de diagnóstico sobre los residuales.
        """
        if self.residuales is None:
            raise ValueError("No hay residuales cargados. Cargue los datos primero.")

        mask = np.isfinite(self.residuales)
        residuales_clean = self.residuales[mask]
        if residuales_clean.size == 0:
            raise ValueError("No hay residuos válidos para analizar")

        resultados: List[ResultadoPrueba] = []

        # 1) Chi² Global — ✅ si p ≥ SIGNIFICANCE_LEVEL
        try:
            chi2_stat, dof, p_valor = self.chi2_global(residuales_clean)
            es_exitoso = np.isfinite(p_valor) and p_valor >= SIGNIFICANCE_LEVEL
            resultados.append(
                ResultadoPrueba(
                    nombre="Chi² Global",
                    estadistico=chi2_stat,
                    grados_libertad=dof,
                    p_valor=p_valor,
                    es_exitoso=es_exitoso,
                    descripcion="Bondad de ajuste de residuales a N(μ,σ)",
                )
            )
        except Exception as e:
            print(f"Error en Chi² Global: {e}")
            resultados.append(
                ResultadoPrueba(
                    nombre="Chi² Global",
                    estadistico=np.nan,
                    grados_libertad=None,
                    p_valor=np.nan,
                    es_exitoso=False,
                    descripcion="Error en la prueba",
                )
            )

        # 2) Shapiro–Wilk — ✅ si p ≥ SIGNIFICANCE_LEVEL
        try:
            if len(residuales_clean) > MAX_SHAPIRO_SAMPLES:
                sample = np.random.choice(residuales_clean, MAX_SHAPIRO_SAMPLES, replace=False)
                sw_stat, sw_p = shapiro(sample)
            else:
                sw_stat, sw_p = shapiro(residuales_clean)
            es_exitoso = np.isfinite(sw_p) and sw_p >= SIGNIFICANCE_LEVEL
            resultados.append(
                ResultadoPrueba(
                    nombre="Shapiro-Wilk",
                    estadistico=float(sw_stat) if np.isfinite(sw_stat) else sw_stat,
                    grados_libertad=None,
                    p_valor=float(sw_p) if np.isfinite(sw_p) else sw_p,
                    es_exitoso=es_exitoso,
                    descripcion="Normalidad de residuales",
                )
            )
        except Exception as e:
            print(f"Error en Shapiro-Wilk: {e}")
            resultados.append(
                ResultadoPrueba(
                    nombre="Shapiro-Wilk",
                    estadistico=np.nan,
                    grados_libertad=None,
                    p_valor=np.nan,
                    es_exitoso=False,
                    descripcion="Error en la prueba",
                )
            )

        # 3) Breusch–Pagan — ✅ si p ≥ SIGNIFICANCE_LEVEL
        try:
            y_pred_clean = self.y_pred[mask]
            X_bp = sm.add_constant(pd.DataFrame({"fitted": y_pred_clean}), has_constant="add")
            bp_stat, bp_p, df_bp, _ = het_breuschpagan(residuales_clean, X_bp)
            es_exitoso = np.isfinite(bp_p) and bp_p >= SIGNIFICANCE_LEVEL
            resultados.append(
                ResultadoPrueba(
                    nombre="Breusch-Pagan",
                    estadistico=float(bp_stat) if np.isfinite(bp_stat) else bp_stat,
                    grados_libertad=int(df_bp) if df_bp is not None else None,
                    p_valor=float(bp_p) if np.isfinite(bp_p) else bp_p,
                    es_exitoso=es_exitoso,
                    descripcion="Homocedasticidad (varianza constante)",
                )
            )
        except Exception as e:
            print(f"Error en Breusch-Pagan: {e}")
            resultados.append(
                ResultadoPrueba(
                    nombre="Breusch-Pagan",
                    estadistico=np.nan,
                    grados_libertad=None,
                    p_valor=np.nan,
                    es_exitoso=False,
                    descripcion="Error en la prueba",
                )
            )

        # 4) Durbin–Watson — ✅ si DW_LOWER_BOUND ≤ DW ≤ DW_UPPER_BOUND
        try:
            dw = float(durbin_watson(residuales_clean))
            es_exitoso = np.isfinite(dw) and DW_LOWER_BOUND <= dw <= DW_UPPER_BOUND
            resultados.append(
                ResultadoPrueba(
                    nombre="Durbin-Watson",
                    estadistico=dw,
                    grados_libertad=None,
                    p_valor=None,
                    es_exitoso=es_exitoso,
                    descripcion=f"Autocorrelación AR(1); rango aceptable [{DW_LOWER_BOUND}, {DW_UPPER_BOUND}]",
                )
            )
        except Exception as e:
            print(f"Error en Durbin-Watson: {e}")
            resultados.append(
                ResultadoPrueba(
                    nombre="Durbin-Watson",
                    estadistico=np.nan,
                    grados_libertad=None,
                    p_valor=None,
                    es_exitoso=False,
                    descripcion="Error en la prueba",
                )
            )

        # 5) Ljung–Box (10) — ✅ si p ≥ SIGNIFICANCE_LEVEL
        try:
            lb10 = acorr_ljungbox(residuales_clean, lags=[10], return_df=True)
            lb10_p = float(lb10["lb_pvalue"].iloc[0])
            lb10_stat = float(lb10["lb_stat"].iloc[0])
            es_exitoso = np.isfinite(lb10_p) and lb10_p >= SIGNIFICANCE_LEVEL
            resultados.append(
                ResultadoPrueba(
                    nombre="Ljung-Box (lag=10)",
                    estadistico=lb10_stat,
                    grados_libertad=10,
                    p_valor=lb10_p,
                    es_exitoso=es_exitoso,
                    descripcion="Autocorrelación conjunta hasta lag 10",
                )
            )
        except Exception as e:
            print(f"Error en Ljung-Box (10): {e}")
            resultados.append(
                ResultadoPrueba(
                    nombre="Ljung-Box (lag=10)",
                    estadistico=np.nan,
                    grados_libertad=10,
                    p_valor=np.nan,
                    es_exitoso=False,
                    descripcion="Error en la prueba",
                )
            )

        # 6) Ljung–Box (20) — ✅ si p ≥ SIGNIFICANCE_LEVEL
        try:
            lb20 = acorr_ljungbox(residuales_clean, lags=[20], return_df=True)
            lb20_p = float(lb20["lb_pvalue"].iloc[0])
            lb20_stat = float(lb20["lb_stat"].iloc[0])
            es_exitoso = np.isfinite(lb20_p) and lb20_p >= SIGNIFICANCE_LEVEL
            resultados.append(
                ResultadoPrueba(
                    nombre="Ljung-Box (lag=20)",
                    estadistico=lb20_stat,
                    grados_libertad=20,
                    p_valor=lb20_p,
                    es_exitoso=es_exitoso,
                    descripcion="Autocorrelación conjunta hasta lag 20",
                )
            )
        except Exception as e:
            print(f"Error en Ljung-Box (20): {e}")
            resultados.append(
                ResultadoPrueba(
                    nombre="Ljung-Box (lag=20)",
                    estadistico=np.nan,
                    grados_libertad=20,
                    p_valor=np.nan,
                    es_exitoso=False,
                    descripcion="Error en la prueba",
                )
            )

        return resultados

    # -----------------------
    # Gráficos de diagnóstico
    # -----------------------
    def generar_graficos(self, directorio_salida: Path) -> Dict[str, Path]:
        """
        Genera y guarda gráficos:
        - Histograma + curva N(μ,σ) de residuales
        - Q–Q plot
        - ACF (sin use_line_collection)
        - Scatter Real vs Predicho (línea y=x)
        - Serie temporal Real vs Predicho
        """
        if self.residuales is None or self.y_real is None or self.y_pred is None:
            raise ValueError("Datos no cargados. Ejecute cargar_datos_csv primero.")

        directorio_salida = Path(directorio_salida)
        directorio_salida.mkdir(parents=True, exist_ok=True)
        rutas: Dict[str, Path] = {}

        # Limpiar residuales
        mask = np.isfinite(self.residuales)
        residuales_clean = self.residuales[mask]

        # 1) Histograma + curva Gauss
        mu = float(np.mean(residuales_clean))
        sd = float(np.std(residuales_clean, ddof=1))
        plt.figure(figsize=PLOT_FIGSIZE)
        plt.hist(
            residuales_clean,
            bins=DEFAULT_BINS,
            density=True,
            edgecolor="black",
            alpha=0.7,
            label="Histograma",
        )
        xs = np.linspace(mu - 4 * sd, mu + 4 * sd, 400)
        if np.isfinite(sd) and sd > 0:
            pdf = norm.pdf(xs, loc=mu, scale=sd)
            plt.plot(xs, pdf, linewidth=2, label="N(μ,σ)")
        plt.title("Histograma de Residuales + Curva Normal")
        plt.xlabel("Residual")
        plt.ylabel("Densidad")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        ruta = directorio_salida / "histograma_residuales_con_normal.png"
        plt.savefig(ruta, dpi=PLOT_DPI, bbox_inches="tight")
        plt.close()
        rutas["histograma_con_normal"] = ruta

        # 2) Q–Q plot
        fig = sm.qqplot(residuales_clean, line="s")
        plt.title("Q–Q Plot de Residuales")
        plt.xlabel("Cuantiles Teóricos")
        plt.ylabel("Cuantiles de la Muestra")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        ruta = directorio_salida / "qq_residuales.png"
        fig.savefig(ruta, dpi=PLOT_DPI, bbox_inches="tight")
        plt.close(fig)
        rutas["qq"] = ruta

        # 3) ACF (sin use_line_collection)
        acf_values = acf_func(residuales_clean, nlags=ACF_LAGS, fft=True)
        plt.figure(figsize=PLOT_FIGSIZE)
        markerline, stemlines, baseline = plt.stem(range(len(acf_values)), acf_values)
        plt.setp(baseline, linewidth=0)
        plt.title("Función de Autocorrelación (ACF)")
        plt.xlabel("Lag")
        plt.ylabel("ACF")
        plt.axhline(y=0, linewidth=0.5)
        ci = 1.96 / np.sqrt(len(residuales_clean))
        plt.axhline(y=ci, linestyle="--", alpha=0.5)
        plt.axhline(y=-ci, linestyle="--", alpha=0.5)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        ruta = directorio_salida / "acf_residuales.png"
        plt.savefig(ruta, dpi=PLOT_DPI, bbox_inches="tight")
        plt.close()
        rutas["acf"] = ruta

        # 4) Scatter Real vs Predicho (línea y=x)
        plt.figure(figsize=PLOT_FIGSIZE)
        plt.scatter(self.y_real[mask], self.y_pred[mask], alpha=0.6, s=20, label="Datos")
        min_val = min(self.y_real[mask].min(), self.y_pred[mask].min())
        max_val = max(self.y_real[mask].max(), self.y_pred[mask].max())
        plt.plot([min_val, max_val], [min_val, max_val], linestyle="--", alpha=0.5, label="y = x")
        plt.title("Valores Reales vs Predichos")
        plt.xlabel("Ozono Real")
        plt.ylabel("Ozono Predicho")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        ruta = directorio_salida / "scatter_real_vs_predicho.png"
        plt.savefig(ruta, dpi=PLOT_DPI, bbox_inches="tight")
        plt.close()
        rutas["scatter"] = ruta

        # 5) Serie temporal Real vs Predicho
        plt.figure(figsize=PLOT_FIGSIZE)
        plt.plot(self.y_real, linewidth=1.4, label="Real")
        plt.plot(self.y_pred, linewidth=1.2, label="Predicho")
        plt.title("Serie Temporal: Real vs Predicho")
        plt.xlabel("Índice temporal")
        plt.ylabel("Ozone")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        ruta = directorio_salida / "ts_real_vs_predicho.png"
        plt.savefig(ruta, dpi=PLOT_DPI, bbox_inches="tight")
        plt.close()
        rutas["serie_temporal"] = ruta

        return rutas

    # -----------------------------
    # Orquestador de diagnóstico
    # -----------------------------
    def ejecutar_diagnostico_completo(
        self,
        path_real: str | Path,
        path_pred: str | Path,
        directorio_salida: Optional[Path] = None,
    ) -> ResultadosDiagnosticos:
        """
        Ejecuta el diagnóstico completo: carga datos, pruebas y gráficos.
        """
        # Cargar datos y residuales
        self.cargar_datos_csv(path_real, path_pred)

        # Pruebas
        pruebas = self.ejecutar_todas_las_pruebas()

        total_pruebas = len(pruebas)
        total_exitosas = sum(1 for p in pruebas if p.es_exitoso)
        porcentaje = (total_exitosas / total_pruebas) * 100 if total_pruebas > 0 else 0.0

        if porcentaje >= 80.0:
            conclusion = (
                f"✓ Modelo adecuado para uso operativo\n"
                f"{total_exitosas}/{total_pruebas} pruebas exitosas ({porcentaje:.0f}%)\n\n"
                "Homocedasticidad y ausencia de autocorrelación confirmadas. "
                "La normalidad estricta puede no cumplirse (común en series ambientales), "
                "pero no invalida el modelo para propósito práctico."
            )
        else:
            conclusion = (
                f"⚠ Modelo requiere revisión\n"
                f"{total_exitosas}/{total_pruebas} pruebas exitosas ({porcentaje:.0f}%)\n\n"
                "Revise especificación (normalidad/autocorrelación) o considere transformaciones."
            )

        # Gráficos
        if directorio_salida is None:
            directorio_salida = Path.cwd() / "out_plots"
        rutas_graficos = self.generar_graficos(directorio_salida)

        return ResultadosDiagnosticos(
            pruebas=pruebas,
            total_exitosas=total_exitosas,
            porcentaje_exitosas=porcentaje,
            conclusion=conclusion,
            residuales=self.residuales if self.residuales is not None else np.array([]),
            rutas_graficos=rutas_graficos,
        )

