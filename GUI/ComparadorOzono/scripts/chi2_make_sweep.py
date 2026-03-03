#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import pandas as pd
import numpy as np
from app.core.chi2 import chi2_from_binned

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--binned", required=True)
    ap.add_argument("--out",    required=True)
    ap.add_argument("--min",    type=int, default=3)
    ap.add_argument("--max",    type=int, default=20)
    args = ap.parse_args()

    df = pd.read_csv(args.binned)
    # mapear nombres flexibles
    cols = {c.lower(): c for c in df.columns}
    def pick(*names):
        for n in names:
            if n.lower() in cols:
                return cols[n.lower()]
        return None
    c_n = pick("n","occ","count")

    rows = []
    for m in range(args.min, args.max + 1):
        d = df.copy()
        if c_n:
            d = d[d[c_n] >= m].copy()
        keep = len(d)
        total = len(df)
        if keep < 2:  # sin suficientes bins para ajustar
            continue

        res = chi2_from_binned(d)  # devuelve dict con chi2, chi2_red, p_cdf, etc.
        rows.append({
            "min_occ": int(m),
            "N_bins": int(keep),
            "pct_reduction": 100.0 * (1.0 - keep / total) if total else 0.0,
            "chi2": float(res.get("chi2", np.nan)),
            "nu": int(res.get("nu", np.nan)),
            # la GUI usa 'chi2_red_mean'; si es 1 valor por m, es el mismo χ²_red
            "chi2_red_mean": float(res.get("chi2_red", np.nan)),
            "p_two_sided": float(res.get("p_value", np.nan)),
            "p_cdf": float(res.get("p_cdf", np.nan)),
            "veredict_chi": res.get("veredict_chi", ""),
            "veredict_tutor": res.get("veredict_tutor", "")
        })

    out = pd.DataFrame(rows)
    out.to_csv(args.out, index=False)
    print(f"[OK] Escrito {args.out} con {len(out)} filas")

if __name__ == "__main__":
    main()

