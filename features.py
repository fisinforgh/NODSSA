# python/features.py

import pandas as pd
import os

def add_lags(df: pd.DataFrame, column: str="Ozone", max_lag: int=24) -> pd.DataFrame:
    """
    Genera variables rezagadas (lags) de 1 a max_lag días.
    """
    df = df.copy().set_index("Date")
    for lag in range(1, max_lag + 1):
        df[f"{column}_lag{lag}"] = df[column].shift(lag)
    return df.reset_index()

if __name__ == "__main__":
    # 1) Leer la serie limpia concatenada 2005-2025
    df = pd.read_parquet("../data/processed/ozone_2005_2025_clean.parquet")

    # 2) Generar lags 1–24
    df_lags = add_lags(df, column="Ozone", max_lag=24)

    # 3) Guardar las features
    os.makedirs("../data/processed", exist_ok=True)
    df_lags.to_parquet("../data/processed/ozone_2005_2025_lags.parquet")
    print("💾 Features (lags) guardadas en data/processed/ozone_2005_2025_lags.parquet")
