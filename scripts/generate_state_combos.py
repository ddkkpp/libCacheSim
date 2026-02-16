#!/usr/bin/env python3
"""Generate compile-time state feature combinations for LOH.

We treat TopK and AvgTopK as mutually exclusive.

Outputs a CSV with columns:
  include_hit_miss, include_cache, include_candidate,
  include_topk, include_avgtopk, include_request

Example:
  /bin/python3 scripts/generate_state_combos.py --out state_combos.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--include-request", action="store_true", help="Include LOH_INCLUDE_REQUEST=0/1 dimension")
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    rows = []
    # toggle flags
    for hit_miss in (0, 1):
        for cache in (0, 1):
            for cand in (0, 1):
                req_vals = (0, 1) if args.include_request else (0,)
                for req in req_vals:
                    # mutually exclusive TopK/AvgTopK: 00, 10, 01
                    for topk, avgtopk in ((0, 0), (1, 0), (0, 1)):
                        rows.append(
                            {
                                "include_hit_miss": hit_miss,
                                "include_cache": cache,
                                "include_candidate": cand,
                                "include_topk": topk,
                                "include_avgtopk": avgtopk,
                                "include_request": req,
                            }
                        )

    out = pd.DataFrame(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"Wrote: {args.out} (n={len(out)})")


if __name__ == "__main__":
    main()
