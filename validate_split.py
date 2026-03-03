import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error
from extract import cargar_ozono
import glob, os
import statsmodels.api as sm

def compute_metrics(y_true, y_pred):
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    r2 = sm.OLS(y_true, sm.add_constant(y_pred)).fit().rsquared
    return rmse, mae, mape, r2

# 1) Cargar datos con lags y resultados OLS
df_lags = pd.read_parquet(os.path.join('..','data','processed','ozone_2005_2025_lags.parquet')).dropna()
df_res = pd.read_parquet(os.path.join('..','data','processed','ols_results.parquet'))
# Asegurar que contienen Date, Ozone, fitted

# 2) Merge DataFrames
df = df_res.copy()

# 3) Train/Test split cronológico 80/20
split = int(len(df) * 0.8)
df_train = df.iloc[:split]
df_test = df.iloc[split:]

# 4) Métricas para OLS
metrics = []
for name, subset in [('in-sample', df_train), ('out-of-sample', df_test)]:
    y_true = subset['Ozone'].values
    y_pred = subset['fitted'].values
    rmse, mae, mape, r2 = compute_metrics(y_true, y_pred)
    metrics.append({
        'model': 'OLS_lags1-12',
        'dataset': name,
        'RMSE': rmse,
        'MAE': mae,
        'MAPE': mape,
        'R2': r2
    })

# 5) Guardar resultados
os.makedirs(os.path.join('..','data','processed'), exist_ok=True)
metrics_df = pd.DataFrame(metrics)
metrics_df.to_csv(os.path.join('..','data','processed','ols_metrics.csv'), index=False)
print('💾 Métricas OLS guardadas en data/processed/ols_metrics.csv')

