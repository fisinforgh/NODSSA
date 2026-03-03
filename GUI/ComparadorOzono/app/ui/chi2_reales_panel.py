# python/GUI/ComparadorOzono/app/ui/chi2_reales_panel.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Optional
import os
import pandas as pd
from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QSpinBox, QTextEdit, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QScrollArea, QTabWidget # Añadido QTabWidget
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from ..core.chi2_bins import (
    from_monthly_real, from_binned_generic,
    compute_chi2_from_bins, sweep_min_occ
)
from ..core.chi2_plots import plot_occurrences_vs_sigma, plot_chi2_probability # Importar nueva función

class Chi2RealesPanel(QWidget):
    """
    Calcula y grafica χ²/χ²_red SOLO con CSV de datos reales.
    Acepta:
      - mensual: Year,Month,Ozone_mean,Ozone_std,Count
      - binned:  sun_bin_center,y_mean,sigma[,occ]
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.csv_path: Optional[str] = None
        self.last_result = None # Almacenar último resultado para el gráfico
        self._build_ui()

    def _build_ui(self):
        # Layout principal del widget (contendrá el ScrollArea)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll Area para evitar compresión
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        main_layout.addWidget(scroll)
        
        # Widget contenedor del contenido
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        
        # Layout del contenido (lo que antes era root)
        root = QVBoxLayout(content_widget)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        # Controles principales
        hdr = QHBoxLayout()
        self.btn_cargar = QPushButton("Cargar CSV (reales)")
        self.btn_cargar.clicked.connect(self._on_cargar)
        hdr.addWidget(self.btn_cargar)

        hdr.addWidget(QLabel("min_occ:"))
        self.spin_minocc = QSpinBox()
        self.spin_minocc.setRange(1, 100)
        self.spin_minocc.setValue(12)
        hdr.addWidget(self.spin_minocc)

        hdr.addWidget(QLabel("Y-Max (Graf 3):"))
        self.spin_ymax = QSpinBox()
        self.spin_ymax.setRange(10, 1000)
        self.spin_ymax.setValue(30) # Default solicitado
        hdr.addWidget(self.spin_ymax)

        self.btn_calc = QPushButton("Calcular χ² (reales)")
        self.btn_calc.clicked.connect(self._on_calcular)
        hdr.addWidget(self.btn_calc)
        
        # Botón de Probabilidad (Nuevo)
        self.btn_prob = QPushButton("Ver Probabilidad")
        self.btn_prob.clicked.connect(self._on_ver_probabilidad)
        self.btn_prob.setEnabled(False) # Deshabilitado hasta calcular
        hdr.addWidget(self.btn_prob)
        
        hdr.addStretch()
        root.addLayout(hdr)

        # Controles de Referencia Manual (N y NDF)
        ref_layout = QHBoxLayout()
        from PySide6.QtWidgets import QCheckBox # Import local to avoid messing up top imports if not present
        self.chk_manual_ref = QCheckBox("Usar referencia manual para %")
        ref_layout.addWidget(self.chk_manual_ref)
        
        ref_layout.addWidget(QLabel("Ref NDF:"))
        self.spin_ref_ndf = QSpinBox()
        self.spin_ref_ndf.setRange(1, 10000)
        self.spin_ref_ndf.setValue(342) # Valor del libro aprox
        self.spin_ref_ndf.setEnabled(False)
        ref_layout.addWidget(self.spin_ref_ndf)

        ref_layout.addWidget(QLabel("Ref N:"))
        self.spin_ref_n = QSpinBox()
        self.spin_ref_n.setRange(1, 10000)
        self.spin_ref_n.setValue(344)
        self.spin_ref_n.setEnabled(False)
        ref_layout.addWidget(self.spin_ref_n)
        
        self.chk_manual_ref.toggled.connect(self.spin_ref_ndf.setEnabled)
        self.chk_manual_ref.toggled.connect(self.spin_ref_n.setEnabled)
        
        ref_layout.addStretch()
        root.addLayout(ref_layout)

        # Gráficas
        grp = QGroupBox("Resultados y Gráficas")
        gl = QVBoxLayout(grp)

        self.canvas_basic = FigureCanvas(Figure())
        self.canvas_basic.setMinimumHeight(350) # Altura mínima para evitar compresión
        self.tb_basic = NavigationToolbar(self.canvas_basic, self)
        gl.addWidget(QLabel("Caso (a) — Sin corte"))
        gl.addWidget(self.tb_basic)
        gl.addWidget(self.canvas_basic)

        self.canvas_cut = FigureCanvas(Figure())
        self.canvas_cut.setMinimumHeight(350) # Altura mínima
        self.tb_cut = NavigationToolbar(self.canvas_cut, self)
        gl.addWidget(QLabel("Caso (b) — Con corte por ocurrencias"))
        gl.addWidget(self.tb_cut)
        gl.addWidget(self.canvas_cut)

        # Tabs para gráficos de justificación
        self.tabs_justificacion = QTabWidget()
        self.tabs_justificacion.setMinimumHeight(400)
        
        # Tab 1: Ocurrencias vs Sigma
        self.tab_occ = QWidget()
        l_occ = QVBoxLayout(self.tab_occ)
        self.canvas_occ = FigureCanvas(Figure())
        self.tb_occ = NavigationToolbar(self.canvas_occ, self.tab_occ)
        l_occ.addWidget(self.tb_occ)
        l_occ.addWidget(self.canvas_occ)
        self.tabs_justificacion.addTab(self.tab_occ, "Ocurrencias vs Sigma")
        
        # Tab 2: Sweep Chi2
        self.tab_sweep = QWidget()
        l_sweep = QVBoxLayout(self.tab_sweep)
        self.canvas_sweep = FigureCanvas(Figure())
        self.tb_sweep = NavigationToolbar(self.canvas_sweep, self.tab_sweep)
        l_sweep.addWidget(self.tb_sweep)
        l_sweep.addWidget(self.canvas_sweep)
        self.tabs_justificacion.addTab(self.tab_sweep, "Barrido χ² vs min_occ")

        gl.addWidget(QLabel("Justificación del umbral (min_occ)")) 
        gl.addWidget(self.tabs_justificacion)

        root.addWidget(grp)

        # Tabla de consolidado (Tabla 13)
        self.table_sweep = QTableWidget()
        self.table_sweep.setColumnCount(4)
        self.table_sweep.setHorizontalHeaderLabels([
            "Mínimo de ocurrencias", "ndf_corrida", 
            "ndf_corrida/ndf_sin_reducción (%)", "χ²_Red"
        ])
        self.table_sweep.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_sweep.setMinimumHeight(200) # Un poco más alto
        self.lbl_table = QLabel("Tabla 13. Consolidado de valores de χ²_Red")
        root.addWidget(self.lbl_table)
        root.addWidget(self.table_sweep)

        # Botón de exportar tabla
        self.btn_export_table = QPushButton("Exportar Tabla")
        self.btn_export_table.clicked.connect(self._on_export_table)
        root.addWidget(self.btn_export_table)

        # Consola de resultados
        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setMinimumHeight(120)
        self.txt.setStyleSheet("QTextEdit{font-family:Consolas,'Courier New',monospace}")
        root.addWidget(self.txt)

    @Slot()
    def _on_cargar(self):
        p, _ = QFileDialog.getOpenFileName(self, "Seleccionar CSV (reales)", "", "CSV (*.csv);;Todos (*.*)")
        if p:
            self.csv_path = p

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
            self.txt.setPlainText(
                "Formato no soportado.\n"
                "Usa mensual (Year,Month,Ozone_mean,Ozone_std,Count)\n"
                "o binned (sun_bin_center,y_mean,sigma[,occ])."
            )
            return

        min_occ = int(self.spin_minocc.value())
        ymax_val = int(self.spin_ymax.value())
        dsw = pd.DataFrame() 
        f_occ = None

        try:
            r0, f0 = compute_chi2_from_bins(bins, min_occ=None)
            r1, f1 = compute_chi2_from_bins(bins, min_occ=min_occ)
            
            # Guardar resultado para gráfico de probabilidad
            self.last_result = r1
            self.btn_prob.setEnabled(True)
            
            # Siempre calculamos el sweep para tener la tabla en el reporte
            dsw, f_sweep = sweep_min_occ(bins, range(3, 21))
            if f_sweep:
                self.canvas_sweep.figure = f_sweep
                self.canvas_sweep.draw()

            # Generar gráfico de Ocurrencias vs Sigma
            f_occ = None
            if {"Ozone_std", "Count"}.issubset(df.columns):
                f_occ = plot_occurrences_vs_sigma(df, min_occ, "Ozone_std", "Count", ymax=ymax_val)
            elif {"sigma", "occ"}.issubset(df.columns):
                f_occ = plot_occurrences_vs_sigma(df, min_occ, "sigma", "occ", ymax=ymax_val)
            
            if f_occ:
                self.canvas_occ.figure = f_occ
                self.canvas_occ.draw()
            else:
                self.canvas_occ.figure.clear()
                self.canvas_occ.draw()

        except Exception as e:
            self.txt.setPlainText(f"Error en cálculo: {e}")
            return

        # Pintar directo en la UI
        self.canvas_basic.figure = f0
        self.canvas_basic.draw_idle()
        self.canvas_cut.figure = f1
        self.canvas_cut.draw_idle()
        
        if f_occ:
            self.canvas_sweep.figure = f_occ
            self.canvas_sweep.draw_idle()

        # Poblar tabla
        if not dsw.empty and "nu" in dsw.columns:
            self.table_sweep.setRowCount(len(dsw))
            
            # Determinar valores de referencia
            if self.chk_manual_ref.isChecked():
                ndf_sin_reduccion = self.spin_ref_ndf.value()
                # n_sin_reduccion = self.spin_ref_n.value() # No se usa en la fórmula de la tabla actual
                ref_source = "Manual"
            else:
                ndf_sin_reduccion = r0.nu
                ref_source = "Automático (r0)"
            
            self.lbl_table.setText(f"Tabla 13. Consolidado de valores de χ²_Red (Ref NDF={ndf_sin_reduccion} [{ref_source}])")

            for i, row in dsw.iterrows():
                m_occ = int(row["min_occ"])
                nu = int(row["nu"])
                chi2_r = row["chi2_red"]
                
                # Cálculo del porcentaje relativo al base
                # El libro muestra el porcentaje de REDUCCIÓN (o diferencia), no de retención.
                # Fórmula: (1 - nu / ndf_sin_reduccion) * 100
                pct_val = (1.0 - (nu / ndf_sin_reduccion)) * 100.0 if ndf_sin_reduccion > 0 else 0.0
                
                self.table_sweep.setItem(i, 0, QTableWidgetItem(str(m_occ)))
                self.table_sweep.setItem(i, 1, QTableWidgetItem(str(nu)))
                self.table_sweep.setItem(i, 2, QTableWidgetItem(f"{pct_val:.1f}"))
                self.table_sweep.setItem(i, 3, QTableWidgetItem(f"{chi2_r:.3f}"))
                
                # Resaltar fila seleccionada
                if m_occ == min_occ:
                    for c in range(4):
                        it = self.table_sweep.item(i, c)
                        font = it.font()
                        font.setBold(True)
                        it.setFont(font)

        def _fmt(r):
            return (f"N={r.N}  ν={r.nu}  χ²={r.chi2:.4g}  χ²/ν={r.chi2_red:.4g}  "
                    f"p(two)={r.p_two_sided:.4g}  CDF={r.p_cdf:.4g}  "
                    f"[{r.chi2_lo:.4g},{r.chi2_hi:.4g}]  "
                    f"a₀={r.a0:.4g}±{r.sigma_a0:.4g}  a₁={r.a1:.4g}±{r.sigma_a1:.4g}  "
                    f"PASA χ²={'✅' if r.veredict_chi else '❌'}  Tutor={'✅' if r.veredict_tutor else '❌'}  "
                    f"min_occ={r.min_occ if r.min_occ is not None else '-'}  %↓={r.pct_reduction:.1f}%")

        self.txt.setPlainText(
            "== SIN CORTE ==\n" + _fmt(r0) +
            "\n\n== CON CORTE ==\n" + _fmt(r1)
        )

    @Slot()
    def _on_ver_probabilidad(self):
        """Muestra el gráfico de probabilidad en un diálogo emergente."""
        if not self.last_result:
            return
            
        r = self.last_result
        fig = plot_chi2_probability(r.nu, r.chi2)
        
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Distribución Chi-Cuadrado (ν={r.nu})")
        dlg.resize(800, 600)
        
        layout = QVBoxLayout(dlg)
        canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(canvas, dlg)
        
        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        
        dlg.exec()

    @Slot()
    def _on_export_table(self):
        """Exporta los datos de la tabla a CSV o Excel."""
        if self.table_sweep.rowCount() == 0:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Tabla", "", "CSV (*.csv);;Excel (*.xlsx)"
        )
        if not path:
            return

        # Extraer datos de la tabla
        rows = self.table_sweep.rowCount()
        cols = self.table_sweep.columnCount()
        headers = [self.table_sweep.horizontalHeaderItem(c).text() for c in range(cols)]
        
        data = []
        for r in range(rows):
            row_data = []
            for c in range(cols):
                item = self.table_sweep.item(r, c)
                row_data.append(item.text() if item else "")
            data.append(row_data)
        
        df = pd.DataFrame(data, columns=headers)
        
        try:
            if path.endswith(".csv"):
                df.to_csv(path, index=False)
            elif path.endswith(".xlsx"):
                df.to_excel(path, index=False)
            self.txt.append(f"Tabla exportada a: {path}")
        except Exception as e:
            self.txt.append(f"Error exportando tabla: {e}")
