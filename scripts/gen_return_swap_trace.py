#!/usr/bin/env python3
"""
Return-position swap trace: SWAP the return timing of a FEW objects
without changing the total trace structure.

Core mechanism:
  - Objects have two natural return gaps: "short" (hot) and "long" (cold)
  - For a SMALL fraction of appearances, SWAP the return gap:
    hot object → returns at LONG gap (label becomes LONG)
    cold object → returns at SHORT gap (label becomes SHORT)
  - The burst features are IDENTICAL → feature-label collision
  - Total trace length unchanged → clean comparison

Design:
  - Hot objects (N=128): normally return at SHORT gap → SHORT label
  - Cold objects (N=128): normally return at LONG gap → LONG label
  - For swap_frac of appearances: hot↔cold return positions are SWAPPED
  - All objects 4KB → size doesn't confound
  - Gap fillers: small reused pool for reasonable baseline MR

Prediction:
  - swap_frac=0 (clean): 3LCache learns correctly → 3LCache ≈ LOH
  - swap_frac>0 (perturbed): feature-label collision → 3LCache < LOH
"""

from __future__ import annotations
import argparse, csv, random
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Return-swap trace")
    p.add_argument("--output-dir", type=Path, required=True)
    # Object pools
    p.add_argument("--hot-pool", type=int, default=128)
    p.add_argument("--cold-pool", type=int, default=128)
    p.add_argument("--obj-size", type=int, default=4096)
    # Per round
    p.add_argument("--hot-per-round", type=int, default=16)
    p.add_argument("--cold-per-round", type=int, default=16)
    p.add_argument("--burst-count", type=int, default=3)
    p.add_argument("--return-count", type=int, default=2)
    # Return gaps
    p.add_argument("--short-gap", type=int, default=100)
    p.add_argument("--long-gap", type=int, default=2000)
    # Swap fraction
    p.add_argument("--swap-frac", type=float, default=0.0,
                   help="Fraction of hot objects whose return is swapped to long gap "
                        "(same fraction of cold objects swapped to short gap)")
    # Gap fillers
    p.add_argument("--gap-pool", type=int, default=256)
    p.add_argument("--gap-size", type=int, default=4096)
    # One-hit noise
    p.add_argument("--onehit-pool", type=int, default=2048)
    p.add_argument("--onehit-per-round", type=int, default=32)
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
    tag = f"swap{int(args.swap_frac*100)}"
    trace_path = args.output_dir / f"return_swap_{tag}.csv"
    summary_path = args.output_dir / f"return_swap_{tag}_summary.md"

    hot_base = 1
    cold_base = hot_base + args.hot_pool
    gap_base = cold_base + args.cold_pool
    onehit_base = gap_base + args.gap_pool

    rng = random.Random(args.seed)
    comp = Counter()
    time = 1
    hot_cursor, cold_cursor = 0, 0
    gap_cursor, onehit_cursor = 0, 0
    n_swapped = 0
    n_total = 0

    with trace_path.open("w", newline="") as f:
        w = csv.writer(f)
        for rnd in range(args.total_rounds):
            hot_ids = [hot_base + ((hot_cursor + i) % args.hot_pool)
                        for i in range(args.hot_per_round)]
            hot_cursor = (hot_cursor + args.hot_per_round) % args.hot_pool

            cold_ids = [cold_base + ((cold_cursor + i) % args.cold_pool)
                         for i in range(args.cold_per_round)]
            cold_cursor = (cold_cursor + args.cold_per_round) % args.cold_pool

            n_total += args.hot_per_round + args.cold_per_round

            # Decide which hot objects get SWAPPED to long gap
            swapped_hot = set()
            swapped_cold = set()
            if args.swap_frac > 0:
                n_swap_hot = int(args.hot_per_round * args.swap_frac)
                n_swap_cold = int(args.cold_per_round * args.swap_frac)
                # Swap equal numbers
                n_swap = min(n_swap_hot, n_swap_cold)
                swapped_hot = set(rng.sample(hot_ids, n_swap))
                swapped_cold = set(rng.sample(cold_ids, n_swap))
                n_swapped += n_swap * 2  # both hot and cold

            # --- Burst: hot + cold interleaved ---
            all_burst = [(oid, "hot") for oid in hot_ids] + [(oid, "cold") for oid in cold_ids]
            rng.shuffle(all_burst)
            for oid, kind in all_burst:
                for _ in range(args.burst_count):
                    time = write_req(w, time, oid, args.obj_size)
                    comp[f"{kind}_burst"] += 1

            # --- Short gap ---
            for i in range(args.short_gap):
                oid = gap_base + ((gap_cursor + i) % args.gap_pool)
                time = write_req(w, time, oid, args.gap_size)
            gap_cursor = (gap_cursor + args.short_gap) % args.gap_pool
            comp["short_gap"] += args.short_gap

            # --- Short return: normal-hot (not swapped) + swapped-cold ---
            # Normal hot returns at short gap (correct for "hot" features)
            # Swapped cold ALSO returns here (incorrect for "cold" features → creates contradiction)
            short_return = ([oid for oid in hot_ids if oid not in swapped_hot] +
                            [oid for oid in cold_ids if oid in swapped_cold])
            rng.shuffle(short_return)
            for oid in short_return:
                for _ in range(args.return_count):
                    time = write_req(w, time, oid, args.obj_size)
                    comp["short_return"] += 1

            # --- Long gap ---
            for i in range(args.long_gap):
                oid = gap_base + ((gap_cursor + i) % args.gap_pool)
                time = write_req(w, time, oid, args.gap_size)
            gap_cursor = (gap_cursor + args.long_gap) % args.gap_pool
            comp["long_gap"] += args.long_gap

            # --- Long return: normal-cold (not swapped) + swapped-hot ---
            # Normal cold returns at long gap (correct for "cold" features)
            # Swapped hot returns HERE (incorrect for "hot" features → creates contradiction)
            long_return = ([oid for oid in cold_ids if oid not in swapped_cold] +
                           [oid for oid in hot_ids if oid in swapped_hot])
            rng.shuffle(long_return)
            for oid in long_return:
                for _ in range(args.return_count):
                    time = write_req(w, time, oid, args.obj_size)
                    comp["long_return"] += 1

            # --- One-hit noise ---
            for i in range(args.onehit_per_round):
                oid = onehit_base + ((onehit_cursor + i) % args.onehit_pool)
                time = write_req(w, time, oid, args.obj_size)
            onehit_cursor = (onehit_cursor + args.onehit_per_round) % args.onehit_pool
            comp["onehit"] += args.onehit_per_round

    total_req = time - 1
    total_unique = args.hot_pool + args.cold_pool + args.gap_pool + args.onehit_pool
    total_bytes = (args.hot_pool + args.cold_pool + args.onehit_pool) * args.obj_size + args.gap_pool * args.gap_size
    swap_pct = n_swapped / n_total * 100 if n_total else 0

    with summary_path.open("w") as f:
        f.write("# Return-Position Swap Trace\n\n")
        f.write(f"**Swap fraction**: {args.swap_frac} ({swap_pct:.1f}% of appearances)\n\n")
        f.write("## Design\n\n")
        f.write(f"- Hot ({args.hot_pool}): normally return at short gap ({args.short_gap}) → SHORT label\n")
        f.write(f"- Cold ({args.cold_pool}): normally return at long gap ({args.long_gap}) → LONG label\n")
        if args.swap_frac > 0:
            f.write(f"- SWAP: {swap_pct:.1f}% have return positions exchanged\n")
            f.write("  - Swapped hot → return at LONG gap (LONG label with 'hot' features)\n")
            f.write("  - Swapped cold → return at SHORT gap (SHORT label with 'cold' features)\n\n")
            f.write("## Mechanism\n\n")
            f.write("Swapped objects have SAME burst features as normal objects\n")
            f.write("(same frequency trend, same interleaved burst timing)\n")
            f.write("but OPPOSITE return label. This creates feature-label collision:\n")
            f.write("hot-like features → sometimes SHORT (normal), sometimes LONG (swapped).\n")
            f.write(f"Swapped = {swap_pct:.1f}% → small LOH epoch MR impact.\n\n")
        f.write(f"Stats: {total_req:,} req, {total_unique:,} obj, {total_bytes/1024/1024:.1f} MB\n")
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
