# -*- coding: utf-8 -*-
"""
CLI para correr χ² y gráficas SIN tocar tu GUI.
Ejemplos:
  # 1) Comparativo local (sin corte / con corte)
  python scripts/chi2_runner.py local \
      --binned-sin data/processed/bogota_binned.csv \
      --binned-cut data/processed/bogota_binned_minocc12.csv \
      --out-a docs/figs/diagnostics/chi2_local_basic.png \
      --out-b docs/figs/diagnostics/chi2_local_cut.png \
      --title-a "Bogotá (sin corte)" --title-b "Bogotá (con corte: min_occ=12)"

  # 2) Curva de justificación
  python scripts/chi2_runner.py sweep \
      --sweep-csv data/processed/chi2_sweep.csv \
      --chosen 12 \
      --out docs/figs/diagnostics/chi2_sweep.png

  # 3) Superficies globales
  python scripts/chi2_runner.py surfaces \
      --diag-basic data/processed/chi2_diagnostics_basic.csv \
      --diag-cut   data/processed/chi2_diagnostics_aug.csv \
      --out-basic docs/figs/diagnostics/chi2_surface_basic.png \
      --out-cut   docs/figs/diagnostics/chi2_surface_cut.png
"""
import argparse, pandas as pd
from app.core.chi2_plots import plot_local, plot_sweep, plot_surface

def cmd_local(args):
    df_a = pd.read_csv(args.binned_sin)
    df_b = pd.read_csv(args.binned_cut)
    plot_local(df_a, args.title_a, args.out_a, alpha=args.alpha)
    plot_local(df_b, args.title_b, args.out_b, alpha=args.alpha)

def cmd_sweep(args):
    df = pd.read_csv(args.sweep_csv)
    plot_sweep(df, args.chosen, args.out)

def cmd_surfaces(args):
    basic = pd.read_csv(args.diag_basic)
    cut   = pd.read_csv(args.diag_cut)
    plot_surface(basic, "Superficie χ²_red — CHI2 (sin corte)", args.out_basic)
    plot_surface(cut,   "Superficie χ²_red — CHI2 CUT (con corte)", args.out_cut)

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("local")
    a.add_argument("--binned-sin", required=True)
    a.add_argument("--binned-cut", required=True)
    a.add_argument("--out-a", required=True)
    a.add_argument("--out-b", required=True)
    a.add_argument("--title-a", default="(sin corte)")
    a.add_argument("--title-b", default="(con corte)")
    a.add_argument("--alpha", type=float, default=0.05)
    a.set_defaults(func=cmd_local)

    s = sub.add_parser("sweep")
    s.add_argument("--sweep-csv", required=True)
    s.add_argument("--chosen", type=int, required=True)
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_sweep)

    m = sub.add_parser("surfaces")
    m.add_argument("--diag-basic", required=True)
    m.add_argument("--diag-cut",   required=True)
    m.add_argument("--out-basic", required=True)
    m.add_argument("--out-cut",   required=True)
    m.set_defaults(func=cmd_surfaces)

    args = ap.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
