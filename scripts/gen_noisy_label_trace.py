#!/usr/bin/env python3
"""
Generate a "noisy label" synthetic trace to test per-object prediction vs
workload-level preference learning.

Core mechanism:
  3LCache learns: per-object log(1+future_reuse_distance) from features.
  Labels come from two sources:
    - Hit: label = log1p(actual_reuse_distance)  ← correct
    - Ghost expiry: label = log1p(MAX_EVICTION_BOUNDARY + waiting_time) ← FAR

  If object reuse distance has HIGH VARIANCE, some instances get correct labels
  (short gap → hit → correct) while others get biased labels (long gap →
  ghost expiry → FAR). The SAME object gets MIXED labels.

  LOH's epoch MR is an AGGREGATE over many objects → variance cancels out.
  CMA-ES learns stable weights despite per-object noise.

Design:
  - N objects, all same size (4KB) — remove size confound
  - Each object i has a "hotness" h_i in [0.1, 0.9]
  - Object i's return gap for each appearance: drawn from Exp(mean = gap_base / h_i)
    → Hot objects (high h_i): typically short gaps
    → Cold objects (low h_i): typically long gaps
  - The exponential distribution creates HIGH VARIANCE in individual gaps
  - But the RANKING by h_i is stable: hotter objects return sooner ON AVERAGE

  For 3LCache:
    - Hot object sometimes has long gap → ghost expiry → FAR label
    - Cold object sometimes has short gap → correct short label
    - Same object, mixed labels → GBM can't achieve high accuracy
    - Ghost expiry creates SYSTEMATIC bias against objects with occasional long gaps

  For LOH:
    - Epoch MR averages over all objects' returns
    - CMA-ES learns: frequency weight ↑ → lower MR
    - The aggregate signal is stable despite per-object noise

Key expectation:
  - 3LCache prediction error has a lower bound (Bayes error) due to label noise
  - This error causes wrong eviction decisions
  - LOH's weights smooth out the noise
  - 3LCache MR > LOH MR, even after both fully converge
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate noisy-label trace")
    p.add_argument("--output-dir", type=Path, required=True)
    # Object pool
    p.add_argument("--num-objects", type=int, default=2048)
    p.add_argument("--obj-size", type=int, default=4096)
    # Hotness distribution: Zipf-like
    p.add_argument("--hotness-alpha", type=float, default=2.0,
                   help="Zipf alpha for hotness distribution")
    p.add_argument("--hotness-min", type=float, default=0.05)
    p.add_argument("--hotness-max", type=float, default=0.95)
    # Gap
    p.add_argument("--gap-base", type=int, default=3000,
                   help="Base gap; actual gap = gap_base / hotness (exponential)")
    p.add_argument("--gap-min", type=int, default=50)
    p.add_argument("--gap-max", type=int, default=50000)
    # Burst and return
    p.add_argument("--burst-count", type=int, default=3)
    p.add_argument("--return-count", type=int, default=2)
    # Objects per epoch
    p.add_argument("--objects-per-epoch", type=int, default=64)
    # Filler between burst and return
    p.add_argument("--filler-pool", type=int, default=256)
    p.add_argument("--filler-size", type=int, default=16384)
    p.add_argument("--filler-base-count", type=int, default=200,
                   help="Minimum filler requests between burst and return")
    # Total epochs
    p.add_argument("--total-epochs", type=int, default=600)
    # Seed
    p.add_argument("--seed", type=int, default=20260601)
    p.add_argument("--no-plots", action="store_true")
    return p.parse_args()


def write_req(writer, time: int, obj_id: int, obj_size: int) -> int:
    writer.writerow([time, obj_id, obj_size, 0])
    return time + 1


def generate(args: argparse.Namespace) -> tuple:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / "noisy_label.csv"
    summary_path = args.output_dir / "noisy_label_summary.md"

    rng = random.Random(args.seed)

    # Assign hotness to each object (Zipf-like: rank^alpha)
    hotness = []
    for i in range(args.num_objects):
        rank = i + 1
        raw = 1.0 / (rank ** (1.0 / args.hotness_alpha))
        hotness.append(raw)
    # Normalize to [hotness_min, hotness_max]
    h_min = min(hotness)
    h_max = max(hotness)
    for i in range(args.num_objects):
        normalized = (hotness[i] - h_min) / (h_max - h_min)
        hotness[i] = args.hotness_min + normalized * (args.hotness_max - args.hotness_min)

    # Filler object base IDs
    filler_base = args.num_objects + 1

    component_counts: Counter = Counter()
    time = 1
    obj_cursor = 0
    filler_cursor = 0

    with trace_path.open("w", newline="") as f:
        writer = csv.writer(f)

        for epoch in range(args.total_epochs):
            # Select objects for this epoch
            obj_ids = [
                (obj_cursor + i) % args.num_objects + 1
                for i in range(args.objects_per_epoch)
            ]
            obj_cursor = (obj_cursor + args.objects_per_epoch) % args.num_objects

            # For each object, draw its return gap from exponential
            obj_gaps = []
            for oid in obj_ids:
                h = hotness[oid - 1]
                mean_gap = args.gap_base / h
                gap = rng.expovariate(1.0 / mean_gap)
                gap = max(args.gap_min, min(args.gap_max, int(gap)))
                obj_gaps.append(gap)

            # --- Burst ---
            for oid in obj_ids:
                for _ in range(args.burst_count):
                    time = write_req(writer, time, oid, args.obj_size)
                    component_counts["burst"] += 1

            # --- Filler (minimum + per-object variable gap) ---
            # Use the maximum gap to determine filler length, but objects
            # return at their individual gap times interspersed with filler
            max_gap = max(obj_gaps)
            total_filler = args.filler_base_count + max_gap

            # Build return schedule: (return_time_offset, obj_id)
            return_schedule = []
            for oid, gap in zip(obj_ids, obj_gaps):
                return_time = args.filler_base_count + gap
                return_schedule.append((return_time, oid))
            return_schedule.sort()  # Return in order of gap

            # Generate filler + interleaved returns
            filler_idx = 0
            next_return_idx = 0
            for pos in range(total_filler):
                # Check if any object returns at this position
                while (next_return_idx < len(return_schedule) and
                       return_schedule[next_return_idx][0] == pos):
                    _, ret_oid = return_schedule[next_return_idx]
                    for _ in range(args.return_count):
                        time = write_req(writer, time, ret_oid, args.obj_size)
                        component_counts["return"] += 1
                    next_return_idx += 1

                # Write filler
                if pos < total_filler - 1 or next_return_idx < len(return_schedule):
                    fid = filler_base + (filler_cursor % args.filler_pool)
                    filler_cursor += 1
                    time = write_req(writer, time, fid, args.filler_size)
                    component_counts["filler"] += 1
                    filler_idx += 1

    total_req = time - 1
    total_unique = args.num_objects + args.filler_pool
    total_bytes = (args.num_objects * args.obj_size +
                   args.filler_pool * args.filler_size)

    # Statistics about gap distribution
    all_gaps = []
    for i in range(args.num_objects):
        h = hotness[i]
        mean_gap = args.gap_base / h
        all_gaps.append(mean_gap)

    with summary_path.open("w") as f:
        f.write("# Noisy Label Trace\n\n")
        f.write("## Design\n\n")
        f.write("- Objects have variable 'hotness': higher → shorter expected return gap.\n")
        f.write("- Actual return gap drawn from Exponential(mean = gap_base / hotness).\n")
        f.write("- HIGH VARIANCE: same object sometimes returns quickly, sometimes slowly.\n")
        f.write("- Quick returns → correct 3LCache labels. Slow returns → ghost expiry → FAR labels.\n")
        f.write("- LOH epoch MR averages over many objects → noise cancels out.\n\n")
        f.write("## Mechanism\n\n")
        f.write("3LCache: per-object labels are mixed (short + FAR) for the same object.\n")
        f.write("- GBM can't predict which instances will be quick vs slow.\n")
        f.write("- Ghost expiry creates systematic label bias for slow-return instances.\n")
        f.write("- Converged model still has prediction error → wrong evictions.\n\n")
        f.write("LOH: epoch MR aggregates over all returns.\n")
        f.write("- Per-object noise cancels out in aggregate.\n")
        f.write("- CMA-ES learns stable weights reflecting average object value.\n\n")
        f.write("## Statistics\n\n")
        f.write(f"- Total requests: {total_req:,}\n")
        f.write(f"- Total epochs: {args.total_epochs}\n")
        f.write(f"- Objects per epoch: {args.objects_per_epoch}\n")
        f.write(f"- Total unique objects: {total_unique:,}\n")
        f.write(f"- Total unique bytes: {total_bytes:,} ({total_bytes/1024/1024:.1f} MB)\n")
        f.write(f"- Object size: {args.obj_size:,} bytes (all same)\n")
        f.write(f"- Hotness range: [{args.hotness_min}, {args.hotness_max}]\n")
        f.write(f"- Mean gap range: [{min(all_gaps):.0f}, {max(all_gaps):.0f}] requests\n")
        f.write(f"- Gap base: {args.gap_base}\n\n")
        f.write("## Request Mix\n\n")
        f.write("| component | count |\n|---|---:|\n")
        for comp, cnt in sorted(component_counts.items()):
            f.write(f"| {comp} | {cnt:,} |\n")

    return trace_path, summary_path


def main() -> None:
    args = parse_args()
    trace_path, summary_path = generate(args)
    print(f"trace={trace_path}")
    print(f"summary={summary_path}")


if __name__ == "__main__":
    main()
