#!/usr/bin/env python3
"""
Generate a two-stage synthetic trace:
1) base requests from a normal Zipf workload
2) post-injected noise requests

Output CSV columns: time,obj_id,obj_size,ttl
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate two-stage Zipf + noise trace")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("tmp/20260529-zipf-noise-two-stage"),
    )
    parser.add_argument("--num-objects", type=int, default=65536)
    parser.add_argument("--num-requests", type=int, default=300000)
    parser.add_argument("--alpha", type=float, default=1.1)
    parser.add_argument("--obj-size", type=int, default=4096)
    parser.add_argument("--noise-pool", type=int, default=32768)
    parser.add_argument("--noise-every", type=int, default=64)
    parser.add_argument("--noise-burst", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260529)
    parser.add_argument(
        "--noise-start-frac",
        type=float,
        default=0.0,
        help="Only inject noise after this fraction of base requests (0.0=whole trace, 0.5=second half only)",
    )
    return parser.parse_args()


def gen_zipf_ids(num_objects: int, alpha: float, num_requests: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    ranks = np.arange(1, num_objects + 1, dtype=np.float64)
    prob = np.power(ranks, -alpha)
    prob /= prob.sum()
    # IDs are 1-based for cachesim CSV convenience.
    return rng.choice(np.arange(1, num_objects + 1, dtype=np.int64), size=num_requests, p=prob)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    trace_path = args.output_dir / "zipf_noise_two_stage.csv"
    metadata_path = args.output_dir / "zipf_noise_two_stage_metadata.csv"
    summary_path = args.output_dir / "zipf_noise_two_stage_summary.md"

    zipf_ids = gen_zipf_ids(args.num_objects, args.alpha, args.num_requests, args.seed)

    noise_base = args.num_objects + 1
    noise_count = 0
    base_count = 0
    t = 1
    noise_start_idx = int(args.num_requests * args.noise_start_frac)

    with trace_path.open("w", newline="") as tf, metadata_path.open("w", newline="") as mf:
        tw = csv.writer(tf)
        mw = csv.writer(mf)
        mw.writerow(["time", "obj_id", "obj_size", "cls"])

        for idx, obj_id in enumerate(zipf_ids, start=1):
            tw.writerow([t, int(obj_id), args.obj_size, 0])
            mw.writerow([t, int(obj_id), args.obj_size, "base_zipf"])
            t += 1
            base_count += 1

            # Inject noise only after base requests, keeping base rule stable.
            # If noise_start_frac > 0, only inject after that fraction of requests.
            if idx % args.noise_every == 0 and idx > noise_start_idx:
                for off in range(args.noise_burst):
                    noise_id = noise_base + ((idx + off) % args.noise_pool)
                    tw.writerow([t, int(noise_id), args.obj_size, 0])
                    mw.writerow([t, int(noise_id), args.obj_size, "noise"])
                    t += 1
                    noise_count += 1

    total = base_count + noise_count
    noise_ratio = (noise_count / total) if total > 0 else 0.0

    with summary_path.open("w") as sf:
        sf.write("# Two-stage Zipf + noise trace\n\n")
        sf.write("- Stage 1 (base): Zipf normal workload\n")
        sf.write("- Stage 2 (noise): post-injected noise requests\n\n")
        sf.write(f"Trace: `{trace_path}`\n\n")
        sf.write(f"Metadata: `{metadata_path}`\n\n")
        sf.write("## Parameters\n\n")
        sf.write(f"- num_objects: {args.num_objects}\n")
        sf.write(f"- num_requests: {args.num_requests}\n")
        sf.write(f"- alpha: {args.alpha}\n")
        sf.write(f"- obj_size: {args.obj_size}\n")
        sf.write(f"- noise_pool: {args.noise_pool}\n")
        sf.write(f"- noise_every: {args.noise_every}\n")
        sf.write(f"- noise_burst: {args.noise_burst}\n")
        sf.write(f"- noise_start_frac: {args.noise_start_frac}\n")
        sf.write(f"- seed: {args.seed}\n\n")
        sf.write("## Request Mix\n\n")
        sf.write(f"- base_zipf requests: {base_count}\n")
        sf.write(f"- noise requests: {noise_count}\n")
        sf.write(f"- total requests: {total}\n")
        sf.write(f"- noise ratio: {noise_ratio:.4f}\n")

    print(f"trace={trace_path}")
    print(f"metadata={metadata_path}")
    print(f"summary={summary_path}")


if __name__ == "__main__":
    main()
