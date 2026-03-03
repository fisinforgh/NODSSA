#!/usr/bin/env python3
"""
varx_forecast.py

Implementa un modelo VARX para las series de ozono y manchas solares
(cómo se influyen mutuamente) y genera forecast conjunto 2026–2036.
"""
import pandas as pd
from statsmodels.tsa.api import VAR
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import timedelta

# --- Configuración ---
data_dir = Path(__file__).resolve().parents[1] / 'data' / 'processed'
# Cargar series limpias
oz = pd.read_parquet(data_dir / 'ozone_2005_2025_clean.parquet').set_index('Date')['Ozone']
sp = pd.read_parquet(data_dir / 'sunspots_2005_2025_clean.parquet').set_index('Date')['SunspotNumber']
# Concatenar en DataFrame multivariante
df = pd.concat([oz, sp], axis=1).dropna()

# 1) Selección de orden de VAR
model = VAR(df)
maxlags = 60  # hasta 60 días
sel = model.select_order(maxlags)
print("Orden óptimo según criterios:")
print(sel.summary())
# Elegir p según AIC
p = sel.aic
print(f"Usando p = {p} rezagos para VAR.")

# 2) Ajustar VAR(p)
var_res = model.fit(p)
print(var_res.summary())

# 3) Forecast conjunto 2026–2036
steps = 365 * 11
last_vals = df.values[-p:]
fc = var_res.forecast(last_vals, steps)
# Crear índice de fechas futuro
d_last = df.index[-1]
dates_fc = pd.date_range(d_last + timedelta(days=1), periods=steps, freq='D')
# DataFrame de forecast
df_fc = pd.DataFrame(fc, index=dates_fc, columns=df.columns)
# Guardar
out_dir = data_dir
df_fc.to_parquet(out_dir / 'varx_forecast.parquet')
print(f"💾 Forecast VARX guardado en {out_dir / 'varx_forecast.parquet'}.")

# 4) Visualización
df['Ozone'].plot(label='Histórico O3', figsize=(10,5))
df_fc['Ozone'].plot(label='Forecast O3')
plt.legend(); plt.title('VARX Forecast Ozone 2026–2036')
plt.tight_layout(); plt.show()

ax2 = df['SunspotNumber'].plot(label='Histórico SN', secondary_y=True)
df_fc['SunspotNumber'].plot(ax=ax2, label='Forecast SN', secondary_y=True)
plt.legend(loc='upper left'); plt.title('VARX Forecast Sunspots 2026–2036')
plt.tight_layout(); plt.show()
