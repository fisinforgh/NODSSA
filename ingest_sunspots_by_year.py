#!/usr/bin/env python3
"""
ingest_sunspots_by_year.py

Automatiza la descarga y segmentación de datos diarios de número de manchas solares
(SN_d_tot_V2.0.csv) en archivos por año, similar al pipeline HE5 para ozono.

Salida:
  data/raw_sunspots/<YYYY>/sunspots_<YYYY>.parquet

Uso:
  python ingest_sunspots_by_year.py --start 2005 --end 2025
"""
import pandas as pd
import requests
from io import StringIO
from pathlib import Path
import argparse

# --- Configuración ---
URL = 'http://sidc.oma.be/silso/DATA/SN_d_tot_V2.0.csv'
DATA_DIR = Path(__file__).resolve().parents[1] / 'data'
RAW_DIR = DATA_DIR / 'raw_sunspots'
RAW_DIR.mkdir(parents=True, exist_ok=True)

# --- Argumentos de línea de comandos ---
parser = argparse.ArgumentParser(
    description="Descarga y segmenta datos diarios de manchas solares por año"
)
parser.add_argument('--start', type=int, default=2005, help='Año inicial (inclusive)')
parser.add_argument('--end',   type=int, default=2025, help='Año final (inclusive)')
args = parser.parse_args()

# --- Descargar datos originales ---
print(f"Descargando datos de manchas solares desde {URL}...")
resp = requests.get(URL)
resp.raise_for_status()
raw = StringIO(resp.text)

# --- Leer CSV ---
cols = ['Year','Month','Day','FracYear','SunspotNumber','StdDev','ObsCount','Provisional']
df = pd.read_csv(raw, sep=';', header=None, names=cols, comment='#')
# Construir columna Date
df['Date'] = pd.to_datetime(df[['Year','Month','Day']])

# --- Segmentar por año ---
for year in range(args.start, args.end + 1):
    df_year = df[df['Date'].dt.year == year][['Date','SunspotNumber']]
    if df_year.empty:
        print(f"⚠️  No hay datos para el año {year}, omitido.")
        continue
    year_dir = RAW_DIR / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)
    out_file = year_dir / f'sunspots_{year}.parquet'
    df_year.to_parquet(out_file, index=False)
    print(f"💾 Guardado: {out_file}")

print("Proceso completado.")

