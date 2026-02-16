#!/usr/bin/env python3
"""Merge multiple CSV files, adding/overriding a 'trace' column.

Used to build a combined summary across traces.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--input",
        action="append",
        nargs=2,
        metavar=("TRACE", "CSV"),
        help="Pair: TRACE_NAME CSV_PATH. Can be repeated.",
        required=True,
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    frames = []
    for trace, csv_path in args.input:
        p = Path(csv_path)
        df = pd.read_csv(p)
        df.insert(0, "trace", trace)
        frames.append(df)

    out = pd.concat(frames, ignore_index=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"Wrote: {args.out} rows={len(out)}")


if __name__ == "__main__":
    main()
