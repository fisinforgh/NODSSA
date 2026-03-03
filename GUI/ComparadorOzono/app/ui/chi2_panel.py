"""
Panel principal para el análisis del modelo lineal O₃–Sₙ (ozono total vs manchas solares).

Incluye:
  - Selector de modo: MENSUAL (modelo candidato) / DIARIO (solo diagnóstico).
  - Gráfica local de bins (sin corte y con min_occ).
  - Gráfica de sweep chi²_red vs min_occ.
  - Resumen textual del veredicto (χ²_red, p, min_occ, N_bins, pct_reduction, etc.).

Reemplaza al chi2_panel.py anterior.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import numpy as np
import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QTextEdit,
    QTabWidget,
    QPushButton,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from app.viewmodels.ozono_sn_viewmodel import OzonoSnViewModel, ModeloChi2Resumen

logger = logging.getLogger(__name__)


class MatplotlibCanvas(FigureCanvas):
    """Canvas sencillo de matplotlib embebido en Qt."""

    def __init__(self, width: float = 5, height: float = 3, dpi: int = 100, parent=None):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)


class Chi2Panel(QWidget):
    """
    Panel GUI para explorar el modelo lineal O₃–Sₙ en modos mensual y diario.

    - Usa OzonoSnViewModel para cargar los CSV preprocesados (gui_mensual / gui_diario).
    - No recalcula χ² desde cero: muestra lo que ya viene en los diagnostics y sweep.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # ViewModel
        self.vm = OzonoSnViewModel()

        # Layout general
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Encabezado: selector de modo + botón refrescar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        lbl_modo = QLabel("Modo de análisis:")
        self.cb_modo = QComboBox()
        self.cb_modo.addItem("MENSUAL (modelo candidato)", userData="mensual")
        self.cb_modo.addItem("DIARIO (solo diagnóstico)", userData="diario")

        self.btn_refrescar = QPushButton("Refrescar")
        self.btn_refrescar.setToolTip(
            "Volver a cargar los archivos CSV del modo seleccionado "
            "(gui_mensual/gui_diario)."
        )

        header_layout.addWidget(lbl_modo)
        header_layout.addWidget(self.cb_modo)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_refrescar)

        layout.addLayout(header_layout)

        # Texto explicativo breve bajo el selector
        self.lbl_info_modo = QLabel()
        self.lbl_info_modo.setWordWrap(True)
        layout.addWidget(self.lbl_info_modo)

        # Tabs internos
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        # --- Tab 1: Local (bins y ajuste) ---
        self.tab_local = QWidget()
        local_layout = QVBoxLayout(self.tab_local)
        local_layout.setContentsMargins(4, 4, 4, 4)
        local_layout.setSpacing(4)

        # Canvas para bins sin corte
        self.canvas_sin = MatplotlibCanvas(width=5, height=3, dpi=100, parent=self)
        # Canvas para bins con corte
        self.canvas_cut = MatplotlibCanvas(width=5, height=3, dpi=100, parent=self)

        local_layout.addWidget(QLabel("Bins O₃–Sₙ SIN corte por ocurrencias:"))
        local_layout.addWidget(self.canvas_sin)
        local_layout.addWidget(QLabel("Bins O₃–Sₙ CON corte (min_occ):"))
        local_layout.addWidget(self.canvas_cut)

        # Resumen textual detallado (ELIMINADO por solicitud del usuario)
        # self.txt_resumen = QTextEdit()
        # self.txt_resumen.setReadOnly(True)
        # local_layout.addWidget(QLabel("Resumen del modelo y veredicto:"))
        # local_layout.addWidget(self.txt_resumen, 1)

        self.tabs.addTab(self.tab_local, "Local (bins y ajuste)")

        # --- Tab 2: Curva de justificación (sweep) ---
        self.tab_sweep = QWidget()
        sweep_layout = QVBoxLayout(self.tab_sweep)
        sweep_layout.setContentsMargins(4, 4, 4, 4)
        sweep_layout.setSpacing(4)

        self.canvas_sweep = MatplotlibCanvas(width=5, height=3, dpi=100, parent=self)
        self.lbl_sweep_info = QLabel()
        self.lbl_sweep_info.setWordWrap(True)

        sweep_layout.addWidget(QLabel("Sweep χ²_red vs min_occ:"))
        sweep_layout.addWidget(self.canvas_sweep)
        sweep_layout.addWidget(self.lbl_sweep_info)

        self.tabs.addTab(self.tab_sweep, "Curva de justificación")

        # --- Tab 3: Superficies (global) ---
        self.tab_superficies = QWidget()
        sup_layout = QVBoxLayout(self.tab_superficies)
        sup_layout.setContentsMargins(4, 4, 4, 4)
        sup_layout.setSpacing(4)

        # Para simplificar: una sola superficie (si existe) y un texto explicativo
        self.canvas_sup = MatplotlibCanvas(width=5, height=3, dpi=100, parent=self)
        self.lbl_sup_info = QLabel()
        self.lbl_sup_info.setWordWrap(True)

        sup_layout.addWidget(QLabel("Superficie global de χ²_red (si existe):"))
        sup_layout.addWidget(self.canvas_sup)
        sup_layout.addWidget(self.lbl_sup_info)

        self.tabs.addTab(self.tab_superficies, "Superficies (global)")

        # Conexiones
        self.cb_modo.currentIndexChanged.connect(self._on_modo_changed)
        self.btn_refrescar.clicked.connect(self.refresh)

        # Inicializar modo y contenido
        self._update_info_modo()
        self.refresh()

    # --------------------
    # Callbacks y helpers
    # --------------------
    def _on_modo_changed(self, idx: int) -> None:
        modo = self.cb_modo.currentData()
        if modo not in ("mensual", "diario"):
            return
        self.vm.set_modo(modo)
        self._update_info_modo()
        self.refresh()

    def _update_info_modo(self) -> None:
        if self.vm.modo == "mensual":
            self.lbl_info_modo.setText(
                "Modo MENSUAL: el modelo lineal O₃–Sₙ puede resultar "
                "estadísticamente aceptable. Aquí se resumen los bins "
                "mensuales, la mejor configuración (min_occ, N_bins) y los "
                "resultados de χ²_red y p."
            )
        else:
            self.lbl_info_modo.setText(
                "Modo DIARIO: el modelo lineal O₃–Sₙ se utiliza SOLO con fines "
                "diagnósticos. Los resultados típicamente muestran χ²_red "
                "altos y p-values muy pequeños, por lo que el modelo se "
                "considera RECHAZADO a escala diaria."
            )

    # --------------------
    # API pública
    # --------------------
    def refresh(self) -> None:
        """
        Recarga datos desde los CSV del modo actual y actualiza
        todas las pestañas.
        """
        self._plot_local_bins()
        self._plot_sweep()
        self._plot_superficies()

    # --------------------
    # Pestaña Local (bins)
    # --------------------
    def _plot_local_bins(self) -> None:
        # Limpiar
        self.canvas_sin.axes.clear()
        self.canvas_cut.axes.clear()
        # self.txt_resumen.clear()

        df_all = self.vm.cargar_binned_sin_corte()
        df_cut = self.vm.cargar_binned_con_corte()
        # resumen = self.vm.construir_resumen()

        if df_all is None:
            self.canvas_sin.axes.text(
                0.5,
                0.5,
                "No se encontró el CSV de bins sin corte.\n"
                "Verifica que exista bogota_binned_gui.csv en gui_*. ",
                ha="center",
                va="center",
                transform=self.canvas_sin.axes.transAxes,
            )
            self.canvas_sin.draw()
        else:
            self._plot_bins_df(
                ax=self.canvas_sin.axes,
                df=df_all,
                titulo="Bins O₃–Sₙ SIN corte por ocurrencias",
            )
            self.canvas_sin.draw()

        if df_cut is None:
            self.canvas_cut.axes.text(
                0.5,
                0.5,
                "No se encontró CSV de bins con corte (min_occ).\n"
                "Verifica bogota_binned_minoccXX.csv en gui_*. ",
                ha="center",
                va="center",
                transform=self.canvas_cut.axes.transAxes,
            )
            self.canvas_cut.draw()
        else:
            self._plot_bins_df(
                ax=self.canvas_cut.axes,
                df=df_cut,
                titulo="Bins O₃–Sₙ CON corte (min_occ)",
            )
            self.canvas_cut.draw()

        # if resumen is not None:
        #     self._mostrar_resumen_textual(resumen)
        # else:
        #     self.txt_resumen.setPlainText(
        #         "No se encontró chi2_diagnostics_basic.csv o no se pudo "
        #         "construir un resumen del modelo."
        #     )

    def _plot_bins_df(self, ax, df: pd.DataFrame, titulo: str) -> None:
        """
        Gráfico de puntos binned con barras de error y una recta ajustada
        simple (OLS sobre el propio CSV preprocesado).

        Estructura esperada (según scripts de preprocesamiento):
          - sun_bin_center: centro del bin de manchas solares → eje X
          - y_mean: ozono medio → eje Y
          - sigma: desviación estándar → barras de error (opcional)
          - occ / n: número de observaciones en el bin (opcional)
        """
        ax.clear()

        if "sun_bin_center" in df.columns and "y_mean" in df.columns:
            x = df["sun_bin_center"].to_numpy()
            y = df["y_mean"].to_numpy()
            yerr = df["sigma"].to_numpy() if "sigma" in df.columns else None

            # Número de ocurrencias (puede ser 'occ' o 'n')
            if "occ" in df.columns:
                n = df["occ"].to_numpy()
            elif "n" in df.columns:
                n = df["n"].to_numpy()
            else:
                n = None
        else:
            # Fallback genérico por nombres alternativos
            col_x = None
            col_y = None
            col_sigma = None
            for c in df.columns:
                cl = c.lower()
                if cl in ("sn_bin", "sun_bin", "sun_bin_center", "bin_sun"):
                    col_x = c
                elif cl in ("o3_mean", "ozone_mean", "y_mean"):
                    col_y = c
                elif cl in ("o3_std", "ozone_std", "sigma", "std"):
                    col_sigma = c

            if col_x is None or col_y is None:
                ax.text(
                    0.5,
                    0.5,
                    "No se encontraron columnas estándar de Sn/O₃.",
                    ha="center",
                    va="center",
                    transform=ax.transAxes,
                )
                ax.set_title(titulo)
                return

            x = df[col_x].to_numpy()
            y = df[col_y].to_numpy()
            yerr = df[col_sigma].to_numpy() if col_sigma is not None else None
            n = None

        # Escala opcional de tamaño de puntos según n
        if n is not None and np.all(n > 0):
            n_norm = (n / n.max()) * 80 + 20
        else:
            n_norm = 40

        # Scatter + errorbars
        if yerr is not None:
            ax.errorbar(x, y, yerr=yerr, fmt="o", capsize=3, alpha=0.8)
        else:
            ax.scatter(x, y, s=n_norm)

        # Ajuste lineal OLS simple (solo para visual, no reemplaza χ² oficial)
        if len(x) >= 2:
            try:
                coeffs = np.polyfit(x, y, deg=1)
                a1, a0 = coeffs  # y = a1*x + a0
                x_line = np.linspace(x.min(), x.max(), 100)
                y_line = a1 * x_line + a0
                ax.plot(
                    x_line,
                    y_line,
                    "-",
                    alpha=0.7,
                    label=f"O₃ = {a0:.1f} + {a1:.3f}·Sₙ",
                )
                ax.legend(loc="best")
            except Exception as exc:
                logger.exception("Error en ajuste lineal para bins: %s", exc)

        ax.set_xlabel("Número de manchas solares (Sₙ, centro del bin)")
        ax.set_ylabel("Columna total de ozono (DU)")
        ax.set_title(titulo)
        ax.grid(True, alpha=0.3)

    def _mostrar_resumen_textual(self, resumen: ModeloChi2Resumen) -> None:
        """
        Escribe en el QTextEdit un resumen legible del mejor modelo.
        """
        lineas = []

        lineas.append(f"Modo: {resumen.modo.upper()}")
        if resumen.lat is not None and resumen.lon is not None:
            lineas.append(f"Ubicación: lat={resumen.lat:.4f}, lon={resumen.lon:.4f}")

        if resumen.n_obs is not None:
            lineas.append(f"N observaciones usadas (N): {resumen.n_obs}")
        if resumen.nu is not None:
            lineas.append(f"Grados de libertad (ν): {resumen.nu}")
        if resumen.chi2 is not None:
            lineas.append(f"χ²: {resumen.chi2:.3f}")
        if resumen.chi2_red is not None:
            lineas.append(f"χ²_red: {resumen.chi2_red:.3f}")
        if resumen.p_value is not None:
            lineas.append(f"p-valor (bondad de ajuste): {resumen.p_value:.3e}")
        if resumen.p_cdf is not None:
            lineas.append(f"F(χ²|ν) (CDF): {resumen.p_cdf:.3f}")
        if resumen.chi2_lo is not None and resumen.chi2_hi is not None:
            lineas.append(
                f"Intervalo crítico χ² (95%): [{resumen.chi2_lo:.3f}, "
                f"{resumen.chi2_hi:.3f}]"
            )

        if resumen.a0 is not None and resumen.a1 is not None:
            if resumen.sigma_a0 is not None and resumen.sigma_a1 is not None:
                lineas.append(
                    f"Modelo: O₃ ≈ ({resumen.a0:.2f} ± {resumen.sigma_a0:.2f}) "
                    f"+ ({resumen.a1:.4f} ± {resumen.sigma_a1:.4f})·Sₙ"
                )
            else:
                lineas.append(
                    f"Modelo: O₃ ≈ {resumen.a0:.2f} + {resumen.a1:.4f}·Sₙ"
                )

        if resumen.min_occ is not None:
            lineas.append(f"min_occ (corte por ocurrencias): {resumen.min_occ}")
        if resumen.n_bins is not None:
            lineas.append(f"Número de bins: {resumen.n_bins}")
        if resumen.pct_reduction is not None:
            lineas.append(
                f"Reducción de observaciones por corte: "
                f"{resumen.pct_reduction:.2f}%"
            )

        if resumen.veredict_chi:
            lineas.append(f"Veredicto χ²: {resumen.veredict_chi}")
        if resumen.veredict_tutor:
            lineas.append(f"Veredicto tutor: {resumen.veredict_tutor}")

        lineas.append("")
        lineas.append(f"Conclusión resumida: {resumen.mensaje_corto}")

        if resumen.es_aceptable:
            lineas.append(
                "\n✅ El modelo cumple los criterios de χ²_red y p "
                "considerados aceptables."
            )
        else:
            # El mensaje ya viene en resumen.mensaje_corto
            pass

        self.txt_resumen.setPlainText("\n".join(lineas))

    # -----------------------
    # Pestaña sweep
    # -----------------------
    def _plot_sweep(self) -> None:
        """
        Dibuja χ²_red_mean vs min_occ usando chi2_sweep.csv.

        Se toma el χ²_red_mean mínimo por cada min_occ, según 'chi2_red_mean'.
        """
        self.canvas_sweep.axes.clear()
        self.lbl_sweep_info.clear()

        try:
            df = self.vm.cargar_sweep()
        except Exception as exc:
            logger.exception("No se pudo cargar chi2_sweep.csv: %s", exc)
            self.canvas_sweep.axes.text(
                0.5,
                0.5,
                "No se pudo cargar chi2_sweep.csv",
                ha="center",
                va="center",
                transform=self.canvas_sweep.axes.transAxes,
            )
            self.canvas_sweep.draw()
            return

        if "min_occ" not in df.columns or "chi2_red_mean" not in df.columns:
            self.canvas_sweep.axes.text(
                0.5,
                0.5,
                "chi2_sweep.csv no contiene columnas 'min_occ' y 'chi2_red_mean'",
                ha="center",
                va="center",
                transform=self.canvas_sweep.axes.transAxes,
            )
            self.canvas_sweep.draw()
            return

        # χ²_red_mean mínimo por cada min_occ
        resumen = df.groupby("min_occ")["chi2_red_mean"].min().reset_index()

        x = resumen["min_occ"].to_numpy()
        y = resumen["chi2_red_mean"].to_numpy()

        self.canvas_sweep.axes.plot(x, y, "o-", label="χ²_red mínimo por min_occ")

        # Banda de aceptabilidad [0.5, 2.0]
        y_min = self.vm.chi2_red_min_aceptable
        y_max = self.vm.chi2_red_max_aceptable
        self.canvas_sweep.axes.axhspan(
            y_min, y_max, color="green", alpha=0.1, label="Zona aceptable"
        )
        self.canvas_sweep.axes.axhline(
            1.0, color="gray", linestyle="--", alpha=0.7, label="χ²_red = 1"
        )

        # Punto mínimo global
        idx_min = np.argmin(y)
        self.canvas_sweep.axes.plot(
            x[idx_min],
            y[idx_min],
            "s",
            mec="black",
            mfc="yellow",
            label="Mínimo global",
        )

        self.canvas_sweep.axes.set_xlabel("min_occ")
        self.canvas_sweep.axes.set_ylabel("χ²_red (χ²_red_mean)")
        self.canvas_sweep.axes.set_title("Curva de justificación χ²_red vs min_occ")
        self.canvas_sweep.axes.grid(True, alpha=0.3)
        self.canvas_sweep.axes.legend()

        self.canvas_sweep.draw()

        # Texto descriptivo
        texto = []
        texto.append("Curva de justificación del modelo O₃–Sₙ.")
        texto.append(
            f"Se muestra el χ²_red_mean mínimo para cada valor de min_occ. "
            f"La banda verde indica el rango aceptable "
            f"[{self.vm.chi2_red_min_aceptable}, {self.vm.chi2_red_max_aceptable}]."
        )

        if self.vm.modo == "mensual":
            texto.append(
                "En modo MENSUAL, se espera que al menos una combinación "
                "(min_occ, N_bins) se encuentre dentro de esta banda o cercana a ella, "
                "respaldando la aceptación del modelo lineal."
            )
        else:
            texto.append(
                "En modo DIARIO, típicamente todos los valores de χ²_red_mean "
                "se mantienen por encima de la banda aceptable, reforzando el rechazo "
                "del modelo lineal a esta escala temporal."
            )

        self.lbl_sweep_info.setText("\n".join(texto))

    # -----------------------
    # Pestaña superficies
    # -----------------------
    def _plot_superficies(self) -> None:
        self.canvas_sup.axes.clear()
        self.lbl_sup_info.clear()

        gui_dir = self.vm.gui_dir
        if not os.path.isdir(gui_dir):
            self.canvas_sup.axes.text(
                0.5,
                0.5,
                "No existe el directorio de resultados para el modo actual.",
                ha="center",
                va="center",
                transform=self.canvas_sup.axes.transAxes,
            )
            self.canvas_sup.draw()
            self.lbl_sup_info.setText(
                "Genere los resultados del modo seleccionado antes de "
                "visualizar superficies globales de χ²_red."
            )
            return

        # Buscamos algún CSV tipo *_grid.csv en el directorio del modo actual
        grid_files = [
            f for f in os.listdir(gui_dir) if f.endswith(".csv") and "grid" in f.lower()
        ]

        if not grid_files:
            self.canvas_sup.axes.text(
                0.5,
                0.5,
                "No se encontraron superficies (archivos *grid.csv) "
                "para el modo actual.",
                ha="center",
                va="center",
                transform=self.canvas_sup.axes.transAxes,
            )
            self.canvas_sup.draw()
            self.lbl_sup_info.setText(
                "Las superficies globales de χ²_red (por ejemplo, sobre lat/lon o "
                "coeficientes a₀–a₁) pueden generarse en el pipeline de "
                "preprocesamiento y visualizarse aquí si se guardan como "
                "archivos *_grid.csv en gui_mensual/gui_diario."
            )
            return

        # Para no complicar, tomamos el primero
        grid_path = os.path.join(gui_dir, grid_files[0])
        try:
            df = pd.read_csv(grid_path)
        except Exception as exc:
            self.canvas_sup.axes.text(
                0.5,
                0.5,
                f"No se pudo leer {grid_files[0]}:\n{exc}",
                ha="center",
                va="center",
                transform=self.canvas_sup.axes.transAxes,
            )
            self.canvas_sup.draw()
            return

        # Intentar inferir columnas X, Y, Z
        if len(df.columns) < 3:
            self.canvas_sup.axes.text(
                0.5,
                0.5,
                "El archivo de grid no tiene al menos 3 columnas.",
                ha="center",
                va="center",
                transform=self.canvas_sup.axes.transAxes,
            )
            self.canvas_sup.draw()
            return

        col_z = None
        for c in df.columns:
            cl = c.lower()
            if cl in ("chi2_red", "chi2red", "chi2_reduced"):
                col_z = c
                break
        if col_z is None:
            # Simplemente tomamos la tercera columna como Z
            col_z = df.columns[2]

        x = df.iloc[:, 0].values
        y = df.iloc[:, 1].values
        z = df[col_z].values

        # Asumimos que es una malla regular ordenada
        try:
            nx = len(np.unique(x))
            ny = len(np.unique(y))
            X = x.reshape(ny, nx)
            Y = y.reshape(ny, nx)
            Z = z.reshape(ny, nx)
        except Exception:
            # Si no podemos reshaping, hacemos scatter
            sc = self.canvas_sup.axes.scatter(x, y, c=z, cmap="viridis")
            self.canvas_sup.figure.colorbar(sc, ax=self.canvas_sup.axes, label="χ²_red")
            self.canvas_sup.axes.set_xlabel(df.columns[0])
            self.canvas_sup.axes.set_ylabel(df.columns[1])
            self.canvas_sup.axes.set_title(f"Superficie dispersa de {col_z}")
            self.canvas_sup.draw()
            self.lbl_sup_info.setText(
                f"Superficie dispersa de χ²_red ({col_z}) en función de "
                f"{df.columns[0]} y {df.columns[1]}."
            )
            return

        im = self.canvas_sup.axes.pcolormesh(X, Y, Z, shading="auto", cmap="viridis")
        self.canvas_sup.figure.colorbar(im, ax=self.canvas_sup.axes, label="χ²_red")
        self.canvas_sup.axes.set_xlabel(df.columns[0])
        self.canvas_sup.axes.set_ylabel(df.columns[1])
        self.canvas_sup.axes.set_title(f"Superficie global de {col_z}")
        self.canvas_sup.draw()

        self.lbl_sup_info.setText(
            f"Superficie global de χ²_red ({col_z}) en función de "
            f"{df.columns[0]} y {df.columns[1]}. Valores cercanos a 1 "
            "indican combinaciones (por ejemplo de coeficientes o de "
            "localización) donde el modelo se ajusta mejor."
        )

