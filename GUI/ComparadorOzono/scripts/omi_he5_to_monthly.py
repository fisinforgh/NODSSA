# python/GUI/ComparadorOzono/scripts/omi_he5_to_monthly.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, re
from pathlib import Path
import numpy as np
import pandas as pd
import h5py

def _list_datasets(h): out=[]; h.visititems(lambda n,o: out.append(n) if isinstance(o,h5py.Dataset) else None); return out
def _guess_paths(h):
    dsets = _list_datasets(h)
    cand_o3 = [
        "HDFEOS/GRIDS/OMI Column Amount O3/Data Fields/ColumnAmountO3",
        "HDFEOS/GRIDS/OMI_Column_Amount_O3/Data Fields/ColumnAmountO3",
    ] + [p for p in dsets if "ColumnAmountO3" in p]
    o3_path = next((p for p in cand_o3 if p in dsets), None)
    cand_lat = [p for p in dsets if re.search(r"(?:Lat|lat|Latitude)$", p)]
    cand_lon = [p for p in dsets if re.search(r"(?:Lon|lon|Longitude)$", p)]
    return o3_path, (cand_lat[0] if cand_lat else None), (cand_lon[0] if cand_lon else None)

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

def _reconstruct_latlon(ds):
    ny, nx = ds.shape[-2], ds.shape[-1]
    lat = np.linspace(-89.875, 89.875, ny)
    lon = np.linspace(-179.875, 179.875, nx)
    return lat, lon

def _parse_date(fname: str) -> pd.Timestamp:
    m = re.search(r"_(\d{4})m(\d{2})(\d{2})", fname) or re.search(r"(\d{4})(\d{2})(\d{2})", fname)
    if not m: raise ValueError(f"No se pudo extraer fecha de: {fname}")
    y, mm, dd = map(int, m.groups())
    return pd.Timestamp(y, mm, dd)

def _read_he5(path: Path):
    with h5py.File(path, "r") as h:
        o3_path, lat_path, lon_path = _guess_paths(h)
        if o3_path is None: raise RuntimeError("No encontré ColumnAmountO3 en HE5.")
        ds = h[o3_path]
        o3 = np.array(ds[()]);  o3 = o3[0,:,:] if o3.ndim==3 else o3
        o3 = _apply_scale_offset(o3, ds.attrs)
        fill = _attr(ds.attrs, "_FillValue","MissingValue", default=np.nan)
        if lat_path and lon_path:
            lat = np.array(h[lat_path][()]); lon = np.array(h[lon_path][()])
            if lat.ndim==2 and lon.ndim==2: lat, lon = lat[:,0], lon[0,:]
        else:
            lat, lon = _reconstruct_latlon(ds)
    return {"date": _parse_date(path.name), "lat": lat, "lon": lon, "o3": o3, "fill": fill}

def _nearest_idx(a: np.ndarray, v: float) -> int: return int(np.argmin(np.abs(a - v)))

def _extract_point(rows, lat0, lon0) -> pd.DataFrame:
    out=[]
    for it in rows:
        i, j = _nearest_idx(it["lat"], lat0), _nearest_idx(it["lon"], lon0)
        v = float(it["o3"][i, j]); fill = it["fill"]
        ok = np.isfinite(v) and (np.isnan(fill) or v != fill) and (100.0 <= v <= 600.0)
        if ok: out.append({"date": it["date"], "lat": float(it["lat"][i]), "lon": float(it["lon"][j]), "O3": v})
    return pd.DataFrame(out).sort_values("date").reset_index(drop=True)

def _monthly(df_point: pd.DataFrame) -> pd.DataFrame:
    df = df_point.copy()
    df["Year"] = df["date"].dt.year; df["Month"] = df["date"].dt.month
    g = df.groupby(["Year","Month"], as_index=False)["O3"]
    out = g.agg(Ozone_mean=("O3","mean"), Ozone_std=("O3","std"), Count=("O3","count"))
    out["Ozone_std"] = out["Ozone_std"].fillna(0.0)
    return out.sort_values(["Year","Month"])

def _to_binned_monthly(dfm: pd.DataFrame) -> pd.DataFrame:
    sigma = dfm["Ozone_std"].astype(float) / np.sqrt(dfm["Count"].clip(lower=1).astype(float))
    return pd.DataFrame({
        "sun_bin_center": dfm["Month"].astype(float),
        "y_mean": dfm["Ozone_mean"].astype(float),
        "sigma": sigma
    }).replace([np.inf,-np.inf], np.nan).dropna()

def _sweep(dfm: pd.DataFrame, sweep=range(3,21)):
    rows = []; base = len(dfm)
    for m in sweep:
        cut = dfm[dfm["Count"] >= m]
        if len(cut) >= 2:
            sigma = cut["Ozone_std"]/np.sqrt(cut["Count"].clip(lower=1))
            x = cut["Month"].astype(float).to_numpy()
            y = cut["Ozone_mean"].astype(float).to_numpy()
            s = sigma.astype(float).to_numpy()
            w = 1.0/np.maximum(s,1e-9)**2
            X = np.vstack([np.ones_like(x), x]).T
            beta = np.linalg.solve((X.T*w)@X, (X.T*w)@y)
            chi2 = float(np.sum(((y-(beta[0]+beta[1]*x))/np.maximum(s,1e-12))**2))
            nu = max(len(x)-2,1); chi2r = chi2/nu
        else:
            chi2r = np.nan
        pct = 100.0*(1-len(cut)/base) if base else np.nan
        rows.append({"min_occ": m, "chi2_red_mean": chi2r, "pct_reduction": pct})
    return pd.DataFrame(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_dir", required=True)
    ap.add_argument("--out_dir", default="../../data/processed")
    ap.add_argument("--lat", type=float, default=4.61)
    ap.add_argument("--lon", type=float, default=-74.08)
    ap.add_argument("--min_occ", type=int, default=12)
    ap.add_argument("--glob", default="*.he5")
    a = ap.parse_args()

    in_dir, out_dir = Path(a.in_dir), Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(in_dir.glob(a.glob))
    if not files: raise SystemExit(f"No HE5 en {in_dir}")

    rows=[]
    for f in files:
        try: rows.append(_read_he5(f))
        except Exception as e: print(f"[WARN] {f.name}: {e}")

    df_point = _extract_point(rows, a.lat, a.lon)
    if df_point.empty: raise SystemExit("Sin datos válidos en el punto (revisa lat/lon).")

    dfm = _monthly(df_point)
    (out_dir/"bogota_monthly.csv").write_text(dfm.to_csv(index=False))

    binned = _to_binned_monthly(dfm)
    (out_dir/"bogota_binned.csv").write_text(binned.to_csv(index=False))

    cut = dfm[dfm["Count"] >= int(a.min_occ)]
    (out_dir/f"bogota_binned_minocc{int(a.min_occ)}.csv").write_text(_to_binned_monthly(cut).to_csv(index=False))

    _sweep(dfm, range(3,21)).to_csv(out_dir/"chi2_sweep.csv", index=False)

    print(f"[OK] Salidas en {out_dir}")
    print(" - bogota_monthly.csv")
    print(" - bogota_binned.csv")
    print(f" - bogota_binned_minocc{int(a.min_occ)}.csv")
    print(" - chi2_sweep.csv")

if __name__ == "__main__":
    main()
