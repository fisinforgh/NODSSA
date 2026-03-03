# python/clean.py

import pandas as pd
import glob
import os
from extract import cargar_ozono

# Variables de configuración
years = range(2005, 2026)  # Desde 2005 hasta 2025 inclusive

all_dfs = []
for yr in years:
    folder = f"../data/raw_test/aura_{yr}"
    if not os.path.isdir(folder):
        print(f"⚠️  No existe carpeta para {yr}, omitiendo.")
        continue
    files = sorted(glob.glob(f"{folder}/*.he5"))
    dfs = [cargar_ozono(f) for f in files if cargar_ozono(f) is not None]
    if dfs:
        df_year = pd.concat(dfs).sort_values("Date").reset_index(drop=True)
        all_dfs.append(df_year)
    else:
        print(f"⚠️  No se cargaron HE5 válidos para {yr}.")

if not all_dfs:
    raise RuntimeError("No se cargó ningún dato válido en todo el rango de años.")

# Concatenar todos los años
df = pd.concat(all_dfs).reset_index(drop=True)

# 1) Poner Date como índice para reindexar
df = df.set_index("Date")

# 2) Reindex para tener todos los días seguidos y detectar huecos
date_full = pd.date_range(df.index.min(), df.index.max(), freq="D")
df = df.reindex(date_full).rename_axis("Date")

# 3) Interpolación lineal + forward/backward fill
df["Ozone"] = df["Ozone"].interpolate().ffill().bfill()

# 4) Volver a tener Date como columna
df = df.reset_index()

# 5) Guardar Parquet limpio
os.makedirs("../data/processed", exist_ok=True)
df.to_parquet("../data/processed/ozone_2005_2025_clean.parquet")
print("💾 Serie limpia guardada en data/processed/ozone_2005_2025_clean.parquet")
