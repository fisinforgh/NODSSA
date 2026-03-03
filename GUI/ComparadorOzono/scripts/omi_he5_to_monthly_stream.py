# scripts/omi_he5_to_monthly_stream.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, re
from pathlib import Path
import numpy as np, pandas as pd, h5py

def _list_he5(root: Path, pattern: str):
    return sorted(root.rglob(pattern)) if "**" in pattern else sorted(root.glob(pattern))

def _attr(attrs, *names, default=None):
    def norm(x): return x.decode() if isinstance(x,(bytes,bytearray)) else str(x)
    for name in names:
        for k in attrs.keys():
            if norm(k).lower()==name.lower():
                v = attrs[k]
                if isinstance(v, np.ndarray) and v.size==1: return v.item()
                return v
    return default

def _apply_scale_offset(arr, attrs):
    scale = _attr(attrs, "ScaleFactor","scale_factor","Scale", default=1.0)
    offs  = _attr(attrs, "AddOffset","add_offset","Offset", default=0.0)
    try: return arr.astype("float64")*float(scale) + float(offs)
    except Exception: return arr.astype("float64")

def _parse_date(fname: str) -> pd.Timestamp:
    m = re.search(r"_(\d{4})m(\d{2})(\d{2})", fname) or re.search(r"(\d{4})(\d{2})(\d{2})", fname)
    if not m: raise ValueError(f"No se pudo extraer fecha de: {fname}")
    y, mm, dd = map(int, m.groups())
    return pd.Timestamp(y, mm, dd)

def _nearest_idx(a: np.ndarray, v: float) -> int: return int(np.argmin(np.abs(a - v)))

def _open_o3_latlon(h: h5py.File):
    # intenta varios paths de O3 L3
    cand = [
        "HDFEOS/GRIDS/OMI Column Amount O3/Data Fields/ColumnAmountO3",
        "HDFEOS/GRIDS/OMI_Column_Amount_O3/Data Fields/ColumnAmountO3",
    ]
    o3 = None
    for p in cand:
        if p in h: o3 = h[p]; break
    if o3 is None:
        # fallback: busca por nombre
        found = []
        h.visititems(lambda n,o: found.append(n) if isinstance(o,h5py.Dataset) and "ColumnAmountO3" in n else None)
        if found: o3 = h[found[0]]
    if o3 is None: raise RuntimeError("No encontré ColumnAmountO3 en HE5.")

    # lat/lon: intenta datasets; si no, reconstruye malla regular
    lat = None; lon = None; lat_ds=None; lon_ds=None
    for name in ("Latitude", "lat", "Lat"):
        for k in h.keys(): pass
    # búsqueda genérica
    dsets = []
    h.visititems(lambda n,o: dsets.append(n) if isinstance(o,h5py.Dataset) else None)
    lat_paths = [p for p in dsets if re.search(r"(?:Lat|lat|Latitude)$", p)]
    lon_paths = [p for p in dsets if re.search(r"(?:Lon|lon|Longitude)$", p)]
    if lat_paths and lon_paths:
        lat = np.array(h[lat_paths[0]][()])
        lon = np.array(h[lon_paths[0]][()])
        if lat.ndim==2 and lon.ndim==2:
            lat, lon = lat[:,0], lon[0,:]  # rejilla regular
    if lat is None or lon is None:
        ny, nx = o3.shape[-2], o3.shape[-1]
        lat = np.linspace(-89.875, 89.875, ny)
        lon = np.linspace(-179.875, 179.875, nx)
    return o3, lat, lon

def run(in_dir: Path, out_dir: Path, pattern: str, lat0: float, lon0: float, min_occ: int):
    out_dir.mkdir(parents=True, exist_ok=True)

    # Acumuladores mensuales (Welford)
    agg = {}  # (Year,Month) -> dict(count, mean, M2)
    files = _list_he5(in_dir, pattern)
    if not files: raise SystemExit(f"No HE5 en {in_dir} con patrón {pattern}")

    for i, f in enumerate(files, 1):
        try:
            with h5py.File(f, "r") as h:
                ds, lat, lon = _open_o3_latlon(h)
                arr = np.array(ds[()])
                arr = arr[0,:,:] if arr.ndim==3 else arr
                arr = _apply_scale_offset(arr, ds.attrs)
                fill = _attr(ds.attrs, "_FillValue","MissingValue", default=np.nan)
                date = _parse_date(f.name)

                # índice más cercano
                ii = _nearest_idx(lat, lat0)
                jj = _nearest_idx(lon, lon0)
                v = float(arr[ii, jj])
                ok = np.isfinite(v) and (np.isnan(fill) or v != fill) and (100.0 <= v <= 600.0)
                if not ok: continue

                key = (date.year, date.month)
                rec = agg.get(key, {"count":0, "mean":0.0, "M2":0.0})
                rec["count"] += 1
                delta = v - rec["mean"]
                rec["mean"] += delta / rec["count"]
                rec["M2"]   += delta * (v - rec["mean"])
                agg[key] = rec

        except Exception as e:
            print(f"[WARN] {f.name}: {e}")

        if i % 200 == 0:
            print(f"[{i}/{len(files)}] procesados...")

    if not agg:
        raise SystemExit("No se reunió ningún dato válido en el punto solicitado.")

    rows = []
    for (Y,M), r in sorted(agg.items()):
        n = r["count"]
        std = (r["M2"]/ (n-1))**0.5 if n > 1 else 0.0
        rows.append({"Year":Y, "Month":M, "Ozone_mean":r["mean"], "Ozone_std":std, "Count":n})
    dfm = pd.DataFrame(rows).sort_values(["Year","Month"])
    dfm.to_csv(out_dir/"bogota_monthly.csv", index=False)

    # binned desde mensual
    sigma = dfm["Ozone_std"].astype(float) / (dfm["Count"].clip(lower=1).astype(float)**0.5)
    binned = pd.DataFrame({
        "sun_bin_center": dfm["Month"].astype(float),
        "y_mean": dfm["Ozone_mean"].astype(float),
        "sigma": sigma
    }).replace([np.inf,-np.inf], np.nan).dropna()
    binned.to_csv(out_dir/"bogota_binned.csv", index=False)

    # corte min_occ
    cut = dfm[dfm["Count"] >= int(min_occ)]
    sigma_cut = cut["Ozone_std"].astype(float) / (cut["Count"].clip(lower=1).astype(float)**0.5)
    binned_cut = pd.DataFrame({
        "sun_bin_center": cut["Month"].astype(float),
        "y_mean": cut["Ozone_mean"].astype(float),
        "sigma": sigma_cut
    })
    binned_cut.to_csv(out_dir/f"bogota_binned_minocc{int(min_occ)}.csv", index=False)

    print("[OK] Generado en", out_dir)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_dir", required=True)
    ap.add_argument("--out_dir", default="data/processed")
    ap.add_argument("--glob", default="**/*.[Hh][Ee]5")
    ap.add_argument("--lat", type=float, default=4.61)
    ap.add_argument("--lon", type=float, default=-74.08)
    ap.add_argument("--min_occ", type=int, default=12)
    a = ap.parse_args()
    run(Path(a.in_dir), Path(a.out_dir), a.glob, a.lat, a.lon, a.min_occ)

if __name__ == "__main__":
    main()
