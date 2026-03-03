"""
Gestión de recursos y rutas de la aplicación.
Maneja rutas de forma robusta, compatible con PyInstaller.
"""

import os
import sys
from pathlib import Path
from typing import Optional


class ResourceManager:
    """Gestor centralizado de recursos de la aplicación."""

    @staticmethod
    def get_app_dir() -> Path:
        """
        Obtiene el directorio base de la aplicación.
        Compatible con ejecución normal y empaquetada con PyInstaller.

        Prioridad:
        1) APP_BASE_DIR (inyectado por main.py)
        2) PyInstaller (sys._MEIPASS)
           - Si detecta estructura empaquetada "ComparadorOzono/app", entra ahí.
        3) Desarrollo (ruta relativa a este archivo)

        Returns:
            Path al directorio base de la aplicación
        """
        # 1) Si main.py inyectó base dir (recomendado)
        env_base = os.getenv("APP_BASE_DIR")
        if env_base:
            base = Path(env_base)

            # Si los assets/styles están directamente aquí, úsalo
            if (base / "assets").exists() or (base / "styles").exists():
                return base

            # Si los datos fueron empaquetados con subruta (PyInstaller add-data)
            nested = base / "ComparadorOzono" / "app"
            if (nested / "assets").exists() or (nested / "styles").exists():
                return nested

            # Si no existe lo esperado, de todas formas retorna base (comportamiento conservador)
            return base

        # 2) PyInstaller (frozen)
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            base = Path(sys._MEIPASS)

            # Caso A: assets/styles en la raíz de MEIPASS
            if (base / "assets").exists() or (base / "styles").exists():
                return base

            # Caso B: assets/styles dentro de "ComparadorOzono/app" (según --add-data)
            nested = base / "ComparadorOzono" / "app"
            if (nested / "assets").exists() or (nested / "styles").exists():
                return nested

            # Fallback
            return base

        # 3) Desarrollo (tu lógica original)
        return Path(__file__).parent.parent

    @staticmethod
    def get_assets_dir() -> Path:
        """
        Obtiene el directorio de assets.

        Returns:
            Path al directorio de assets
        """
        return ResourceManager.get_app_dir() / "assets"

    @staticmethod
    def get_styles_dir() -> Path:
        """
        Obtiene el directorio de estilos.

        Returns:
            Path al directorio de estilos
        """
        return ResourceManager.get_app_dir() / "styles"

    @staticmethod
    def get_data_dir() -> Path:
        """
        Obtiene el directorio de datos del usuario.

        Returns:
            Path al directorio de datos
        """
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", "."))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path.home() / ".local" / "share"

        data_dir = base / "ComparadorOzono"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    @staticmethod
    def get_log_dir() -> Path:
        """
        Obtiene el directorio de logs.

        Returns:
            Path al directorio de logs
        """
        log_dir = ResourceManager.get_data_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    @staticmethod
    def get_output_dir(base_path: Optional[Path] = None) -> Path:
        """
        Obtiene el directorio de salida para los resultados.

        Args:
            base_path: Ruta base opcional (por defecto, directorio de datos)

        Returns:
            Path al directorio de salida
        """
        if base_path is None:
            base_path = ResourceManager.get_data_dir()

        output_dir = Path(base_path) / "out_plots"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    @staticmethod
    def get_asset(filename: str) -> Path:
        """
        Obtiene la ruta completa de un asset.

        Args:
            filename: Nombre del archivo de asset

        Returns:
            Path al archivo de asset
        """
        return ResourceManager.get_assets_dir() / filename

    @staticmethod
    def get_style(filename: str) -> Path:
        """
        Obtiene la ruta completa de un archivo de estilo.

        Args:
            filename: Nombre del archivo de estilo

        Returns:
            Path al archivo de estilo
        """
        return ResourceManager.get_styles_dir() / filename

    @staticmethod
    def get_logo() -> Path:
        """
        Obtiene la ruta del logo de la universidad.

        Returns:
            Path al archivo del logo
        """
        return ResourceManager.get_asset("logo_universidad.png")

    @staticmethod
    def get_icon() -> Path:
        """
        Obtiene la ruta del ícono de la aplicación.

        Returns:
            Path al archivo del ícono
        """
        return ResourceManager.get_asset("icon.png")

    @staticmethod
    def ensure_directories() -> None:
        """Asegura que todos los directorios necesarios existan."""
        dirs = [
            ResourceManager.get_data_dir(),
            ResourceManager.get_log_dir(),
            ResourceManager.get_assets_dir(),
            ResourceManager.get_styles_dir(),
        ]

        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def file_exists(filepath: Path) -> bool:
        """
        Verifica si un archivo existe.

        Args:
            filepath: Ruta del archivo a verificar

        Returns:
            True si el archivo existe, False en caso contrario
        """
        return Path(filepath).exists() and Path(filepath).is_file()

    @staticmethod
    def read_text_file(filepath: Path, encoding: str = "utf-8") -> Optional[str]:
        """
        Lee un archivo de texto de forma segura.

        Args:
            filepath: Ruta del archivo a leer
            encoding: Codificación del archivo

        Returns:
            Contenido del archivo o None si hay error
        """
        try:
            with open(filepath, "r", encoding=encoding) as f:
                return f.read()
        except Exception as e:
            print(f"Error leyendo archivo {filepath}: {e}")
            return None
