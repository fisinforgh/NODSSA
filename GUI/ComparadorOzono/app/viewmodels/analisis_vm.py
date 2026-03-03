"""
ViewModel para el análisis de datos de ozono.
Maneja la lógica de presentación siguiendo el patrón MVVM.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from PySide6.QtCore import QObject, Signal

from ..core.diagnosticos import DiagnosticosEstadisticos, ResultadosDiagnosticos
from ..core.recursos import ResourceManager


class AnalisisViewModel(QObject):
    """ViewModel que gestiona la lógica del análisis de ozono."""
    
    # Señales
    archivo_cargado = Signal(str, str)  # tipo ('real'/'predicho'), ruta
    analisis_iniciado = Signal()
    analisis_completado = Signal(dict)  # resultados
    progreso_actualizado = Signal(int, str)  # porcentaje, mensaje
    error_ocurrido = Signal(str)  # mensaje de error
    
    def __init__(self):
        """Inicializa el ViewModel."""
        super().__init__()
        self._archivo_real: Optional[str] = None
        self._archivo_predicho: Optional[str] = None
        self._diagnosticos = DiagnosticosEstadisticos()
        self._ultimo_resultado: Optional[ResultadosDiagnosticos] = None
        
        logging.info("ViewModel de análisis inicializado")
    
    @property
    def archivo_real(self) -> Optional[str]:
        """Obtiene la ruta del archivo de datos reales."""
        return self._archivo_real
    
    @property
    def archivo_predicho(self) -> Optional[str]:
        """Obtiene la ruta del archivo de datos predichos."""
        return self._archivo_predicho
    
    def cargar_archivo_real(self, ruta: str) -> bool:
        """
        Carga el archivo de datos reales.
        
        Args:
            ruta: Ruta del archivo CSV
            
        Returns:
            True si se cargó correctamente
            
        Raises:
            ValueError: Si el archivo no existe o no es válido
        """
        ruta_path = Path(ruta)
        
        if not ruta_path.exists():
            raise ValueError(f"El archivo no existe: {ruta}")
        
        if not ruta_path.suffix.lower() == '.csv':
            raise ValueError("El archivo debe ser formato CSV")
        
        self._archivo_real = str(ruta_path)
        self.archivo_cargado.emit("real", str(ruta_path))
        
        logging.info(f"Archivo real cargado: {ruta_path.name}")
        return True
    
    def cargar_archivo_predicho(self, ruta: str) -> bool:
        """
        Carga el archivo de datos predichos.
        
        Args:
            ruta: Ruta del archivo CSV
            
        Returns:
            True si se cargó correctamente
            
        Raises:
            ValueError: Si el archivo no existe o no es válido
        """
        ruta_path = Path(ruta)
        
        if not ruta_path.exists():
            raise ValueError(f"El archivo no existe: {ruta}")
        
        if not ruta_path.suffix.lower() == '.csv':
            raise ValueError("El archivo debe ser formato CSV")
        
        self._archivo_predicho = str(ruta_path)
        self.archivo_cargado.emit("predicho", str(ruta_path))
        
        logging.info(f"Archivo predicho cargado: {ruta_path.name}")
        return True
    
    def archivos_listos(self) -> bool:
        """
        Verifica si ambos archivos están cargados.
        
        Returns:
            True si ambos archivos están cargados
        """
        return self._archivo_real is not None and self._archivo_predicho is not None
    
    def ejecutar_analisis(self) -> Dict[str, Any]:
        """
        Ejecuta el análisis de diagnóstico completo.
        
        Returns:
            Diccionario con los resultados del análisis
            
        Raises:
            ValueError: Si faltan archivos o hay error en el análisis
        """
        if not self.archivos_listos():
            raise ValueError("Deben cargarse ambos archivos antes de ejecutar el análisis")
        
        try:
            self.analisis_iniciado.emit()
            logging.info("Iniciando análisis de diagnóstico")
            
            # Determinar directorio de salida (junto al archivo predicho)
            directorio_salida = Path(self._archivo_predicho).parent / "out_plots"
            
            # Ejecutar diagnóstico completo
            resultado = self._diagnosticos.ejecutar_diagnostico_completo(
                self._archivo_real,
                self._archivo_predicho,
                directorio_salida
            )
            
            self._ultimo_resultado = resultado

            # === NUEVO (no rompe lógica): extraer figuras si existen ===
            figuras = {}
            if hasattr(resultado, "figuras") and isinstance(resultado.figuras, dict):
                figuras = resultado.figuras
            elif hasattr(self._diagnosticos, "figuras") and isinstance(self._diagnosticos.figuras, dict):
                # fallback si el objeto de diagnósticos guarda allí las figuras
                figuras = self._diagnosticos.figuras

            # Preparar diccionario de resultados para la UI
            resultados_dict = {
                "pruebas": resultado.pruebas,
                "total_exitosas": resultado.total_exitosas,
                "porcentaje_exitosas": resultado.porcentaje_exitosas,
                "conclusion": resultado.conclusion,
                "rutas_graficos": resultado.rutas_graficos,
                "figuras": figuras,  # <-- agregado
            }
            
            self.analisis_completado.emit(resultados_dict)
            logging.info(f"Análisis completado: {resultado.total_exitosas}/{len(resultado.pruebas)} pruebas exitosas")
            
            return resultados_dict
            
        except Exception as e:
            mensaje_error = f"Error durante el análisis: {str(e)}"
            logging.error(mensaje_error, exc_info=True)
            self.error_ocurrido.emit(mensaje_error)
            raise

    
    def exportar_resultados(self, ruta_archivo: str) -> bool:
        """
        Exporta los resultados del último análisis a un archivo.
        
        Args:
            ruta_archivo: Ruta donde guardar el archivo
            
        Returns:
            True si se exportó correctamente
            
        Raises:
            ValueError: Si no hay resultados para exportar
        """
        if self._ultimo_resultado is None:
            raise ValueError("No hay resultados para exportar. Ejecute el análisis primero.")
        
        try:
            ruta = Path(ruta_archivo)
            
            # Preparar contenido
            lineas = []
            lineas.append("=" * 80)
            lineas.append("RESULTADOS DEL ANÁLISIS DE DIAGNÓSTICO")
            lineas.append("=" * 80)
            lineas.append("")
            
            # Información de archivos
            lineas.append("ARCHIVOS ANALIZADOS:")
            lineas.append(f"  Datos reales: {Path(self._archivo_real).name}")
            lineas.append(f"  Datos predichos: {Path(self._archivo_predicho).name}")
            lineas.append("")
            
            # Tabla de resultados
            lineas.append("PRUEBAS ESTADÍSTICAS:")
            lineas.append("-" * 80)
            lineas.append(f"{'Prueba':<25} {'Estadístico':>15} {'GL/Lag':>10} {'p-valor':>15} {'Estado':>10}")
            lineas.append("-" * 80)
            
            for prueba in self._ultimo_resultado.pruebas:
                # Formatear valores
                if prueba.estadistico is not None and not np.isnan(prueba.estadistico):
                    est_str = f"{prueba.estadistico:>15.6g}"
                else:
                    est_str = f"{'---':>15}"
                
                if prueba.grados_libertad is not None:
                    gl_str = f"{int(prueba.grados_libertad):>10}"
                else:
                    gl_str = f"{'---':>10}"
                
                if prueba.p_valor is not None and not np.isnan(prueba.p_valor):
                    p_str = f"{prueba.p_valor:>15.6g}"
                else:
                    p_str = f"{'---':>15}"
                
                estado_str = "OK" if prueba.es_exitoso else "FALLÓ"
                
                lineas.append(f"{prueba.nombre:<25} {est_str} {gl_str} {p_str} {estado_str:>10}")
            
            lineas.append("-" * 80)
            lineas.append("")
            
            # Resumen
            lineas.append("RESUMEN:")
            lineas.append(f"  Total de pruebas: {len(self._ultimo_resultado.pruebas)}")
            lineas.append(f"  Pruebas exitosas: {self._ultimo_resultado.total_exitosas}")
            lineas.append(f"  Porcentaje de éxito: {self._ultimo_resultado.porcentaje_exitosas:.1f}%")
            lineas.append("")
            
            # Conclusión
            lineas.append("CONCLUSIÓN:")
            for linea in self._ultimo_resultado.conclusion.split('\n'):
                lineas.append(f"  {linea}")
            lineas.append("")
            
            # Gráficos generados
            lineas.append("GRÁFICOS GENERADOS:")
            for nombre, ruta_grafico in self._ultimo_resultado.rutas_graficos.items():
                lineas.append(f"  - {nombre}: {ruta_grafico}")
            lineas.append("")
            
            lineas.append("=" * 80)
            lineas.append(f"Análisis generado por Comparador de Ozono v2.0.0")
            lineas.append(f"Universidad Nacional de Colombia")
            lineas.append("=" * 80)
            
            # Escribir archivo
            if ruta.suffix.lower() == '.csv':
                # Exportar como CSV
                self._exportar_csv(ruta)
            else:
                # Exportar como texto
                with open(ruta, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lineas))
            
            logging.info(f"Resultados exportados a: {ruta}")
            return True
            
        except Exception as e:
            mensaje_error = f"Error al exportar resultados: {str(e)}"
            logging.error(mensaje_error)
            raise
    
    def _exportar_csv(self, ruta: Path) -> None:
        """
        Exporta los resultados en formato CSV.
        
        Args:
            ruta: Ruta del archivo CSV
        """
        import csv
        
        with open(ruta, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Encabezado
            writer.writerow(['Prueba', 'Estadístico', 'Grados_Libertad', 'P_Valor', 'Estado'])
            
            # Datos
            for prueba in self._ultimo_resultado.pruebas:
                writer.writerow([
                    prueba.nombre,
                    prueba.estadistico if prueba.estadistico is not None else '',
                    int(prueba.grados_libertad) if prueba.grados_libertad is not None else '',
                    prueba.p_valor if prueba.p_valor is not None else '',
                    'OK' if prueba.es_exitoso else 'FALLÓ'
                ])
            
            # Resumen
            writer.writerow([])
            writer.writerow(['RESUMEN'])
            writer.writerow(['Total pruebas', len(self._ultimo_resultado.pruebas)])
            writer.writerow(['Pruebas exitosas', self._ultimo_resultado.total_exitosas])
            writer.writerow(['Porcentaje éxito', f"{self._ultimo_resultado.porcentaje_exitosas:.1f}%"])
    
    def limpiar_datos(self) -> None:
        """Limpia los datos cargados y resultados."""
        self._archivo_real = None
        self._archivo_predicho = None
        self._ultimo_resultado = None
        self._diagnosticos = DiagnosticosEstadisticos()
        
        logging.info("Datos y resultados limpiados")
    
    def obtener_estadisticas_basicas(self) -> Optional[Dict[str, float]]:
        """
        Obtiene estadísticas básicas de los residuales.
        
        Returns:
            Diccionario con estadísticas o None si no hay datos
        """
        if self._diagnosticos.residuales is None:
            return None
        
        residuales = self._diagnosticos.residuales
        mask = np.isfinite(residuales)
        residuales_clean = residuales[mask]
        
        if len(residuales_clean) == 0:
            return None
        
        return {
            "media": float(np.mean(residuales_clean)),
            "mediana": float(np.median(residuales_clean)),
            "desviacion_estandar": float(np.std(residuales_clean, ddof=1)),
            "minimo": float(np.min(residuales_clean)),
            "maximo": float(np.max(residuales_clean)),
            "q1": float(np.percentile(residuales_clean, 25)),
            "q3": float(np.percentile(residuales_clean, 75)),
            "n_observaciones": len(residuales_clean)
        }


# Importar numpy para los cálculos
import numpy as np
