#!/usr/bin/env python3
"""
Generate a stationary label-noise trace for learned-cache target analysis.

The workload has one stable preference: a small active hot set returns after a
short gap.  The noise stream has the same local size/frequency signature as the
hot stream, but most noise objects do not return within the useful window.

This is intended to stress object-level future-distance learners without using
phase flips.  The easy workload-level rule stays stable: keep recently active
objects from the hot stream; ignore the long-tail decoys.
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import Counter, defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate stationary label-noise preference trace")
    parser.add_argument("--output-dir", type=Path, default=Path("tmp/20260529-label-noise-preference-trace"))
    parser.add_argument("--epochs", type=int, default=320)
    parser.add_argument("--hot-pool", type=int, default=8192)
    parser.add_argument("--decoy-pool", type=int, default=32768)
    parser.add_argument("--filler-pool", type=int, default=32768)
    parser.add_argument("--hot-per-epoch", type=int, default=64)
    parser.add_argument("--decoy-per-epoch", type=int, default=512)
    parser.add_argument("--short-gap-per-epoch", type=int, default=128)
    parser.add_argument("--tail-gap-per-epoch", type=int, default=512)
    parser.add_argument("--burst-repeats", type=int, default=3)
    parser.add_argument("--candidate-burst-repeats", type=int, default=None)
    parser.add_argument("--poison-burst-repeats", type=int, default=None)
    parser.add_argument("--return-repeats", type=int, default=2)
    parser.add_argument("--object-size", type=int, default=4096)
    parser.add_argument("--candidate-size", type=int, default=None)
    parser.add_argument("--poison-size", type=int, default=None)
    parser.add_argument("--scan-size", type=int, default=None)
    parser.add_argument("--random-label-noise", action="store_true")
    parser.add_argument("--post-return-poison", action="store_true")
    parser.add_argument("--candidate-per-epoch", type=int, default=512)
    parser.add_argument("--short-reuse-prob", type=float, default=0.125)
    parser.add_argument("--poison-per-epoch", type=int, default=512)
    parser.add_argument("--seed", type=int, default=20260529)
    parser.add_argument("--no-plots", action="store_true")
    return parser.parse_args()


def write_request(writer: csv.writer, time: int, obj_id: int, obj_size: int) -> int:
    writer.writerow([time, obj_id, obj_size, 0])
    return time + 1


def cyclic_ids(start: int, count: int, pool_start: int, pool_size: int) -> list[int]:
    return [pool_start + ((start + offset) % pool_size) for offset in range(count)]


def add_metadata(
    metadata: list[dict[str, object]],
    epoch: int,
    obj_class: str,
    feature_bin: str,
    short_reuse: int,
    obj_size: int,
    warmup_freq: int,
) -> None:
    metadata.append(
        {
            "epoch": epoch,
            "obj_class": obj_class,
            "feature_bin": feature_bin,
            "short_reuse": short_reuse,
            "obj_size": obj_size,
            "warmup_freq": warmup_freq,
        }
    )


def generate(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.output_dir / "label_noise_preference.csv"
    metadata_path = args.output_dir / "label_noise_metadata.csv"
    summary_path = args.output_dir / "label_noise_summary.md"

    hot_base = 1
    decoy_base = hot_base + args.hot_pool
    filler_base = decoy_base + args.decoy_pool
    candidate_size = args.candidate_size if args.candidate_size is not None else args.object_size
    poison_size = args.poison_size if args.poison_size is not None else args.object_size
    scan_size = args.scan_size if args.scan_size is not None else args.object_size
    candidate_burst = (
        args.candidate_burst_repeats
        if args.candidate_burst_repeats is not None
        else args.burst_repeats
    )
    poison_burst = (
        args.poison_burst_repeats
        if args.poison_burst_repeats is not None
        else args.burst_repeats
    )

    metadata: list[dict[str, object]] = []
    component_counts: Counter[str] = Counter()
    time = 1

    rng = random.Random(args.seed)

    with trace_path.open("w", newline="") as trace_file:
        writer = csv.writer(trace_file)
        for epoch in range(args.epochs):
            if args.post_return_poison:
                candidate_start = epoch * args.candidate_per_epoch
                poison_start = epoch * args.poison_per_epoch + args.hot_pool // 2
                filler_start = epoch * (args.short_gap_per_epoch + args.tail_gap_per_epoch)
                candidate_ids = cyclic_ids(candidate_start, args.candidate_per_epoch, hot_base, args.hot_pool)
                poison_ids = cyclic_ids(poison_start, args.poison_per_epoch, hot_base, args.hot_pool)

                for obj_id in candidate_ids:
                    for _ in range(candidate_burst):
                        time = write_request(writer, time, obj_id, candidate_size)
                        component_counts["candidate_burst"] += 1
                    add_metadata(
                        metadata,
                        epoch,
                        "candidate",
                        "candidate_freq3",
                        1,
                        candidate_size,
                        candidate_burst,
                    )

                short_gap_ids = cyclic_ids(filler_start, args.short_gap_per_epoch, filler_base, args.filler_pool)
                for obj_id in short_gap_ids:
                    time = write_request(writer, time, obj_id, scan_size)
                    component_counts["short_gap_scan"] += 1

                for obj_id in candidate_ids:
                    for _ in range(args.return_repeats):
                        time = write_request(writer, time, obj_id, candidate_size)
                        component_counts["candidate_return"] += 1

                for obj_id in poison_ids:
                    for _ in range(poison_burst):
                        time = write_request(writer, time, obj_id, poison_size)
                        component_counts["poison_burst"] += 1
                    add_metadata(
                        metadata,
                        epoch,
                        "poison",
                        "poison_freq3",
                        0,
                        poison_size,
                        poison_burst,
                    )

                tail_gap_ids = cyclic_ids(
                    filler_start + args.short_gap_per_epoch,
                    args.tail_gap_per_epoch,
                    filler_base,
                    args.filler_pool,
                )
                for obj_id in tail_gap_ids:
                    time = write_request(writer, time, obj_id, scan_size)
                    component_counts["tail_gap_scan"] += 1
                continue

            if args.random_label_noise:
                candidate_start = epoch * args.candidate_per_epoch
                filler_start = epoch * (args.short_gap_per_epoch + args.tail_gap_per_epoch)
                candidate_ids = cyclic_ids(candidate_start, args.candidate_per_epoch, hot_base, args.hot_pool)
                return_ids: list[int] = []

                for obj_id in candidate_ids:
                    for _ in range(candidate_burst):
                        time = write_request(writer, time, obj_id, candidate_size)
                        component_counts["candidate_burst"] += 1
                    short_reuse = 1 if rng.random() < args.short_reuse_prob else 0
                    if short_reuse:
                        return_ids.append(obj_id)
                    add_metadata(
                        metadata,
                        epoch,
                        "candidate",
                        "size4k_freq3",
                        short_reuse,
                        candidate_size,
                        candidate_burst,
                    )

                short_gap_ids = cyclic_ids(filler_start, args.short_gap_per_epoch, filler_base, args.filler_pool)
                for obj_id in short_gap_ids:
                    time = write_request(writer, time, obj_id, scan_size)
                    component_counts["short_gap_scan"] += 1

                for obj_id in return_ids:
                    for _ in range(args.return_repeats):
                        time = write_request(writer, time, obj_id, candidate_size)
                        component_counts["candidate_return"] += 1

                tail_gap_ids = cyclic_ids(
                    filler_start + args.short_gap_per_epoch,
                    args.tail_gap_per_epoch,
                    filler_base,
                    args.filler_pool,
                )
                for obj_id in tail_gap_ids:
                    time = write_request(writer, time, obj_id, scan_size)
                    component_counts["tail_gap_scan"] += 1
                continue

            hot_start = epoch * args.hot_per_epoch
            decoy_start = epoch * args.decoy_per_epoch
            filler_start = epoch * (args.short_gap_per_epoch + args.tail_gap_per_epoch)

            hot_ids = cyclic_ids(hot_start, args.hot_per_epoch, hot_base, args.hot_pool)
            decoy_ids = cyclic_ids(decoy_start, args.decoy_per_epoch, decoy_base, args.decoy_pool)
            short_gap_ids = cyclic_ids(filler_start, args.short_gap_per_epoch, filler_base, args.filler_pool)
            tail_gap_ids = cyclic_ids(
                filler_start + args.short_gap_per_epoch,
                args.tail_gap_per_epoch,
                filler_base,
                args.filler_pool,
            )

            for obj_id in hot_ids:
                for _ in range(candidate_burst):
                    time = write_request(writer, time, obj_id, args.object_size)
                    component_counts["hot_burst"] += 1
                add_metadata(
                    metadata,
                    epoch,
                    "hot",
                    "size4k_freq3",
                    1,
                    args.object_size,
                    candidate_burst,
                )

            for obj_id in short_gap_ids:
                time = write_request(writer, time, obj_id, args.object_size)
                component_counts["short_gap_scan"] += 1

            for obj_id in hot_ids:
                for _ in range(args.return_repeats):
                    time = write_request(writer, time, obj_id, args.object_size)
                    component_counts["hot_return"] += 1

            for obj_id in decoy_ids:
                for _ in range(poison_burst):
                    time = write_request(writer, time, obj_id, args.object_size)
                    component_counts["decoy_burst"] += 1
                add_metadata(
                    metadata,
                    epoch,
                    "decoy",
                    "size4k_freq3",
                    0,
                    args.object_size,
                    poison_burst,
                )

            for obj_id in tail_gap_ids:
                time = write_request(writer, time, obj_id, args.object_size)
                component_counts["tail_gap_scan"] += 1

    with metadata_path.open("w", newline="") as metadata_file:
        fieldnames = ["epoch", "obj_class", "feature_bin", "short_reuse", "obj_size", "warmup_freq"]
        writer = csv.DictWriter(metadata_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(metadata)

    label_counts: dict[str, Counter[int]] = defaultdict(Counter)
    for row in metadata:
        label_counts[str(row["obj_class"])][int(row["short_reuse"])] += 1
        label_counts["all"][int(row["short_reuse"])] += 1

    with summary_path.open("w") as summary_file:
        summary_file.write("# Label-noise preference trace\n\n")
        summary_file.write("Purpose: keep the workload preference stationary while adding decoy objects that pollute object-level future-distance labels.\n\n")
        if args.post_return_poison:
            summary_file.write("- Stable useful rule: candidates always return after the short scan gap.\n")
            if candidate_size == poison_size == scan_size:
                summary_file.write(
                    "- Noise rule: poison objects share the same local size/frequency signature but are injected only after useful returns finish.\n"
                )
                summary_file.write(
                    "- Expected hard target for LRB/3LCache: training sees many same-feature no-return examples even though they do not affect the useful keep/evict window.\n"
                )
            else:
                summary_file.write(
                    "- Noise rule: poison objects arrive after returns and are size-skewed (candidate={:,}B, poison={:,}B).\n"
                    .format(candidate_size, poison_size)
                )
                summary_file.write(
                    "- Expected hard target for LRB/3LCache: byte-focused feedback is dominated by large no-return objects, conflicting with the stable short-reuse rule.\n"
                )
            if candidate_burst != poison_burst:
                summary_file.write(
                    "- Burst skew: candidate burst repeats = {}, poison burst repeats = {}.\n"
                    .format(candidate_burst, poison_burst)
                )
            summary_file.write(
                "- Expected easy target for LOH-like recency preference: the poison stream arrives after the hits, so it mainly pollutes labels rather than evicting useful candidates before reuse.\n\n"
            )
        elif args.random_label_noise:
            summary_file.write("- Stable useful rule: recently requested candidates are worth keeping only probabilistically; the workload has no phase flip.\n")
            summary_file.write("- Noise rule: every candidate has the same local `size4k_freq3` signature, but its short-reuse label is sampled independently.\n")
            summary_file.write("- Expected hard target for LRB/3LCache: object-level future labels have high aleatoric noise and cannot be reliably separated from local history.\n")
            summary_file.write("- Expected easy target for LOH-like recency preference: the useful returns occur immediately after the short scan gap, so recency remains a reasonable low-variance rule.\n\n")
        else:
            summary_file.write("- Stable useful rule: hot objects have short reuse after a small scan gap.\n")
            summary_file.write("- Noise rule: decoy objects have the same local `size4k_freq3` signature but no short useful return.\n")
            summary_file.write("- Expected hard target for LRB/3LCache: the dominant label for `size4k_freq3` is noisy because decoys outnumber hot objects.\n")
            summary_file.write("- Expected easy target for LOH-like recency preference: decoys arrive after hot returns, so they mainly train labels rather than disrupting the short hot reuse.\n\n")
        summary_file.write(f"Trace: `{trace_path}`\n\n")
        summary_file.write(f"Metadata: `{metadata_path}`\n\n")
        summary_file.write(f"Requests: {time - 1:,}\n\n")
        summary_file.write(f"Working-set objects: {args.hot_pool + args.decoy_pool + args.filler_pool:,}\n\n")
        summary_file.write(f"Default object size: {args.object_size:,} bytes\n\n")
        summary_file.write(f"Candidate object size: {candidate_size:,} bytes\n\n")
        summary_file.write(f"Poison object size: {poison_size:,} bytes\n\n")
        summary_file.write(f"Scan object size: {scan_size:,} bytes\n\n")
        summary_file.write("## Request mix\n\n")
        summary_file.write("| component | requests |\n")
        summary_file.write("|---|---:|\n")
        for component, count in sorted(component_counts.items()):
            summary_file.write(f"| {component} | {count:,} |\n")
        summary_file.write("\n## Label mix for local training bins\n\n")
        summary_file.write("| class | short_reuse=1 | short_reuse=0 | p(short reuse) |\n")
        summary_file.write("|---|---:|---:|---:|\n")
        obj_classes = sorted(obj_class for obj_class in label_counts if obj_class != "all") + ["all"]
        for obj_class in obj_classes:
            yes = label_counts[obj_class][1]
            no = label_counts[obj_class][0]
            total = yes + no
            p_short = yes / total if total else 0.0
            summary_file.write(f"| {obj_class} | {yes:,} | {no:,} | {p_short:.4f} |\n")

    return trace_path, metadata_path, summary_path


def plot_outputs(output_dir: Path, metadata_path: Path) -> list[Path]:
    import matplotlib.pyplot as plt

    rows: list[dict[str, str]] = []
    with metadata_path.open(newline="") as metadata_file:
        rows.extend(csv.DictReader(metadata_file))

    by_class: dict[str, Counter[int]] = defaultdict(Counter)
    by_epoch: dict[int, Counter[int]] = defaultdict(Counter)
    for row in rows:
        obj_class = row["obj_class"]
        label = int(row["short_reuse"])
        epoch = int(row["epoch"])
        by_class[obj_class][label] += 1
        by_class["all"][label] += 1
        by_epoch[epoch][label] += 1

    label_mix_path = output_dir / "label_noise_mix.png"
    classes = sorted(obj_class for obj_class in by_class if obj_class != "all") + ["all"]
    p_short = []
    for obj_class in classes:
        yes = by_class[obj_class][1]
        no = by_class[obj_class][0]
        p_short.append(yes / (yes + no) if yes + no else 0.0)
    fig, ax = plt.subplots(figsize=(7, 3.2))
    colors = ["#4C78A8", "#F58518", "#54A24B", "#B279A2", "#72B7B2"]
    ax.bar(classes, p_short, color=colors[: len(classes)])
    ax.set_ylim(0, 1)
    ax.set_ylabel("P(short reuse)")
    ax.set_title("Same local feature bin, noisy future labels")
    for idx, value in enumerate(p_short):
        ax.text(idx, value + 0.03, f"{value:.3f}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(label_mix_path, dpi=180)
    plt.close(fig)

    timeline_path = output_dir / "label_noise_timeline.png"
    epochs = sorted(by_epoch)
    values = []
    for epoch in epochs:
        yes = by_epoch[epoch][1]
        no = by_epoch[epoch][0]
        values.append(yes / (yes + no) if yes + no else 0.0)
    fig, ax = plt.subplots(figsize=(9, 2.8))
    ax.plot(epochs, values, color="#4C78A8", linewidth=1.5)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("P(short reuse)")
    ax.set_title("Stationary label-noise ratio over time")
    fig.tight_layout()
    fig.savefig(timeline_path, dpi=180)
    plt.close(fig)

    return [label_mix_path, timeline_path]


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
