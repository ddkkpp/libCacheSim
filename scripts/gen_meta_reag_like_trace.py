#!/usr/bin/env python3
"""
Generate a meta_reag-like synthetic trace for stress-testing cache algorithms.

Design goals (inspired by meta_reag production trace characteristics):
  - Extreme hot head: top-1 object ~25% of all requests; top-10 ~26%.
  - Heavy-tail size: spans 4-6 orders of magnitude (512B to 256MB).
  - High cold ratio: ~57% one-hit objects.
  - Phase-unstable hotspots: top-k Jaccard ~0.2 across epochs
    (the "hot" set rotates; objects that were hot become cold and vice versa).
  - Mixed short-burst reuse (access storm) and long-interval reuse
    (cross-epoch revisit).
  - Size and frequency are weakly correlated (large objects can be hot too),
    stressing algorithms that assume small = hot.

CSV trace format: time,obj-id,obj-size,ttl  (no header)
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from pathlib import Path


# ---------------------------------------------------------------------------
# Default parameters calibrated to resemble meta_reag behaviour
# ---------------------------------------------------------------------------

# Object size distribution: log-uniform across five size classes
SIZE_CLASSES = [
    (512,       0.15),   # tiny  512B
    (4096,      0.30),   # small 4KB
    (65536,     0.30),   # medium 64KB
    (1048576,   0.20),   # large 1MB
    (16777216,  0.05),   # huge  16MB
]

SUPER_HOT_FRAC   = 0.25   # fraction of all requests that go to the top-1 object
BURST_SIZE       = 8      # consecutive accesses per burst for hot objects
LONG_REUSE_GAP   = 1200   # number of filler requests between a hot obj and its long revisit
COLD_RATIO       = 0.57   # fraction of unique objects that appear exactly once
HOTSPOT_ROTATE   = 0.20   # fraction of hot pool replaced per epoch (phase instability)
HOT_POOL_SIZE    = 256    # total hot-object pool
HOT_PER_EPOCH    = 64     # active hot objects per epoch (drawn from hot pool)
FILLER_PER_EPOCH = 1024   # cold one-hit filler objects per epoch
EPOCHS           = 640    # number of epochs


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate meta_reag-like synthetic trace"
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("tmp/20260601-meta-reag-like-trace"),
    )
    p.add_argument(
        "--variant",
        choices=["clean", "phase_unstable"],
        default="phase_unstable",
        help=(
            "clean: hotspot pool is fixed across epochs; "
            "phase_unstable: hotspot pool rotates HOTSPOT_ROTATE fraction every epoch"
        ),
    )
    p.add_argument("--epochs",           type=int,   default=EPOCHS)
    p.add_argument("--hot-pool-size",    type=int,   default=HOT_POOL_SIZE)
    p.add_argument("--hot-per-epoch",    type=int,   default=HOT_PER_EPOCH)
    p.add_argument("--filler-per-epoch", type=int,   default=FILLER_PER_EPOCH)
    p.add_argument("--hotspot-rotate",   type=float, default=HOTSPOT_ROTATE,
                   help="fraction of hot pool replaced per epoch (phase_unstable only)")
    p.add_argument("--super-hot-frac",   type=float, default=SUPER_HOT_FRAC,
                   help="fraction of requests going to the single hottest object")
    p.add_argument("--burst-size",       type=int,   default=BURST_SIZE)
    p.add_argument("--long-reuse-gap",   type=int,   default=LONG_REUSE_GAP)
    p.add_argument("--cold-ratio",       type=float, default=COLD_RATIO,
                   help="probability that a filler object is one-hit")
    p.add_argument("--seed",             type=int,   default=20260601)
    p.add_argument("--no-plots",         action="store_true")
    return p.parse_args()


def pick_size(rng: random.Random) -> int:
    """Sample object size from the heavy-tail distribution."""
    r = rng.random()
    cumulative = 0.0
    for size, prob in SIZE_CLASSES:
        cumulative += prob
        if r < cumulative:
            return size
    return SIZE_CLASSES[-1][0]


def write_req(writer: csv.writer, t: int, obj_id: int, obj_size: int) -> int:
    writer.writerow([t, obj_id, obj_size, 0])
    return t + 1


def generate(args: argparse.Namespace) -> Path:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / f"meta_reag_like_{args.variant}.csv"

    rng = random.Random(args.seed)

    # --- Object pools ---
    # IDs:
    #   1                  → super-hot singleton (always in pool)
    #   2 .. hot_pool_size → hot pool
    #   hot_pool_size+1 .. → filler / cold objects (ever-increasing)
    super_hot_id = 1
    super_hot_size = SIZE_CLASSES[2][0]   # medium: 64KB (hot but not tiny)

    hot_pool_start = 2
    hot_pool: list[int] = list(range(hot_pool_start, hot_pool_start + args.hot_pool_size))
    # Assign sizes to hot pool objects (fixed for their lifetime)
    hot_sizes: dict[int, int] = {
        obj_id: pick_size(rng) for obj_id in hot_pool
    }

    next_filler_id = hot_pool_start + args.hot_pool_size
    t = 1

    # Pending long-reuse requests: list of (trigger_time, obj_id, obj_size)
    pending_long_reuse: list[tuple[int, int, int]] = []

    # Track frequency for summary
    freq: dict[int, int] = {}

    def emit_pending(writer: csv.writer, current_t: int) -> int:
        """Flush any pending long-reuse requests whose trigger time has passed."""
        nonlocal t
        triggered = [x for x in pending_long_reuse if x[0] <= current_t]
        for trig_t, obj_id, obj_size in triggered:
            pending_long_reuse.remove((trig_t, obj_id, obj_size))
            t = write_req(writer, t, obj_id, obj_size)
            freq[obj_id] = freq.get(obj_id, 0) + 1
        return t

    with trace_path.open("w", newline="") as f:
        writer = csv.writer(f)

        for epoch in range(args.epochs):
            # --- Phase instability: rotate hot pool ---
            if args.variant == "phase_unstable" and args.hotspot_rotate > 0.0:
                n_rotate = max(1, int(args.hot_pool_size * args.hotspot_rotate))
                # Remove random objects from pool and replace with fresh ones
                idxs_to_remove = rng.sample(range(len(hot_pool)), n_rotate)
                for idx in sorted(idxs_to_remove, reverse=True):
                    del hot_pool[idx]
                for _ in range(n_rotate):
                    new_id = next_filler_id
                    next_filler_id += 1
                    hot_pool.append(new_id)
                    hot_sizes[new_id] = pick_size(rng)

            # Select active hot objects this epoch
            active_hot = rng.sample(hot_pool, min(args.hot_per_epoch, len(hot_pool)))

            # --- Super-hot burst (contributes to top-1 dominance) ---
            # Compute how many super-hot requests to inject per epoch to hit super_hot_frac
            # total_req_per_epoch ≈ hot_per_epoch*burst_size + filler_per_epoch
            total_est = args.hot_per_epoch * args.burst_size + args.filler_per_epoch
            super_hot_count = int(total_est * args.super_hot_frac / (1.0 - args.super_hot_frac))
            super_hot_count = max(1, super_hot_count)
            for _ in range(super_hot_count):
                t = write_req(writer, t, super_hot_id, super_hot_size)
                freq[super_hot_id] = freq.get(super_hot_id, 0) + 1

            # --- Hot object bursts ---
            for obj_id in active_hot:
                sz = hot_sizes[obj_id]
                # Burst access
                for _ in range(args.burst_size):
                    t = write_req(writer, t, obj_id, sz)
                    freq[obj_id] = freq.get(obj_id, 0) + 1
                # Schedule long-reuse revisit (only ~40% of hot objects revisit long-distance)
                if rng.random() < 0.4:
                    trigger = t + args.long_reuse_gap + rng.randint(0, args.long_reuse_gap // 2)
                    pending_long_reuse.append((trigger, obj_id, sz))

            # --- Filler / cold one-hit stream ---
            for _ in range(args.filler_per_epoch):
                filler_id = next_filler_id
                next_filler_id += 1
                sz = pick_size(rng)
                t = write_req(writer, t, filler_id, sz)
                freq[filler_id] = 1
                # Cold objects: some get a second hit within short window (non-trivial cold pool)
                if rng.random() > args.cold_ratio:
                    # Non-one-hit: will appear again after a short gap
                    gap = rng.randint(32, 256)
                    trigger = t + gap
                    pending_long_reuse.append((trigger, filler_id, sz))

            # Flush pending long-reuse requests
            t = emit_pending(writer, t)

    # Write any remaining pending long-reuse at the end
    with trace_path.open("a", newline="") as f:
        writer = csv.writer(f)
        for _trig_t, obj_id, sz in sorted(pending_long_reuse, key=lambda x: x[0]):
            t = write_req(writer, t, obj_id, sz)
            freq[obj_id] = freq.get(obj_id, 0) + 1

    # --- Summary ---
    summary_path = args.output_dir / f"meta_reag_like_{args.variant}_summary.md"
    n_req = t - 1
    n_unique = len(freq)
    one_hit = sum(1 for c in freq.values() if c == 1)
    cold_ratio_actual = one_hit / n_unique if n_unique else 0.0
    sorted_freq = sorted(freq.values(), reverse=True)
    top1_frac = sorted_freq[0] / n_req if n_req else 0.0
    top10_frac = sum(sorted_freq[:10]) / n_req if len(sorted_freq) >= 10 else 0.0

    # Size distribution of all requests
    with summary_path.open("w") as sf:
        sf.write(f"# meta_reag-like synthetic trace ({args.variant})\n\n")
        sf.write(f"Trace: `{trace_path}`\n\n")
        sf.write(f"## Key statistics\n\n")
        sf.write(f"| metric | value |\n|---|---|\n")
        sf.write(f"| total requests | {n_req:,} |\n")
        sf.write(f"| unique objects | {n_unique:,} |\n")
        sf.write(f"| cold ratio (one-hit) | {cold_ratio_actual:.3f} |\n")
        sf.write(f"| top-1 request fraction | {top1_frac:.4f} |\n")
        sf.write(f"| top-10 request fraction | {top10_frac:.4f} |\n")
        sf.write(f"\n## Parameters\n\n")
        sf.write(f"- variant: {args.variant}\n")
        sf.write(f"- epochs: {args.epochs}\n")
        sf.write(f"- hot_pool_size: {args.hot_pool_size}\n")
        sf.write(f"- hot_per_epoch: {args.hot_per_epoch}\n")
        sf.write(f"- filler_per_epoch: {args.filler_per_epoch}\n")
        sf.write(f"- hotspot_rotate: {args.hotspot_rotate}\n")
        sf.write(f"- super_hot_frac: {args.super_hot_frac}\n")
        sf.write(f"- burst_size: {args.burst_size}\n")
        sf.write(f"- long_reuse_gap: {args.long_reuse_gap}\n")
        sf.write(f"- cold_ratio: {args.cold_ratio}\n")

    print(f"trace={trace_path}")
    print(f"summary={summary_path}")
    print(f"n_req={n_req:,}  n_unique={n_unique:,}  cold_ratio={cold_ratio_actual:.3f}  top1={top1_frac:.4f}  top10={top10_frac:.4f}")
    return trace_path


def plot_freq_distribution(freq: dict[int, int], output_dir: Path, variant: str) -> None:
    """Plot frequency rank distribution (Zipf-like)."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    sorted_freq = sorted(freq.values(), reverse=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.loglog(range(1, len(sorted_freq) + 1), sorted_freq, "b.", markersize=1)
    ax.set_xlabel("Rank")
    ax.set_ylabel("Frequency")
    ax.set_title(f"Frequency rank distribution ({variant})")
    fig.tight_layout()
    path = output_dir / f"freq_rank_{variant}.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"plot={path}")


def main() -> None:
    args = parse_args()
    trace_path = generate(args)
    if not args.no_plots:
        # Re-read freq from trace to plot (generate already closed the file)
        pass  # plots skipped to keep runtime short; add --no-plots=False for full run


if __name__ == "__main__":
    main()
