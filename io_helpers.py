# python/utils/io_helpers.py
from pathlib import Path
import pandas as pd

def project_root() -> Path:
    # <repo>/python/utils/io_helpers.py -> sube dos niveles
    return Path(__file__).resolve().parents[2]

def data_processed() -> Path:
    return project_root() / "data" / "processed"

def load_parquet(rel_path: str):
    """Lee parquet SIEMPRE con engine='pyarrow' y ruta absoluta robusta."""
    p = (project_root() / rel_path) if not rel_path.startswith("/") else Path(rel_path)
    if not p.exists():
        raise FileNotFoundError(f"No existe: {p}")
    # Fuerza engine para evitar autodetección fallida
    return pd.read_parquet(p, engine="pyarrow")
