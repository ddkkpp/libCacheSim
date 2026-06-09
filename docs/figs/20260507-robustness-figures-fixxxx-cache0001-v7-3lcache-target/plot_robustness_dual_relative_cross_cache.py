#!/usr/bin/env python3
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd


for font_path in [
    "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Bold.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Italic.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Bold_Italic.ttf",
]:
    if Path(font_path).exists():
        font_manager.fontManager.addfont(font_path)

matplotlib.rcParams["font.family"] = "Times New Roman"
matplotlib.rcParams["font.serif"] = ["Times New Roman", "Nimbus Roman", "Liberation Serif", "DejaVu Serif"]
matplotlib.rcParams["mathtext.fontset"] = "stix"

HERE = Path(__file__).resolve().parent

LARGE_RELATIVE_CSV = HERE / "dual_avg_relative_cache01.csv"
SMALL_RELATIVE_CSV = HERE / "dual_avg_relative_cache0001.csv"

OMR_OUT = HERE / "dual_avg_relative_omr.pdf"
BMR_OUT = HERE / "dual_avg_relative_bmr.pdf"

FONT_SCALE = 3.5
FONT_LABEL = int(10 * FONT_SCALE)
FONT_TICK = int(8 * FONT_SCALE)
FONT_VALUE = int(6 * FONT_SCALE)
LEFT_COLOR = "#2E86AB"
RIGHT_COLOR = "#F18F01"


def load_cross_cache_relative_data():
    large = pd.read_csv(LARGE_RELATIVE_CSV)
    small = pd.read_csv(SMALL_RELATIVE_CSV)

    expected_cols = {"algo", "algo_display", "mr_value", "bmr_value"}
    if set(large.columns) != expected_cols or set(small.columns) != expected_cols:
        raise ValueError("dual_avg_relative.csv schema mismatch")

    algo_order = large["algo"].tolist()
    if small["algo"].tolist() != algo_order:
        raise ValueError("large/small cache algo order mismatch")

    merged = large.rename(
        columns={
            "mr_value": "omr_large",
            "bmr_value": "bmr_large",
        }
    ).merge(
        small[["algo", "mr_value", "bmr_value"]].rename(
            columns={
                "mr_value": "omr_small",
                "bmr_value": "bmr_small",
            }
        ),
        on="algo",
        how="inner",
        validate="one_to_one",
    )

    return merged


def set_dual_ticks(ax, values):
    lim = float(np.nanmax(np.abs(values))) * 1.15
    lim = max(0.2, math.ceil(lim / 0.2) * 0.2)
    ax.set_xlim(-lim, lim)
    ticks = np.arange(-lim, lim + 1e-9, 0.2)
    ticks = sorted(set(round(float(tick), 4) for tick in ticks))
    ax.set_xticks(ticks)
    ax.set_xticklabels(
        ["0" if abs(tick) < 1e-9 else f"{abs(tick):.1f}" for tick in ticks],
        fontsize=FONT_TICK,
        fontweight="bold",
    )
    return lim


def add_side_labels(ax):
    ax.text(
        0.28,
        1.025,
        "Large cache size",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=FONT_LABEL,
        fontweight="bold",
        color=LEFT_COLOR,
        clip_on=False,
    )
    ax.text(
        0.78,
        1.025,
        "Small cache size",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=FONT_LABEL,
        fontweight="bold",
        color=RIGHT_COLOR,
        clip_on=False,
    )


def annotate_bar_values(ax, left_vals, right_vals, lim):
    offset = lim * 0.035
    for idx, (left_val, right_val) in enumerate(zip(left_vals, right_vals)):
        ax.text(
            -left_val - offset,
            idx,
            f"{left_val:.3f}",
            ha="right",
            va="center",
            fontsize=FONT_VALUE,
            fontweight="bold",
            color=LEFT_COLOR,
        )
        ax.text(
            right_val + offset,
            idx,
            f"{right_val:.3f}",
            ha="left",
            va="center",
            fontsize=FONT_VALUE,
            fontweight="bold",
            color=RIGHT_COLOR,
        )


def render_metric(df, left_col, right_col, out_path):
    labels = df["algo_display"].tolist()
    left_vals = df[left_col].to_numpy(dtype=float)
    right_vals = df[right_col].to_numpy(dtype=float)

    y = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(12, 7), dpi=150)
    ax.barh(y, -left_vals, color=LEFT_COLOR, alpha=0.85)
    ax.barh(y, right_vals, color=RIGHT_COLOR, alpha=0.75)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=FONT_TICK, fontweight="bold")
    lim = set_dual_ticks(ax, np.concatenate([left_vals, right_vals]))
    ax.axvline(0, color="black", linewidth=1.0, alpha=0.8)
    ax.grid(axis="x", alpha=0.25)
    annotate_bar_values(ax, left_vals, right_vals, lim)
    add_side_labels(ax)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out_path, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def main():
    data = load_cross_cache_relative_data()
    render_metric(data, "omr_large", "omr_small", OMR_OUT)
    render_metric(data, "bmr_large", "bmr_small", BMR_OUT)
    print(f"omr_out={OMR_OUT}")
    print(f"bmr_out={BMR_OUT}")


if __name__ == "__main__":
    main()