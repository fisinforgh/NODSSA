#!/usr/bin/env python3
"""
model_arimax.py

Ajusta un modelo SARIMAX con exógeno solar y evalúa performance:
1. Carga series limpias de ozono y manchas solares.
2. Divide en train (80%) y test (20%) cronológicamente.
3. Grid search simplificado sobre p,d,q para minimizar AIC.
4. Ajusta SARIMAX(endog, exog, order, seasonal_order=(1,1,1,12)).
5. Pronostica sobre test y calcula RMSE, MAE, R2.
6. Guarda resultados y métricas.
"""
import pandas as pd
import numpy as np
import statsmodels.api as sm
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import os

# 1) Cargar datos
df_oz = pd.read_parquet('../data/processed/ozone_2005_2025_clean.parquet').set_index('Date')
df_sp = pd.read_parquet('../data/processed/sunspots_2005_2025_clean.parquet').set_index('Date')
df = df_oz.join(df_sp, how='inner').dropna()

enod = df['Ozone']
exog_full = df[['SunspotNumber']]

# 2) Train/Test split 80/20 cronológico
total = len(df)
train_end = int(0.8 * total)
endog_train = enod.iloc[:train_end]
endog_test  = enod.iloc[train_end:]
exog_train  = exog_full.iloc[:train_end]
exog_test   = exog_full.iloc[train_end:]

# 3) Grid search simplificado para ARIMAX
template = []
for p in range(0,3):
    for d in range(0,2):
        for q in range(0,3):
            try:
                mod = sm.tsa.SARIMAX(endog_train, exog=exog_train,
                                     order=(p,d,q), seasonal_order=(1,1,1,12),
                                     enforce_stationarity=False, enforce_invertibility=False)
                res = mod.fit(disp=False)
                template.append({'order':(p,d,q), 'aic': res.aic})
            except Exception:
                continue
# Seleccionar mejor orden
best = min(template, key=lambda x: x['aic'])
print(f"Mejor orden ARIMAX (p,d,q) = {best['order']} con AIC={best['aic']:.1f}")

# 4) Ajustar modelo con mejor orden sobre train
p, d, q = best['order']
model = sm.tsa.SARIMAX(endog_train, exog=exog_train,
                       order=(p,d,q), seasonal_order=(1,1,1,12),
                       enforce_stationarity=False, enforce_invertibility=False)
res = model.fit(disp=False)
print(res.summary())

# 5) Pronóstico y métricas
pred = res.get_forecast(steps=len(endog_test), exog=exog_test)
fitted = pred.predicted_mean
rmse = np.sqrt(mean_squared_error(endog_test, fitted))
mae  = mean_absolute_error(endog_test, fitted)
r2   = r2_score(endog_test, fitted)
print(f"RMSE (test) = {rmse:.2f}")
print(f"MAE  (test) = {mae:.2f}")
print(f"R2   (test) = {r2:.3f}")

# 6) Guardar resultados
ios = os.makedirs
os.makedirs('../data/processed', exist_ok=True)
# Serie pronosticada y real
df_res = pd.DataFrame({
    'Date': endog_test.index,
    'Ozone_true': endog_test.values,
    'Ozone_pred': fitted.values,
    'resid': endog_test.values - fitted.values
})
out_parquet = '../data/processed/arimax_results.parquet'
df_res.to_parquet(out_parquet, index=False)
# Guardar métricas en CSV
metrics = pd.DataFrame([{'Model':'ARIMAX', 'p':p, 'd':d, 'q':q,
                         'RMSE':rmse, 'MAE':mae, 'R2':r2}])
metrics.to_csv('../data/processed/arimax_metrics.csv', index=False)
print(f"💾 Resultados guardados en {out_parquet} y métricas en arimax_metrics.csv")

