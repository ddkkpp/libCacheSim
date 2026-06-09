#!/usr/bin/env python3
"""
Generate a phase-flip synthetic trace for testing workload-preference learning.

CSV trace format: time,obj-id,obj-size,ttl

Design:
  - Alternate two phases with identical object-level feature bins but opposite
    future values.
  - freq phase: small high-frequency objects return after the filler scan;
    large low-frequency objects do not return.
  - size phase: large low-frequency objects return after the filler scan;
    small high-frequency objects do not return.

This intentionally stresses object-level future-value predictors: the same
feature bin (small/freq3 or large/freq1) has phase-dependent labels. A
workload-preference layer can instead learn the lower-dimensional control
problem: emphasize frequency in freq phases and size/byte value in size phases.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_SIZE_SMALL = 4 * 1024
DEFAULT_SIZE_FILLER = 16 * 1024
DEFAULT_SIZE_LARGE = 1 * 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate phase-flip preference trace")
    parser.add_argument("--output-dir", type=Path, default=Path("tmp/20260528-phase-flip-preference-trace"))
    parser.add_argument("--cycles", type=int, default=4, help="number of freq/size phase pairs")
    parser.add_argument("--rounds-per-phase", type=int, default=40)
    parser.add_argument("--hot-per-round", type=int, default=32)
    parser.add_argument("--large-per-round", type=int, default=32)
    parser.add_argument("--filler-per-round", type=int, default=768)
    parser.add_argument("--return-repeats", type=int, default=2)
    parser.add_argument("--small-size", type=int, default=DEFAULT_SIZE_SMALL)
    parser.add_argument("--filler-size", type=int, default=DEFAULT_SIZE_FILLER)
    parser.add_argument("--large-size", type=int, default=DEFAULT_SIZE_LARGE)
    parser.add_argument("--no-plots", action="store_true")
    return parser.parse_args()


def write_request(writer: csv.writer, time: int, obj_id: int, obj_size: int) -> int:
    writer.writerow([time, obj_id, obj_size, 0])
    return time + 1


def add_metadata(metadata: list[dict[str, object]], phase_id: int, phase_kind: str, obj_class: str,
                 feature_bin: str, short_reuse: int, obj_size: int, warmup_freq: int) -> None:
    metadata.append(
        {
            "phase_id": phase_id,
            "phase_kind": phase_kind,
            "obj_class": obj_class,
            "feature_bin": feature_bin,
            "short_reuse": short_reuse,
            "obj_size": obj_size,
            "warmup_freq": warmup_freq,
        }
    )


def generate(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / "phase_flip_preference.csv"
    metadata_path = args.output_dir / "phase_flip_metadata.csv"
    summary_path = args.output_dir / "phase_flip_summary.md"

    metadata: list[dict[str, object]] = []
    phase_req_counts: Counter[tuple[int, str, str]] = Counter()
    time = 1
    next_obj_id = 1

    with trace_path.open("w", newline="") as trace_file:
        writer = csv.writer(trace_file)
        for phase_id in range(args.cycles * 2):
            phase_kind = "freq_preference" if phase_id % 2 == 0 else "size_preference"
            for _round in range(args.rounds_per_phase):
                hot_ids = list(range(next_obj_id, next_obj_id + args.hot_per_round))
                next_obj_id += args.hot_per_round
                large_ids = list(range(next_obj_id, next_obj_id + args.large_per_round))
                next_obj_id += args.large_per_round

                for obj_id in hot_ids:
                    for _ in range(3):
                        time = write_request(writer, time, obj_id, args.small_size)
                        phase_req_counts[(phase_id, phase_kind, "hot_warmup")] += 1
                    add_metadata(
                        metadata,
                        phase_id,
                        phase_kind,
                        "small_highfreq",
                        "small_freq3",
                        1 if phase_kind == "freq_preference" else 0,
                        args.small_size,
                        3,
                    )

                for obj_id in large_ids:
                    time = write_request(writer, time, obj_id, args.large_size)
                    phase_req_counts[(phase_id, phase_kind, "large_warmup")] += 1
                    add_metadata(
                        metadata,
                        phase_id,
                        phase_kind,
                        "large_lowfreq",
                        "large_freq1",
                        1 if phase_kind == "size_preference" else 0,
                        args.large_size,
                        1,
                    )

                for _ in range(args.filler_per_round):
                    filler_id = next_obj_id
                    next_obj_id += 1
                    time = write_request(writer, time, filler_id, args.filler_size)
                    phase_req_counts[(phase_id, phase_kind, "filler_scan")] += 1

                return_ids = hot_ids if phase_kind == "freq_preference" else large_ids
                return_size = args.small_size if phase_kind == "freq_preference" else args.large_size
                return_name = "hot_return" if phase_kind == "freq_preference" else "large_return"
                for obj_id in return_ids:
                    for _ in range(args.return_repeats):
                        time = write_request(writer, time, obj_id, return_size)
                        phase_req_counts[(phase_id, phase_kind, return_name)] += 1

    with metadata_path.open("w", newline="") as metadata_file:
        fieldnames = ["phase_id", "phase_kind", "obj_class", "feature_bin", "short_reuse", "obj_size", "warmup_freq"]
        writer = csv.DictWriter(metadata_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(metadata)

    with summary_path.open("w") as summary_file:
        summary_file.write("# Phase-flip preference trace\n\n")
        summary_file.write("Purpose: make object-level future-value labels phase-dependent while keeping the workload-level preference simple.\n\n")
        summary_file.write("- `freq_preference`: `small_freq3` has short reuse, `large_freq1` is far/no reuse.\n")
        summary_file.write("- `size_preference`: `large_freq1` has short reuse, `small_freq3` is far/no reuse.\n")
        summary_file.write("- Expected easy target for RSD/LOH: switch global preference between frequency and size/byte value by phase.\n")
        summary_file.write("- Expected hard target for LRB/3LCache: the same feature bin has opposite future labels across phases unless phase/context is learned.\n\n")
        summary_file.write(f"Trace: `{trace_path}`\n\n")
        summary_file.write(f"Metadata: `{metadata_path}`\n\n")
        summary_file.write(f"Requests: {time - 1:,}\n\n")
        summary_file.write("## Object sizes\n\n")
        summary_file.write(f"- small: {args.small_size:,} bytes\n")
        summary_file.write(f"- filler: {args.filler_size:,} bytes\n")
        summary_file.write(f"- large: {args.large_size:,} bytes\n\n")
        summary_file.write("## Request mix by phase\n\n")
        summary_file.write("| phase | kind | component | requests |\n")
        summary_file.write("|---:|---|---|---:|\n")
        for (phase_id, phase_kind, component), count in sorted(phase_req_counts.items()):
            summary_file.write(f"| {phase_id} | {phase_kind} | {component} | {count} |\n")

    return trace_path, metadata_path, summary_path


def plot_outputs(output_dir: Path, metadata_path: Path) -> list[Path]:
    import matplotlib.pyplot as plt

    rows: list[dict[str, str]] = []
    with metadata_path.open(newline="") as metadata_file:
        rows.extend(csv.DictReader(metadata_file))

    phase_ids = sorted({int(row["phase_id"]) for row in rows})
    bins = ["small_freq3", "large_freq1"]
    values: dict[str, list[float]] = {feature_bin: [] for feature_bin in bins}
    for feature_bin in bins:
        for phase_id in phase_ids:
            matching = [int(row["short_reuse"]) for row in rows if row["feature_bin"] == feature_bin and int(row["phase_id"]) == phase_id]
            values[feature_bin].append(sum(matching) / len(matching))

    heatmap_path = output_dir / "feature_label_flip_heatmap.png"
    fig, ax = plt.subplots(figsize=(9, 3.6))
    matrix = [values[feature_bin] for feature_bin in bins]
    image = ax.imshow(matrix, aspect="auto", vmin=0, vmax=1, cmap="viridis")
    ax.set_yticks(range(len(bins)), bins)
    ax.set_xticks(range(len(phase_ids)), phase_ids)
    ax.set_xlabel("Phase")
    ax.set_ylabel("Feature bin")
    ax.set_title("P(short reuse | feature bin, phase)")
    for row_idx, feature_bin in enumerate(bins):
        for col_idx, value in enumerate(values[feature_bin]):
            ax.text(col_idx, row_idx, f"{value:.0f}", ha="center", va="center", color="white" if value < 0.5 else "black")
    fig.colorbar(image, ax=ax, label="short reuse probability")
    fig.tight_layout()
    fig.savefig(heatmap_path, dpi=180)
    plt.close(fig)

    preference_path = output_dir / "phase_preference_timeline.png"
    fig, ax = plt.subplots(figsize=(9, 2.8))
    phase_labels = ["frequency" if phase_id % 2 == 0 else "size" for phase_id in phase_ids]
    colors = ["#4C78A8" if label == "frequency" else "#F58518" for label in phase_labels]
    ax.bar(phase_ids, [1] * len(phase_ids), color=colors)
    ax.set_yticks([])
    ax.set_xlabel("Phase")
    ax.set_title("Oracle workload preference by phase")
    for phase_id, label in zip(phase_ids, phase_labels):
        ax.text(phase_id, 0.5, label, ha="center", va="center", color="white", fontsize=9)
    fig.tight_layout()
    fig.savefig(preference_path, dpi=180)
    plt.close(fig)

    return [heatmap_path, preference_path]


def main() -> None:
    args = parse_args()
    trace_path, metadata_path, summary_path = generate(args)
    plot_paths: list[Path] = []
    if not args.no_plots:
        plot_paths = plot_outputs(args.output_dir, metadata_path)

    print(f"trace={trace_path}")
    print(f"metadata={metadata_path}")
    print(f"summary={summary_path}")
    for plot_path in plot_paths:
        print(f"plot={plot_path}")


if __name__ == "__main__":
    main()
