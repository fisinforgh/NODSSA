"""
Tests para el módulo de diagnósticos estadísticos.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import tempfile

from app.core.diagnosticos import (
    DiagnosticosEstadisticos, 
    ResultadoPrueba, 
    ResultadosDiagnosticos
)


class TestDiagnosticosEstadisticos:
    """Tests para la clase DiagnosticosEstadisticos."""
    
    @pytest.fixture
    def diagnosticos(self):
        """Fixture que crea una instancia de DiagnosticosEstadisticos."""
        return DiagnosticosEstadisticos()
    
    @pytest.fixture
    def datos_prueba(self):
        """Fixture que genera datos de prueba sintéticos."""
        np.random.seed(42)
        n = 100
        fechas = pd.date_range('2024-01-01', periods=n, freq='D')
        
        # Datos reales (con algo de ruido)
        real = 50 + 10 * np.sin(np.linspace(0, 4*np.pi, n)) + np.random.normal(0, 3, n)
        
        # Datos predichos (similares pero con sesgo y ruido diferente)
        pred = 48 + 10 * np.sin(np.linspace(0, 4*np.pi, n)) + np.random.normal(0, 2, n)
        
        return fechas, real, pred
    
    @pytest.fixture
    def archivos_csv(self, datos_prueba):
        """Fixture que crea archivos CSV temporales con datos de prueba."""
        fechas, real, pred = datos_prueba
        
        # Crear archivos temporales
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f_real:
            df_real = pd.DataFrame({
                'Date': fechas,
                'Ozone': real
            })
            df_real.to_csv(f_real, index=False)
            path_real = f_real.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f_pred:
            df_pred = pd.DataFrame({
                'Date': fechas,
                'Ozone': pred
            })
            df_pred.to_csv(f_pred, index=False)
            path_pred = f_pred.name
        
        yield path_real, path_pred
        
        # Limpiar archivos
        Path(path_real).unlink(missing_ok=True)
        Path(path_pred).unlink(missing_ok=True)
    
    def test_inicializacion(self, diagnosticos):
        """Test de inicialización correcta."""
        assert diagnosticos.residuales is None
        assert diagnosticos.y_real is None
        assert diagnosticos.y_pred is None
    
    def test_cargar_datos_csv(self, diagnosticos, archivos_csv):
        """Test de carga de archivos CSV."""
        path_real, path_pred = archivos_csv
        
        df = diagnosticos.cargar_datos_csv(path_real, path_pred)
        
        assert not df.empty
        assert 'Date' in df.columns
        assert 'Ozone_real' in df.columns
        assert 'Ozone_pred' in df.columns
        assert diagnosticos.residuales is not None
        assert len(diagnosticos.residuales) == len(df)
    
    def test_cargar_datos_csv_archivo_invalido(self, diagnosticos):
        """Test de manejo de archivos inválidos."""
        with pytest.raises(FileNotFoundError):
            diagnosticos.cargar_datos_csv("no_existe.csv", "tampoco_existe.csv")
    
    def test_chi2_global(self, diagnosticos):
        """Test de la prueba Chi2 global."""
        # Generar residuales normales
        np.random.seed(42)
        residuales = np.random.normal(0, 1, 1000)
        
        chi2_stat, dof, p_valor = diagnosticos.chi2_global(residuales)
        
        assert chi2_stat > 0
        assert dof > 0
        assert 0 <= p_valor <= 1
    
    def test_chi2_global_datos_insuficientes(self, diagnosticos):
        """Test de Chi2 con datos insuficientes."""
        residuales = np.array([1, 2, 3])  # Muy pocos datos
        
        chi2_stat, dof, p_valor = diagnosticos.chi2_global(residuales)
        
        assert np.isnan(chi2_stat)
        assert np.isnan(p_valor)
    
    def test_ejecutar_todas_las_pruebas(self, diagnosticos, archivos_csv):
        """Test de ejecución de todas las pruebas diagnósticas."""
        path_real, path_pred = archivos_csv
        diagnosticos.cargar_datos_csv(path_real, path_pred)
        
        resultados = diagnosticos.ejecutar_todas_las_pruebas()
        
        assert len(resultados) == 6  # Debe haber 6 pruebas
        assert all(isinstance(r, ResultadoPrueba) for r in resultados)
        
        # Verificar que cada prueba tiene los campos esperados
        for resultado in resultados:
            assert resultado.nombre is not None
            assert resultado.estadistico is not None
            assert resultado.es_exitoso is not None
    
    def test_generar_graficos(self, diagnosticos, archivos_csv):
        """Test de generación de gráficos."""
        path_real, path_pred = archivos_csv
        diagnosticos.cargar_datos_csv(path_real, path_pred)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_salida = Path(tmpdir)
            rutas = diagnosticos.generar_graficos(dir_salida)
            
            # Verificar que se crearon los 4 gráficos
            assert len(rutas) == 4
            assert 'histograma' in rutas
            assert 'qq' in rutas
            assert 'acf' in rutas
            assert 'scatter' in rutas
            
            # Verificar que los archivos existen
            for nombre, ruta in rutas.items():
                assert Path(ruta).exists()
                assert Path(ruta).suffix == '.png'
    
    def test_ejecutar_diagnostico_completo(self, diagnosticos, archivos_csv):
        """Test del flujo completo de diagnóstico."""
        path_real, path_pred = archivos_csv
        
        with tempfile.TemporaryDirectory() as tmpdir:
            resultado = diagnosticos.ejecutar_diagnostico_completo(
                path_real, 
                path_pred,
                Path(tmpdir)
            )
            
            assert isinstance(resultado, ResultadosDiagnosticos)
            assert len(resultado.pruebas) == 6
            assert resultado.total_exitosas >= 0
            assert 0 <= resultado.porcentaje_exitosas <= 100
            assert resultado.conclusion is not None
            assert resultado.residuales is not None
            assert len(resultado.rutas_graficos) == 4


class TestResultadoPrueba:
    """Tests para la clase ResultadoPrueba."""
    
    def test_creacion_resultado(self):
        """Test de creación de un resultado de prueba."""
        resultado = ResultadoPrueba(
            nombre="Test",
            estadistico=1.23,
            grados_libertad=10,
            p_valor=0.05,
            es_exitoso=True,
            descripcion="Prueba de test"
        )
        
        assert resultado.nombre == "Test"
        assert resultado.estadistico == 1.23
        assert resultado.grados_libertad == 10
        assert resultado.p_valor == 0.05
        assert resultado.es_exitoso is True
        assert resultado.descripcion == "Prueba de test"


class TestIntegracion:
    """Tests de integración para verificar el flujo completo."""
    
    def test_flujo_completo_datos_normales(self):
        """Test con datos que deberían pasar la mayoría de pruebas."""
        np.random.seed(42)
        n = 500
        fechas = pd.date_range('2024-01-01', periods=n, freq='D')
        
        # Crear datos casi idénticos con residuales normales
        base = 50 + 10 * np.sin(np.linspace(0, 4*np.pi, n))
        real = base + np.random.normal(0, 1, n)
        pred = base + np.random.normal(0, 0.95, n)
        
        # Crear archivos temporales
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f_real:
            pd.DataFrame({'Date': fechas, 'Ozone': real}).to_csv(f_real, index=False)
            path_real = f_real.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f_pred:
            pd.DataFrame({'Date': fechas, 'Ozone': pred}).to_csv(f_pred, index=False)
            path_pred = f_pred.name
        
        try:
            diagnosticos = DiagnosticosEstadisticos()
            
            with tempfile.TemporaryDirectory() as tmpdir:
                resultado = diagnosticos.ejecutar_diagnostico_completo(
                    path_real,
                    path_pred,
                    Path(tmpdir)
                )
                
                # Con datos casi normales, esperamos que pase al menos algunas pruebas
                assert resultado.total_exitosas > 0
                assert resultado.porcentaje_exitosas > 0
                
                # Verificar que los gráficos se generaron
                for ruta in resultado.rutas_graficos.values():
                    assert Path(ruta).exists()
        
        finally:
            # Limpiar archivos
            Path(path_real).unlink(missing_ok=True)
            Path(path_pred).unlink(missing_ok=True)
