#!/usr/bin/env python3
"""
Feature-Label Flip trace: a FEW objects have features→label mapping OPPOSITE
to the majority, creating feature-space contradiction for 3LCache's GBM.

Mechanism:
  - Normal-hot (N=128): high freq, short past → SHORT reuse (return at gap=100)
  - Normal-cold (N=128): low freq, long past → LONG reuse (return at gap=5000)
  - Flipped-hot (K=8): SAME features as normal-hot (interleaved burst, similar freq)
    but return at LONG gap (like normal-cold) → label is LONG despite "hot" features
  → FEATURE COLLISION: features[high_freq, short_past] → sometimes SHORT (normal),
    sometimes LONG (flipped) → 3LCache can't converge accurately

For 3LCache: contradictory labels in same feature region → prediction uncertainty
  → ranking errors at eviction time.
For LOH: flipped objects are ~3% of recurring → small epoch MR impact → weights stable.

ALL objects 4KB → size can't distinguish.
"""

from __future__ import annotations
import argparse, csv, random
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Feature-Label Flip trace")
    p.add_argument("--output-dir", type=Path, required=True)
    # Object pools
    p.add_argument("--normal-hot-pool", type=int, default=128)
    p.add_argument("--normal-cold-pool", type=int, default=128)
    p.add_argument("--flipped-pool", type=int, default=8)
    p.add_argument("--onehit-pool", type=int, default=4096)
    p.add_argument("--gap-pool", type=int, default=64,
                   help="Small pool of REUSED gap filler objects (keeps MR reasonable)")
    p.add_argument("--obj-size", type=int, default=4096)
    # Per round
    p.add_argument("--hot-per-round", type=int, default=8)
    p.add_argument("--cold-per-round", type=int, default=8)
    p.add_argument("--flipped-per-round", type=int, default=2,
                   help="Flipped objects per round (< flipped_pool)")
    p.add_argument("--burst-count", type=int, default=3)
    p.add_argument("--return-count", type=int, default=2)
    # Gaps
    p.add_argument("--short-gap", type=int, default=100,
                   help="Gap for normal-hot return (SHORT label)")
    p.add_argument("--long-gap", type=int, default=3000,
                   help="Gap for normal-cold AND flipped-hot return (LONG label)")
    # One-hit noise
    p.add_argument("--onehit-per-round", type=int, default=16)
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
    trace_path = args.output_dir / "feature_label_flip.csv"
    summary_path = args.output_dir / "feature_label_flip_summary.md"

    hot_base = 1
    cold_base = hot_base + args.normal_hot_pool
    flipped_base = cold_base + args.normal_cold_pool
    gap_base = flipped_base + args.flipped_pool
    onehit_base = gap_base + args.gap_pool

    rng = random.Random(args.seed)
    comp = Counter()
    time = 1
    hot_cursor = 0
    cold_cursor = 0
    flipped_cursor = 0
    gap_cursor = 0
    onehit_cursor = 0

    with trace_path.open("w", newline="") as f:
        w = csv.writer(f)
        for rnd in range(args.total_rounds):
            hot_ids = [hot_base + ((hot_cursor + i) % args.normal_hot_pool)
                        for i in range(args.hot_per_round)]
            hot_cursor = (hot_cursor + args.hot_per_round) % args.normal_hot_pool

            cold_ids = [cold_base + ((cold_cursor + i) % args.normal_cold_pool)
                         for i in range(args.cold_per_round)]
            cold_cursor = (cold_cursor + args.cold_per_round) % args.normal_cold_pool

            flipped_ids = [flipped_base + ((flipped_cursor + i) % args.flipped_pool)
                            for i in range(args.flipped_per_round)]
            flipped_cursor = (flipped_cursor + args.flipped_per_round) % args.flipped_pool

            # --- Burst: hot + flipped + cold, INTERLEAVED ---
            # Hot and flipped are INDISTINGUISHABLE at burst time
            # Cold objects are also burst here but return later
            all_burst = ([(oid, "hot") for oid in hot_ids] +
                         [(oid, "flipped") for oid in flipped_ids] +
                         [(oid, "cold") for oid in cold_ids])
            rng.shuffle(all_burst)
            for oid, kind in all_burst:
                for _ in range(args.burst_count):
                    time = write_req(w, time, oid, args.obj_size)
                    comp[f"{kind}_burst"] += 1

            # --- Short gap: REUSED filler objects (small pool → most are hits) ---
            for i in range(args.short_gap):
                oid = gap_base + ((gap_cursor + i) % args.gap_pool)
                time = write_req(w, time, oid, args.obj_size)
            gap_cursor = (gap_cursor + args.short_gap) % args.gap_pool
            comp["short_gap"] += args.short_gap

            # --- Short return: ONLY normal-hot, NOT flipped ---
            # Flipped objects DON'T return here (they return after LONG gap)
            for oid in hot_ids:
                for _ in range(args.return_count):
                    time = write_req(w, time, oid, args.obj_size)
                    comp["hot_return"] += 1

            # --- Long gap: REUSED filler objects ---
            for i in range(args.long_gap):
                oid = gap_base + ((gap_cursor + i) % args.gap_pool)
                time = write_req(w, time, oid, args.obj_size)
            gap_cursor = (gap_cursor + args.long_gap) % args.gap_pool
            comp["long_gap"] += args.long_gap

            # --- Long return: normal-cold AND flipped-hot ---
            # KEY: flipped objects return HERE with LONG reuse distance
            # despite having "hot" features (same burst timing as normal-hot)
            long_return = [(oid, "cold") for oid in cold_ids] + \
                          [(oid, "flipped") for oid in flipped_ids]
            rng.shuffle(long_return)
            for oid, kind in long_return:
                for _ in range(args.return_count):
                    time = write_req(w, time, oid, args.obj_size)
                    comp[f"{kind}_return"] += 1

            # --- Extra one-hit ---
            for i in range(args.onehit_per_round):
                oid = onehit_base + ((onehit_cursor + i) % args.onehit_pool)
                time = write_req(w, time, oid, args.obj_size)
            onehit_cursor = (onehit_cursor + args.onehit_per_round) % args.onehit_pool
            comp["onehit_extra"] += args.onehit_per_round

    total_req = time - 1
    total_unique = (args.normal_hot_pool + args.normal_cold_pool +
                    args.flipped_pool + args.gap_pool + args.onehit_pool)
    total_bytes = total_unique * args.obj_size

    # Statistics
    hot_req = comp["hot_burst"] + comp["hot_return"]
    cold_req = comp["cold_burst"] + comp["cold_return"]
    flipped_req = comp["flipped_burst"] + comp["flipped_return"]
    recurring = hot_req + cold_req + flipped_req
    flipped_pct = flipped_req / recurring * 100 if recurring else 0

    with summary_path.open("w") as f:
        f.write("# Feature-Label Flip Trace\n\n")
        f.write("## Object Types\n\n")
        f.write(f"- **Normal-hot** ({args.normal_hot_pool}): burst → short gap({args.short_gap}) → return → SHORT label\n")
        f.write(f"- **Normal-cold** ({args.normal_cold_pool}): burst → long gap({args.long_gap}) → return → LONG label\n")
        f.write(f"- **Flipped** ({args.flipped_pool}): burst like hot → BUT return at long gap({args.long_gap}) → LONG label with HOT features\n\n")
        f.write("## Mechanism\n\n")
        f.write("Flipped objects have SAME burst timing as normal-hot (interleaved)\n")
        f.write("→ same features[short_past, high_freq] at burst time.\n")
        f.write("But their return label is LONG (like cold objects).\n")
        f.write(f"Flipped = {flipped_pct:.1f}% of recurring → small for LOH, but creates\n")
        f.write("feature-space contradiction for 3LCache's GBM.\n\n")
        f.write(f"Stats: {total_req:,} req, {total_unique:,} obj, {total_bytes/1024/1024:.1f} MB\n")
        f.write(f"Flipped recurring: {flipped_pct:.1f}%\n\n")
        f.write("## Mix\n\n| component | count |\n|---|---:|\n")
        for c, n in sorted(comp.items()):
            f.write(f"| {c} | {n:,} |\n")

    return trace_path, summary_path


def main():
    args = parse_args()
    trace_path, summary_path = generate(args)
    print(f"trace={trace_path}")
    print(f"summary={summary_path}")


if __name__ == "__main__":
    main()
