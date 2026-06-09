#!/usr/bin/env python3
"""
Generate a trace that exposes 3LCache-OMR's structural weakness:
scoring by exp(predicted_reuse_distance) ignores object size.

Core mechanism (structural):
  3LCache-OMR score = exp(predicted_reuse_distance)  → IGNORES size
  But for OMR, evicting a larger object frees more cache space → better.
  → 3LCache-OMR is structurally suboptimal when object sizes differ.

Noise mechanism (amplifier):
  Objects have PROBABILISTIC returns → reuse distance prediction is uncertain.
  Many objects have similar predicted reuse → tiebreaking matters.
  Optimal tiebreaker: evict larger objects (same expected miss, more space).
  3LCache-OMR: can't use size → random tiebreaking → higher MR.
  LOH: CMA-ES learns negative size weight → systematic tiebreaking → lower MR.

Design:
  - Type S: 512 small objects (4KB). Return probability p_s ~ Beta(3,2).
  - Type L: 512 large objects (1MB). Return probability p_l ~ Beta(2,3).
  - p_s > p_l on average, but distributions OVERLAP → prediction uncertainty.
  - All objects burst 3 times, gap 500 filler, then return with prob p_i.
  - Objects cycle through pools → sustained workload.
  - All objects same size WITHIN type → two-tier size structure.
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate size-tiebreak trace")
    p.add_argument("--output-dir", type=Path, required=True)
    # Object pools
    p.add_argument("--small-pool", type=int, default=512)
    p.add_argument("--large-pool", type=int, default=512)
    p.add_argument("--small-size", type=int, default=4096)
    p.add_argument("--large-size", type=int, default=1048576)
    # Return probability distributions
    p.add_argument("--small-beta-a", type=float, default=3.0,
                   help="Beta(a,b) 'a' for small objects (higher→more returns)")
    p.add_argument("--small-beta-b", type=float, default=2.0)
    p.add_argument("--large-beta-a", type=float, default=2.0,
                   help="Beta(a,b) 'a' for large objects (lower→fewer returns)")
    p.add_argument("--large-beta-b", type=float, default=3.0)
    # Per round
    p.add_argument("--small-per-round", type=int, default=32)
    p.add_argument("--large-per-round", type=int, default=32)
    p.add_argument("--burst-count", type=int, default=3)
    p.add_argument("--return-count", type=int, default=2)
    # Gap between burst and return
    p.add_argument("--gap-requests", type=int, default=500)
    # One-hit noise objects
    p.add_argument("--onehit-per-round", type=int, default=64)
    p.add_argument("--onehit-pool", type=int, default=4096)
    p.add_argument("--onehit-size", type=int, default=4096)
    p.add_argument("--onehit-burst", type=int, default=3)
    # Filler
    p.add_argument("--filler-pool", type=int, default=256)
    p.add_argument("--filler-size", type=int, default=16384)
    # Rounds
    p.add_argument("--total-rounds", type=int, default=600)
    # Seed
    p.add_argument("--seed", type=int, default=20260601)
    p.add_argument("--no-plots", action="store_true")
    # Noise level: 0=deterministic (always return), 1=fully probabilistic
    p.add_argument("--noise-level", type=float, default=1.0,
                   help="0=deterministic returns, 1=full probabilistic (Beta)")
    return p.parse_args()


def write_req(writer, time: int, obj_id: int, obj_size: int) -> int:
    writer.writerow([time, obj_id, obj_size, 0])
    return time + 1


def generate(args: argparse.Namespace) -> tuple:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / "size_tiebreak.csv"
    summary_path = args.output_dir / "size_tiebreak_summary.md"

    rng = random.Random(args.seed)

    # Object ID ranges
    small_base = 1
    large_base = small_base + args.small_pool
    onehit_base = large_base + args.large_pool
    filler_base = onehit_base + args.onehit_pool

    # Assign return probabilities
    small_probs = []
    for _ in range(args.small_pool):
        p = rng.betavariate(args.small_beta_a, args.small_beta_b)
        # Blend with deterministic based on noise_level
        p = args.noise_level * p + (1 - args.noise_level) * 1.0
        small_probs.append(p)

    large_probs = []
    for _ in range(args.large_pool):
        p = rng.betavariate(args.large_beta_a, args.large_beta_b)
        p = args.noise_level * p + (1 - args.noise_level) * 1.0
        large_probs.append(p)

    component_counts: Counter = Counter()
    metadata: list[dict] = []
    time = 1
    small_cursor = 0
    large_cursor = 0
    onehit_cursor = 0
    filler_cursor = 0

    with trace_path.open("w", newline="") as f:
        writer = csv.writer(f)

        for rnd in range(args.total_rounds):
            # Select objects
            small_ids = [
                small_base + ((small_cursor + i) % args.small_pool)
                for i in range(args.small_per_round)
            ]
            small_cursor = (small_cursor + args.small_per_round) % args.small_pool

            large_ids = [
                large_base + ((large_cursor + i) % args.large_pool)
                for i in range(args.large_per_round)
            ]
            large_cursor = (large_cursor + args.large_per_round) % args.large_pool

            # Determine which objects return (probabilistic)
            returning_small = []
            returning_large = []
            for oid in small_ids:
                if rng.random() < small_probs[oid - small_base]:
                    returning_small.append(oid)
            for oid in large_ids:
                if rng.random() < large_probs[oid - large_base]:
                    returning_large.append(oid)

            # --- Burst: small objects ---
            for oid in small_ids:
                for _ in range(args.burst_count):
                    time = write_req(writer, time, oid, args.small_size)
                    component_counts["small_burst"] += 1
                metadata.append({
                    "round": rnd, "obj_class": "small",
                    "returns": 1 if oid in returning_small else 0,
                    "obj_size": args.small_size,
                })

            # --- Burst: large objects ---
            for oid in large_ids:
                for _ in range(args.burst_count):
                    time = write_req(writer, time, oid, args.large_size)
                    component_counts["large_burst"] += 1
                metadata.append({
                    "round": rnd, "obj_class": "large",
                    "returns": 1 if oid in returning_large else 0,
                    "obj_size": args.large_size,
                })

            # --- Gap filler ---
            gap_ids = [
                filler_base + ((filler_cursor + i) % args.filler_pool)
                for i in range(args.gap_requests)
            ]
            filler_cursor = (filler_cursor + args.gap_requests) % args.filler_pool
            for oid in gap_ids:
                time = write_req(writer, time, oid, args.filler_size)
                component_counts["gap_filler"] += 1

            # --- Return: small objects that "pass" the probabilistic check ---
            for oid in returning_small:
                for _ in range(args.return_count):
                    time = write_req(writer, time, oid, args.small_size)
                    component_counts["small_return"] += 1

            # --- Return: large objects that "pass" ---
            for oid in returning_large:
                for _ in range(args.return_count):
                    time = write_req(writer, time, oid, args.large_size)
                    component_counts["large_return"] += 1

            # --- One-hit noise ---
            onehit_ids = [
                onehit_base + ((onehit_cursor + i) % args.onehit_pool)
                for i in range(args.onehit_per_round)
            ]
            onehit_cursor = (onehit_cursor + args.onehit_per_round) % args.onehit_pool
            for oid in onehit_ids:
                for _ in range(args.onehit_burst):
                    time = write_req(writer, time, oid, args.onehit_size)
                    component_counts["onehit_burst"] += 1

    total_req = time - 1
    total_unique = args.small_pool + args.large_pool + args.onehit_pool + args.filler_pool
    total_bytes = (args.small_pool * args.small_size +
                   args.large_pool * args.large_size +
                   args.onehit_pool * args.onehit_size +
                   args.filler_pool * args.filler_size)

    # Statistics
    small_p_mean = sum(small_probs) / len(small_probs)
    large_p_mean = sum(large_probs) / len(large_probs)
    small_p_min = min(small_probs)
    small_p_max = max(small_probs)
    large_p_min = min(large_probs)
    large_p_max = max(large_probs)

    # Overlap: fraction of large objects with p > fraction of small objects
    small_threshold = sorted(small_probs)[len(small_probs) // 4]  # 25th percentile
    large_above = sum(1 for p in large_probs if p > small_threshold)
    overlap_pct = large_above / len(large_probs) * 100

    with summary_path.open("w") as f:
        f.write("# Size-Aware Tiebreaking Trace\n\n")
        f.write(f"**Noise level**: {args.noise_level}\n\n")
        f.write("## Design\n\n")
        f.write("- Small objects (4KB): higher return probability on average.\n")
        f.write("- Large objects (1MB): lower return probability on average.\n")
        f.write("- Return is PROBABILISTIC → reuse distance prediction is UNCERTAIN.\n")
        f.write("- When predictions are similar → size should be tiebreaker.\n")
        f.write("- 3LCache-OMR ignores size → suboptimal tiebreaking.\n")
        f.write("- LOH learns size weight → systematic advantage.\n\n")
        f.write("## Prediction\n\n")
        f.write("- 3LCache-OMR: size-blind scoring → higher MR, especially under cache pressure.\n")
        f.write("- LOH f001_orig (with size): learns negative size weight → lower MR.\n")
        f.write("- Gap should widen as cache shrinks (more tiebreaking needed).\n\n")
        f.write("## Statistics\n\n")
        f.write(f"- Total requests: {total_req:,}\n")
        f.write(f"- Total rounds: {args.total_rounds}\n")
        f.write(f"- Total unique objects: {total_unique:,}\n")
        f.write(f"- Total unique bytes: {total_bytes:,} ({total_bytes/1024/1024:.1f} MB)\n")
        f.write(f"- Small return prob: mean={small_p_mean:.3f}, range=[{small_p_min:.3f}, {small_p_max:.3f}]\n")
        f.write(f"- Large return prob: mean={large_p_mean:.3f}, range=[{large_p_min:.3f}, {large_p_max:.3f}]\n")
        f.write(f"- Overlap: {overlap_pct:.1f}% of large objects have p > 25th percentile of small\n\n")
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
