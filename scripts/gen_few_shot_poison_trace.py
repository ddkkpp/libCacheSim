#!/usr/bin/env python3
"""
Few-shot poison trace v2: probabilistic poison returns.

Key difference from v1: poison objects RETURN with probability p (e.g., 0.3),
not "never return". This means:
  - Poison training samples come from BOTH hit path (SHORT, when they return)
    and ghost expiry (FAR, when they don't)
  - Labels for poison objects are MIXED → genuine feature-label ambiguity
  - 3LCache sees: same features, sometimes SHORT, sometimes FAR → can't converge
  - But the POISON RATIO is low → LOH's epoch MR barely shifts

Design:
  - Hot (N=128): 4KB, burst 3, ALWAYS return → clean SHORT labels
  - Poison (M=8): 4KB, burst 3, return with prob p → MIXED labels
  - One-hit: 4KB, burst 3, never return → FAR labels (background)
  - Burst interleaved → identical access patterns at burst time
  - No fillers → all objects 4KB → size can't distinguish
"""

from __future__ import annotations
import argparse, csv, random
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Few-shot poison trace v2")
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--hot-pool", type=int, default=128)
    p.add_argument("--poison-pool", type=int, default=8)
    p.add_argument("--onehit-pool", type=int, default=4096)
    p.add_argument("--obj-size", type=int, default=4096)
    p.add_argument("--hot-per-round", type=int, default=16)
    p.add_argument("--poison-per-round", type=int, default=4)
    p.add_argument("--onehit-per-round", type=int, default=32)
    p.add_argument("--burst-count", type=int, default=3)
    p.add_argument("--return-count", type=int, default=2)
    p.add_argument("--return-gap", type=int, default=200)
    p.add_argument("--poison-return-prob", type=float, default=0.3,
                   help="Probability a poison object returns (0=never, 1=always)")
    p.add_argument("--total-rounds", type=int, default=2000)
    p.add_argument("--seed", type=int, default=20260602)
    p.add_argument("--no-plots", action="store_true")
    return p.parse_args()


def write_req(writer, time, oid, sz):
    writer.writerow([time, oid, sz, 0])
    return time + 1


def generate(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / "few_shot_poison.csv"
    summary_path = args.output_dir / "few_shot_poison_summary.md"

    hot_base = 1
    poison_base = hot_base + args.hot_pool
    onehit_base = poison_base + args.poison_pool

    rng = random.Random(args.seed)
    comp = Counter()
    time = 1
    hot_cursor = 0
    poison_cursor = 0
    onehit_cursor = 0

    with trace_path.open("w", newline="") as f:
        w = csv.writer(f)
        for rnd in range(args.total_rounds):
            hot_ids = [hot_base + ((hot_cursor + i) % args.hot_pool)
                        for i in range(args.hot_per_round)]
            hot_cursor = (hot_cursor + args.hot_per_round) % args.hot_pool

            poison_ids = [poison_base + ((poison_cursor + i) % args.poison_pool)
                           for i in range(args.poison_per_round)]
            poison_cursor = (poison_cursor + args.poison_per_round) % args.poison_pool

            # Determine which poison objects return (probabilistic)
            returning_poison = [oid for oid in poison_ids
                                if rng.random() < args.poison_return_prob]

            # --- Burst: interleave hot + poison (INDISTINGUISHABLE at burst time) ---
            all_burst = [(oid, "hot") for oid in hot_ids] + [(oid, "poison") for oid in poison_ids]
            rng.shuffle(all_burst)
            for oid, kind in all_burst:
                for _ in range(args.burst_count):
                    time = write_req(w, time, oid, args.obj_size)
                    comp[f"{kind}_burst"] += 1

            # --- Gap: one-hit requests ---
            gap_ids = [onehit_base + ((onehit_cursor + i) % args.onehit_pool)
                        for i in range(args.return_gap)]
            onehit_cursor = (onehit_cursor + args.return_gap) % args.onehit_pool
            for oid in gap_ids:
                time = write_req(w, time, oid, args.obj_size)
                comp["gap_onehit"] += 1

            # --- Return: hot ALWAYS, poison PROBABILISTIC ---
            returning_all = [(oid, "hot") for oid in hot_ids] + \
                            [(oid, "poison") for oid in returning_poison]
            rng.shuffle(returning_all)
            for oid, kind in returning_all:
                for _ in range(args.return_count):
                    time = write_req(w, time, oid, args.obj_size)
                    comp[f"{kind}_return"] += 1

            # --- Extra one-hit noise ---
            extra_ids = [onehit_base + ((onehit_cursor + i) % args.onehit_pool)
                          for i in range(args.onehit_per_round)]
            onehit_cursor = (onehit_cursor + args.onehit_per_round) % args.onehit_pool
            for oid in extra_ids:
                time = write_req(w, time, oid, args.obj_size)
                comp["onehit_extra"] += 1

    total_req = time - 1
    total_unique = args.hot_pool + args.poison_pool + args.onehit_pool
    total_bytes = total_unique * args.obj_size

    hot_req = comp["hot_burst"] + comp["hot_return"]
    poison_req = comp["poison_burst"] + comp["poison_return"]
    poison_pct = poison_req / (hot_req + poison_req) * 100 if (hot_req + poison_req) else 0

    with summary_path.open("w") as f:
        f.write("# Few-Shot Poison Trace v2 (Probabilistic)\n\n")
        f.write(f"- Hot ({args.hot_pool}): ALWAYS return → clean SHORT labels\n")
        f.write(f"- Poison ({args.poison_pool}): return prob={args.poison_return_prob} → MIXED labels\n")
        f.write(f"- ALL {args.obj_size}B → size can't distinguish\n")
        f.write(f"- Poison recurring ratio: {poison_pct:.1f}%\n\n")
        f.write("## Mechanism\n\n")
        f.write("Poison objects' LABELS are mixed (SHORT when they return, FAR when they don't).\n")
        f.write("Same features → different labels → 3LCache can't predict accurately.\n")
        f.write(f"Poison is {poison_pct:.1f}% of recurring → small impact on LOH epoch MR.\n\n")
        f.write(f"Stats: {total_req:,} req, {total_unique:,} obj, {total_bytes/1024/1024:.1f} MB\n")

    return trace_path, summary_path


def main():
    args = parse_args()
    trace_path, summary_path = generate(args)
    print(f"trace={trace_path}")
    print(f"summary={summary_path}")


if __name__ == "__main__":
    main()
