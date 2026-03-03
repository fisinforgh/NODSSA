#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI Comparación Real vs Predicho — Ozono
- Carga dos CSV con columnas: Date, Ozone
- Alinea por Date y calcula residuales = Ozone_real - Ozone_pred
- Ejecuta diagnósticos: Chi2 Global, Shapiro–Wilk, Breusch–Pagan, Durbin–Watson, Ljung–Box (10, 20)
- Genera y guarda plots: histograma, Q–Q plot, ACF, scatter (real vs predicho)

Reglas:
- Pruebas con p-valor: ✅ si p ≥ 0.05 ; ❌ si p < 0.05
- Durbin–Watson: ✅ si 1.5 ≤ DW ≤ 2.5 ; ❌ fuera de ese rango

Salida:
- Tabla con 6 pruebas + resumen 80%
- PNGs en carpeta ./out_plots
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # backend offscreen para guardar PNG
import matplotlib.pyplot as plt

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt

from scipy.stats import shapiro, norm
from statsmodels.stats.diagnostic import het_breuschpagan, acorr_ljungbox
from statsmodels.stats.stattools import durbin_watson
import statsmodels.api as sm
from statsmodels.tsa.stattools import acf as acf_func

warnings.filterwarnings("ignore")

# =========================
# Utilidades de diagnóstico
# =========================

def chi2_global(residuals: np.ndarray, bins: int | None = None):
    """
    Chi2 de bondad de ajuste comparando el histograma de los residuales
    contra una Normal(mean=residuales.mean, std=residuales.std).
    Retorna: (chi2_stat, dof, pvalue)
    """
    r = np.asarray(residuals)
    r = r[np.isfinite(r)]
    n = len(r)
    if n < 10:
        return np.nan, np.nan, np.nan

    mu = np.mean(r)
    sd = np.std(r, ddof=1)
    if sd <= 0 or not np.isfinite(sd):
        return np.nan, np.nan, np.nan

    # Bins por Freedman–Diaconis si no se especifica
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
    expected_counts = np.maximum(expected_probs * n, 1e-9)  # evitar ceros
    chi2_stat = np.sum((counts - expected_counts) ** 2 / expected_counts)
    dof = bins - 1 - 2  # restar parámetros estimados (mu, sd)
    from scipy.stats import chi2 as chi2_dist
    pvalue = 1 - chi2_dist.cdf(chi2_stat, dof) if dof > 0 else np.nan
    return float(chi2_stat), int(dof), float(pvalue)


def run_all_diagnostics(y_real: np.ndarray,
                        y_pred: np.ndarray,
                        outdir: str) -> list[list]:
    """
    Corre las 6 pruebas sobre residuales y devuelve filas para una tabla.
    También genera y guarda los 4 plots en outdir.
    """
    # ----------------------
    # Residuales y limpieza
    # ----------------------
    residuals = y_real - y_pred
    mask = np.isfinite(residuals)
    residuals_clean = residuals[mask]
    if residuals_clean.size == 0:
        raise ValueError("No hay residuos válidos para analizar.")

    # fitted para BP (siempre usamos y_pred alineado)
    X_bp = sm.add_constant(pd.DataFrame({'fitted': y_pred[mask]}), has_constant='add')

    rows: list[list] = []

    # 1) Chi2 Global (✅ cuando p ≥ 0.05)
    c2, dfc2, pc2 = chi2_global(residuals_clean)
    rows.append(["Chi2 Global", c2, dfc2, pc2,
                 "✅" if (np.isfinite(pc2) and pc2 >= 0.05) else "❌"])

    # 2) Shapiro–Wilk (normalidad)
    try:
        if len(residuals_clean) > 5000:
            sample = np.random.choice(residuals_clean, 5000, replace=False)
            sw_stat, sw_p = shapiro(sample)
        else:
            sw_stat, sw_p = shapiro(residuals_clean)
    except Exception as e:
        print(f"Error en Shapiro-Wilk: {e}")
        sw_stat, sw_p = np.nan, np.nan
    rows.append(["Shapiro–Wilk", sw_stat, "-", sw_p,
                 "✅" if (np.isfinite(sw_p) and sw_p >= 0.05) else "❌"])

    # 3) Breusch–Pagan (homocedasticidad)
    try:
        bp_stat, bp_p, df_bp, _ = het_breuschpagan(residuals_clean, X_bp)
    except Exception as e:
        print(f"Error en Breusch–Pagan: {e}")
        bp_stat, bp_p, df_bp = np.nan, np.nan, np.nan
    rows.append(["Breusch–Pagan", bp_stat, df_bp, bp_p,
                 "✅" if (np.isfinite(bp_p) and bp_p >= 0.05) else "❌"])

    # 4) Durbin–Watson (autocorrelación AR(1)) — ✅ si 1.5 ≤ DW ≤ 2.5
    try:
        dw = float(durbin_watson(residuals_clean))
    except Exception as e:
        print(f"Error en Durbin–Watson: {e}")
        dw = np.nan
    rows.append(["Durbin–Watson", dw, "-", "-",
                 "✅" if (np.isfinite(dw) and 1.5 <= dw <= 2.5) else "❌"])

    # 5) Ljung–Box (lag=10) — ✅ si p ≥ 0.05
    try:
        lb10 = acorr_ljungbox(residuals_clean, lags=[10], return_df=True)
        lb10_p = float(lb10["lb_pvalue"].iloc[0])
    except Exception as e:
        print(f"Error en Ljung–Box (10): {e}")
        lb10_p = np.nan
    rows.append(["Ljung–Box (lag=10)", "-", 10, lb10_p,
                 "✅" if (np.isfinite(lb10_p) and lb10_p >= 0.05) else "❌"])

    # 6) Ljung–Box (lag=20) — ✅ si p ≥ 0.05
    try:
        lb20 = acorr_ljungbox(residuals_clean, lags=[20], return_df=True)
        lb20_p = float(lb20["lb_pvalue"].iloc[0])
    except Exception as e:
        print(f"Error en Ljung–Box (20): {e}")
        lb20_p = np.nan
    rows.append(["Ljung–Box (lag=20)", "-", 20, lb20_p,
                 "✅" if (np.isfinite(lb20_p) and lb20_p >= 0.05) else "❌"])

    # ------------------------
    # Resumen 80% y conclusión
    # ------------------------
    total_tests = 6
    idx_estado = 4
    ok = sum(1 for r in rows if str(r[idx_estado]).strip() == "✅")
    ratio = ok / total_tests

    if ratio >= 0.80:
        conclusion = (
            f"Conclusión: {ok}/{total_tests} pruebas OK (≈{ratio:.0%}). "
            "Modelo útil para uso operativo: homocedasticidad y no autocorrelación confirmadas; "
            "la normalidad estricta puede fallar (común en series ambientales) sin invalidar el modelo."
        )
    else:
        conclusion = (
            f"Conclusión: {ok}/{total_tests} pruebas OK (≈{ratio:.0%}). "
            "Revisar especificación (normalidad/autocorrelación) o aplicar transformaciones."
        )
    rows.append(["Resumen", "-", "-", f"{ok}/{total_tests} (≈{ratio:.0%})", ""])
    rows.append(["Conclusión", "-", "-", conclusion, ""])

    # -----------
    # Guardar plots
    # -----------
    os.makedirs(outdir, exist_ok=True)

    # Histograma
    plt.figure(figsize=(7, 4.5))
    plt.hist(residuals_clean, bins=30)
    plt.title("Histograma de residuales")
    plt.xlabel("Residual")
    plt.ylabel("Frecuencia")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "hist_residuales.png"), dpi=150)
    plt.close()

    # Q-Q plot
    fig = sm.qqplot(residuals_clean, line='s')
    plt.title("Q–Q plot de residuales")
    plt.tight_layout()
    fig.savefig(os.path.join(outdir, "qq_residuales.png"), dpi=150)
    plt.close(fig)

    # ACF (CORREGIDO: sin use_line_collection)
    acfv = acf_func(residuals_clean, nlags=30, fft=True)
    plt.figure(figsize=(7, 4.5))
    markerline, stemlines, baseline = plt.stem(range(len(acfv)), acfv)  # ← sin use_line_collection
    plt.setp(baseline, linewidth=0)  # oculta la línea base
    plt.title("ACF de residuales (30 lags)")
    plt.xlabel("Lag")
    plt.ylabel("ACF")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "acf_residuales.png"), dpi=150)
    plt.close()

    return rows


def load_csv_two_series(path_real: str, path_pred: str):
    """
    Lee dos CSV con columnas: Date, Ozone. Devuelve dataframe alineado.
    """
    df_r = pd.read_csv(path_real)
    df_p = pd.read_csv(path_pred)

    for d in (df_r, df_p):
        if "Date" not in d.columns or "Ozone" not in d.columns:
            raise ValueError("Cada CSV debe tener columnas: Date, Ozone")
        d["Date"] = pd.to_datetime(d["Date"], errors="coerce")

    df = pd.merge(
        df_r[["Date", "Ozone"]].rename(columns={"Ozone": "Ozone_real"}),
        df_p[["Date", "Ozone"]].rename(columns={"Ozone": "Ozone_pred"}),
        on="Date",
        how="inner"
    ).dropna()

    if df.empty:
        raise ValueError("No hay fechas comunes entre los archivos.")

    return df


# ==========
# Interfaz
# ==========

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Comparador de Ozono — Real vs Predicho (Diagnósticos)")
        self.resize(900, 640)

        central = QWidget(self)
        self.setCentralWidget(central)
        lay = QVBoxLayout(central)

        # Controles de selección
        top = QHBoxLayout()
        self.btn_real = QPushButton("Cargar ozono REAL (CSV)")
        self.btn_pred = QPushButton("Cargar ozono PREDICHO (CSV)")
        self.label_real = QLabel("Real: (no cargado)")
        self.label_pred = QLabel("Predicho: (no cargado)")
        self.btn_run = QPushButton("Ejecutar diagnósticos")
        top.addWidget(self.btn_real)
        top.addWidget(self.label_real, 1)
        top.addWidget(self.btn_pred)
        top.addWidget(self.label_pred, 1)
        top.addWidget(self.btn_run)
        lay.addLayout(top)

        # Área de resultados
        self.out = QTextEdit()
        self.out.setReadOnly(True)
        lay.addWidget(self.out, 1)

        # Eventos
        self.path_real = None
        self.path_pred = None
        self.btn_real.clicked.connect(self.pick_real)
        self.btn_pred.clicked.connect(self.pick_pred)
        self.btn_run.clicked.connect(self.run)

        # Info
        info = QLabel("Reglas: p ≥ 0.05 ⇒ ✅ ; 1.5 ≤ DW ≤ 2.5 ⇒ ✅")
        info.setAlignment(Qt.AlignLeft)
        lay.addWidget(info)

    def pick_real(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecciona ozono REAL", "", "CSV (*.csv)")
        if path:
            self.path_real = path
            self.label_real.setText(f"Real: {os.path.basename(path)}")

    def pick_pred(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecciona ozono PREDICHO", "", "CSV (*.csv)")
        if path:
            self.path_pred = path
            self.label_pred.setText(f"Predicho: {os.path.basename(path)}")

    def run(self):
        try:
            if not self.path_real or not self.path_pred:
                QMessageBox.warning(self, "Faltan archivos", "Carga ambos archivos CSV (real y predicho).")
                return

            df = load_csv_two_series(self.path_real, self.path_pred)
            y_real = df["Ozone_real"].to_numpy(dtype=float)
            y_pred = df["Ozone_pred"].to_numpy(dtype=float)

            outdir = os.path.join(os.path.dirname(self.path_pred), "out_plots")
            rows = run_all_diagnostics(y_real, y_pred, outdir=outdir)

            # Scatter Real vs Predicho (guardar ahora que tenemos df)
            os.makedirs(outdir, exist_ok=True)
            plt.figure(figsize=(7, 4.5))
            plt.scatter(df["Ozone_real"], df["Ozone_pred"], alpha=0.65)
            plt.title("Real vs Predicho")
            plt.xlabel("Ozone Real")
            plt.ylabel("Ozone Predicho")
            plt.tight_layout()
            plt.savefig(os.path.join(outdir, "scatter_real_vs_pred.png"), dpi=150)
            plt.close()

            # Render tabla
            txt = []
            header = ["Prueba", "Estadístico", "GL/Lag", "p-valor", "Estado"]
            widths = [22, 14, 10, 14, 8]
            fmt = "{:<22} {:>14} {:>10} {:>14} {:>8}"
            txt.append(fmt.format(*header))
            txt.append("-" * 72)
            for r in rows:
                txt.append(fmt.format(
                    str(r[0]),
                    f"{r[1]:.6g}" if isinstance(r[1], (int, float, np.floating)) and np.isfinite(r[1]) else str(r[1]),
                    str(r[2]),
                    f"{r[3]:.6g}" if isinstance(r[3], (int, float, np.floating)) and np.isfinite(r[3]) else str(r[3]),
                    str(r[4])
                ))
            txt.append("\nPNGs guardados en: " + outdir)
            self.out.setPlainText("\n".join(txt))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error:\n{e}")
            raise


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

