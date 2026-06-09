#!/usr/bin/env python3
"""Generate one large-font throughput figure averaged across two cache sizes."""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
AGG_TABLE = HERE / "20260515-dual-cache-all-trace-throughput-table.md"
OUT_STEM = HERE / "20260518-throughput-cacheavg-largefont"
OUT_CSV = HERE / "20260518-throughput-cacheavg-largefont.csv"

ORDERED_KEYS = (
    ["LRU", "LHD", "ARC", "SIEVE", "S3-FIFO", "W-TinyLFU"] +
    ["LeCaR", "Cacheus", "GL-Cache", "LRB", "3L-Cache"] +
    ["RSD"]
)
DISPLAY_LABELS = {
    "LRU": "LRU",
    "LHD": "LHD",
    "ARC": "ARC",
    "SIEVE": "SIEVE",
    "S3-FIFO": "S3-FIFO",
    "W-TinyLFU": "W-TinyLFU",
    "LeCaR": "LeCaR",
    "Cacheus": "CACHEUS",
    "GL-Cache": "GL-Cache",
    "LRB": "LRB",
    "3L-Cache": "3L-Cache",
    "RSD": "RSM",
}

HEURISTIC_IDX = (0, 5)
LIGHTWEIGHT_IDX = (6, 8)
HEAVY_IDX = (9, 9)
LEARNING_IDX = (6, 10)

TICK_SIZE = 20
LABEL_SIZE = 22
BRACKET_SIZE = 18
GROUP_SIZE = 20
BAR_WIDTH = 0.62
BAR_SPACING = 0.98


def parse_qps_cell(text):
    text = text.strip()
    if not text or text == "-":
        return None
    return float(text.replace(",", ""))


def collect_values_from_aggregate_table():
    large = {}
    small = {}
    in_algo_table = False
    for raw_line in AGG_TABLE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("| step2 / RSD "):
            parts = [part.strip() for part in line.strip("|").split("|")]
            if len(parts) == 3:
                small["RSD"] = parse_qps_cell(parts[1])
                large["RSD"] = parse_qps_cell(parts[2])
            continue
        if line.startswith("| canonical_algo "):
            in_algo_table = True
            continue
        if not in_algo_table or not line.startswith("|") or line.startswith("|---"):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) != 5:
            continue
        canonical_algo, _, small_qps, _, large_qps = parts
        if canonical_algo == "3L-Cache (OMR/BMR avg)":
            label = "3L-Cache"
        elif canonical_algo.startswith("ThreeLCache-"):
            continue
        else:
            label = canonical_algo
        if label in ORDERED_KEYS:
            small_value = parse_qps_cell(small_qps)
            large_value = parse_qps_cell(large_qps)
            if small_value is not None:
                small[label] = small_value
            if large_value is not None:
                large[label] = large_value

    missing_large = [algo for algo in ORDERED_KEYS if algo not in large]
    missing_small = [algo for algo in ORDERED_KEYS if algo not in small]
    if missing_large or missing_small:
        raise ValueError(f"missing qps values: large={missing_large}, small={missing_small}")
    return large, small


def build_color_map():
    greys = plt.get_cmap("Greys")
    blues = plt.get_cmap("Blues")
    reds = plt.get_cmap("Reds")
    colors = {}
    for algo, stop in zip(ORDERED_KEYS[0:6], np.linspace(0.20, 0.55, 6)):
        colors[algo] = greys(stop)
    for algo, stop in zip(["LeCaR", "Cacheus", "GL-Cache", "3L-Cache"], np.linspace(0.32, 0.60, 4)):
        colors[algo] = blues(stop)
    colors["LRB"] = blues(0.92)
    colors["RSD"] = reds(0.78)
    return colors


def draw_bracket(ax, trans, x_start, x_end, y_line, label, y_text,
                 tick_size=0.025, fontsize=BRACKET_SIZE):
    margin = BAR_WIDTH * 0.55
    ax.plot([x_start - margin, x_end + margin], [y_line, y_line], color="black",
            linewidth=1.2, transform=trans, clip_on=False)
    for x_tick in (x_start - margin, x_end + margin):
        ax.plot([x_tick, x_tick], [y_line, y_line + tick_size],
                color="black", linewidth=1.2, transform=trans, clip_on=False)
    ax.text((x_start + x_end) / 2, y_text, label, ha="center", va="top",
            fontsize=fontsize, fontweight="bold", transform=trans)


def write_average_csv(large, small, average):
    with OUT_CSV.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["algo", "cache01_qps", "cache0001_qps", "avg_qps"])
        for algo in ORDERED_KEYS:
            writer.writerow([algo, large[algo], small[algo], average[algo]])


def draw_average(average):
    plt.rcParams.update({
        "font.size": TICK_SIZE,
        "axes.labelsize": LABEL_SIZE,
        "xtick.labelsize": TICK_SIZE,
        "ytick.labelsize": TICK_SIZE,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    color_map = build_color_map()
    values = [average[algo] for algo in ORDERED_KEYS]
    colors = [color_map[algo] for algo in ORDERED_KEYS]
    display_labels = [DISPLAY_LABELS[algo] for algo in ORDERED_KEYS]
    x_positions = np.arange(len(ORDERED_KEYS)) * BAR_SPACING

    fig, ax = plt.subplots(figsize=(11.2, 8.8))
    ax.bar(x_positions, values, width=BAR_WIDTH, color=colors,
           edgecolor="black", linewidth=0.8)
    ax.set_xlim(x_positions[0] - 0.58, x_positions[-1] + 0.58)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(display_labels)
    ax.set_yscale("log")
    ax.set_ylabel("Throughput (req/s)", fontweight="bold")
    ax.grid(axis="y", which="both", linestyle="--", alpha=0.35, linewidth=0.8)
    ax.tick_params(axis="x", rotation=45, pad=4)
    ax.tick_params(axis="y", pad=4)
    for tick_label in ax.get_xticklabels():
        tick_label.set_horizontalalignment("right")
        tick_label.set_rotation_mode("anchor")
        tick_label.set_fontweight("bold")
    for tick_label in ax.get_yticklabels():
        tick_label.set_fontweight("bold")

    from matplotlib.transforms import blended_transform_factory
    trans = blended_transform_factory(ax.transData, ax.transAxes)

    draw_bracket(ax, trans, x_positions[LIGHTWEIGHT_IDX[0]], x_positions[LIGHTWEIGHT_IDX[1]],
                 -0.30, "Lightweight", -0.37)
    draw_bracket(ax, trans, x_positions[HEAVY_IDX[0]], x_positions[HEAVY_IDX[1]],
                 -0.30, "Heavy", -0.37)
    draw_bracket(ax, trans, x_positions[HEURISTIC_IDX[0]], x_positions[HEURISTIC_IDX[1]],
                 -0.48, "Heuristic-based", -0.56,
                 fontsize=GROUP_SIZE)
    draw_bracket(ax, trans, x_positions[LEARNING_IDX[0]], x_positions[LEARNING_IDX[1]],
                 -0.48, "Learning-based", -0.56,
                 fontsize=GROUP_SIZE)

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.43, left=0.15, right=0.99, top=0.98)
    fig.savefig(OUT_STEM.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.03)
    fig.savefig(OUT_STEM.with_suffix(".png"), dpi=300, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    print(f"[done] wrote {OUT_STEM.with_suffix('.pdf')}")
    print(f"[done] wrote {OUT_STEM.with_suffix('.png')}")


def main():
    large, small = collect_values_from_aggregate_table()
    average = {algo: (large[algo] + small[algo]) / 2 for algo in ORDERED_KEYS}
    write_average_csv(large, small, average)
    draw_average(average)


if __name__ == "__main__":
    main()