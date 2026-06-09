#!/usr/bin/env python3
"""
Generate a covariate-shift synthetic trace for testing LOH vs 3LCache robustness.

CSV trace format: time,obj-id,obj-size,ttl

Design:
  - Two object pools (small 4KB and large 1MB) with fixed IDs that are REUSED
    across rounds (cyclically selected). This keeps the working set bounded.
  - Phase A (freq_preference): small objects return after a short gap;
    large objects do not return.
  - Phase B (size_preference): large objects return after a short gap;
    small objects do not return.
  - Phases alternate, creating covariate shift: the same feature→label mapping flips.

Key difference from phase_flip:
  - Objects are REUSED (not unique per round) → bounded working set
  - Minimal filler (gap objects reused) → cache=0.1 is meaningful
  - 3LCache trains on Phase A → model becomes wrong in Phase B → high MR
  - LOH CMA-ES adapts within ~500 requests (RL interval) per epoch

Expected outcome:
  - 3LCache-OMR: model staleness → high MR after phase flips
  - LOH: quick CMA-ES adaptation → lower MR after phase flips
  - LRU: baseline, no adaptation
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate covariate-shift preference trace")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--small-pool", type=int, default=1024,
                        help="Number of small (4KB) objects in the pool")
    parser.add_argument("--large-pool", type=int, default=1024,
                        help="Number of large (1MB) objects in the pool")
    parser.add_argument("--gap-pool", type=int, default=256,
                        help="Number of gap (16KB) objects (reused)")
    parser.add_argument("--per-round-small", type=int, default=64,
                        help="Small objects selected per round")
    parser.add_argument("--per-round-large", type=int, default=64,
                        help="Large objects selected per round")
    parser.add_argument("--burst-repeats", type=int, default=3,
                        help="Burst accesses per object")
    parser.add_argument("--return-repeats", type=int, default=2,
                        help="Return accesses per object")
    parser.add_argument("--gap-per-round", type=int, default=256,
                        help="Gap requests per round")
    parser.add_argument("--rounds-per-phase", type=int, default=200,
                        help="Rounds per phase")
    parser.add_argument("--total-phases", type=int, default=8,
                        help="Total number of phases (should be even)")
    parser.add_argument("--small-size", type=int, default=4096)
    parser.add_argument("--large-size", type=int, default=1048576)
    parser.add_argument("--gap-size", type=int, default=16384)
    parser.add_argument("--seed", type=int, default=20260601)
    parser.add_argument("--no-plots", action="store_true")
    return parser.parse_args()


def write_request(writer, time: int, obj_id: int, obj_size: int) -> int:
    writer.writerow([time, obj_id, obj_size, 0])
    return time + 1


def generate(args: argparse.Namespace) -> tuple:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / "covariate_shift.csv"
    metadata_path = args.output_dir / "covariate_shift_metadata.csv"
    summary_path = args.output_dir / "covariate_shift_summary.md"

    # Object ID ranges:
    #   small:  1 .. small_pool
    #   large:  small_pool+1 .. small_pool+large_pool
    #   gap:    small_pool+large_pool+1 .. small_pool+large_pool+gap_pool
    small_base = 1
    large_base = small_base + args.small_pool
    gap_base = large_base + args.large_pool

    metadata: list[dict] = []
    component_counts: Counter = Counter()
    time = 1
    small_cursor = 0
    large_cursor = 0
    gap_cursor = 0

    with trace_path.open("w", newline="") as f:
        writer = csv.writer(f)

        for phase_id in range(args.total_phases):
            is_freq_phase = (phase_id % 2 == 0)
            phase_kind = "freq_preference" if is_freq_phase else "size_preference"

            for _round in range(args.rounds_per_phase):
                # Select objects (cycling through pools)
                small_ids = [
                    small_base + ((small_cursor + i) % args.small_pool)
                    for i in range(args.per_round_small)
                ]
                small_cursor = (small_cursor + args.per_round_small) % args.small_pool

                large_ids = [
                    large_base + ((large_cursor + i) % args.large_pool)
                    for i in range(args.per_round_large)
                ]
                large_cursor = (large_cursor + args.per_round_large) % args.large_pool

                # --- Burst: small objects ---
                for obj_id in small_ids:
                    for _ in range(args.burst_repeats):
                        time = write_request(writer, time, obj_id, args.small_size)
                        component_counts[f"{phase_kind}_small_burst"] += 1
                    metadata.append({
                        "phase_id": phase_id,
                        "phase_kind": phase_kind,
                        "obj_class": "small",
                        "short_reuse": 1 if is_freq_phase else 0,
                        "obj_size": args.small_size,
                        "burst_count": args.burst_repeats,
                    })

                # --- Burst: large objects (only 1 access to create freq asymmetry) ---
                for obj_id in large_ids:
                    time = write_request(writer, time, obj_id, args.large_size)
                    component_counts[f"{phase_kind}_large_burst"] += 1
                    metadata.append({
                        "phase_id": phase_id,
                        "phase_kind": phase_kind,
                        "obj_class": "large",
                        "short_reuse": 1 if not is_freq_phase else 0,
                        "obj_size": args.large_size,
                        "burst_count": 1,
                    })

                # --- Gap: reused gap objects ---
                gap_ids = [
                    gap_base + ((gap_cursor + i) % args.gap_pool)
                    for i in range(args.gap_per_round)
                ]
                gap_cursor = (gap_cursor + args.gap_per_round) % args.gap_pool
                for obj_id in gap_ids:
                    time = write_request(writer, time, obj_id, args.gap_size)
                    component_counts[f"{phase_kind}_gap"] += 1

                # --- Return: only the "preferred" group returns ---
                return_ids = small_ids if is_freq_phase else large_ids
                return_size = args.small_size if is_freq_phase else args.large_size
                return_kind = "small_return" if is_freq_phase else "large_return"
                for obj_id in return_ids:
                    for _ in range(args.return_repeats):
                        time = write_request(writer, time, obj_id, return_size)
                        component_counts[f"{phase_kind}_{return_kind}"] += 1

    total_requests = time - 1

    # Write metadata
    with metadata_path.open("w", newline="") as f:
        fieldnames = ["phase_id", "phase_kind", "obj_class", "short_reuse",
                       "obj_size", "burst_count"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(metadata)

    # Compute per-round and trace stats
    total_unique_objects = args.small_pool + args.large_pool + args.gap_pool
    total_bytes = (args.small_pool * args.small_size +
                   args.large_pool * args.large_size +
                   args.gap_pool * args.gap_size)
    requests_per_round = (args.per_round_small * args.burst_repeats +
                          args.per_round_large * 1 +
                          args.gap_per_round +
                          args.per_round_small * args.return_repeats)  # same count whether small or large returns
    requests_per_phase = requests_per_round * args.rounds_per_phase

    # Write summary
    with summary_path.open("w") as f:
        f.write("# Covariate Shift Preference Trace\n\n")
        f.write("## Design\n\n")
        f.write("- Two object pools: small (4KB) and large (1MB), IDs reused cyclically.\n")
        f.write("- Phase A (freq): small objects return, large are one-hit → 'keep small'\n")
        f.write("- Phase B (size): large objects return, small are one-hit → 'keep large'\n")
        f.write("- Gap objects: reused filler, constant throughout.\n\n")
        f.write("## Expected Mechanism\n\n")
        f.write("- 3LCache: GBM trains on Phase A data, model becomes stale in Phase B.\n")
        f.write("  Batch size = 65536 eviction samples → slow adaptation.\n")
        f.write("- LOH: CMA-ES adapts every ~500 requests → fast recovery after flip.\n")
        f.write("- LRU: no learning, baseline for comparison.\n\n")
        f.write("## Statistics\n\n")
        f.write(f"- Total requests: {total_requests:,}\n")
        f.write(f"- Total unique objects: {total_unique_objects:,}\n")
        f.write(f"- Total unique bytes: {total_bytes:,} ({total_bytes/1024/1024:.1f} MB)\n")
        f.write(f"- Requests per round: {requests_per_round}\n")
        f.write(f"- Requests per phase: {requests_per_phase:,}\n")
        f.write(f"- Object pools: small={args.small_pool}, large={args.large_pool}, gap={args.gap_pool}\n")
        f.write(f"- Object sizes: small={args.small_size}, large={args.large_size}, gap={args.gap_size}\n\n")
        f.write("## Request Mix\n\n")
        f.write("| component | count |\n")
        f.write("|---|---:|\n")
        for comp, count in sorted(component_counts.items()):
            f.write(f"| {comp} | {count:,} |\n")

    return trace_path, metadata_path, summary_path


def plot_outputs(output_dir: Path, metadata_path: Path) -> list:
    """Generate feature-label flip heatmap and phase preference timeline."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[WARN] matplotlib not available; skip plots")
        return []

    rows = []
    with metadata_path.open(newline="") as f:
        rows.extend(csv.DictReader(f))

    phase_ids = sorted({int(r["phase_id"]) for r in rows})
    obj_classes = ["small", "large"]
    values: dict[str, list[float]] = {c: [] for c in obj_classes}
    for cls in obj_classes:
        for pid in phase_ids:
            matching = [int(r["short_reuse"]) for r in rows
                        if r["obj_class"] == cls and int(r["phase_id"]) == pid]
            values[cls].append(sum(matching) / len(matching) if matching else 0.0)

    # Heatmap
    heatmap_path = output_dir / "feature_label_flip_heatmap.png"
    fig, ax = plt.subplots(figsize=(max(6, len(phase_ids) * 0.8), 2.5))
    matrix = [values[c] for c in obj_classes]
    im = ax.imshow(matrix, aspect="auto", vmin=0, vmax=1, cmap="RdYlGn")
    ax.set_yticks(range(len(obj_classes)), obj_classes)
    ax.set_xticks(range(len(phase_ids)), [str(p) for p in phase_ids])
    ax.set_xlabel("Phase")
    ax.set_ylabel("Object class")
    ax.set_title("P(short reuse | object_class, phase)")
    for ri, cls in enumerate(obj_classes):
        for ci, val in enumerate(values[cls]):
            ax.text(ci, ri, f"{val:.0f}", ha="center", va="center",
                    color="white" if val < 0.5 else "black", fontsize=10)
    fig.colorbar(im, ax=ax, label="short reuse probability")
    fig.tight_layout()
    fig.savefig(heatmap_path, dpi=150)
    plt.close(fig)

    # Timeline
    timeline_path = output_dir / "phase_preference_timeline.png"
    fig, ax = plt.subplots(figsize=(max(6, len(phase_ids) * 0.8), 2.0))
    colors = ["#4C78A8" if pid % 2 == 0 else "#F58518" for pid in phase_ids]
    labels = ["freq\n(keep small)" if pid % 2 == 0 else "size\n(keep large)"
              for pid in phase_ids]
    ax.bar(phase_ids, [1] * len(phase_ids), color=colors)
    ax.set_yticks([])
    ax.set_xlabel("Phase")
    ax.set_title("Oracle workload preference by phase")
    for pid, label in zip(phase_ids, labels):
        ax.text(pid, 0.5, label, ha="center", va="center", color="white", fontsize=7)
    fig.tight_layout()
    fig.savefig(timeline_path, dpi=150)
    plt.close(fig)

    return [heatmap_path, timeline_path]


def main() -> None:
    args = parse_args()
    trace_path, metadata_path, summary_path = generate(args)
    print(f"trace={trace_path}")
    print(f"metadata={metadata_path}")
    print(f"summary={summary_path}")

    if not args.no_plots:
        plot_paths = plot_outputs(args.output_dir, metadata_path)
        for p in plot_paths:
            print(f"plot={p}")


if __name__ == "__main__":
    main()
