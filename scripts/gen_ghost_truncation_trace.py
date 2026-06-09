#!/usr/bin/env python3
"""
Generate a "ghost truncation" synthetic trace to test 3LCache vs LOH robustness.

CSV trace format: time,obj-id,obj-size,ttl

Core mechanism:
  3LCache trains on (features, future_label) pairs. Labels come from:
    - Object returns (hit): label = log1p(actual_reuse_distance) ← CORRECT
    - Ghost expiry: label = log1p(MAX_EVICTION_BOUNDARY + waiting_time) ← BIASED (FAR)

  If an object's return gap exceeds ghost cache lifetime, it systematically gets
  FAR labels despite having real future value. 3LCache's converged model is biased.

  LOH uses epoch-level MR feedback — no ghost window → all returns count.

Design:
  - "Quick" objects (4KB): return after SHORT gap (within ghost lifetime)
    → 3LCache gets correct labels → learns to keep them ✓
  - "Slow" objects (1MB): return after LONG gap (beyond ghost lifetime)
    → 3LCache gets FAR labels → learns to evict them ✗
    → But slow objects return REPEATEDLY → sustained value
  - "One-hit" objects: never return → no value

  Optimal OMR policy: keep slow objects (they return) over one-hit objects.
  3LCache can't learn this due to ghost truncation.
  LOH can learn via epoch MR.

Two variants:
  - "ghost_truncated": slow object return gap >> typical ghost lifetime
  - "within_ghost" (control): slow object return gap << ghost lifetime
    → 3LCache gets correct labels → should perform similarly to LOH
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate ghost-truncation trace")
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--variant", type=str, default="ghost_truncated",
                   choices=["ghost_truncated", "within_ghost"])
    # Quick objects: always return quickly
    p.add_argument("--quick-pool", type=int, default=256)
    p.add_argument("--quick-size", type=int, default=4096)
    p.add_argument("--quick-burst", type=int, default=3)
    p.add_argument("--quick-return", type=int, default=2)
    # Slow objects: return after long gap
    p.add_argument("--slow-pool", type=int, default=128)
    p.add_argument("--slow-size", type=int, default=1048576)
    p.add_argument("--slow-burst", type=int, default=1)
    p.add_argument("--slow-return", type=int, default=2)
    # Gap between burst and return
    p.add_argument("--short-gap", type=int, default=256,
                   help="Gap requests between burst and return (quick objects)")
    p.add_argument("--long-gap", type=int, default=15000,
                   help="Gap requests between burst and return (slow objects, ghost_truncated)")
    p.add_argument("--long-gap-control", type=int, default=500,
                   help="Gap for slow objects in within_ghost variant")
    # One-hit objects (noise)
    p.add_argument("--onehit-per-round", type=int, default=128)
    p.add_argument("--onehit-pool", type=int, default=8192)
    p.add_argument("--onehit-size", type=int, default=4096)
    p.add_argument("--onehit-burst", type=int, default=3)
    # Rounds
    p.add_argument("--total-rounds", type=int, default=800,
                   help="Total rounds in the trace")
    # Gap filler
    p.add_argument("--gap-pool", type=int, default=256)
    p.add_argument("--gap-size", type=int, default=16384)
    # Seed
    p.add_argument("--seed", type=int, default=20260601)
    p.add_argument("--no-plots", action="store_true")
    return p.parse_args()


def write_req(writer, time: int, obj_id: int, obj_size: int) -> int:
    writer.writerow([time, obj_id, obj_size, 0])
    return time + 1


def generate(args: argparse.Namespace) -> tuple:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / f"ghost_truncation_{args.variant}.csv"
    summary_path = args.output_dir / f"ghost_truncation_{args.variant}_summary.md"

    # Object ID ranges
    quick_base = 1
    slow_base = quick_base + args.quick_pool
    onehit_base = slow_base + args.slow_pool
    gap_base = onehit_base + args.onehit_pool

    # Determine slow gap based on variant
    slow_gap = (args.long_gap if args.variant == "ghost_truncated"
                else args.long_gap_control)

    component_counts: Counter = Counter()
    time = 1
    quick_cursor = 0
    slow_cursor = 0
    onehit_cursor = 0
    gap_cursor = 0

    # Pre-generate slow object schedule:
    # Slow objects appear every N rounds so that their inter-arrival gap
    # exceeds ghost lifetime. They burst and return in the SAME round,
    # but their NEXT appearance is many rounds later.
    slow_round_interval = max(1, args.slow_pool // 4)  # each slow obj appears every N rounds
    slow_per_round = max(1, args.slow_pool // slow_round_interval)

    with trace_path.open("w", newline="") as f:
        writer = csv.writer(f)

        for rnd in range(args.total_rounds):
            # --- Quick objects: burst ---
            quick_ids = [
                quick_base + ((quick_cursor + i) % args.quick_pool)
                for i in range(slow_per_round * 2)  # more quick than slow
            ]
            quick_cursor = (quick_cursor + len(quick_ids)) % args.quick_pool

            for oid in quick_ids:
                for _ in range(args.quick_burst):
                    time = write_req(writer, time, oid, args.quick_size)
                    component_counts["quick_burst"] += 1

            # --- Slow objects: burst ---
            slow_ids = [
                slow_base + ((slow_cursor + i) % args.slow_pool)
                for i in range(slow_per_round)
            ]
            slow_cursor = (slow_cursor + len(slow_ids)) % args.slow_pool

            for oid in slow_ids:
                for _ in range(args.slow_burst):
                    time = write_req(writer, time, oid, args.slow_size)
                    component_counts["slow_burst"] += 1

            # --- Short gap filler (reused objects) ---
            gap_n = args.short_gap
            gap_ids_list = [
                gap_base + ((gap_cursor + i) % args.gap_pool)
                for i in range(gap_n)
            ]
            gap_cursor = (gap_cursor + gap_n) % args.gap_pool
            for oid in gap_ids_list:
                time = write_req(writer, time, oid, args.gap_size)
                component_counts["short_gap"] += 1

            # --- Quick objects: return ---
            for oid in quick_ids:
                for _ in range(args.quick_return):
                    time = write_req(writer, time, oid, args.quick_size)
                    component_counts["quick_return"] += 1

            # --- One-hit objects: burst (noise, never return) ---
            onehit_ids = [
                onehit_base + ((onehit_cursor + i) % args.onehit_pool)
                for i in range(args.onehit_per_round)
            ]
            onehit_cursor = (onehit_cursor + len(onehit_ids)) % args.onehit_pool
            for oid in onehit_ids:
                for _ in range(args.onehit_burst):
                    time = write_req(writer, time, oid, args.onehit_size)
                    component_counts["onehit_burst"] += 1

            # --- Long gap filler (reused) ---
            gap_n2 = slow_gap
            gap_ids_list2 = [
                gap_base + ((gap_cursor + i) % args.gap_pool)
                for i in range(gap_n2)
            ]
            gap_cursor = (gap_cursor + gap_n2) % args.gap_pool
            for oid in gap_ids_list2:
                time = write_req(writer, time, oid, args.gap_size)
                component_counts["long_gap"] += 1

            # --- Slow objects: return (after long gap) ---
            for oid in slow_ids:
                for _ in range(args.slow_return):
                    time = write_req(writer, time, oid, args.slow_size)
                    component_counts["slow_return"] += 1

    total_req = time - 1

    # Summary
    total_unique = args.quick_pool + args.slow_pool + args.onehit_pool + args.gap_pool
    total_bytes = (args.quick_pool * args.quick_size +
                   args.slow_pool * args.slow_size +
                   args.onehit_pool * args.onehit_size +
                   args.gap_pool * args.gap_size)
    req_per_round = (len(quick_ids) * args.quick_burst +
                     len(slow_ids) * args.slow_burst +
                     args.short_gap +
                     len(quick_ids) * args.quick_return +
                     args.onehit_per_round * args.onehit_burst +
                     slow_gap +
                     len(slow_ids) * args.slow_return)
    quick_round_interval = args.quick_pool / len(quick_ids)
    slow_round_interval_val = args.slow_pool / len(slow_ids)
    quick_inter_arrival = quick_round_interval * req_per_round
    slow_inter_arrival = slow_round_interval_val * req_per_round

    with summary_path.open("w") as f:
        f.write("# Ghost Truncation Trace\n\n")
        f.write(f"**Variant**: `{args.variant}`\n\n")
        f.write("## Design\n\n")
        f.write("- **Quick objects** (4KB): burst → short gap → return. ")
        f.write("Inter-arrival ≈ {:.0f} req. Within ghost lifetime.\n".format(quick_inter_arrival))
        f.write("- **Slow objects** (1MB): burst → LONG gap → return. ")
        f.write("Inter-arrival ≈ {:.0f} req. ".format(slow_inter_arrival))
        if args.variant == "ghost_truncated":
            f.write("**Exceeds ghost lifetime** → 3LCache labels systematically biased.\n")
        else:
            f.write("Within ghost lifetime → 3LCache gets correct labels (control).\n")
        f.write("- **One-hit objects**: burst, never return → pure noise.\n\n")
        f.write("## Mechanism\n\n")
        f.write("3LCache training labels:\n")
        f.write("- Object returns → label = log1p(actual_reuse_distance) ← CORRECT\n")
        f.write("- Ghost expiry → label = log1p(MAX_EVICTION_BOUNDARY + waiting_time) ← FAR (biased)\n\n")
        if args.variant == "ghost_truncated":
            f.write("Slow objects' return gap exceeds ghost lifetime:\n")
            f.write("- 3LCache always labels slow objects as FAR → model learns to evict them\n")
            f.write("- But slow objects return repeatedly → sustained value → 3LCache is WRONG\n")
            f.write("- LOH gets epoch MR feedback including slow object returns → can learn value\n")
        else:
            f.write("Slow objects return within ghost lifetime:\n")
            f.write("- 3LCache gets correct labels → learns correctly\n")
            f.write("- Both algorithms should perform similarly\n")
        f.write("\n## Statistics\n\n")
        f.write(f"- Total requests: {total_req:,}\n")
        f.write(f"- Total rounds: {args.total_rounds}\n")
        f.write(f"- Requests per round: {req_per_round}\n")
        f.write(f"- Total unique objects: {total_unique:,}\n")
        f.write(f"- Total unique bytes: {total_bytes:,} ({total_bytes/1024/1024:.1f} MB)\n")
        f.write(f"- Quick inter-arrival: {quick_inter_arrival:.0f} req\n")
        f.write(f"- Slow inter-arrival: {slow_inter_arrival:.0f} req\n")
        f.write(f"- Slow return gap: {slow_gap} req\n\n")
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
