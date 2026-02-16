#!/usr/bin/env python3
"""Pick a single (mode, softmax, signs) config that is most robust across traces.

This script is intentionally log-free: it only consumes the summarized CSV produced by
`scripts/summarize_compound_softmax_sign_matrix.py`.

Typical usage:
  /bin/python3 scripts/pick_global_config_from_matrix.py \
    sweeps/.../combined_matrix_summary.csv

By default it optimizes mean miss_ratio across traces. You can switch to byte_miss_ratio
or use a simple robustness objective that penalizes worst-trace performance.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class Objective:
    metric: str
    objective: str
    worst_weight: float


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument(
        "csv",
        type=Path,
        help="Path to combined_matrix_summary.csv or per-trace matrix_summary.csv",
    )
    p.add_argument(
        "--metric",
        choices=["miss_ratio", "byte_miss_ratio"],
        default="miss_ratio",
        help="Which metric to optimize",
    )
    p.add_argument(
        "--objective",
        choices=["mean", "worst", "mean+worst"],
        default="mean",
        help="How to aggregate across traces for a single config",
    )
    p.add_argument(
        "--worst-weight",
        type=float,
        default=0.5,
        help="Only used when objective=mean+worst: score = mean + worst_weight * worst",
    )
    p.add_argument(
        "--show-per-trace-best",
        action="store_true",
        help="Also print the best config per trace (requires 'trace' column)",
    )
    return p.parse_args()


def _score(df: pd.DataFrame, obj: Objective) -> pd.DataFrame:
    key_cols = ["mode", "softmax", "signs"]
    missing = [c for c in key_cols + [obj.metric] if c not in df.columns]
    if missing:
        raise SystemExit(f"CSV missing required columns: {missing}")

    grouped = (
        df.assign(key=df[key_cols].astype(str).agg("|".join, axis=1))
        .groupby("key")
        .agg(
            mean=(obj.metric, "mean"),
            worst=(obj.metric, "max"),
            n=(obj.metric, "size"),
        )
        .reset_index()
    )

    if obj.objective == "mean":
        grouped["score"] = grouped["mean"]
    elif obj.objective == "worst":
        grouped["score"] = grouped["worst"]
    elif obj.objective == "mean+worst":
        grouped["score"] = grouped["mean"] + obj.worst_weight * grouped["worst"]
    else:
        raise SystemExit(f"Unknown objective: {obj.objective}")

    return grouped.sort_values(["score", "worst", "mean"], ascending=True)


def main() -> None:
    args = _parse_args()
    df = pd.read_csv(args.csv)

    if args.show_per_trace_best:
        if "trace" not in df.columns:
            raise SystemExit("--show-per-trace-best requires a 'trace' column")
        key_cols = ["mode", "softmax", "signs"]
        df2 = df.assign(key=df[key_cols].astype(str).agg("|".join, axis=1))
        if args.metric not in df2.columns:
            raise SystemExit(f"Metric not found in CSV: {args.metric}")
        idx = df2.groupby("trace")[args.metric].idxmin()
        best = df2.loc[idx, ["trace", args.metric, "key"]].sort_values("trace")
        print("Per-trace BEST (lower is better):")
        print(best.to_string(index=False))
        uniq = set(best["key"].tolist())
        if len(uniq) == 1:
            print(f"A single config is BEST for all traces: {next(iter(uniq))}")
        else:
            print(f"No single config is BEST for all traces. Unique best keys: {sorted(uniq)}")
        print("\n---\n")

    obj = Objective(metric=args.metric, objective=args.objective, worst_weight=args.worst_weight)
    ranked = _score(df, obj)

    best = ranked.iloc[0]
    print(f"Input: {args.csv}")
    print(f"Optimize: metric={obj.metric}, objective={obj.objective}, worst_weight={obj.worst_weight}")
    print("\nTop candidates:")
    print(ranked.head(8).to_string(index=False))

    mode, softmax, signs = best["key"].split("|")
    print("\nBest single config (by this objective):")
    print(f"  mode   = {mode}")
    print(f"  softmax= {softmax}")
    print(f"  signs  = {signs}")

    # Emit env-vars snippet (keeps the same naming style as existing scripts)
    print("\nEnv vars:")
    if mode.startswith("compound=0"):
        print("  export LOH_SCORE_USE_COMPOUND=0")
        print("  export LOH_SCORE_USE_IRT=0")
    else:
        print("  export LOH_SCORE_USE_COMPOUND=1")
    print(f"  export LOH_USE_SOFTMAX={softmax}")
    print(f"  export LOH_USE_HEURISTIC_SIGNS={signs}")


if __name__ == "__main__":
    main()
