"""
ViewModel para conectar la GUI de Comparador de Ozono con los resultados
preprocesados de ozono vs manchas solares (modo diario / mensual).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ModeloChi2Resumen:
    """
    Resumen compacto del mejor modelo encontrado en chi2_diagnostics_*.

    Esta estructura se usa únicamente para mostrar un resumen legible
    en la GUI, no para volver a calcular estadísticos.
    """

    modo: str

    # Estadísticos básicos
    n_obs: Optional[int] = None
    nu: Optional[int] = None  # grados de libertad
    chi2: Optional[float] = None
    chi2_red: Optional[float] = None
    p_value: Optional[float] = None
    p_cdf: Optional[float] = None
    chi2_lo: Optional[float] = None
    chi2_hi: Optional[float] = None

    # Coeficientes del modelo lineal O3 ≈ a0 + a1 * Sn
    a0: Optional[float] = None
    a1: Optional[float] = None
    sigma_a0: Optional[float] = None
    sigma_a1: Optional[float] = None

    # Parámetros de reducción de datos
    min_occ: Optional[int] = None
    n_bins: Optional[int] = None
    pct_reduction: Optional[float] = None

    # Información geográfica (si está disponible)
    lat: Optional[float] = None
    lon: Optional[float] = None

    # Veredictos
    veredict_chi: str = ""
    veredict_tutor: str = ""
    mensaje_corto: str = ""
    es_aceptable: bool = False


class OzonoSnViewModel:
    """
    ViewModel para el análisis ozono–manchas solares en la GUI.

    Responsabilidades principales:
      - Resolver rutas a los directorios de resultados (gui_mensual / gui_diario)
      - Cargar los CSV agregados por los scripts de preprocesamiento:
          * bogota_binned_gui.csv
          * bogota_binned_minoccXX.csv
          * chi2_sweep.csv
          * chi2_diagnostics_basic.csv
          * chi2_diagnostics_aug.csv
      - Construir un resumen del mejor modelo para la vista textual.
    """

    # Rango "razonable" de chi2_red para considerar un buen ajuste
    chi2_red_min_aceptable: float = 0.5
    chi2_red_max_aceptable: float = 2.0

    def __init__(self, modo: str = "mensual", base_dir: Optional[str] = None) -> None:
        """
        Parameters
        ----------
        modo : {"mensual", "diario"}
            Modo de análisis inicial. "mensual" suele tener un modelo
            candidato aceptable; "diario" se usa sólo para diagnóstico.
        base_dir : str, optional
            Directorio base donde viven los subdirectorios:
                base_dir/gui_mensual
                base_dir/gui_diario
            Si no se proporciona, se intenta inferir a partir de la
            estructura del proyecto ('ozono-tesis/data/processed').
        """
        self.modo = "mensual"  # valor por defecto
        self.base_dir = self._resolver_base_dir(base_dir)
        self.gui_dir: str = ""  # se inicializa en set_modo

        logger.info(
            "OzonoSnViewModel inicializado en modo %s (BASE_DIR=%s)",
            modo,
            self.base_dir,
        )

        self.set_modo(modo)

    # ------------------------------------------------------------------
    # Resolución de rutas
    # ------------------------------------------------------------------
    def _resolver_base_dir(self, base_dir: Optional[str]) -> str:
        """Intenta resolver el directorio base donde están gui_mensual/gui_diario."""
        if base_dir:
            return os.path.abspath(base_dir)

        # 1) Variable de entorno, si existe
        env = os.getenv("OZONO_DATA_BASEDIR")
        if env:
            return os.path.abspath(env)

        # 2) Inferir a partir de la estructura típica del proyecto:
        #    .../ozono-tesis/python/GUI/ComparadorOzono/app/viewmodels/ozono_sn_viewmodel.py
        #    Queremos llegar a .../ozono-tesis/data/processed
        here = Path(__file__).resolve()
        parents = list(here.parents)
        root_project = None
        for p in parents:
            if p.name == "ozono-tesis":
                root_project = p
                break

        if root_project is None and len(parents) >= 5:
            # Fallback genérico: subir ~5 niveles
            root_project = parents[4]

        candidate = root_project / "data" / "processed"
        return str(candidate)

    def set_modo(self, modo: str) -> None:
        """Cambia entre modo 'mensual' y 'diario' y actualiza self.gui_dir."""
        modo = modo.lower()
        if modo not in ("mensual", "diario"):
            logger.warning("Modo desconocido '%s', usando 'mensual' por defecto", modo)
            modo = "mensual"

        self.modo = modo
        self.gui_dir = os.path.join(self.base_dir, f"gui_{self.modo}")

        logger.info("Modo cambiado a %s (GUI_DIR=%s)", self.modo, self.gui_dir)

    # ------------------------------------------------------------------
    # Carga de BINS locales
    # ------------------------------------------------------------------
    def _ruta_binned_sin_corte(self) -> str:
        return os.path.join(self.gui_dir, "bogota_binned_gui.csv")

    def _ruta_binned_con_corte(self) -> Optional[str]:
        """
        Devuelve la ruta al archivo bogota_binned_minoccXX.csv más adecuado.

        Estrategia:
          1) Si en chi2_diagnostics_basic.csv hay una fila marcada como
             'es_aceptable', usamos su min_occ asociado (si hay archivo).
          2) Si no, buscamos todos los archivos bogota_binned_minocc*.csv
             y escogemos el que tenga min_occ más cercano a un valor
             preferido (20 mensual, 30 diario).
        """
        # Intentar usar el min_occ del mejor modelo, si existe
        diag = self._cargar_diag_basic_sin_cache()
        preferido = 20 if self.modo == "mensual" else 30

        min_occ_diag: Optional[int] = None
        if diag is not None:
            if "es_aceptable" in diag.columns and "min_occ" in diag.columns:
                aceptables = diag[diag["es_aceptable"] == True]  # noqa: E712
                if not aceptables.empty:
                    min_occ_diag = int(aceptables.iloc[0]["min_occ"])
            if min_occ_diag is None and "min_occ_mejor" in diag.columns:
                try:
                    min_occ_diag = int(diag["min_occ_mejor"].iloc[0])
                except Exception:
                    min_occ_diag = None

        # Buscar archivos disponibles
        if not os.path.isdir(self.gui_dir):
            return None

        candidatos = []
        for fname in os.listdir(self.gui_dir):
            if not fname.startswith("bogota_binned_minocc") or not fname.endswith(".csv"):
                continue
            # Extraer número después de 'minocc'
            try:
                parte = fname.split("minocc", 1)[1]
                num_str = "".join(ch for ch in parte if ch.isdigit())
                if num_str:
                    candidatos.append((int(num_str), fname))
            except Exception:
                continue

        if not candidatos:
            return None

        # Elegir el mejor candidato
        if min_occ_diag is not None:
            target = min_occ_diag
        else:
            target = preferido

        candidatos.sort(key=lambda t: abs(t[0] - target))
        mejor_min_occ, mejor_fname = candidatos[0]
        ruta = os.path.join(self.gui_dir, mejor_fname)
        logger.info(
            "Usando archivo de bins con corte '%s' (min_occ≈%s) para modo %s",
            mejor_fname,
            mejor_min_occ,
            self.modo,
        )
        return ruta

    def cargar_binned_sin_corte(self) -> Optional[pd.DataFrame]:
        """Carga bogota_binned_gui.csv del modo actual."""
        path = self._ruta_binned_sin_corte()
        if not os.path.isfile(path):
            logger.warning("No se encontró archivo de bins sin corte: %s", path)
            return None
        try:
            df = pd.read_csv(path)
            return df
        except Exception as exc:
            logger.exception("Error leyendo %s: %s", path, exc)
            return None

    def cargar_binned_con_corte(self) -> Optional[pd.DataFrame]:
        """Carga el bogota_binned_minoccXX.csv más adecuado para el modo actual."""
        path = self._ruta_binned_con_corte()
        if path is None:
            logger.warning(
                "No se encontró ningún archivo bogota_binned_minocc*.csv en %s",
                self.gui_dir,
            )
            return None

        if not os.path.isfile(path):
            logger.warning("Ruta de bins con corte inexistente: %s", path)
            return None

        try:
            df = pd.read_csv(path)
            return df
        except Exception as exc:
            logger.exception("Error leyendo %s: %s", path, exc)
            return None

    # ------------------------------------------------------------------
    # Carga de sweep y diagnósticos
    # ------------------------------------------------------------------
    def cargar_sweep(self) -> pd.DataFrame:
        """
        Carga chi2_sweep.csv del modo actual.

        Levanta excepción si no existe; se maneja en la capa de GUI.
        """
        path = os.path.join(self.gui_dir, "chi2_sweep.csv")
        logger.info("Cargando sweep desde: %s", path)
        df = pd.read_csv(path)
        return df

    def _cargar_diag_basic_sin_cache(self) -> Optional[pd.DataFrame]:
        """
        Carga chi2_diagnostics_basic.csv del modo actual sin caching.

        Uso interno para ayudar a seleccionar min_occ y construir resúmenes.
        """
        path = os.path.join(self.gui_dir, "chi2_diagnostics_basic.csv")
        if not os.path.isfile(path):
            logger.warning("No se encontró chi2_diagnostics_basic.csv en %s", path)
            return None
        try:
            df = pd.read_csv(path)
            return df
        except Exception as exc:
            logger.exception("Error leyendo %s: %s", path, exc)
            return None

    def cargar_diag_aug(self) -> Optional[pd.DataFrame]:
        """Carga chi2_diagnostics_aug.csv si existe."""
        path = os.path.join(self.gui_dir, "chi2_diagnostics_aug.csv")
        if not os.path.isfile(path):
            logger.info("No se encontró chi2_diagnostics_aug.csv en %s", path)
            return None
        try:
            df = pd.read_csv(path)
            return df
        except Exception as exc:
            logger.exception("Error leyendo %s: %s", path, exc)
            return None

    # ------------------------------------------------------------------
    # Construcción del resumen del mejor modelo
    # ------------------------------------------------------------------
    def construir_resumen(self) -> Optional[ModeloChi2Resumen]:
        """
        Construye un ModeloChi2Resumen a partir de chi2_diagnostics_basic/aug.

        Regla:
          - Si hay filas con 'es_aceptable'==True, tomamos la primera.
          - Si no, tomamos la fila con chi2_red mínimo como "mejor aproximación".
        """
        df_basic = self._cargar_diag_basic_sin_cache()
        if df_basic is None or df_basic.empty:
            return None

        fila = None

        # 1) Buscar modelos explícitamente aceptables
        if "es_aceptable" in df_basic.columns:
            aceptables = df_basic[df_basic["es_aceptable"] == True]  # noqa: E712
            if not aceptables.empty:
                fila = aceptables.iloc[0]

        # 2) Si no hay aceptables, usar el chi2_red mínimo
        if fila is None:
            if "chi2_red" in df_basic.columns:
                idx = df_basic["chi2_red"].idxmin()
                fila = df_basic.loc[idx]
            else:
                # Último recurso: primera fila
                fila = df_basic.iloc[0]

        # Cargar diag_aug para completar info si existe
        df_aug = self.cargar_diag_aug()
        fila_aug: Optional[pd.Series] = None
        if df_aug is not None and not df_aug.empty:
            # Suponemos que se refiere al mismo mejor modelo; tomamos la primera fila
            fila_aug = df_aug.iloc[0]

        resumen = ModeloChi2Resumen(modo=self.modo)

        def _get(s: pd.Series, key: str) -> Optional[Any]:
            return s.get(key) if key in s.index else None

        # Copiar campos básicos
        for key in (
            "n_obs",
            "nu",
            "chi2",
            "chi2_red",
            "p_value",
            "p_cdf",
            "chi2_lo",
            "chi2_hi",
            "min_occ",
            "n_bins",
            "pct_reduction_obs",
            "lat_ciudad",
            "lon_ciudad",
            "veredict_chi",
            "veredict_tutor",
            "mensaje_corto",
            "es_aceptable",
        ):
            val = _get(fila, key) if fila is not None else None
            if key == "pct_reduction_obs":
                resumen.pct_reduction = float(val) if val is not None else None
            elif key == "lat_ciudad":
                resumen.lat = float(val) if val is not None else None
            elif key == "lon_ciudad":
                resumen.lon = float(val) if val is not None else None
            elif key == "es_aceptable":
                resumen.es_aceptable = bool(val) if val is not None else False
            elif hasattr(resumen, key):
                setattr(resumen, key, val)

        # Coeficientes (preferimos de aug, si están)
        fuente_coef = fila_aug if fila_aug is not None else fila
        if fuente_coef is not None:
            for key in ("a0", "a1", "sigma_a0", "sigma_a1"):
                val = _get(fuente_coef, key)
                if hasattr(resumen, key):
                    setattr(resumen, key, val)

        # Mensaje corto por defecto si está vacío
        if not resumen.mensaje_corto:
            if resumen.es_aceptable:
                resumen.mensaje_corto = (
                    "El modelo cumple los criterios de χ²_red y p definidos "
                    "para considerar aceptable la relación lineal O₃–Sₙ."
                )
            else:
                resumen.mensaje_corto = (
                    "⚠️ El modelo NO cumple los criterios de χ²_red/p. "
                    "En modo mensual esto implica cautela; en modo diario implica "
                    "rechazo del modelo lineal O₃–Sₙ."
                )

        return resumen

