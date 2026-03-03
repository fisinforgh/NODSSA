# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap

from ..core.constantes import APP_NAME
from ..core.recursos import ResourceManager

class PresentationPanel(QWidget):
    """
    Panel de presentación inicial de la aplicación.
    Muestra el título, autores y descripción breve.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # Logos
        logos_layout = QHBoxLayout()
        logos_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logos_layout.setSpacing(30)

        # Helper para crear logos
        def add_logo(filename, height=120):
            lbl = QLabel()
            path = ResourceManager.get_asset(filename)
            if path.exists():
                pixmap = QPixmap(str(path))
                lbl.setPixmap(pixmap.scaledToHeight(height, Qt.TransformationMode.SmoothTransformation))
            else:
                lbl.setText(f"[Logo: {filename}]")
                lbl.setStyleSheet("border: 1px dashed gray; padding: 10px;")
            logos_layout.addWidget(lbl)

        # Agregar los 3 logos (ajustar nombres según disponibilidad)
        add_logo("logoLIFAE.png", 200)  # Izquierda
        add_logo("logo_universidad.png", 220)    # Centro (más grande)
        add_logo("logo_fisinfor.png", 200)  # Derecha (simetría)

        layout.addLayout(logos_layout)
        layout.addSpacing(20)

        # Título
        lbl_title = QLabel(APP_NAME)
        lbl_title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        # Subtítulo / Versión
        lbl_subtitle = QLabel("Herramienta de Análisis y Validación Estadística")
        lbl_subtitle.setFont(QFont("Arial", 16))
        lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_subtitle.setStyleSheet("color: #555;")
        layout.addWidget(lbl_subtitle)

        # Espacio
        layout.addSpacing(30)

        # Descripción
        desc_text = (
            "Plataforma computacional el análisis estadístico y modelado de la columna total de ozono.\n"
            "Implementa algoritmos de ajuste por Mínimos Cuadrados Ponderados (WLS), pruebas de bondad de ajuste Chi-cuadrado (χ²)\n"
            "y validación rigurosa de supuestos (Shapiro-Wilk, Breusch-Pagan) para evaluar la correlación con la actividad solar.\n"
            "Diseñada para el procesamiento eficiente de series temporales y la generación automatizada de diagnósticos científicos."
        )
        lbl_desc = QLabel(desc_text)
        lbl_desc.setFont(QFont("Arial", 12))
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_desc)

        # Créditos
        layout.addSpacing(40)
        lbl_credits = QLabel("Autores: Julián Andrés Salamanca Bernal\nDiego Daniel Forero Castro")
        lbl_credits.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        lbl_credits.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_credits.setStyleSheet("color: #333;")
        layout.addWidget(lbl_credits)

        layout.addStretch()
