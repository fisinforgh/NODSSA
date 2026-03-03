"""
Tests para el ViewModel de análisis.
"""

import pytest
import tempfile
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtCore import QObject
from app.viewmodels.analisis_vm import AnalisisViewModel


class TestAnalisisViewModel:
    """Tests para el ViewModel de análisis."""
    
    @pytest.fixture
    def view_model(self):
        """Fixture que crea una instancia del ViewModel."""
        return AnalisisViewModel()
    
    @pytest.fixture
    def archivos_prueba(self):
        """Fixture que crea archivos CSV de prueba."""
        # Crear datos de prueba
        np.random.seed(42)
        n = 100
        fechas = pd.date_range('2024-01-01', periods=n, freq='D')
        ozono_real = 50 + np.random.normal(0, 5, n)
        ozono_pred = 48 + np.random.normal(0, 4, n)
        
        # Crear archivos temporales
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f_real:
            pd.DataFrame({
                'Date': fechas,
                'Ozone': ozono_real
            }).to_csv(f_real, index=False)
            path_real = f_real.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f_pred:
            pd.DataFrame({
                'Date': fechas,
                'Ozone': ozono_pred
            }).to_csv(f_pred, index=False)
            path_pred = f_pred.name
        
        yield path_real, path_pred
        
        # Limpiar
        Path(path_real).unlink(missing_ok=True)
        Path(path_pred).unlink(missing_ok=True)
    
    def test_inicializacion(self, view_model):
        """Test de inicialización correcta del ViewModel."""
        assert view_model.archivo_real is None
        assert view_model.archivo_predicho is None
        assert view_model._ultimo_resultado is None
    
    def test_cargar_archivo_real_valido(self, view_model, archivos_prueba):
        """Test de carga exitosa de archivo real."""
        path_real, _ = archivos_prueba
        
        # Conectar señal para verificar emisión
        signal_spy = Mock()
        view_model.archivo_cargado.connect(signal_spy)
        
        resultado = view_model.cargar_archivo_real(path_real)
        
        assert resultado is True
        assert view_model.archivo_real == path_real
        signal_spy.assert_called_once_with("real", path_real)
    
    def test_cargar_archivo_real_no_existe(self, view_model):
        """Test de manejo de archivo inexistente."""
        with pytest.raises(ValueError, match="El archivo no existe"):
            view_model.cargar_archivo_real("no_existe.csv")
    
    def test_cargar_archivo_real_formato_invalido(self, view_model):
        """Test de rechazo de formato no CSV."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            path = f.name
        
        try:
            with pytest.raises(ValueError, match="formato CSV"):
                view_model.cargar_archivo_real(path)
        finally:
            Path(path).unlink(missing_ok=True)
    
    def test_cargar_archivo_predicho_valido(self, view_model, archivos_prueba):
        """Test de carga exitosa de archivo predicho."""
        _, path_pred = archivos_prueba
        
        signal_spy = Mock()
        view_model.archivo_cargado.connect(signal_spy)
        
        resultado = view_model.cargar_archivo_predicho(path_pred)
        
        assert resultado is True
        assert view_model.archivo_predicho == path_pred
        signal_spy.assert_called_once_with("predicho", path_pred)
    
    def test_archivos_listos(self, view_model, archivos_prueba):
        """Test de verificación de archivos listos."""
        path_real, path_pred = archivos_prueba
        
        # Inicialmente no hay archivos
        assert view_model.archivos_listos() is False
        
        # Cargar solo archivo real
        view_model.cargar_archivo_real(path_real)
        assert view_model.archivos_listos() is False
        
        # Cargar archivo predicho también
        view_model.cargar_archivo_predicho(path_pred)
        assert view_model.archivos_listos() is True
    
    def test_ejecutar_analisis_sin_archivos(self, view_model):
        """Test de intento de análisis sin archivos cargados."""
        with pytest.raises(ValueError, match="Deben cargarse ambos archivos"):
            view_model.ejecutar_analisis()
    
    def test_ejecutar_analisis_exitoso(self, view_model, archivos_prueba):
        """Test de ejecución exitosa del análisis."""
        path_real, path_pred = archivos_prueba
        
        # Cargar archivos
        view_model.cargar_archivo_real(path_real)
        view_model.cargar_archivo_predicho(path_pred)
        
        # Conectar señales
        signal_iniciado = Mock()
        signal_completado = Mock()
        view_model.analisis_iniciado.connect(signal_iniciado)
        view_model.analisis_completado.connect(signal_completado)
        
        # Ejecutar análisis
        resultado = view_model.ejecutar_analisis()
        
        # Verificaciones
        assert isinstance(resultado, dict)
        assert 'pruebas' in resultado
        assert 'total_exitosas' in resultado
        assert 'porcentaje_exitosas' in resultado
        assert 'conclusion' in resultado
        assert 'rutas_graficos' in resultado
        
        signal_iniciado.assert_called_once()
        signal_completado.assert_called_once()
        
        # Verificar que se guardó el resultado
        assert view_model._ultimo_resultado is not None
    
    def test_exportar_resultados_sin_analisis(self, view_model):
        """Test de intento de exportar sin haber ejecutado análisis."""
        with pytest.raises(ValueError, match="No hay resultados para exportar"):
            view_model.exportar_resultados("resultados.txt")
    
    def test_exportar_resultados_txt(self, view_model, archivos_prueba):
        """Test de exportación de resultados a archivo TXT."""
        path_real, path_pred = archivos_prueba
        
        # Ejecutar análisis primero
        view_model.cargar_archivo_real(path_real)
        view_model.cargar_archivo_predicho(path_pred)
        view_model.ejecutar_analisis()
        
        # Exportar resultados
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            path_export = f.name
        
        try:
            resultado = view_model.exportar_resultados(path_export)
            
            assert resultado is True
            assert Path(path_export).exists()
            
            # Verificar contenido
            with open(path_export, 'r', encoding='utf-8') as f:
                contenido = f.read()
                assert "RESULTADOS DEL ANÁLISIS" in contenido
                assert "PRUEBAS ESTADÍSTICAS" in contenido
                assert "CONCLUSIÓN" in contenido
        
        finally:
            Path(path_export).unlink(missing_ok=True)
    
    def test_exportar_resultados_csv(self, view_model, archivos_prueba):
        """Test de exportación de resultados a archivo CSV."""
        path_real, path_pred = archivos_prueba
        
        # Ejecutar análisis primero
        view_model.cargar_archivo_real(path_real)
        view_model.cargar_archivo_predicho(path_pred)
        view_model.ejecutar_analisis()
        
        # Exportar resultados
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            path_export = f.name
        
        try:
            resultado = view_model.exportar_resultados(path_export)
            
            assert resultado is True
            assert Path(path_export).exists()
            
            # Verificar contenido CSV
            df = pd.read_csv(path_export, nrows=6)
            assert 'Prueba' in df.columns
            assert 'Estadístico' in df.columns
            assert 'P_Valor' in df.columns
            assert 'Estado' in df.columns
        
        finally:
            Path(path_export).unlink(missing_ok=True)
    
    def test_limpiar_datos(self, view_model, archivos_prueba):
        """Test de limpieza de datos."""
        path_real, path_pred = archivos_prueba
        
        # Cargar archivos y ejecutar análisis
        view_model.cargar_archivo_real(path_real)
        view_model.cargar_archivo_predicho(path_pred)
        view_model.ejecutar_analisis()
        
        # Verificar que hay datos
        assert view_model.archivo_real is not None
        assert view_model.archivo_predicho is not None
        assert view_model._ultimo_resultado is not None
        
        # Limpiar
        view_model.limpiar_datos()
        
        # Verificar limpieza
        assert view_model.archivo_real is None
        assert view_model.archivo_predicho is None
        assert view_model._ultimo_resultado is None
    
    def test_obtener_estadisticas_basicas(self, view_model, archivos_prueba):
        """Test de obtención de estadísticas básicas."""
        path_real, path_pred = archivos_prueba
        
        # Sin datos cargados
        assert view_model.obtener_estadisticas_basicas() is None
        
        # Cargar y ejecutar análisis
        view_model.cargar_archivo_real(path_real)
        view_model.cargar_archivo_predicho(path_pred)
        view_model.ejecutar_analisis()
        
        # Obtener estadísticas
        stats = view_model.obtener_estadisticas_basicas()
        
        assert stats is not None
        assert 'media' in stats
        assert 'mediana' in stats
        assert 'desviacion_estandar' in stats
        assert 'minimo' in stats
        assert 'maximo' in stats
        assert 'q1' in stats
        assert 'q3' in stats
        assert 'n_observaciones' in stats
        
        # Verificar tipos
        for key, value in stats.items():
            if key == 'n_observaciones':
                assert isinstance(value, int)
            else:
                assert isinstance(value, float)


class TestSignals:
    """Tests para verificar el correcto funcionamiento de las señales."""
    
    def test_emision_senales_flujo_completo(self):
        """Test de emisión correcta de señales en el flujo completo."""
        view_model = AnalisisViewModel()
        
        # Crear archivos de prueba
        np.random.seed(42)
        fechas = pd.date_range('2024-01-01', periods=50, freq='D')
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Crear archivos CSV
            path_real = Path(tmpdir) / "real.csv"
            path_pred = Path(tmpdir) / "pred.csv"
            
            pd.DataFrame({
                'Date': fechas,
                'Ozone': np.random.normal(50, 5, 50)
            }).to_csv(path_real, index=False)
            
            pd.DataFrame({
                'Date': fechas,
                'Ozone': np.random.normal(48, 4, 50)
            }).to_csv(path_pred, index=False)
            
            # Conectar espías a todas las señales
            spy_archivo = Mock()
            spy_iniciado = Mock()
            spy_completado = Mock()
            spy_error = Mock()
            
            view_model.archivo_cargado.connect(spy_archivo)
            view_model.analisis_iniciado.connect(spy_iniciado)
            view_model.analisis_completado.connect(spy_completado)
            view_model.error_ocurrido.connect(spy_error)
            
            # Ejecutar flujo completo
            view_model.cargar_archivo_real(str(path_real))
            view_model.cargar_archivo_predicho(str(path_pred))
            view_model.ejecutar_analisis()
            
            # Verificar emisiones
            assert spy_archivo.call_count == 2  # Una por cada archivo
            spy_iniciado.assert_called_once()
            spy_completado.assert_called_once()
            spy_error.assert_not_called()  # No debe haber errores
