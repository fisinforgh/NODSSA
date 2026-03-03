import xarray as xr
import pandas as pd
import sys
import os
import re

def cargar_ozono(path_he5: str) -> pd.DataFrame | None:
    try:
        ds = xr.open_dataset(
            path_he5,
            engine="netcdf4",
            group="/HDFEOS/GRIDS/OMI Column Amount O3/Data Fields",
            decode_times=False
        )
    except OSError as e:
        print(f"⚠️  Warning: no pude abrir {os.path.basename(path_he5)} → {e}")
        return None

    oz = ds["ColumnAmountO3"]
    valor = float(oz.mean().values)

    # Extraer fecha
    fname = os.path.basename(path_he5)
    parts = fname.split('_')
    date_token = next((p for p in parts if re.match(r'^\d{4}m\d{4}$', p)), None)
    if not date_token:
        print(f"⚠️  Warning: no pude extraer fecha de '{fname}'")
        return None

    year = date_token[0:4]
    month = date_token[5:7]
    day = date_token[7:9]
    fecha = pd.to_datetime(f"{year}-{month}-{day}")

    return pd.DataFrame({"Date": [fecha], "Ozone": [valor]})

if __name__ == "__main__":
    he5 = sys.argv[1]
    df = cargar_ozono(he5)
    if df is not None:
        print(df)


