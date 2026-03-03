"""
Gestión de temas de la aplicación (claro/oscuro).
"""

from pathlib import Path
from typing import Optional, Dict
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import QSettings, Signal, QObject

from .recursos import ResourceManager
from .constantes import DEFAULT_THEME, AVAILABLE_THEMES


class ThemeManager(QObject):
    """Gestor de temas de la aplicación."""
    
    tema_cambiado = Signal(str)  # Emite el nombre del nuevo tema
    
    def __init__(self):
        """Inicializa el gestor de temas."""
        super().__init__()
        self._tema_actual = DEFAULT_THEME
        self._settings = QSettings("UDISTRITAL", "ComparadorOzono")
        self._paletas = {
            "dark": self._crear_paleta_oscura(),
            "light": self._crear_paleta_clara()
        }
    
    @property
    def tema_actual(self) -> str:
        """Obtiene el tema actual."""
        return self._tema_actual
    
    def _crear_paleta_oscura(self) -> QPalette:
        """Crea la paleta para tema oscuro."""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 48))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(40, 40, 40))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(60, 60, 60))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.Text, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Link, QColor(46, 134, 171))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(46, 134, 171))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(127, 127, 127))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(127, 127, 127))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor(80, 80, 80))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, QColor(127, 127, 127))
        return palette
    
    def _crear_paleta_clara(self) -> QPalette:
        """Crea la paleta para tema claro."""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0)) # Negro puro
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0)) # Negro puro
        palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0)) # Negro puro
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(46, 134, 171))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(46, 134, 171))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(160, 160, 160))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(160, 160, 160))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(160, 160, 160))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor(200, 200, 200))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, QColor(160, 160, 160))
        return palette
    
    def aplicar_tema(self, nombre_tema: str) -> bool:
        """Aplica un tema a la aplicación (Qt + QSS)."""
        if nombre_tema not in AVAILABLE_THEMES:
            return False
        app = QApplication.instance()
        if not app:
            return False
        app.setPalette(self._paletas[nombre_tema])
        qss = self._cargar_qss(nombre_tema)
        if qss:
            app.setStyleSheet(qss)
        self._tema_actual = nombre_tema
        self._settings.setValue("theme", nombre_tema)
        self.tema_cambiado.emit(nombre_tema)
        return True
    
    def _cargar_qss(self, nombre_tema: str) -> Optional[str]:
        """Carga el QSS del tema."""
        qss_file = ResourceManager.get_style(f"theme_{nombre_tema}.qss")
        return ResourceManager.read_text_file(qss_file)
    
    def alternar_tema(self) -> str:
        """Alterna entre tema claro y oscuro."""
        nuevo_tema = "light" if self._tema_actual == "dark" else "dark"
        self.aplicar_tema(nuevo_tema)
        return nuevo_tema
    
    def cargar_tema_guardado(self) -> str:
        """Carga el tema guardado en preferencias."""
        tema_guardado = self._settings.value("theme", DEFAULT_THEME)
        self.aplicar_tema(tema_guardado)
        return tema_guardado
    
    def get_icono_tema(self) -> str:
        """Ícono acorde al tema actual."""
        return "sun.svg" if self._tema_actual == "dark" else "moon.svg"
    
    def es_tema_oscuro(self) -> bool:
        """¿Tema oscuro?"""
        return self._tema_actual == "dark"


# === Funciones de theming para Matplotlib (MÓDULO, no dentro de la clase) ===

def mpl_params(tema: str) -> dict:
    dark = (tema or "").lower() == "dark"
    base = {
        "figure.dpi": 120,
        "savefig.dpi": 150,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "axes.linewidth": 1.0,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.8,
        "grid.linestyle": "-",
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "xtick.direction": "inout",
        "ytick.direction": "inout",
        "xtick.major.size": 6,
        "ytick.major.size": 6,
        "legend.frameon": False,
        "legend.fontsize": 10,
        "lines.linewidth": 1.6,
        "lines.markersize": 4.5,
        "font.size": 11,
        "font.family": ["DejaVu Sans", "Arial", "Liberation Sans"],
        "figure.autolayout": True,
    }
    if dark:
        base.update({
            "figure.facecolor": "#101418",
            "axes.facecolor":   "#101418",
            "axes.edgecolor":   "#D6E1F5",
            "text.color":       "#E8F0FF",
            "axes.labelcolor":  "#E8F0FF",
            "xtick.color":      "#CED8F0",
            "ytick.color":      "#CED8F0",
            "grid.color":       "#93A2C6",
        })
    else:
        base.update({
            "figure.facecolor": "white",
            "axes.facecolor":   "white",
            "axes.edgecolor":   "#000000",
            "text.color":       "#000000",
            "axes.labelcolor":  "#000000",
            "xtick.color":      "#000000",
            "ytick.color":      "#000000",
            "grid.color":       "#7a8a99",
        })
    return base


def apply_mpl_theme(tema: str) -> None:
    import matplotlib as mpl
    mpl.rcParams.update(mpl.rcParamsDefault)  # reset limpio
    mpl.rcParams.update(mpl_params(tema))

