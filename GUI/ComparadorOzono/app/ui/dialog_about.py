# -*- coding: utf-8 -*-
"""
Diálogo "Acerca de" de la aplicación Comparador de Ozono.

Muestra información básica de la aplicación:
  - Nombre y versión.
  - Descripción corta.
  - Institución / facultad.
  - Autoría (personalizable).
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from app.core.constantes import (
    APP_NAME,
    APP_VERSION,
    APP_DESCRIPTION,
    APP_ORGANIZATION,
    APP_DEPARTMENT,
)


class DialogAbout(QDialog):
    """
    Diálogo modal sencillo con información de la aplicación.

    Se llama desde la ventana principal con:
        dlg = DialogAbout(self)
        dlg.exec()
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Acerca de {APP_NAME}")
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self._configurar_ui()

    # ------------------------------------------------------------------ #
    # UI
    # ------------------------------------------------------------------ #
    def _configurar_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Título
        label_titulo = QLabel(f"{APP_NAME} v{APP_VERSION}")
        label_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_titulo.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        layout.addWidget(label_titulo)

        # Organización / facultad
        label_org = QLabel(
            f"<b>{APP_ORGANIZATION}</b><br/>{APP_DEPARTMENT}"
        )
        label_org.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_org.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(label_org)

        # Descripción
        label_desc = QLabel(APP_DESCRIPTION)
        label_desc.setAlignment(Qt.AlignmentFlag.AlignJustify)
        label_desc.setWordWrap(True)
        layout.addWidget(label_desc)

        # Línea separadora
        separador = QLabel("<hr>")
        separador.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(separador)

        # Información adicional / créditos
        texto_extra = QLabel(
            "Esta herramienta se integra con el proyecto de tesis sobre la "
            "relación físico–estadística entre la columna total de ozono (O₃) "
            "y la actividad solar (manchas solares, Sₙ), permitiendo explorar "
            "modelos lineales, diagnósticos de χ² y visualizaciones de bins "
            "a escala diaria y mensual."
        )
        texto_extra.setWordWrap(True)
        texto_extra.setAlignment(Qt.AlignmentFlag.AlignJustify)
        layout.addWidget(texto_extra)

        layout.addSpacerItem(
            QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        # Botón Cerrar
        boton_layout = QHBoxLayout()
        boton_layout.addStretch(1)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        boton_layout.addWidget(btn_cerrar)

        layout.addLayout(boton_layout)

        # Tamaño inicial cómodo
        self.resize(480, 320)


