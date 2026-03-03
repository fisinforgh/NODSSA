import xarray as xr
import pandas as pd
import re
import os
import sys

def cargar_ozono(path_he5: str) -> pd.DataFrame:
    # Abrir datos de ozono
    ds = xr.open_dataset(
        path_he5,
        engine="netcdf4",
        group="/HDFEOS/GRIDS/OMI Column Amount O3/Data Fields",
        decode_times=False
    )
    oz = ds["ColumnAmountO3"]
    # Promedio espacial global (la grilla completa)
    valor = float(oz.mean().values)

    # Extraer la fecha del nombre de archivo: busca 'YYYYmMMDD'
    fname = os.path.basename(path_he5)
    m = re.search(r"(\\d{4})m(\\d{2})(\\d{2})", fname)
    if not m:
        raise ValueError(f"No pude extraer fecha de '{fname}'")
    fecha = pd.to_datetime(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")

    return pd.DataFrame({"Date": [fecha], "Ozone": [valor]})

if __name__ == "__main__":
    he5 = sys.argv[1]
    df = cargar_ozono(he5)
    print(df)
