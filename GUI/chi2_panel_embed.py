# python/GUI/chi2_panel_embed.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Optional, Tuple
import os, pandas as pd
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QSpinBox, QTextEdit, QGroupBox
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from ..chi2_bins import (
    from_monthly_real, from_binned_generic,
    compute_chi2_from_bins, sweep_min_occ
)

class Chi2PanelEmbed(QWidget):
    """
    Pestaña para calcular/visualizar χ² y χ²_red SOLO con CSV de 'reales'.
    Acepta:
      - mensual: Year,Month,Ozone_mean,Ozone_std,Count
      - binned:  sun_bin_center,y_mean,sigma[,occ]
    """
    def __init__(self, parent: Optional[QWidget]=None):
        super().__init__(parent)
        self.csv_path: Optional[str] = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(8,8,8,8); root.setSpacing(10)
        hdr = QHBoxLayout()
        self.btn_cargar = QPushButton("Cargar CSV (reales)"); self.btn_cargar.clicked.connect(self._on_cargar)
        hdr.addWidget(self.btn_cargar)
        hdr.addWidget(QLabel("min_occ:"))
        self.spin_minocc = QSpinBox(); self.spin_minocc.setRange(1,100); self.spin_minocc.setValue(12)
        hdr.addWidget(self.spin_minocc)
        self.btn_calc = QPushButton("Calcular χ² (reales)"); self.btn_calc.clicked.connect(self._on_calcular)
        hdr.addWidget(self.btn_calc); hdr.addStretch(); root.addLayout(hdr)

        grp = QGroupBox("Resultados y Gráficas"); gl = QVBoxLayout(grp)

        self.canvas_basic = FigureCanvas(None); self.tb_basic = NavigationToolbar(self.canvas_basic, self)
        gl.addWidget(QLabel("Caso (a) — Sin corte")); gl.addWidget(self.tb_basic); gl.addWidget(self.canvas_basic, 1)

        self.canvas_cut = FigureCanvas(None); self.tb_cut = NavigationToolbar(self.canvas_cut, self)
        gl.addWidget(QLabel("Caso (b) — Con corte por ocurrencias")); gl.addWidget(self.tb_cut); gl.addWidget(self.canvas_cut, 1)

        self.canvas_sweep = FigureCanvas(None); self.tb_sweep = NavigationToolbar(self.canvas_sweep, self)
        gl.addWidget(QLabel("Curva de justificación — χ²/ν vs min_occ")); gl.addWidget(self.tb_sweep); gl.addWidget(self.canvas_sweep, 1)

        root.addWidget(grp, 1)

        self.txt = QTextEdit(); self.txt.setReadOnly(True); self.txt.setMinimumHeight(140)
        self.txt.setStyleSheet("QTextEdit{font-family:Consolas,'Courier New',monospace}")
        root.addWidget(self.txt)

    @Slot()
    def _on_cargar(self):
        p, _ = QFileDialog.getOpenFileName(self, "Seleccionar CSV (reales)", "", "CSV (*.csv);;Todos (*.*)")
        if p: self.csv_path = p

    @Slot()
    def _on_calcular(self):
        if not self.csv_path or not os.path.exists(self.csv_path):
            self.txt.setPlainText("Debes cargar un CSV válido.")
            return
        df = pd.read_csv(self.csv_path)
        # Detección de formato
        if {"Year","Month","Ozone_mean","Ozone_std","Count"}.issubset(df.columns):
            bins = from_monthly_real(df)
        elif {"sun_bin_center","y_mean","sigma"}.issubset(df.columns):
            bins = from_binned_generic(df)
        else:
            self.txt.setPlainText("Formato no soportado. Usa mensual (Year,Month,...) o binned (sun_bin_center,y_mean,sigma).")
            return

        min_occ = int(self.spin_minocc.value())
        try:
            r0, f0 = compute_chi2_from_bins(bins, min_occ=None)
            r1, f1 = compute_chi2_from_bins(bins, min_occ=min_occ)
            dsw, fsw = sweep_min_occ(bins, range(3,21))
        except Exception as e:
            self.txt.setPlainText(f"Error en cálculo: {e}")
            return

        # Pintar
        self.canvas_basic.figure = f0; self.canvas_basic.draw_idle()
        self.canvas_cut.figure   = f1; self.canvas_cut.draw_idle()
        self.canvas_sweep.figure = fsw; self.canvas_sweep.draw_idle()

        def fmt_row(r):
            return (f"N={r.N} ν={r.nu} χ²={r.chi2:.4g} χ²/ν={r.chi2_red:.4g}  "
                    f"p(two)={r.p_two_sided:.4g} CDF={r.p_cdf:.4g} "
                    f"[{r.chi2_lo:.4g},{r.chi2_hi:.4g}]  "
                    f"a₀={r.a0:.4g}±{r.sigma_a0:.4g}  a₁={r.a1:.4g}±{r.sigma_a1:.4g}  "
                    f"PASA χ²={'✅' if r.veredict_chi else '❌'}  Tutor={'✅' if r.veredict_tutor else '❌'}  "
                    f"min_occ={r.min_occ if r.min_occ is not None else '-'}  %↓={r.pct_reduction:.1f}%")

        self.txt.setPlainText(
            "== SIN CORTE ==\n" + fmt_row(r0) +
            "\n\n== CON CORTE ==\n" + fmt_row(r1) +
            "\n\n== SWEEP (primeros 10) ==\n" + dsw.head(10).to_string(index=False, float_format=lambda x: f"{x:.4g}")
        )
