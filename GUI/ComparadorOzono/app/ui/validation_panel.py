# python/GUI/ComparadorOzono/app/ui/validation_panel.py
# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QDoubleSpinBox, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QTextEdit, QSplitter)
from PySide6.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
import pandas as pd
import numpy as np

class ValidationPanel(QWidget):
    """
    Panel para visualizar la validación de supuestos estadísticos.
    Muestra histogramas de p-valores y tablas resumen dinámicas.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.df_results = pd.DataFrame() # ['dataset_id', 'test_name', 'p_value']
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # --- Controles Superiores ---
        controls_layout = QHBoxLayout()
        
        # Selector de Alpha (El selector de test se elimina para mostrar todos)
        self.spin_alpha = QDoubleSpinBox()
        self.spin_alpha.setRange(0.001, 0.20)
        self.spin_alpha.setSingleStep(0.01)
        self.spin_alpha.setValue(0.05)
        self.spin_alpha.setDecimals(3)
        self.spin_alpha.setPrefix("α = ")
        self.spin_alpha.valueChanged.connect(self.update_all)
        
        controls_layout.addWidget(QLabel("Nivel de Significancia Global:"))
        controls_layout.addWidget(self.spin_alpha)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # --- Splitter Principal (Gráfico vs Resumen) ---
        splitter = QSplitter(Qt.Horizontal)
        
        # 1. Panel Izquierdo: Gráfico (Grilla 2x2)
        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)
        
        # Aumentamos el tamaño de la figura para acomodar 4 gráficos
        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        
        splitter.addWidget(plot_widget)
        
        # 2. Panel Derecho: Resumen y Tabla
        summary_widget = QWidget()
        summary_layout = QVBoxLayout(summary_widget)
        
        # Texto Resumen
        self.text_summary = QTextEdit()
        self.text_summary.setReadOnly(True)
        # self.text_summary.setMaximumHeight(200) # Permitir que crezca un poco más
        
        # Tabla Resumen Global
        self.table_summary = QTableWidget()
        self.table_summary.setColumnCount(4)
        self.table_summary.setHorizontalHeaderLabels(["Supuesto", "Test", "N (p > α)", "% (p > α)"])
        self.table_summary.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        summary_layout.addWidget(QLabel("<b>Resumen del Análisis:</b>"))
        summary_layout.addWidget(self.text_summary, 1) # Stretch factor 1
        summary_layout.addWidget(QLabel("<b>Tabla Resumen (Todos los Tests):</b>"))
        summary_layout.addWidget(self.table_summary, 1) # Stretch factor 1
        
        splitter.addWidget(summary_widget)
        
        # Configurar tamaños iniciales del splitter
        splitter.setStretchFactor(0, 3) # Gráfico más grande
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)

    def load_data(self, df: pd.DataFrame):
        """
        Carga los resultados de los tests.
        df debe tener columnas: ['dataset_id', 'test_name', 'p_value']
        """
        self.df_results = df
        self.update_all()

    def update_all(self):
        self.update_plots()
        self.update_summary_table()
        self.update_summary_text()

    def update_plots(self):
        """Dibuja los 4 histogramas en una grilla 2x2 con estilo de publicación."""
        self.figure.clear()
        # Forzar fondo blanco para coincidir con el libro
        self.figure.patch.set_facecolor('white')
        
        if self.df_results.empty:
            self.canvas.draw()
            return
            
        alpha = self.spin_alpha.value()
        
        # Definir los 4 tests y sus posiciones
        # Formato título: "Nombre [test Metodo]"
        tests_config = [
            ("Linealidad (Rainbow)", 221, "Linealidad [test Rainbow]"),
            ("Independencia (Ljung-Box)", 222, "Independencia [test Ljung-Box]"),
            ("Normalidad (Shapiro-Wilk)", 223, "Normalidad [test Shapiro-Wilk]"),
            ("Homocedasticidad (Breusch-Pagan)", 224, "Homocedasticidad [test Breusch-Pagan]")
        ]
        
        for test_name, subplot_idx, title_full in tests_config:
            ax = self.figure.add_subplot(subplot_idx)
            ax.set_facecolor('white') # Fondo del eje blanco
            
            df_test = self.df_results[self.df_results["test_name"] == test_name]
            p_values = df_test["p_value"].dropna()
            
            if len(p_values) > 0:
                # Histograma: Barras grises con borde negro (estilo libro)
                counts, bins, patches = ax.hist(
                    p_values, 
                    bins=30, 
                    color='#aaaaaa', # Gris
                    edgecolor='black', 
                    linewidth=0.8,
                    alpha=1.0
                )
                
                # Línea de Alpha roja punteada
                ax.axvline(alpha, color='red', linestyle='--', linewidth=1.5)
                
                # Texto "p-valor=0.05" en rojo
                # Posición: un poco a la derecha de la línea, arriba
                y_max = ax.get_ylim()[1]
                ax.text(
                    alpha + 0.02, 
                    y_max * 0.85, 
                    f'p-valor={alpha}', 
                    color='red', 
                    fontsize=9,
                    fontweight='normal'
                )
            
            # Títulos y etiquetas
            ax.set_title(title_full, fontsize=10, fontweight='bold', pad=10)
            ax.set_xlim(0, 1)
            
            # Etiquetas de ejes (solo en bordes exteriores o en todos según imagen)
            # La imagen muestra etiquetas en todos o al menos "Conjuntos de datos" en Y
            ax.set_ylabel("Conjuntos de datos", fontsize=9)
            ax.set_xlabel("p-valor", fontsize=9)
            
            # Estilo "limpio": quitar spines superior y derecho
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_linewidth(0.8)
            ax.spines['bottom'].set_linewidth(0.8)
            
            # Sin grid (o muy sutil si se prefiere, pero la imagen parece no tener)
            ax.grid(False)
            
            ax.tick_params(labelsize=8)

        self.figure.tight_layout()
        self.canvas.draw()

    def update_summary_text(self):
        """Genera un resumen textual para todos los tests."""
        if self.df_results.empty:
            self.text_summary.clear()
            return

        alpha = self.spin_alpha.value()
        tests = [
            "Linealidad (Rainbow)", 
            "Independencia (Ljung-Box)", 
            "Normalidad (Shapiro-Wilk)", 
            "Homocedasticidad (Breusch-Pagan)"
        ]
        
        html = f"<h3>Análisis de Supuestos (α = {alpha})</h3>"
        
        for test_name in tests:
            df_test = self.df_results[self.df_results["test_name"] == test_name]
            p_values = df_test["p_value"].dropna()
            n_total = len(p_values)
            
            if n_total == 0:
                continue
                
            n_pass = np.sum(p_values > alpha)
            pct_pass = (n_pass / n_total) * 100
            
            # Interpretación breve
            status = "<b>CUMPLE</b>" if pct_pass > 50 else "<span style='color:red'>NO CUMPLE</span>"
            
            html += (
                f"<p><b>{test_name}:</b><br>"
                f"• {n_pass} de {n_total} conjuntos ({pct_pass:.1f}%) tienen p > α.<br>"
                f"• Tendencia general: {status} la hipótesis nula."
                f"</p>"
            )
            
        self.text_summary.setHtml(html)

    def update_summary_table(self):
        if self.df_results.empty:
            return
            
        alpha = self.spin_alpha.value()
        tests = self.df_results["test_name"].unique()
        
        self.table_summary.setRowCount(len(tests))
        
        # Mapeo de Test a Supuesto
        supuesto_map = {
            "Linealidad (Rainbow)": "Linealidad",
            "Independencia (Ljung-Box)": "Independencia",
            "Normalidad (Shapiro-Wilk)": "Normalidad",
            "Homocedasticidad (Breusch-Pagan)": "Homocedasticidad"
        }
        
        for i, test in enumerate(tests):
            df_test = self.df_results[self.df_results["test_name"] == test]
            p_values = df_test["p_value"].dropna()
            
            n_total = len(p_values)
            n_pass = np.sum(p_values > alpha)
            pct_pass = (n_pass / n_total) * 100 if n_total > 0 else 0
            
            supuesto = supuesto_map.get(test, "Otro")
            
            self.table_summary.setItem(i, 0, QTableWidgetItem(supuesto))
            self.table_summary.setItem(i, 1, QTableWidgetItem(test))
            self.table_summary.setItem(i, 2, QTableWidgetItem(f"{n_pass} / {n_total}"))
            self.table_summary.setItem(i, 3, QTableWidgetItem(f"{pct_pass:.2f}%"))
