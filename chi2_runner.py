# scripts/chi2_runner.py
# -*- coding: utf-8 -*-
"""
Runner por CLI que toma los CSV generados (mensual o binned) y produce:
- data/processed/chi2_diagnostics_basic.csv
- data/processed/chi2_diagnostics_aug.csv
- data/processed/chi2_sweep.csv
- docs/figs/diagnostics/chi2_local_basic.png
- docs/figs/diagnostics/chi2_local_cut.png
- docs/figs/diagnostics/chi2_sweep.png
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

from python.chi2_bins import (
    from_monthly_real, from_binned_generic,
    compute_chi2_from_bins, sweep_min_occ
)

def _detect_input(df: pd.DataFrame) -> str:
    if {"Year","Month","Ozone_mean","Ozone_std","Count"}.issubset(df.columns): return "monthly"
    if {"sun_bin_center","y_mean","sigma"}.issubset(df.columns): return "binned"
    raise SystemExit("Formato no reconocido. Esperaba mensual (Year,Month,...) o binned (sun_bin_center, y_mean, sigma).")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input_csv", required=True, help="bogota_monthly.csv o bogota_binned.csv")
    ap.add_argument("--out_data", default="data/processed")
    ap.add_argument("--out_figs", default="docs/figs/diagnostics")
    ap.add_argument("--min_occ", type=int, default=12)
    ap.add_argument("--alpha", type=float, default=0.05)
    args = ap.parse_args()

    p_in = Path(args.input_csv)
    p_data = Path(args.out_data); p_data.mkdir(parents=True, exist_ok=True)
    p_figs = Path(args.out_figs); p_figs.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(p_in)
    mode = _detect_input(df)
    bins = from_monthly_real(df) if mode=="monthly" else from_binned_generic(df)

    # (a) sin corte
    r0, f0 = compute_chi2_from_bins(bins, min_occ=None, alpha=args.alpha)
    pd.DataFrame([r0.__dict__]).to_csv(p_data/"chi2_diagnostics_basic.csv", index=False)
    f0.savefig(p_figs/"chi2_local_basic.png", dpi=150)

    # (b) con corte
    r1, f1 = compute_chi2_from_bins(bins, min_occ=args.min_occ, alpha=args.alpha)
    pd.DataFrame([r1.__dict__]).to_csv(p_data/"chi2_diagnostics_aug.csv", index=False)
    f1.savefig(p_figs/"chi2_local_cut.png", dpi=150)

    # (c) barrido
    dsw, fsw = sweep_min_occ(bins, range(3,21), alpha=args.alpha)
    dsw.to_csv(p_data/"chi2_sweep.csv", index=False)
    fsw.savefig(p_figs/"chi2_sweep.png", dpi=150)

    print("[OK] Tablas en", p_data)
    print("[OK] Figuras en", p_figs)

if __name__ == "__main__":
    main()
