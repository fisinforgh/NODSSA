#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Punto de entrada principal de la aplicación Comparador de Ozono.
Configura el entorno, inicializa la aplicación Qt y lanza la interfaz.

Incluye soporte para ejecución "frozen" (PyInstaller) sin cambiar la lógica original:
- Define APP_BASE_DIR para que ResourceManager resuelva assets/styles en dev y en ejecutable.
"""

import sys
import os
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.recursos import ResourceManager
from app.core.tema import ThemeManager
from app.core.constantes import APP_NAME, APP_VERSION, DEFAULT_THEME
from app.ui.splash_window import SplashWindow
from app.ui.main_window import MainWindow


def get_runtime_base_dir() -> Path:
    """
    Devuelve el directorio base correcto en:
    - Desarrollo (ejecutando desde el repo)
    - Ejecutable PyInstaller (modo frozen, con sys._MEIPASS)
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def preparar_entorno_recursos() -> None:
    """
    Inyecta una pista de 'directorio base' para que ResourceManager encuentre:
    - assets/
    - styles/
    - logs/

    No altera la lógica original: solo define APP_BASE_DIR si no existe.
    """
    base_dir = get_runtime_base_dir()
    os.environ.setdefault("APP_BASE_DIR", str(base_dir))


def configurar_logging() -> None:
    """Configura el sistema de logging de la aplicación."""
    log_dir = ResourceManager.get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.info(f"Iniciando {APP_NAME} v{APP_VERSION}")


def configurar_aplicacion(app: QApplication) -> None:
    """
    Configura los parámetros globales de la aplicación Qt.

    Args:
        app: Instancia de QApplication
    """
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("Universidad Nacional de Colombia")
    app.setOrganizationDomain("unal.edu.co")

    # Configurar ícono de la aplicación
    icon_path = ResourceManager.get_asset("icon.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Habilitar DPI alto para pantallas de alta resolución
    app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)


def main() -> int:
    """
    Función principal que inicia la aplicación.

    Returns:
        Código de salida de la aplicación
    """
    try:
        # Preparar base dir para recursos (dev y PyInstaller)
        preparar_entorno_recursos()

        # Configurar logging
        configurar_logging()

        # Crear aplicación Qt
        app = QApplication(sys.argv)
        configurar_aplicacion(app)

        # Configurar tema inicial
        theme_manager = ThemeManager()
        theme_manager.aplicar_tema(DEFAULT_THEME)

        # Crear y mostrar splash screen
        splash = SplashWindow()
        splash.show()

        # Procesar eventos para que se muestre el splash
        app.processEvents()

        # Crear ventana principal (pero no mostrarla aún)
        main_window = MainWindow()

        # Conectar señal del splash para mostrar la ventana principal
        def mostrar_ventana_principal():
            main_window.show()
            splash.close()

        splash.ingreso_solicitado.connect(mostrar_ventana_principal)

        # Alternativamente, cerrar splash después de 3 segundos si no se hace click
        QTimer.singleShot(
            3000,
            lambda: splash.boton_ingresar.click() if splash.isVisible() else None,
        )

        logging.info("Aplicación iniciada correctamente")

        # Ejecutar loop de eventos
        return app.exec()

    except Exception as e:
        logging.critical(f"Error crítico al iniciar la aplicación: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
