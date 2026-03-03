"""
Módulo core con la lógica central de la aplicación.

Expone los componentes principales del núcleo:
  - ResourceManager: gestión de rutas y recursos (assets, estilos, logs).
  - ThemeManager: gestión de temas (oscuro/claro) para Qt.
  - DiagnosticosEstadisticos: utilidades para diagnósticos de modelos.
  - apply_mpl_theme / mpl_params: theming para Matplotlib.
"""

from __future__ import annotations

from .recursos import ResourceManager
from .tema import ThemeManager

# Diagnósticos estadísticos (puede no ser usado en todas las vistas)
try:
    from .diagnosticos import DiagnosticosEstadisticos
except Exception:
    DiagnosticosEstadisticos = None  # type: ignore

# Funciones de theming para Matplotlib
try:
    from .tema import apply_mpl_theme, mpl_params
except Exception:
    apply_mpl_theme = None  # type: ignore
    mpl_params = None       # type: ignore

__all__ = [
    "ResourceManager",
    "ThemeManager",
    "DiagnosticosEstadisticos",
    "apply_mpl_theme",
    "mpl_params",
]

