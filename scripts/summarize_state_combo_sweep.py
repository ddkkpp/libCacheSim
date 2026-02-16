#!/usr/bin/env python3
"""Summarize combined_state_combo_summary.csv from state combo sweeps.

Outputs:
- best_per_layout.csv: for each (trace, compile-time layout) pick the best RL_STATE_USE_MISSRATIO.
- best_overall_per_trace.csv: best layout for each trace.

This stays small and does not scan raw logs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


LAYOUT_COLS = [
    "include_hit_miss",
    "include_cache",
    "include_candidate",
    "include_topk",
    "include_avgtopk",
    "include_request",
]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("combined_csv", type=Path)
    p.add_argument("--metric", choices=["miss_ratio", "byte_miss_ratio"], default="miss_ratio")
    p.add_argument("--out-dir", type=Path, required=True)
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    df = pd.read_csv(args.combined_csv)

    required = {"trace", args.metric, "rl_state_use_missratio"} | set(LAYOUT_COLS)
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit(f"combined_csv missing columns: {missing}")

    # Normalize numeric columns
    for c in LAYOUT_COLS + ["rl_state_use_missratio"]:
        df[c] = df[c].astype(int)

    df[args.metric] = pd.to_numeric(df[args.metric], errors="coerce")
    df = df.dropna(subset=[args.metric])

    # Best per (trace, layout)
    grp_cols = ["trace"] + LAYOUT_COLS
    idx = df.groupby(grp_cols)[args.metric].idxmin()
    best_layout = df.loc[idx].copy()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    best_layout_path = out_dir / "best_per_layout.csv"
    best_layout.sort_values(["trace", args.metric]).to_csv(best_layout_path, index=False)

    # Best overall per trace
    idx2 = best_layout.groupby("trace")[args.metric].idxmin()
    best_trace = best_layout.loc[idx2].copy()
    best_trace_path = out_dir / "best_overall_per_trace.csv"
    best_trace.sort_values(["trace"]).to_csv(best_trace_path, index=False)

    print(f"Wrote: {best_layout_path}")
    print(f"Wrote: {best_trace_path}")


if __name__ == "__main__":
    main()
