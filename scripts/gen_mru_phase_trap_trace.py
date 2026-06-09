#!/usr/bin/env python3
import argparse
import csv
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a multiscale MRU-trap trace with phase-dependent labels."
    )
    parser.add_argument(
        "--output-dir",
        default="tmp/20260528-mru-phase-trap-trace",
        help="Directory for trace, metadata, summary, and plots.",
    )
    parser.add_argument("--large-objects", type=int, default=20000)
    parser.add_argument("--small-objects", type=int, default=200)
    parser.add_argument("--large-repeats", type=int, default=8)
    parser.add_argument("--small-repeats", type=int, default=500)
    parser.add_argument("--burst-rounds", type=int, default=10000)
    parser.add_argument("--object-size", type=int, default=4096)
    parser.add_argument("--no-plots", action="store_true")
    return parser.parse_args()


def write_request(writer, time, obj_id, obj_size):
    writer.writerow([time, obj_id, obj_size, 0])
    return time + 1


def add_metadata(rows, phase_id, phase_kind, feature_bin, short_reuse, requests):
    rows.append(
        {
            "phase_id": phase_id,
            "phase_kind": phase_kind,
            "feature_bin": feature_bin,
            "short_reuse": int(short_reuse),
            "requests": requests,
        }
    )


def generate(args):
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = output_dir / "mru_phase_trap.csv"
    metadata_path = output_dir / "mru_phase_trap_metadata.csv"
    summary_path = output_dir / "mru_phase_trap_summary.md"

    phase_counts = Counter()
    metadata = []
    time = 1

    large_ids = list(range(1, args.large_objects + 1))
    small_ids = large_ids[: args.small_objects]
    burst_ids = large_ids[args.small_objects : args.small_objects + args.burst_rounds]
    if len(burst_ids) < args.burst_rounds:
        raise ValueError("large-objects must be at least small-objects + burst-rounds")

    with trace_path.open("w", newline="") as trace_file:
        writer = csv.writer(trace_file)
        phase_id = 0

        # A full-cycle scan where MRU-like eviction keeps the earliest cache slice.
        for _ in range(args.large_repeats):
            for obj_id in large_ids:
                time = write_request(writer, time, obj_id, args.object_size)
            phase_counts[(phase_id, "large_mru_scan")] += args.large_objects
        add_metadata(
            metadata,
            phase_id,
            "large_mru_scan",
            "age0_freq1_size4k",
            False,
            phase_counts[(phase_id, "large_mru_scan")],
        )

        phase_id += 1
        for _ in range(args.small_repeats):
            for obj_id in small_ids:
                time = write_request(writer, time, obj_id, args.object_size)
            phase_counts[(phase_id, "small_mru_scan")] += args.small_objects
        add_metadata(
            metadata,
            phase_id,
            "small_mru_scan",
            "age0_freq1_size4k",
            False,
            phase_counts[(phase_id, "small_mru_scan")],
        )

        phase_id += 1
        for obj_id in burst_ids:
            time = write_request(writer, time, obj_id, args.object_size)
            time = write_request(writer, time, obj_id, args.object_size)
            phase_counts[(phase_id, "burst_immediate_reuse")] += 2
        add_metadata(
            metadata,
            phase_id,
            "burst_immediate_reuse",
            "age0_freq1_size4k",
            True,
            phase_counts[(phase_id, "burst_immediate_reuse")],
        )

    with metadata_path.open("w", newline="") as metadata_file:
        fieldnames = ["phase_id", "phase_kind", "feature_bin", "short_reuse", "requests"]
        writer = csv.DictWriter(metadata_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(metadata)

    total_requests = time - 1
    with summary_path.open("w") as summary_file:
        summary_file.write("# MRU Phase-Trap Synthetic Trace\n\n")
        summary_file.write(f"Trace: `{trace_path}`\n\n")
        summary_file.write(f"Requests: {total_requests:,}\n")
        summary_file.write(f"Unique objects: {args.large_objects:,}\n")
        summary_file.write(f"Object size: {args.object_size:,} bytes\n\n")
        summary_file.write("## Design\n\n")
        summary_file.write(
            "- `large_mru_scan`: one full cyclic scan over the total working set; at cache=0.1, MRU-style eviction can keep the early cache slice while LRU churns.\n"
        )
        summary_file.write(
            "- `small_mru_scan`: cyclic scan over a 1% sub-working-set; at cache=0.001, the same MRU trap appears at the smaller scale.\n"
        )
        summary_file.write(
            "- `burst_immediate_reuse`: the same first-touch local feature bin is followed by immediate reuse, creating a phase-dependent object-label flip.\n\n"
        )
        summary_file.write("## Request Mix\n\n")
        summary_file.write("| phase | kind | requests |\n")
        summary_file.write("|---:|---|---:|\n")
        for (pid, kind), count in sorted(phase_counts.items()):
            summary_file.write(f"| {pid} | {kind} | {count:,} |\n")

    return trace_path, metadata_path, summary_path


def plot_outputs(output_dir, metadata_path):
    output_dir = Path(output_dir)
    rows = []
    with Path(metadata_path).open() as metadata_file:
        reader = csv.DictReader(metadata_file)
        for row in reader:
            rows.append(row)

    phase_ids = [int(row["phase_id"]) for row in rows]
    labels = [row["phase_kind"] for row in rows]
    short_probs = [float(row["short_reuse"]) for row in rows]
    requests = [int(row["requests"]) for row in rows]

    plt.figure(figsize=(8, 2.6))
    plt.imshow([short_probs], aspect="auto", cmap="viridis", vmin=0, vmax=1)
    plt.yticks([0], ["age0_freq1_size4k"])
    plt.xticks(range(len(phase_ids)), [str(pid) for pid in phase_ids])
    plt.xlabel("phase")
    plt.colorbar(label="P(short reuse | feature bin, phase)")
    plt.title("Same Local Feature, Phase-Dependent Label")
    plt.tight_layout()
    heatmap_path = output_dir / "feature_label_phase_flip.png"
    plt.savefig(heatmap_path, dpi=180)
    plt.close()

    colors = ["#2f6f9f", "#2f6f9f", "#b23a48"]
    plt.figure(figsize=(8, 3.2))
    plt.bar(phase_ids, requests, color=colors[: len(phase_ids)])
    plt.xticks(phase_ids, labels, rotation=18, ha="right")
    plt.ylabel("requests")
    plt.title("Workload Preference Timeline")
    plt.tight_layout()
    timeline_path = output_dir / "phase_preference_timeline.png"
    plt.savefig(timeline_path, dpi=180)
    plt.close()

    return heatmap_path, timeline_path


def main():
    args = parse_args()
    trace_path, metadata_path, summary_path = generate(args)
    print(f"trace={trace_path}")
    print(f"metadata={metadata_path}")
    print(f"summary={summary_path}")
    if not args.no_plots:
        for plot_path in plot_outputs(args.output_dir, metadata_path):
            print(f"plot={plot_path}")


if __name__ == "__main__":
    main()
