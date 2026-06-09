#!/usr/bin/env python3
"""
Proxy-gap trace: demonstrate that Belady (reuse distance oracle) and
BeladySize (size*reuse oracle) can be suboptimal, proving the gap between
reuse-distance prediction and optimal eviction.

Belady (MIN): optimal for OMR, but poor for BMR (ignores size).
BeladySize (size * reuse): heuristic → can be beaten on BOTH OMR and BMR.

Key scenario for BeladySize failure:
  - "Steady" large objects (1MB): long next reuse but MANY future returns
  - "Flash" small objects (4KB): short next reuse but ONE-TIME
  - BeladySize over-penalizes steady objects (large * long_reuse >> small * short_reuse)
  - Optimal: keep steady objects (many hits), evict flash objects (one hit done)

Design:
  - Steady objects (N=32, 1MB): appear every K rounds, return every round in between
    → many hits over the trace → HIGH total value, MODERATE next reuse
  - Flash objects (N=1024, 4KB): appear once, return once after gap → ONE hit
    → LOW total value, SHORT next reuse
  - Gap fillers (4KB, reused): background noise
"""

from __future__ import annotations
import argparse, csv, random
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Proxy-gap demonstration trace")
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--steady-pool", type=int, default=32)
    p.add_argument("--steady-size", type=int, default=1048576)
    p.add_argument("--flash-pool", type=int, default=1024)
    p.add_argument("--flash-size", type=int, default=4096)
    p.add_argument("--gap-pool", type=int, default=128)
    p.add_argument("--gap-size", type=int, default=4096)
    p.add_argument("--steady-per-round", type=int, default=4)
    p.add_argument("--flash-per-round", type=int, default=32)
    p.add_argument("--burst-count", type=int, default=1)
    p.add_argument("--return-count", type=int, default=1)
    p.add_argument("--flash-gap", type=int, default=50)
    p.add_argument("--steady-interval", type=int, default=200,
                   help="Steady objects return every N requests between gaps")
    p.add_argument("--gap-per-round", type=int, default=100)
    p.add_argument("--total-rounds", type=int, default=500)
    p.add_argument("--seed", type=int, default=20260602)
    p.add_argument("--no-plots", action="store_true")
    return p.parse_args()


def write_req(writer, time, oid, sz):
    writer.writerow([time, oid, sz, 0])
    return time + 1


def generate(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / "proxy_gap.csv"
    summary_path = args.output_dir / "proxy_gap_summary.md"

    steady_base = 1
    flash_base = steady_base + args.steady_pool
    gap_base = flash_base + args.flash_pool

    rng = random.Random(args.seed)
    comp = Counter()
    time = 1
    steady_cursor, flash_cursor, gap_cursor = 0, 0, 0

    # Steady objects: accumulate many returns
    steady_hits = Counter()

    with trace_path.open("w", newline="") as f:
        w = csv.writer(f)
        for rnd in range(args.total_rounds):
            steady_ids = [steady_base + ((steady_cursor + i) % args.steady_pool)
                           for i in range(args.steady_per_round)]
            steady_cursor = (steady_cursor + args.steady_per_round) % args.steady_pool

            flash_ids = [flash_base + ((flash_cursor + i) % args.flash_pool)
                          for i in range(args.flash_per_round)]
            flash_cursor = (flash_cursor + args.flash_per_round) % args.flash_pool

            # --- Burst: steady + flash ---
            all_burst = [(oid, args.steady_size, "steady") for oid in steady_ids] + \
                        [(oid, args.flash_size, "flash") for oid in flash_ids]
            rng.shuffle(all_burst)
            for oid, sz, kind in all_burst:
                for _ in range(args.burst_count):
                    time = write_req(w, time, oid, sz)
                    comp[f"{kind}_burst"] += 1

            # --- Short gap ---
            for i in range(args.flash_gap):
                oid = gap_base + ((gap_cursor + i) % args.gap_pool)
                time = write_req(w, time, oid, args.gap_size)
            gap_cursor = (gap_cursor + args.flash_gap) % args.gap_pool
            comp["short_gap"] += args.flash_gap

            # --- Flash return: one-time hits ---
            rng.shuffle(flash_ids)
            for oid in flash_ids:
                for _ in range(args.return_count):
                    time = write_req(w, time, oid, args.flash_size)
                    comp["flash_return"] += 1

            # --- Steady returns: repeated hits over interval ---
            # Steady objects return multiple times, spread across the interval
            n_returns = args.steady_interval // 50  # ~4 returns per steady object
            for ret in range(n_returns):
                gap_n = max(10, args.steady_interval // n_returns)
                for i in range(gap_n):
                    oid = gap_base + ((gap_cursor + i) % args.gap_pool)
                    time = write_req(w, time, oid, args.gap_size)
                gap_cursor = (gap_cursor + gap_n) % args.gap_pool
                comp["steady_gap"] += gap_n

                for oid in steady_ids:
                    for _ in range(args.return_count):
                        time = write_req(w, time, oid, args.steady_size)
                        comp["steady_return"] += 1
                        steady_hits[oid] += 1

            # --- More gap ---
            for i in range(args.gap_per_round):
                oid = gap_base + ((gap_cursor + i) % args.gap_pool)
                time = write_req(w, time, oid, args.gap_size)
            gap_cursor = (gap_cursor + args.gap_per_round) % args.gap_pool
            comp["end_gap"] += args.gap_per_round

    total_req = time - 1
    total_unique = args.steady_pool + args.flash_pool + args.gap_pool
    total_bytes = (args.steady_pool * args.steady_size + args.flash_pool * args.flash_size +
                   args.gap_pool * args.gap_size)
    avg_steady_hits = sum(steady_hits.values()) / len(steady_hits) if steady_hits else 0

    with summary_path.open("w") as f:
        f.write("# Proxy-Gap Demonstration Trace\n\n")
        f.write(f"- Steady ({args.steady_pool}×{args.steady_size/1024/1024:.0f}MB): avg {avg_steady_hits:.0f} hits each\n")
        f.write(f"- Flash ({args.flash_pool}×{args.flash_size}B): 1 hit each\n")
        f.write(f"- Gap ({args.gap_pool}×{args.gap_size}B): reused filler\n\n")
        f.write("## Expected Oracle Behavior\n\n")
        f.write("- Belady (MIN): optimal OMR → should win OMR, poor BMR\n")
        f.write("- BeladySize (size*reuse): penalizes large steady objects → evicts them → poor OMR\n")
        f.write("- LOH: learns steady=valuable via size+freq weights → good OMR+BMR\n\n")
        f.write(f"Stats: {total_req:,} req, {total_unique:,} obj, {total_bytes/1024/1024:.1f} MB\n")

    return trace_path, summary_path


def main():
    args = parse_args()
    trace_path, summary_path = generate(args)
    print(f"trace={trace_path}")
    print(f"summary={summary_path}")


if __name__ == "__main__":
    main()
