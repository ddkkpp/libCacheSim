#!/usr/bin/env python3
"""
Size-Tiered Return Swap: combines heterogeneous sizes with temporal perturbation.

Design:
  - Small objects (4KB, N=128): normally return at SHORT gap → SHORT label
  - Large objects (1MB, N=128): normally return at LONG gap → LONG label
  - SWAP: swap_frac of small↔large return positions each round
    → Small with LONG label, Large with SHORT label
    → Feature-label collision in BOTH size tiers

Prediction:
  - Clean (0% swap): LOH beats 3LCache (size-tiebreak baseline)
  - Swapped (>0%): 3LCache degrades MORE than LOH → gap widens
"""

from __future__ import annotations
import argparse, csv, random
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Size-Tiered Return Swap trace")
    p.add_argument("--output-dir", type=Path, required=True)
    # Object pools
    p.add_argument("--small-pool", type=int, default=128)
    p.add_argument("--large-pool", type=int, default=128)
    p.add_argument("--small-size", type=int, default=4096)
    p.add_argument("--large-size", type=int, default=1048576)
    # Per round
    p.add_argument("--small-per-round", type=int, default=16)
    p.add_argument("--large-per-round", type=int, default=16)
    p.add_argument("--burst-count", type=int, default=3)
    p.add_argument("--return-count", type=int, default=2)
    # Return gaps
    p.add_argument("--short-gap", type=int, default=100)
    p.add_argument("--long-gap", type=int, default=2000)
    # Swap
    p.add_argument("--swap-frac", type=float, default=0.0)
    # Gap fillers
    p.add_argument("--gap-pool", type=int, default=256)
    p.add_argument("--gap-size", type=int, default=16384)
    # One-hit noise
    p.add_argument("--onehit-pool", type=int, default=2048)
    p.add_argument("--onehit-size", type=int, default=4096)
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
    trace_path = args.output_dir / f"size_tiered_swap_{tag}.csv"
    summary_path = args.output_dir / f"size_tiered_swap_{tag}_summary.md"

    small_base = 1
    large_base = small_base + args.small_pool
    gap_base = large_base + args.large_pool
    onehit_base = gap_base + args.gap_pool

    rng = random.Random(args.seed)
    comp = Counter()
    time = 1
    small_cursor, large_cursor = 0, 0
    gap_cursor, onehit_cursor = 0, 0
    n_swapped = 0
    n_total = 0

    with trace_path.open("w", newline="") as f:
        w = csv.writer(f)
        for rnd in range(args.total_rounds):
            small_ids = [small_base + ((small_cursor + i) % args.small_pool)
                          for i in range(args.small_per_round)]
            small_cursor = (small_cursor + args.small_per_round) % args.small_pool

            large_ids = [large_base + ((large_cursor + i) % args.large_pool)
                          for i in range(args.large_per_round)]
            large_cursor = (large_cursor + args.large_per_round) % args.large_pool

            n_total += args.small_per_round + args.large_per_round

            # Swap decisions
            swapped_small, swapped_large = set(), set()
            if args.swap_frac > 0:
                n_swap = int(min(args.small_per_round, args.large_per_round) * args.swap_frac)
                if n_swap > 0:
                    swapped_small = set(rng.sample(small_ids, n_swap))
                    swapped_large = set(rng.sample(large_ids, n_swap))
                    n_swapped += n_swap * 2

            # --- Burst: small + large interleaved ---
            all_burst = ([(oid, "small", args.small_size) for oid in small_ids] +
                         [(oid, "large", args.large_size) for oid in large_ids])
            rng.shuffle(all_burst)
            for oid, kind, sz in all_burst:
                for _ in range(args.burst_count):
                    time = write_req(w, time, oid, sz)
                    comp[f"{kind}_burst"] += 1

            # --- Short gap ---
            for i in range(args.short_gap):
                oid = gap_base + ((gap_cursor + i) % args.gap_pool)
                time = write_req(w, time, oid, args.gap_size)
            gap_cursor = (gap_cursor + args.short_gap) % args.gap_pool
            comp["short_gap"] += args.short_gap

            # --- Short return: normal-small + swapped-large ---
            short_return = ([(oid, args.small_size) for oid in small_ids if oid not in swapped_small] +
                            [(oid, args.large_size) for oid in large_ids if oid in swapped_large])
            rng.shuffle(short_return)
            for oid, sz in short_return:
                for _ in range(args.return_count):
                    time = write_req(w, time, oid, sz)
                    comp["short_return"] += 1

            # --- Long gap ---
            for i in range(args.long_gap):
                oid = gap_base + ((gap_cursor + i) % args.gap_pool)
                time = write_req(w, time, oid, args.gap_size)
            gap_cursor = (gap_cursor + args.long_gap) % args.gap_pool
            comp["long_gap"] += args.long_gap

            # --- Long return: normal-large + swapped-small ---
            long_return = ([(oid, args.large_size) for oid in large_ids if oid not in swapped_large] +
                           [(oid, args.small_size) for oid in small_ids if oid in swapped_small])
            rng.shuffle(long_return)
            for oid, sz in long_return:
                for _ in range(args.return_count):
                    time = write_req(w, time, oid, sz)
                    comp["long_return"] += 1

            # --- One-hit noise ---
            for i in range(args.onehit_per_round):
                oid = onehit_base + ((onehit_cursor + i) % args.onehit_pool)
                time = write_req(w, time, oid, args.onehit_size)
            onehit_cursor = (onehit_cursor + args.onehit_per_round) % args.onehit_pool
            comp["onehit"] += args.onehit_per_round

    total_req = time - 1
    total_unique = args.small_pool + args.large_pool + args.gap_pool + args.onehit_pool
    total_bytes = (args.small_pool * args.small_size + args.large_pool * args.large_size +
                   args.gap_pool * args.gap_size + args.onehit_pool * args.onehit_size)
    swap_pct = n_swapped / n_total * 100 if n_total else 0

    with summary_path.open("w") as f:
        f.write("# Size-Tiered Return Swap Trace\n\n")
        f.write(f"**Swap fraction**: {args.swap_frac} ({swap_pct:.1f}% of appearances)\n\n")
        f.write("## Design\n\n")
        f.write(f"- Small ({args.small_pool}×{args.small_size}B): normal gap={args.short_gap} → SHORT\n")
        f.write(f"- Large ({args.large_pool}×{args.large_size/1024/1024:.0f}MB): normal gap={args.long_gap} → LONG\n")
        if args.swap_frac > 0:
            f.write(f"- SWAP {swap_pct:.1f}%: small→LONG gap, large→SHORT gap\n")
        f.write("\n## Prediction\n\n")
        f.write("- Clean: LOH beats 3LCache (size-tiebreak baseline)\n")
        f.write("- Swapped: 3LCache degrades MORE → gap widens\n")
        f.write(f"\nStats: {total_req:,} req, {total_unique:,} obj, {total_bytes/1024/1024:.1f} MB\n")

    return trace_path, summary_path


def main():
    args = parse_args()
    trace_path, summary_path = generate(args)
    print(f"trace={trace_path}")
    print(f"summary={summary_path}")


if __name__ == "__main__":
    main()
