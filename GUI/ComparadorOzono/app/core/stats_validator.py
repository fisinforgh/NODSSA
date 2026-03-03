# python/GUI/ComparadorOzono/app/core/stats_validator.py
# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.diagnostic import linear_rainbow, het_breuschpagan, acorr_ljungbox
from scipy.stats import shapiro
from typing import Dict, List, Optional
from pathlib import Path
import logging

class AssumptionValidator:
    """
    Clase para validar los supuestos del modelo de regresión lineal:
    1. Linealidad (Rainbow Test)
    2. Independencia (Ljung-Box como proxy de p-valor para autocorrelación, o Durbin-Watson stat)
    3. Normalidad de residuos (Shapiro-Wilk)
    4. Homocedasticidad (Breusch-Pagan)
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def run_tests(self, df: pd.DataFrame, x_col: str, y_col: str) -> Dict[str, float]:
        """
        Ejecuta los tests estadísticos sobre un DataFrame dado.
        Retorna un diccionario con los p-valores.
        """
        # Limpieza básica
        data = df[[x_col, y_col]].dropna()
        if len(data) < 10:
            return {
                "rainbow_p": np.nan,
                "shapiro_p": np.nan,
                "bp_p": np.nan,
                "independence_p": np.nan
            }

        x = data[x_col].values
        y = data[y_col].values

        # Ajuste OLS
        X = sm.add_constant(x)
        model = sm.OLS(y, X).fit()
        residuals = model.resid

        results = {}

        # 1. Linealidad: Rainbow Test
        # H0: La relación es lineal
        try:
            stat, p_rainbow = linear_rainbow(model)
            results["rainbow_p"] = p_rainbow
        except Exception as e:
            self.logger.warning(f"Error en Rainbow test: {e}")
            results["rainbow_p"] = np.nan

        # 2. Normalidad: Shapiro-Wilk
        # H0: Los residuos siguen una distribución normal
        try:
            # Shapiro tiene un límite de N < 5000 en scipy, pero suele funcionar o dar warning
            if len(residuals) > 5000:
                # Si es muy grande, tomamos una muestra aleatoria para el test
                res_sample = np.random.choice(residuals, 5000, replace=False)
                stat, p_shapiro = shapiro(res_sample)
            else:
                stat, p_shapiro = shapiro(residuals)
            results["shapiro_p"] = p_shapiro
        except Exception as e:
            self.logger.warning(f"Error en Shapiro test: {e}")
            results["shapiro_p"] = np.nan

        # 3. Homocedasticidad: Breusch-Pagan
        # H0: La varianza de los errores es constante (homocedasticidad)
        try:
            # het_breuschpagan retorna: lm, lm_pvalue, fvalue, f_pvalue
            lm, lm_p_bp, fval, f_p_bp = het_breuschpagan(residuals, model.model.exog)
            results["bp_p"] = lm_p_bp
        except Exception as e:
            self.logger.warning(f"Error en Breusch-Pagan test: {e}")
            results["bp_p"] = np.nan

        # 4. Independencia: Autocorrelación
        # El usuario pide Durbin-Watson, pero statsmodels solo da el estadístico (0-4), no el p-valor.
        # Para obtener una distribución de p-valores, usamos Ljung-Box sobre los residuos.
        # H0: No hay autocorrelación (Independencia)
        try:
            # Ljung-Box retorna un DataFrame. Tomamos el p-valor del primer lag o un promedio.
            # Usualmente lag=1 es comparable a DW.
            lb_res = acorr_ljungbox(residuals, lags=[1], return_df=True)
            p_independence = lb_res["lb_pvalue"].iloc[0]
            results["independence_p"] = p_independence
        except Exception as e:
            self.logger.warning(f"Error en Independencia test: {e}")
            results["independence_p"] = np.nan

        return results

    def batch_process(self, files: List[Path], x_col: str = "sun_bin", y_col: str = "o3_mean") -> pd.DataFrame:
        """
        Procesa una lista de archivos CSV y acumula los resultados.
        Retorna un DataFrame con formato tidy: ['dataset_id', 'test_name', 'p_value']
        """
        records = []
        
        for i, file_path in enumerate(files):
            try:
                # Intentar cargar asumiendo formato de la GUI (binned) o raw
                df = pd.read_csv(file_path)
                
                # Mapeo de columnas si es necesario
                # La GUI usa 'sun_bin_center' o 'sun_bin', 'y_mean' o 'o3_mean'
                # Ajustar según tus archivos reales
                cols_map = {
                    "sun_bin_center": "x", "sun_bin": "x", "Manchas": "x",
                    "y_mean": "y", "o3_mean": "y", "Ozono": "y"
                }
                df_renamed = df.rename(columns=cols_map)
                
                if "x" not in df_renamed.columns or "y" not in df_renamed.columns:
                    # Si no encuentra columnas, saltar
                    continue
                
                p_values = self.run_tests(df_renamed, "x", "y")
                
                # Agregar a la lista
                dataset_id = file_path.stem
                
                records.append({
                    "dataset_id": dataset_id,
                    "test_name": "Linealidad (Rainbow)",
                    "p_value": p_values["rainbow_p"]
                })
                records.append({
                    "dataset_id": dataset_id,
                    "test_name": "Normalidad (Shapiro-Wilk)",
                    "p_value": p_values["shapiro_p"]
                })
                records.append({
                    "dataset_id": dataset_id,
                    "test_name": "Homocedasticidad (Breusch-Pagan)",
                    "p_value": p_values["bp_p"]
                })
                records.append({
                    "dataset_id": dataset_id,
                    "test_name": "Independencia (Ljung-Box)", # Proxy de DW
                    "p_value": p_values["independence_p"]
                })
                
            except Exception as e:
                self.logger.error(f"Error procesando archivo {file_path}: {e}")
                continue
                
        return pd.DataFrame(records)

# Ejemplo de uso (para test manual)
if __name__ == "__main__":
    # Crear datos dummy
    np.random.seed(42)
    x = np.linspace(0, 100, 50)
    y = 3 * x + 10 + np.random.normal(0, 5, 50)
    df_test = pd.DataFrame({"x": x, "y": y})
    
    validator = AssumptionValidator()
    res = validator.run_tests(df_test, "x", "y")
    print("Resultados Test Dummy:", res)
