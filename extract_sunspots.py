#!/usr/bin/env python3
"""
extract_sunspots.py

Concatena y limpia series diarias de manchas solares segmentadas por año,
creando un único Parquet para su uso en análisis posterior.

Salida:
  data/processed/sunspots_2005_2025_clean.parquet

Uso:
  python extract_sunspots.py
"""
import pandas as pd
from pathlib import Path
import glob, os

# Directorios
BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / 'data' / 'raw_sunspots'
OUT_DIR = BASE_DIR / 'data' / 'processed'
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 1) Recopilar todos los Parquet anuales
paths = sorted(glob.glob(str(RAW_DIR / '*' / 'sunspots_*.parquet')))
if not paths:
    raise FileNotFoundError(f"No se encontraron archivos en {RAW_DIR}")

# 2) Leer y concatenar
dfs = [pd.read_parquet(p) for p in paths]
df = pd.concat(dfs).sort_values('Date').reset_index(drop=True)

# 3) Asegurar índice diario y rellenar huecos
df['Date'] = pd.to_datetime(df['Date'])
df = df.set_index('Date')
full_idx = pd.date_range(df.index.min(), df.index.max(), freq='D')
df = df.reindex(full_idx).rename_axis('Date')
# Interpolación y fwd/bwd fill
if 'SunspotNumber' in df:
    df['SunspotNumber'] = df['SunspotNumber'].interpolate().ffill().bfill()
else:
    raise KeyError('Columna SunspotNumber no encontrada en los datos')

# 4) Guardar parquet limpio
out_file = OUT_DIR / 'sunspots_2005_2025_clean.parquet'
df.reset_index().to_parquet(out_file, index=False)
print(f"💾 Sunspots limpios guardados en {out_file}")

