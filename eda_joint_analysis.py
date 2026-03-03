#!/usr/bin/env python3
"""
eda_joint_analysis.py

Realiza análisis exploratorio conjunto de las series de ozono y manchas solares:
1. Función de correlación cruzada (CCF) para identificar retardos relevantes.
2. Scatter plot con coeficientes de correlación de Pearson y Kendall.
3. Análisis espectral mediante periodograma para comparar ciclos (~11 años).

Uso:
  python eda_joint_analysis.py
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import periodogram
from scipy.stats import pearsonr, kendalltau

# Cargar datos limpios
df_oz   = pd.read_parquet('../data/processed/ozone_2005_2025_clean.parquet').set_index('Date')
df_spots = pd.read_parquet('../data/processed/sunspots_2005_2025_clean.parquet').set_index('Date')

# Unir ambas series
df = df_oz.join(df_spots, how='inner')
series_oz = df['Ozone']
series_sp = df['SunspotNumber']

# 1) Correlación Cruzada
def plot_ccf(x, y, maxlag=365, title='CCF Ozone vs Sunspots'):
    lags = np.arange(-maxlag, maxlag+1)
    corr = [x.corr(y.shift(lag)) for lag in lags]
    plt.figure(figsize=(10,4))
    markerline, stemlines, baseline = plt.stem(lags, corr)
    plt.setp(markerline, 'markerfacecolor', 'b')
    plt.setp(stemlines, 'color', 'gray')
    plt.title(title)
    plt.xlabel('Lag (days)')
    plt.ylabel('Correlation')
    plt.xlim(-maxlag, maxlag)
    plt.tight_layout()
    plt.show()

print("\n*** Cross-correlation Ozone vs Sunspots ***")
plot_ccf(series_oz, series_sp, maxlag=365*2)

# 2) Scatter Plot y Correlaciones
r_pearson, p_pearson = pearsonr(series_sp, series_oz)
r_kendall, p_kendall = kendalltau(series_sp, series_oz)
print(f"Pearson r = {r_pearson:.3f}, p = {p_pearson:.3e}")
print(f"Kendall tau = {r_kendall:.3f}, p = {p_kendall:.3e}\n")

plt.figure(figsize=(6,6))
plt.scatter(series_sp, series_oz, alpha=0.3)
plt.title('Ozono vs Manchas Solares')
plt.xlabel('Sunspot Number')
plt.ylabel('Ozone (DU)')
plt.annotate(f"r={r_pearson:.2f}", xy=(0.05,0.95), xycoords='axes fraction')
plt.tight_layout()
plt.show()

# 3) Análisis Espectral (Periodograma)
def plot_periodogram(series, fs=1.0, title='Periodogram'):
    f, Pxx = periodogram(series - np.mean(series), fs=fs)
    plt.figure(figsize=(10,4))
    plt.semilogy(f, Pxx)
    plt.title(title)
    plt.xlabel('Frequency (cycles/day)')
    plt.ylabel('Power')
    plt.tight_layout()
    plt.show()

print("\n*** Periodograma de Ozono ***")
plot_periodogram(series_oz, fs=1.0, title='Periodograma Ozono')
print("\n*** Periodograma de Manchas Solares ***")
plot_periodogram(series_sp, fs=1.0, title='Periodograma Manchas Solares')

# Identificar pico alrededor de ciclo de 11 años (~1/(11*365) cycles/day)
f_oz, P_oz = periodogram(series_oz - np.mean(series_oz), fs=1.0)
f_sp, P_sp = periodogram(series_sp - np.mean(series_sp), fs=1.0)
target_freq = 1/(11*365)

idx_oz = np.argmin(np.abs(f_oz - target_freq))
idx_sp = np.argmin(np.abs(f_sp - target_freq))
print(f"Ozone power at ~11y cycle (f={f_oz[idx_oz]:.6f}): {P_oz[idx_oz]:.2e}")
print(f"Sunspots power at ~11y cycle (f={f_sp[idx_sp]:.6f}): {P_sp[idx_sp]:.2e}")

