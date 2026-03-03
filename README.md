# NODSSA — NASA Ozone Data – Sunspots Statistical Analyzer

NODSSA es un sistema de software científico desarrollado en Python para analizar la relación físico–estadística entre la actividad solar (p. ej., número/área de manchas solares del WDC–SILSO) y la columna total de ozono estratosférico obtenida desde misiones satelitales de la NASA. El flujo de trabajo está orientado a series temporales mensuales de largo plazo (1979–2025) y soporta tanto ejecución por scripts como una interfaz gráfica (GUI) basada en PySide6.

El proyecto fue construido con énfasis en reproducibilidad: aislamiento de dependencias (entornos virtuales), documentación técnica, validación estadística y pruebas sistemáticas del software.

## Alcance del análisis

- Periodo principal de estudio: 1979–2025 (series mensuales).
- Cobertura espacial: cinturón global 90°N–90°S (con posibilidad de operar en dominios más restringidos).
- Fuentes de datos: registros satelitales de ozono (misiones NASA disponibles en el pipeline) y registros solares estandarizados (WDC–SILSO).

## Características principales

- Pipeline automatizado: armonización y control de calidad de datos, generación de insumos para análisis y reportes.
- Modelado y evaluación: regresión (incluida ponderada según el módulo), métricas de desempeño (RMSE/MAE) y validación temporal (ventanas deslizantes/rolling cuando aplica).
- Diagnósticos de supuestos: pruebas como Shapiro–Wilk (normalidad), Breusch–Pagan (heterocedasticidad) y Ljung–Box (autocorrelación), entre otras, según el módulo de validación.
- Métricas χ² y χ²_red para evaluar ajuste en componentes específicos del sistema.
- GUI (PySide6): interfaz de escritorio para exploración interactiva, visualización y revisión de diagnósticos.

## Estructura del repositorio (referencia rápida)

A nivel general encontrarás:
- Scripts de procesamiento, conversión y análisis (ingesta/ETL, EDA, modelos y validación).
- `GUI/ComparadorOzono/`: aplicación de escritorio (PySide6), con:
  - `app/main.py`: punto de entrada de la GUI.
  - `app/core/`: lógica del análisis (χ², diagnósticos, validación, recursos, tema, constantes).
  - `app/ui/`: componentes de interfaz (ventana principal, splash, paneles).
  - `app/assets/`: imágenes e íconos.
  - `app/styles/`: temas QSS.
  - `tests/`: pruebas unitarias.

## Requisitos

- Python 3.12 recomendado (o compatible).
- Dependencias en `requirements.txt` (incluye, entre otras: numpy, pandas, scipy, statsmodels, matplotlib y PySide6).
- Linux (Ubuntu 20.04 LTS o superior) recomendado para instalación guía; también es compatible con Windows/macOS usando entornos virtuales.

## Instalación y ejecución

Consulta el archivo [`INSTALL.md`](INSTALL.md) para una guía paso a paso (Linux/Windows/macOS) y para empaquetar la GUI como ejecutable.

## Pruebas y validación

Durante el desarrollo se consideraron, entre otras, las siguientes categorías de pruebas:
- Ingesta de datos (consistencia con registros originales).
- Algoritmos numéricos (contraste con implementaciones de referencia).
- Validación estadística (datasets sintéticos para verificar el comportamiento de los tests).
- Interfaz gráfica (funcionalidad e interactividad de paneles).
- Reproducibilidad del pipeline (mismas condiciones → mismos resultados dentro de tolerancias).

## Autores

- Diego Daniel Forero Castro — Universidad Distrital Francisco José de Caldas (UDFJC)
- Julián Andrés Salamanca Bernal — Universidad Distrital Francisco José de Caldas (UDFJC)

## Licencia

Define la licencia del proyecto (por ejemplo MIT) y agrega el archivo `LICENSE` en la raíz del repositorio.

## Agradecimientos

- Universidad Distrital Francisco José de Caldas (apoyo institucional y académico).
- NASA y WDC–SILSO por la disponibilidad de datos públicos para investigación.
