#!/usr/bin/env python3
"""
Frequency-vs-Reuse trace: objects with HIGH frequency but LONG current reuse
(frequent burst objects) vs objects with LOW frequency but SHORT current reuse.

BeladySize (size × current_reuse): penalizes frequent-burst objects
  (long current reuse × large size → high score → evict)
  → loses their MANY future hits → poor MR

LOH: frequency weight captures accumulated value → keeps frequent objects
  → good MR

Key mechanism: BeladySize is STATELESS (only current reuse), LOH is STATEFUL
(accumulated frequency via CMA-ES weights).

Design:
  - "Frequent" objects (N=64, 4KB): burst all together, then ALL return after
    a long gap → HIGH frequency, LONG current reuse (right after burst)
  - "Rare" objects (N=512, 4KB): appear one at a time → LOW frequency,
    SHORT current reuse
  - Gap fillers (256, 4KB): reused
"""

from __future__ import annotations
import argparse, csv, random
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Frequency-vs-Reuse trace")
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--freq-pool", type=int, default=64)
    p.add_argument("--rare-pool", type=int, default=512)
    p.add_argument("--gap-pool", type=int, default=256)
    p.add_argument("--obj-size", type=int, default=4096)
    p.add_argument("--freq-per-round", type=int, default=32)
    p.add_argument("--rare-per-round", type=int, default=16)
    p.add_argument("--burst-count", type=int, default=1)
    p.add_argument("--return-count", type=int, default=1)
    p.add_argument("--short-gap", type=int, default=100)
    p.add_argument("--long-gap", type=int, default=2000)
    p.add_argument("--total-rounds", type=int, default=500)
    p.add_argument("--seed", type=int, default=20260602)
    p.add_argument("--no-plots", action="store_true")
    # Size heterogeneity option
    p.add_argument("--freq-size", type=int, default=4096)
    p.add_argument("--rare-size", type=int, default=4096)
    p.add_argument("--gap-size", type=int, default=4096)
    return p.parse_args()


def write_req(writer, time, oid, sz):
    writer.writerow([time, oid, sz, 0])
    return time + 1


def generate(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / "freq_vs_reuse.csv"
    summary_path = args.output_dir / "freq_vs_reuse_summary.md"

    freq_base = 1
    rare_base = freq_base + args.freq_pool
    gap_base = rare_base + args.rare_pool

    rng = random.Random(args.seed)
    comp = Counter()
    time = 1
    freq_cursor, rare_cursor, gap_cursor = 0, 0, 0
    freq_hits = Counter()

    with trace_path.open("w", newline="") as f:
        w = csv.writer(f)
        for rnd in range(args.total_rounds):
            freq_ids = [freq_base + ((freq_cursor + i) % args.freq_pool)
                         for i in range(args.freq_per_round)]
            freq_cursor = (freq_cursor + args.freq_per_round) % args.freq_pool

            rare_ids = [rare_base + ((rare_cursor + i) % args.rare_pool)
                         for i in range(args.rare_per_round)]
            rare_cursor = (rare_cursor + args.rare_per_round) % args.rare_pool

            # --- Burst: ALL frequent + rare objects, INTERLEAVED ---
            # Frequent objects burst together → their "current reuse" after burst
            # is the time to get through all other burst objects + gap + returns
            all_burst = [(oid, args.freq_size, "freq") for oid in freq_ids] + \
                        [(oid, args.rare_size, "rare") for oid in rare_ids]
            rng.shuffle(all_burst)
            for oid, sz, kind in all_burst:
                for _ in range(args.burst_count):
                    time = write_req(w, time, oid, sz)
                    comp[f"{kind}_burst"] += 1

            # --- Short gap ---
            for i in range(args.short_gap):
                oid = gap_base + ((gap_cursor + i) % args.gap_pool)
                time = write_req(w, time, oid, args.gap_size)
            gap_cursor = (gap_cursor + args.short_gap) % args.gap_pool
            comp["short_gap"] += args.short_gap

            # --- Rare return: short reuse ---
            for oid in rare_ids:
                for _ in range(args.return_count):
                    time = write_req(w, time, oid, args.rare_size)
                    comp["rare_return"] += 1

            # --- Long gap: frequent objects have LONG current reuse ---
            for i in range(args.long_gap):
                oid = gap_base + ((gap_cursor + i) % args.gap_pool)
                time = write_req(w, time, oid, args.gap_size)
            gap_cursor = (gap_cursor + args.long_gap) % args.gap_pool
            comp["long_gap"] += args.long_gap

            # --- Frequent return: LONG reuse, but HIGH accumulated frequency ---
            for oid in freq_ids:
                for _ in range(args.return_count):
                    time = write_req(w, time, oid, args.freq_size)
                    comp["freq_return"] += 1
                    freq_hits[oid] += 1

    total_req = time - 1
    total_unique = args.freq_pool + args.rare_pool + args.gap_pool
    total_bytes = (args.freq_pool * args.freq_size + args.rare_pool * args.rare_size +
                   args.gap_pool * args.gap_size)
    avg_freq_hits = sum(freq_hits.values()) / max(len(freq_hits), 1)

    with summary_path.open("w") as f:
        f.write("# Frequency-vs-Reuse Trace\n\n")
        f.write(f"- Frequent ({args.freq_pool}×{args.freq_size}B): burst together → LONG current reuse(~{args.long_gap}) → HIGH accumulated freq(avg {avg_freq_hits:.0f} hits)\n")
        f.write(f"- Rare ({args.rare_pool}×{args.rare_size}B): burst → SHORT current reuse(~{args.short_gap}) → LOW freq(1 hit)\n")
        f.write(f"- Gap ({args.gap_pool}×{args.gap_size}B): reused filler\n\n")
        f.write("## Expected\n\n")
        f.write("- BeladySize: frequent objects have LONG reuse → high score → EVICT → loses many hits → high MR\n")
        f.write("- LOH: frequency weight captures frequent objects' value → KEEP → low MR\n\n")
        f.write(f"Stats: {total_req:,} req, {total_unique:,} obj, {total_bytes/1024/1024:.1f} MB\n")

    return trace_path, summary_path


def main():
    args = parse_args()
    trace_path, summary_path = generate(args)
    print(f"trace={trace_path}")
    print(f"summary={summary_path}")


if __name__ == "__main__":
    main()
