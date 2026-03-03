"""
Constantes globales de la aplicación Comparador de Ozono.
"""

from __future__ import annotations

from pathlib import Path

# ============================================================================
# INFORMACIÓN GENERAL DE LA APLICACIÓN
# ============================================================================

APP_NAME = "O3-Sn Statistical Analyzer"
APP_VERSION = "1.0.0"

APP_DESCRIPTION = (
    "Herramienta para el análisis comparativo de datos de ozono y la "
    "evaluación de modelos estadísticos (por ejemplo, modelo lineal O₃–Sₙ "
    "entre columna total de ozono y número de manchas solares), incluyendo "
    "diagnósticos de χ², χ²_red y p-valores."
)

# Organización / institución (ajustada a tu contexto actual)
APP_ORGANIZATION = "Universidad Distrital Francisco José de Caldas"
APP_DEPARTMENT = "Facultad de Ingeniería"

# Alias por compatibilidad con código previo
ORGANIZATION = APP_ORGANIZATION
DEPARTMENT = APP_DEPARTMENT

# ============================================================================
# RUTAS BASE PARA DATOS Y RESULTADOS (INTEGRACIÓN CON ozono-tesis)
# ============================================================================

import sys

# ...

# Archivo actual:
#   .../ozono-tesis/python/GUI/ComparadorOzono/app/core/constantes.py
THIS_FILE = Path(__file__).resolve()

if getattr(sys, 'frozen', False):
    # Si estamos en el ejecutable de PyInstaller, los datos están en _MEIPASS
    # Se asume que se empaquetaron con --add-data "data/processed:data/processed"
    GUI_BASE_DIR = str(Path(sys._MEIPASS) / "data" / "processed")
else:
    # Estructura típica de padres:
    #   parents[0] = core
    #   parents[1] = app
    #   parents[2] = ComparadorOzono
    #   parents[3] = GUI
    #   parents[4] = python
    #   parents[5] = ozono-tesis   <-- aquí vive data/processed
    OZONO_TESIS_ROOT = THIS_FILE.parents[5]

    # Directorio base donde los scripts de la tesis generan:
    #   data/processed/gui_mensual
    #   data/processed/gui_diario
    GUI_BASE_DIR = str(OZONO_TESIS_ROOT / "data" / "processed")

# ============================================================================
# CONFIGURACIÓN DE TEMAS
# ============================================================================

DEFAULT_THEME = "light"
AVAILABLE_THEMES = ["light", "dark"]

# ============================================================================
# CONFIGURACIÓN DE VENTANAS
# ============================================================================

WINDOW_MIN_WIDTH = 1024
WINDOW_MIN_HEIGHT = 700
SPLASH_DURATION_MS = 2000

# ============================================================================
# CONFIGURACIÓN DE ANÁLISIS ESTADÍSTICO GENERAL
#   (para diagnósticos de residuales real vs predicho, etc.)
# ============================================================================

MAX_SHAPIRO_SAMPLES = 5000   # Límite para la prueba de Shapiro-Wilk
DEFAULT_BINS = 30            # Bins por defecto para histogramas
ACF_LAGS = 30                # Lags para el gráfico ACF
SIGNIFICANCE_LEVEL = 0.05    # Nivel de significancia para las pruebas
DW_LOWER_BOUND = 1.5         # Límite inferior para Durbin-Watson
DW_UPPER_BOUND = 2.5         # Límite superior para Durbin-Watson

# ============================================================================
# CONFIGURACIÓN ESPECÍFICA PARA χ² DEL MODELO O₃–Sₙ (ozono vs manchas solares)
# ============================================================================

# Rango "razonable" de χ²_red para considerar el modelo aceptable
CHI2_RED_MIN_ACEPTABLE = 0.5
CHI2_RED_MAX_ACEPTABLE = 2.0

# Umbral de p-valor (bilateral) para aceptar el modelo
P_UMBRAL_ACEPTABLE = 0.05

# ============================================================================
# CONFIGURACIÓN DE GRÁFICOS
# ============================================================================

PLOT_DPI = 150
PLOT_FIGSIZE = (7, 4.5)
PLOT_STYLE = "seaborn-v0_8-darkgrid"

# ============================================================================
# NOMBRES DE ARCHIVOS DE SALIDA (ANÁLISIS REAL vs PREDICHO)
# ============================================================================

OUTPUT_DIR = "out_plots"
PLOT_HISTOGRAM = "histograma_residuales.png"
PLOT_QQ = "qq_residuales.png"
PLOT_ACF = "acf_residuales.png"
PLOT_SCATTER = "scatter_real_vs_predicho.png"

# ============================================================================
# FORMATOS DE ARCHIVO
# ============================================================================

SUPPORTED_FORMATS = ["CSV (*.csv)", "Excel (*.xlsx *.xls)"]
DATE_FORMAT = "%Y-%m-%d"

# ============================================================================
# MENSAJES DE LA APLICACIÓN
# ============================================================================

MSG_NO_FILES = "Por favor, cargue ambos archivos CSV (real y predicho)"
MSG_NO_COMMON_DATES = "No hay fechas comunes entre los archivos"
MSG_INVALID_FORMAT = "Cada archivo debe contener las columnas: Date, Ozone"
MSG_ANALYSIS_COMPLETE = "Análisis completado exitosamente"
MSG_ANALYSIS_ERROR = "Error durante el análisis"

# ============================================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================================

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_MAX_BYTES = 10485760  # 10 MB
LOG_BACKUP_COUNT = 5

# ============================================================================
# COLORES DEL TEMA (RGB)
# ============================================================================

COLORS = {
    "primary": "#2E86AB",
    "secondary": "#A23B72",
    "success": "#73AB84",
    "warning": "#F18F01",
    "danger": "#C73E1D",
    "info": "#6C9BD2",
    "light": "#F5F5F5",
    "dark": "#2B2D42",
}

# ============================================================================
# ATAJOS DE TECLADO
# ============================================================================

SHORTCUTS = {
    "open_real": "Ctrl+O",
    "open_pred": "Ctrl+P",
    "run_analysis": "Ctrl+R",
    "export_results": "Ctrl+E",
    "toggle_theme": "Ctrl+T",
    "show_help": "F1",
    "show_about": "Ctrl+H",
    "quit": "Ctrl+Q",
}

