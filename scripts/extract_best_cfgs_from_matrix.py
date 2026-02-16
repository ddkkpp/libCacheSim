#!/usr/bin/env python3
"""Extract per-trace best base config from a matrix summary CSV.

Input: a CSV like sweeps/.../combined_matrix_summary.csv with columns:
  trace, compound, irt, softmax, signs, miss_ratio, ...

Output: CSV with one row per trace and the corresponding LOH env vars.

Example:
  /bin/python3 scripts/extract_best_cfgs_from_matrix.py \
    sweeps/.../combined_matrix_summary.csv \
    --metric miss_ratio \
    --out sweeps/.../best_cfgs.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("matrix_csv", type=Path)
    p.add_argument("--metric", choices=["miss_ratio", "byte_miss_ratio"], default="miss_ratio")
    p.add_argument("--out", type=Path, required=True)
    return p.parse_args()


def _to_int01(v) -> int:
    try:
        if pd.isna(v):
            return 0
        return 1 if int(float(v)) != 0 else 0
    except Exception:
        s = str(v).strip().lower()
        if s in {"1", "true", "yes", "on"}:
            return 1
        return 0


def main() -> None:
    args = _parse_args()
    df = pd.read_csv(args.matrix_csv)
    required = {"trace", args.metric, "compound", "softmax", "signs"}
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit(f"matrix_csv missing columns: {missing}")

    # pick best per trace by metric (lower is better)
    idx = df.groupby("trace")[args.metric].idxmin()
    best = df.loc[idx].copy()

    out_rows = []
    for _, row in best.iterrows():
        trace = str(row["trace"]).strip()
        compound = _to_int01(row.get("compound"))
        softmax = _to_int01(row.get("softmax"))
        signs = _to_int01(row.get("signs"))

        if compound == 1:
            score_use_compound = 1
            score_use_irt = 1
            mode = "compound=1"
        else:
            score_use_compound = 0
            # In the current matrix runs, compound=0 rows correspond to irt=0 mode.
            score_use_irt = 0
            mode = "compound=0,irt=0"

        out_rows.append(
            {
                "trace": trace,
                "mode": mode,
                "metric": args.metric,
                "metric_value": float(row[args.metric]),
                "LOH_SCORE_USE_COMPOUND": score_use_compound,
                "LOH_SCORE_USE_IRT": score_use_irt,
                "LOH_USE_SOFTMAX": softmax,
                "LOH_USE_HEURISTIC_SIGNS": signs,
            }
        )

    out = pd.DataFrame(out_rows).sort_values(["trace"]).reset_index(drop=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"Wrote: {args.out} ({len(out)} traces)")


if __name__ == "__main__":
    main()
