#!/usr/bin/env python3
"""
Outlier noise trace: a FEW objects with EXTREME reuse distance corrupt
3LCache's GBM via high-leverage training samples.

Mechanism:
  - Normal objects (N=128): burst → gap=300 → return → SHORT label (~5.7)
  - Outlier objects (K=4):   burst → gap=50000 → return → EXTREME label (~10.8)
  - All objects 4KB, interleaved burst → SIMILAR FEATURES at burst time
  - GBM's MSE loss dominated by outliers (residual ~5^2 = 25 vs ~0.1^2 for normal)
  - Model shifts to predict LONGER reuse for all objects in this feature region
  - Normal objects get overestimated reuse → wrongly evicted → MR penalty

For LOH:
  - 4 outliers / 132 total = 3% → small epoch MR contribution
  - CMA-ES weights barely affected
"""

from __future__ import annotations
import argparse, csv, random
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Outlier noise trace")
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--normal-pool", type=int, default=128)
    p.add_argument("--outlier-pool", type=int, default=4)
    p.add_argument("--obj-size", type=int, default=4096)
    p.add_argument("--normal-per-round", type=int, default=16)
    p.add_argument("--outlier-per-round", type=int, default=2)
    p.add_argument("--burst-count", type=int, default=3)
    p.add_argument("--return-count", type=int, default=2)
    p.add_argument("--normal-gap", type=int, default=300)
    p.add_argument("--outlier-gap", type=int, default=50000)
    p.add_argument("--gap-pool", type=int, default=256)
    p.add_argument("--gap-size", type=int, default=4096)
    p.add_argument("--onehit-pool", type=int, default=2048)
    p.add_argument("--onehit-per-round", type=int, default=32)
    p.add_argument("--total-rounds", type=int, default=2000)
    p.add_argument("--seed", type=int, default=20260602)
    p.add_argument("--no-plots", action="store_true")
    return p.parse_args()


def write_req(writer, time, oid, sz):
    writer.writerow([time, oid, sz, 0])
    return time + 1


def generate(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / "outlier_noise.csv"
    summary_path = args.output_dir / "outlier_noise_summary.md"

    normal_base = 1
    outlier_base = normal_base + args.normal_pool
    gap_base = outlier_base + args.outlier_pool
    onehit_base = gap_base + args.gap_pool

    rng = random.Random(args.seed)
    comp = Counter()
    time = 1
    normal_cursor, outlier_cursor = 0, 0
    gap_cursor, onehit_cursor = 0, 0

    with trace_path.open("w", newline="") as f:
        w = csv.writer(f)
        for rnd in range(args.total_rounds):
            normal_ids = [normal_base + ((normal_cursor + i) % args.normal_pool)
                           for i in range(args.normal_per_round)]
            normal_cursor = (normal_cursor + args.normal_per_round) % args.normal_pool

            outlier_ids = [outlier_base + ((outlier_cursor + i) % args.outlier_pool)
                            for i in range(args.outlier_per_round)]
            outlier_cursor = (outlier_cursor + args.outlier_per_round) % args.outlier_pool

            # --- Burst: normal + outlier INTERLEAVED (same features at burst) ---
            all_burst = ([(oid, "normal") for oid in normal_ids] +
                         [(oid, "outlier") for oid in outlier_ids])
            rng.shuffle(all_burst)
            for oid, kind in all_burst:
                for _ in range(args.burst_count):
                    time = write_req(w, time, oid, args.obj_size)
                    comp[f"{kind}_burst"] += 1

            # --- Short gap: gap fillers ---
            for i in range(args.normal_gap):
                oid = gap_base + ((gap_cursor + i) % args.gap_pool)
                time = write_req(w, time, oid, args.gap_size)
            gap_cursor = (gap_cursor + args.normal_gap) % args.gap_pool
            comp["short_gap"] += args.normal_gap

            # --- Normal return: ONLY normal objects ---
            for oid in normal_ids:
                for _ in range(args.return_count):
                    time = write_req(w, time, oid, args.obj_size)
                    comp["normal_return"] += 1

            # --- Long gap: for outlier return timing ---
            extra_gap = args.outlier_gap - args.normal_gap
            for i in range(extra_gap):
                oid = gap_base + ((gap_cursor + i) % args.gap_pool)
                time = write_req(w, time, oid, args.gap_size)
            gap_cursor = (gap_cursor + extra_gap) % args.gap_pool
            comp["long_gap"] += extra_gap

            # --- Outlier return: EXTREME delay ---
            for oid in outlier_ids:
                for _ in range(args.return_count):
                    time = write_req(w, time, oid, args.obj_size)
                    comp["outlier_return"] += 1

            # --- One-hit noise ---
            for i in range(args.onehit_per_round):
                oid = onehit_base + ((onehit_cursor + i) % args.onehit_pool)
                time = write_req(w, time, oid, args.obj_size)
            onehit_cursor = (onehit_cursor + args.onehit_per_round) % args.onehit_pool
            comp["onehit"] += args.onehit_per_round

    total_req = time - 1
    total_unique = args.normal_pool + args.outlier_pool + args.gap_pool + args.onehit_pool
    total_bytes = total_unique * args.obj_size
    outlier_pct = (comp["outlier_burst"] + comp["outlier_return"]) / total_req * 100

    # Key: the label range
    normal_label = f"log(1+{args.normal_gap}) ≈ {__import__('math').log(1+args.normal_gap):.1f}"
    outlier_label = f"log(1+{args.outlier_gap}) ≈ {__import__('math').log(1+args.outlier_gap):.1f}"

    with summary_path.open("w") as f:
        f.write("# Outlier Noise Trace\n\n")
        f.write(f"- Normal ({args.normal_pool}): gap={args.normal_gap} → label {normal_label}\n")
        f.write(f"- Outlier ({args.outlier_pool}): gap={args.outlier_gap} → label {outlier_label}\n")
        f.write(f"- ALL {args.obj_size}B, interleaved burst → SIMILAR features\n")
        f.write(f"- Outliers = {outlier_pct:.1f}% of requests → small LOH impact\n\n")
        f.write("## Mechanism\n\n")
        f.write(f"Outlier label ({outlier_label}) is ~2× normal ({normal_label}).\n")
        f.write("GBM's MSE loss: outlier residuals >> normal residuals → model shifts\n")
        f.write("to predict longer reuse for the shared feature region.\n")
        f.write("Normal objects get overestimated reuse → wrongly evicted → higher MR.\n\n")
        f.write(f"Stats: {total_req:,} req, {total_unique:,} obj, {total_bytes/1024/1024:.1f} MB\n")

    return trace_path, summary_path


def main():
    args = parse_args()
    trace_path, summary_path = generate(args)
    print(f"trace={trace_path}")
    print(f"summary={summary_path}")


if __name__ == "__main__":
    main()
