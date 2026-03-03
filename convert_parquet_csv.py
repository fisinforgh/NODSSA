#!/usr/bin/env python3
"""
Script para convertir archivos .parquet a .csv
"""
import os
import sys
import pandas as pd
from pathlib import Path

def convert_parquet_to_csv(parquet_path: str, csv_path: str = None):
    """Convierte un archivo parquet a CSV."""
    if not os.path.exists(parquet_path):
        print(f"❌ Error: No existe {parquet_path}")
        return False
    
    try:
        # Leer parquet
        print(f"📖 Leyendo {parquet_path}...")
        df = pd.read_parquet(parquet_path)
        
        # Generar nombre de salida si no se proporciona
        if csv_path is None:
            csv_path = parquet_path.replace('.parquet', '.csv')
        
        # Guardar como CSV
        print(f"💾 Guardando {csv_path}...")
        df.to_csv(csv_path, index=False)
        
        print(f"✅ Conversión exitosa!")
        print(f"   Filas: {len(df)}, Columnas: {len(df.columns)}")
        print(f"   Columnas: {', '.join(df.columns)}")
        return True
        
    except Exception as e:
        print(f"❌ Error al convertir: {e}")
        return False

def convert_directory(directory: str):
    """Convierte todos los archivos .parquet en un directorio."""
    path = Path(directory)
    parquet_files = list(path.glob("**/*.parquet"))
    
    if not parquet_files:
        print(f"No se encontraron archivos .parquet en {directory}")
        return
    
    print(f"📦 Encontrados {len(parquet_files)} archivos .parquet")
    print("-" * 60)
    
    success = 0
    for pf in parquet_files:
        csv_path = str(pf).replace('.parquet', '.csv')
        if convert_parquet_to_csv(str(pf), csv_path):
            success += 1
        print("-" * 60)
    
    print(f"\n✅ Convertidos exitosamente: {success}/{len(parquet_files)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python convert_to_csv.py archivo.parquet")
        print("  python convert_to_csv.py directorio/")
        sys.exit(1)
    
    target = sys.argv[1]
    
    if os.path.isfile(target):
        convert_parquet_to_csv(target)
    elif os.path.isdir(target):
        convert_directory(target)
    else:
        print(f"❌ No existe: {target}")