#!/usr/bin/env python3
"""
Temporal perturbation trace: shift return timing of a FEW object appearances
to corrupt 3LCache's feature→label mapping.

Mechanism (clean):
  - All objects follow predictable pattern: burst → gap → return
  - Features at burst time reliably predict return timing
  - 3LCache learns accurately → good predictions → good MR

Mechanism (perturbed):
  - For perturb_frac of object appearances, randomly DELAY the return
    (e.g., gap × 5 or gap + 2000)
  - At burst time, features DON'T indicate whether this instance is perturbed
  - SAME features → sometimes normal label, sometimes LONG label
  - 3LCache: can't predict accurately → ranking errors → worse MR
  - LOH: perturbed returns contribute little to epoch MR → weights stable

Key: the perturbation changes the LABEL without changing the PRE-PERTURBATION FEATURES.
This is genuine feature-label collision, achieved by temporal shift of existing objects.
"""

from __future__ import annotations
import argparse, csv, random
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Temporal perturbation trace")
    p.add_argument("--output-dir", type=Path, required=True)
    # Object pool
    p.add_argument("--obj-pool", type=int, default=256)
    p.add_argument("--obj-size", type=int, default=4096)
    # Per round
    p.add_argument("--obj-per-round", type=int, default=16)
    p.add_argument("--burst-count", type=int, default=3)
    p.add_argument("--return-count", type=int, default=2)
    p.add_argument("--normal-gap", type=int, default=300,
                   help="Normal return gap (one-hit requests between burst and return)")
    # Perturbation
    p.add_argument("--perturb-frac", type=float, default=0.0,
                   help="Fraction of object appearances with perturbed return timing "
                        "(0=clean, 0.2=20% perturbed)")
    p.add_argument("--perturb-delay", type=int, default=2000,
                   help="Extra delay added to perturbed returns")
    # One-hit noise
    p.add_argument("--onehit-pool", type=int, default=1024)
    p.add_argument("--onehit-per-round", type=int, default=32)
    # Gap fillers (reused)
    p.add_argument("--gap-pool", type=int, default=64)
    p.add_argument("--gap-size", type=int, default=4096)
    # Rounds
    p.add_argument("--total-rounds", type=int, default=2000)
    p.add_argument("--seed", type=int, default=20260602)
    p.add_argument("--no-plots", action="store_true")
    return p.parse_args()


def write_req(writer, time, oid, sz):
    writer.writerow([time, oid, sz, 0])
    return time + 1


def generate(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    tag = f"perturb{int(args.perturb_frac*100)}"
    trace_path = args.output_dir / f"temporal_perturb_{tag}.csv"
    summary_path = args.output_dir / f"temporal_perturb_{tag}_summary.md"

    obj_base = 1
    gap_base = obj_base + args.obj_pool
    onehit_base = gap_base + args.gap_pool

    rng = random.Random(args.seed)
    comp = Counter()
    time = 1
    obj_cursor = 0
    gap_cursor = 0
    onehit_cursor = 0

    # Track perturbation stats
    n_perturbed = 0
    n_normal = 0

    with trace_path.open("w", newline="") as f:
        w = csv.writer(f)
        for rnd in range(args.total_rounds):
            obj_ids = [obj_base + ((obj_cursor + i) % args.obj_pool)
                        for i in range(args.obj_per_round)]
            obj_cursor = (obj_cursor + args.obj_per_round) % args.obj_pool

            # Decide which objects are perturbed THIS round
            perturbed = set()
            for oid in obj_ids:
                if rng.random() < args.perturb_frac:
                    perturbed.add(oid)
                    n_perturbed += 1
                else:
                    n_normal += 1

            # --- Burst (all objects, same timing) ---
            for oid in obj_ids:
                for _ in range(args.burst_count):
                    time = write_req(w, time, oid, args.obj_size)
                    comp["burst"] += 1

            # --- Gap: reused fillers (short) ---
            short_gap = args.normal_gap
            for i in range(short_gap):
                oid = gap_base + ((gap_cursor + i) % args.gap_pool)
                time = write_req(w, time, oid, args.gap_size)
            gap_cursor = (gap_cursor + short_gap) % args.gap_pool
            comp["short_gap"] += short_gap

            # --- Normal return: non-perturbed objects ---
            normal_ret = [oid for oid in obj_ids if oid not in perturbed]
            for oid in normal_ret:
                for _ in range(args.return_count):
                    time = write_req(w, time, oid, args.obj_size)
                    comp["normal_return"] += 1

            # --- Extra gap for perturbed objects ---
            if perturbed:
                extra_gap = args.perturb_delay
                for i in range(extra_gap):
                    oid = gap_base + ((gap_cursor + i) % args.gap_pool)
                    time = write_req(w, time, oid, args.gap_size)
                gap_cursor = (gap_cursor + extra_gap) % args.gap_pool
                comp["perturb_gap"] += extra_gap

                # --- Perturbed return (delayed) ---
                for oid in perturbed:
                    for _ in range(args.return_count):
                        time = write_req(w, time, oid, args.obj_size)
                        comp["perturbed_return"] += 1

            # --- One-hit noise ---
            for i in range(args.onehit_per_round):
                oid = onehit_base + ((onehit_cursor + i) % args.onehit_pool)
                time = write_req(w, time, oid, args.obj_size)
            onehit_cursor = (onehit_cursor + args.onehit_per_round) % args.onehit_pool
            comp["onehit"] += args.onehit_per_round

    total_req = time - 1
    total_unique = args.obj_pool + args.gap_pool + args.onehit_pool
    total_bytes = (args.obj_pool * args.obj_size +
                   args.gap_pool * args.gap_size +
                   args.onehit_pool * args.obj_size)
    perturb_pct = n_perturbed / (n_perturbed + n_normal) * 100 if (n_perturbed + n_normal) else 0

    with summary_path.open("w") as f:
        f.write("# Temporal Perturbation Trace\n\n")
        f.write(f"**Perturb fraction**: {args.perturb_frac} ({perturb_pct:.1f}% of appearances)\n\n")
        f.write("## Design\n\n")
        f.write(f"- {args.obj_pool} objects, all {args.obj_size}B, burst {args.burst_count}, return {args.return_count}\n")
        f.write(f"- Normal return gap: {args.normal_gap}\n")
        if args.perturb_frac > 0:
            f.write(f"- Perturbed return: +{args.perturb_delay} extra delay\n")
            f.write(f"- {perturb_pct:.1f}% of appearances have perturbed (delayed) return\n\n")
            f.write("## Mechanism\n\n")
            f.write("Perturbed objects have SAME burst features as normal objects\n")
            f.write("(same frequency trend, same past distances before perturbation)\n")
            f.write("but LONG return label. This creates feature-label collision:\n")
            f.write("same features → variable labels → 3LCache prediction uncertainty.\n\n")
            f.write(f"Perturbation affects {perturb_pct:.1f}% of appearances → small LOH impact.\n\n")
        f.write(f"Stats: {total_req:,} req, {total_unique:,} obj, {total_bytes/1024/1024:.1f} MB\n")

    return trace_path, summary_path


def main():
    args = parse_args()
    trace_path, summary_path = generate(args)
    print(f"trace={trace_path}")
    print(f"summary={summary_path}")


if __name__ == "__main__":
    main()
