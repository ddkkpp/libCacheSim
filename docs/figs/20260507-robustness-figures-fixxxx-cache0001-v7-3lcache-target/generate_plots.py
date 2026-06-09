#!/usr/bin/env python3
import math
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib import ticker
import numpy as np
import pandas as pd

for _p in [
    "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Bold.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Italic.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Bold_Italic.ttf",
]:
    if Path(_p).exists():
        font_manager.fontManager.addfont(_p)

matplotlib.rcParams["font.family"] = "Times New Roman"
matplotlib.rcParams["font.serif"] = ["Times New Roman", "Nimbus Roman", "Liberation Serif", "DejaVu Serif"]
matplotlib.rcParams["mathtext.fontset"] = "stix"

def find_repo_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / "CMakeLists.txt").exists() and (parent / "libCacheSim").is_dir():
            return parent
    raise RuntimeError(f"cannot locate repository root from {start}")


ROOT = find_repo_root(Path(__file__).resolve())
SRC_DIR = ROOT / "docs/20260423-ablation-per-group-fixxxx-cache0001/cmaes版本LOH"
BASELINE_MD = ROOT / "docs/20260423-ablation-per-group-fixxxx-cache0001/cmaes版本LOH/baseline_summary_v7_3lcache-target.md"
ROBUSTNESS_MD = ROOT / "docs/20260423-ablation-per-group-fixxxx-cache0001/cmaes版本LOH/robustness_summary_v7_3lcache-target.md"
OUT_DIR = Path(__file__).resolve().parent
DOC_OUT = ROOT / "docs/20260507-ROBUSTNESS_PLOTS_STATS-fixxxx-cache0001-v7-3lcache-target.md"

GROUPS = [
    "alibabaBlock",
    "metaCDN",
    "metaKV",
    "tencentBlock",
    "tencentPhoto",
    "wiki",
]

ALGO_ORDER = [
    "LRU",
    "LHD",
    "ARC",
    "Sieve",
    "S3FIFO-0.1000-2",
    "WTinyLFU-w0.01-SLRU",
    "LeCaR",
    "Cacheus",
    "GLCache",
    "LRB-BMR",
    "ThreeLCache-target",
    "best_LOH",
]

DISPLAY_NAME = {
    "LRU": "LRU",
    "LHD": "LHD",
    "ARC": "ARC",
    "Sieve": "SIEVE",
    "S3FIFO-0.1000-2": "S3-FIFO",
    "WTinyLFU-w0.01-SLRU": "W-TinyLFU",
    "LeCaR": "LeCaR",
    "Cacheus": "CACHEUS",
    "GLCache": "GL-Cache",
    "LRB-BMR": "LRB",
    "ThreeLCache-target": "3L-Cache",
    "best_LOH": "RSM",
}

GROUP_LABEL = {
    "alibabaBlock": "Alibaba",
    "metaCDN": "Meta CDN",
    "metaKV": "Meta KV",
    "tencentBlock": "Tencent CBS",
    "tencentPhoto": "TencentPhoto",
    "wiki": "Wikipedia",
}

PLOT_ALGOS_NO_LRU = [a for a in ALGO_ORDER if a != "LRU"]
FONT_SCALE = 3.5
FONT_LABEL = int(10 * FONT_SCALE)
FONT_TICK = int(8 * FONT_SCALE)
FONT_BOX_AXIS_LABEL = int(FONT_LABEL * 1.5)
FONT_BOX_ALGO_TICK = 48
FONT_LEGEND = int(8 * FONT_SCALE)
FONT_TITLE = int(11 * FONT_SCALE)
LOG_EPS = 1e-12


def metric_full_name(metric_key):
    return "Object miss ratio" if metric_key == "mr" else "Byte miss ratio"


def metric_variant_label(vk):
    return vk.replace("relative", "relative to LRU")


def finish_plot_title_below(fig, text):
    fig.text(0.5, 0.01, text, ha="center", va="bottom", fontsize=FONT_TITLE, fontweight="bold")


def split_md_row(line: str):
    # Keep internal empty cells to avoid column-shift on trailing blank fields.
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_num(cell: str):
    t = cell.replace("**", "").replace(",", "").strip()
    if t in ("", "-", "—", "NA", "N/A"):
        return np.nan
    try:
        return float(t)
    except ValueError:
        return np.nan


def parse_table_after(lines, idx):
    i = idx + 1
    while i < len(lines) and not lines[i].startswith("|"):
        i += 1
    if i >= len(lines):
        return [], []
    header = split_md_row(lines[i])
    i += 1
    if i < len(lines) and lines[i].startswith("|"):
        i += 1
    rows = []
    while i < len(lines) and lines[i].startswith("|"):
        rows.append(split_md_row(lines[i]))
        i += 1
    return header, rows


def parse_group(group_name: str):
    path = SRC_DIR / f"{group_name}.md"
    lines = path.read_text(encoding="utf-8").splitlines()

    n_req = {}
    one_hit = {}
    mr = {}
    bmr = {}
    loh_mr_v7 = {}
    loh_bmr_v7 = {}

    def find_algo_col(idx_map, algo, metric_kind):
        if algo in idx_map:
            return idx_map[algo]
        # Group tables use ThreeLCache-{OMR,BMR} while plots expect ThreeLCache-target.
        if algo == "ThreeLCache-target":
            if metric_kind == "mr":
                for c in ("ThreeLCache-OMR", "ThreeLCache-target", "ThreeLCache"):
                    if c in idx_map:
                        return idx_map[c]
            else:
                for c in ("ThreeLCache-BMR", "ThreeLCache-target", "ThreeLCache"):
                    if c in idx_map:
                        return idx_map[c]
        return None

    for i, line in enumerate(lines):
        if line.startswith("## 表1"):
            h, rows = parse_table_after(lines, i)
            idx = {k: j for j, k in enumerate(h)}
            if "trace" in idx and "n_req" in idx:
                for r in rows:
                    tr = r[idx["trace"]]
                    if tr.startswith("**"):
                        continue
                    n_req[tr] = int(r[idx["n_req"]].replace(",", ""))
                    if "one_hit" in idx and idx["one_hit"] < len(r):
                        one_hit[tr] = parse_num(r[idx["one_hit"]])

        if line.startswith("## 表2"):
            h, rows = parse_table_after(lines, i)
            idx = {k: j for j, k in enumerate(h)}
            if "trace" in idx:
                for r in rows:
                    tr = r[idx["trace"]]
                    if tr.startswith("**"):
                        continue
                    # v7 MR strategy: f001_orig, fallback to f100_ns.
                    val = np.nan
                    if "f001_orig" in idx and idx["f001_orig"] < len(r):
                        val = parse_num(r[idx["f001_orig"]])
                    if pd.isna(val) and "f100_ns" in idx and idx["f100_ns"] < len(r):
                        val = parse_num(r[idx["f100_ns"]])
                    loh_mr_v7[tr] = val

        if line.startswith("## 表3"):
            h, rows = parse_table_after(lines, i)
            idx = {k: j for j, k in enumerate(h)}
            if "trace" in idx:
                for r in rows:
                    tr = r[idx["trace"]]
                    if tr.startswith("**"):
                        continue
                    # v7 BMR strategy: one_hit<=0.72 -> f100_ns, else f101_orig; fallback f100_ns.
                    selected_col = "f100_ns" if one_hit.get(tr, np.nan) <= 0.72 else "f101_orig"
                    val = np.nan
                    if selected_col in idx and idx[selected_col] < len(r):
                        val = parse_num(r[idx[selected_col]])
                    if pd.isna(val) and "f100_ns" in idx and idx["f100_ns"] < len(r):
                        val = parse_num(r[idx["f100_ns"]])
                    loh_bmr_v7[tr] = val

        if line.startswith("## 表4"):
            h, rows = parse_table_after(lines, i)
            idx = {k: j for j, k in enumerate(h)}
            for r in rows:
                tr = r[idx["trace"]]
                if tr.startswith("**"):
                    continue
                mr[tr] = {}
                for a in ALGO_ORDER:
                    j = find_algo_col(idx, a, "mr")
                    if j is None:
                        continue
                    mr[tr][a] = parse_num(r[j]) if j < len(r) else np.nan
                # For plotting, RSD must follow v7-selected LOH rather than table4 auto-compound best_LOH.
                mr[tr]["best_LOH"] = loh_mr_v7.get(tr, np.nan)

        if line.startswith("## 表5"):
            h, rows = parse_table_after(lines, i)
            idx = {k: j for j, k in enumerate(h)}
            for r in rows:
                tr = r[idx["trace"]]
                if tr.startswith("**"):
                    continue
                bmr[tr] = {}
                for a in ALGO_ORDER:
                    j = find_algo_col(idx, a, "bmr")
                    if j is None:
                        continue
                    bmr[tr][a] = parse_num(r[j]) if j < len(r) else np.nan
                # For plotting, RSD must follow v7-selected LOH rather than table5 auto-compound best_LOH.
                bmr[tr]["best_LOH"] = loh_bmr_v7.get(tr, np.nan)

    traces = sorted(set(n_req.keys()) & set(mr.keys()) & set(bmr.keys()))
    rows = []
    for tr in traces:
        for a in ALGO_ORDER:
            if a not in mr[tr] or a not in bmr[tr]:
                continue
            rows.append(
                {
                    "group": group_name,
                    "trace": tr,
                    "n_req": n_req[tr],
                    "algo": a,
                    "mr": mr[tr][a],
                    "bmr": bmr[tr][a],
                }
            )
    return pd.DataFrame(rows)


def enrich(df):
    out = df.copy()

    lru = out[out["algo"] == "LRU"][["group", "trace", "mr", "bmr"]].rename(
        columns={"mr": "mr_lru", "bmr": "bmr_lru"}
    )
    out = out.merge(lru, on=["group", "trace"], how="left")

    out["mr_rel"] = out["mr"] / out["mr_lru"]
    out["bmr_rel"] = out["bmr"] / out["bmr_lru"]

    # Weight should be computed per trace (once), not per (trace, algo) row.
    trace_w = out[["group", "trace", "n_req"]].drop_duplicates().copy()
    trace_w["w"] = trace_w["n_req"] / trace_w.groupby("group")["n_req"].transform("sum")
    out = out.merge(trace_w[["group", "trace", "w"]], on=["group", "trace"], how="left")

    out["mr_w"] = out["mr"] * out["w"]
    out["bmr_w"] = out["bmr"] * out["w"]
    out["mr_rel_w"] = out["mr_rel"] * out["w"]
    out["bmr_rel_w"] = out["bmr_rel"] * out["w"]

    return out


def make_dirs():
    for p in [
        OUT_DIR,
        OUT_DIR / "boxplots",
        OUT_DIR / "ranklines",
        OUT_DIR / "dualaxis",
        OUT_DIR / "percentiles",
        OUT_DIR / "data",
        OUT_DIR / "logs",
    ]:
        p.mkdir(parents=True, exist_ok=True)


def _box_ylabel(metric, vk):
    if metric == "mr":
        base = "OMR"
    else:
        base = "BMR"
    if vk == "raw":
        return base
    if vk == "weighted":
        return f"Weighted {base}"
    if vk == "relative":
        return f"Relative {base}"
    return f"Weighted Relative {base}"


def _fix_linear_ticks(ax, step=0.2, narrow_step=0.1, include_one=True):
    """Apply linear-axis ticks. Default step=0.2; if too sparse, fallback to 0.1."""
    ax.figure.canvas.draw()
    ylo, yhi = ax.get_ylim()
    if not (np.isfinite(ylo) and np.isfinite(yhi)):
        return
    if yhi < ylo:
        ylo, yhi = yhi, ylo
    if include_one:
        ylo = min(ylo, 1.0)
        yhi = max(yhi, 1.0)
        ax.set_ylim(ylo, yhi)

    def _fmt(x, pos):
        return f"{x:.1f}"

    def _ticks_with(s):
        start = math.floor(ylo / s) * s
        vals = np.arange(start, yhi + s * 0.51, s)
        out = [round(float(v), 1) for v in vals if ylo - 1e-9 <= v <= yhi + 1e-9]
        if include_one:
            out.append(1.0)
        return sorted(set(out))

    ticks = _ticks_with(step)
    if len(ticks) <= 1:
        ticks = _ticks_with(narrow_step)
    if len(ticks) <= 1:
        ticks = sorted(set([round(ylo, 1), round(yhi, 1), 1.0 if include_one else round(ylo, 1)]))

    ax.yaxis.set_major_locator(ticker.FixedLocator(ticks))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(_fmt))
    ax.yaxis.set_minor_locator(ticker.NullLocator())


def _positive_for_log(vals):
    arr = np.array(vals, dtype=float)
    arr = arr[np.isfinite(arr) & (arr > 0)]
    if arr.size == 0:
        return np.array([], dtype=float)
    return arr


def _safe_scatter_vals(vals):
    """Keep finite values for linear-axis scatter."""
    arr = np.array(vals, dtype=float)
    arr[~np.isfinite(arr)] = np.nan
    return arr


def _dual_side_label(col):
    """Derive human-readable label from column name like 'mr_raw', 'bmr_rel_w'."""
    parts = col.split("_")
    base = "Object miss ratio" if parts[0] == "mr" else "Byte miss ratio"
    suffixes = []
    if "rel" in parts:
        suffixes.append("relative to LRU")
    if parts[-1] == "w":
        suffixes.append("weighted")
    if suffixes:
        return f"{base} ({', '.join(suffixes)})"
    return base


def _annotate_zero_bars(ax, m1_vals, m2_vals, lim):
    """For bars whose value is 0, draw a short elbow-arrow annotation pointing to 0."""
    ZERO_THRESH = 1e-9
    for i, (mv, bv) in enumerate(zip(m1_vals, m2_vals)):
        if abs(mv) < ZERO_THRESH:
            ax.annotate(
                "0",
                xy=(0, i),
                xytext=(-lim * 0.18, i + 0.4),
                ha="right",
                va="center",
                fontsize=FONT_TICK,
                color="#2E86AB",
                arrowprops=dict(
                    arrowstyle="->",
                    color="#2E86AB",
                    lw=1.2,
                    connectionstyle="arc3,rad=0.3",
                ),
            )
        if abs(bv) < ZERO_THRESH:
            ax.annotate(
                "0",
                xy=(0, i),
                xytext=(lim * 0.18, i + 0.4),
                ha="left",
                va="center",
                fontsize=FONT_TICK,
                color="#F18F01",
                arrowprops=dict(
                    arrowstyle="->",
                    color="#F18F01",
                    lw=1.2,
                    connectionstyle="arc3,rad=-0.3",
                ),
            )


def _add_dual_side_labels(ax, left_label, right_label):
    """Add metric name labels below the x-axis, pointing left (MR) and right (BMR)."""
    ax.text(
        0.35, -0.12,
        f"\u2190 {left_label}",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=FONT_LABEL,
        fontweight="bold",
        color="#2E86AB",
        clip_on=False,
    )
    ax.text(
        0.72, -0.12,
        f"{right_label} \u2192",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=FONT_LABEL,
        fontweight="bold",
        color="#F18F01",
        clip_on=False,
    )


def save_boxplots(df):
    box_data_dir = OUT_DIR / "boxplots" / "data"
    box_data_dir.mkdir(parents=True, exist_ok=True)

    variants = {
        "raw": {"mr": "mr", "bmr": "bmr"},
        "weighted": {"mr": "mr_w", "bmr": "bmr_w"},
        "relative": {"mr": "mr_rel", "bmr": "bmr_rel"},
        "relative_weighted": {"mr": "mr_rel_w", "bmr": "bmr_rel_w"},
    }

    count = 0
    for g in GROUPS:
        dg = df[df["group"] == g]
        group_label = GROUP_LABEL.get(g, g)
        for metric in ["mr", "bmr"]:
            metric_name = metric_full_name(metric)
            for vk, m in variants.items():
                col = m[metric]
                data = [_positive_for_log(dg[dg["algo"] == a][col].dropna().values) for a in PLOT_ALGOS_NO_LRU]

                plot_df = dg[dg["algo"].isin(PLOT_ALGOS_NO_LRU)][["trace", "algo", col]].copy()
                plot_df = plot_df.rename(columns={col: "value"})
                plot_df["algo_display"] = plot_df["algo"].map(DISPLAY_NAME)
                plot_df.to_csv(box_data_dir / f"box_{g}_{metric}_{vk}.csv", index=False)

                fig, ax = plt.subplots(figsize=(18, 6), dpi=150)
                ax.boxplot(data, tick_labels=[DISPLAY_NAME[a] for a in PLOT_ALGOS_NO_LRU], showfliers=False)
                # 在每个箱体上额外标出均值（菱形标记，无图例）
                means = [d.mean() if len(d) > 0 else float("nan") for d in data]
                ax.scatter(
                    range(1, len(PLOT_ALGOS_NO_LRU) + 1),
                    means,
                    marker="D",
                    color="tab:red",
                    s=40,
                    zorder=5,
                )
                ax.set_ylabel(_box_ylabel(metric, vk), fontsize=FONT_BOX_AXIS_LABEL, fontweight="bold", labelpad=16)
                ax.set_yscale("linear")
                ax.yaxis.set_major_locator(ticker.NullLocator())
                ax.yaxis.set_major_formatter(ticker.NullFormatter())
                ax.yaxis.set_minor_locator(ticker.NullLocator())
                ax.set_xlim(0.3, len(PLOT_ALGOS_NO_LRU) + 0.7)
                ax.tick_params(axis="x", rotation=30, labelsize=FONT_BOX_ALGO_TICK, pad=50)
                ax.tick_params(axis="y", labelsize=FONT_TICK)
                for lb in ax.get_xticklabels() + ax.get_yticklabels():
                    lb.set_fontweight("bold")
                for lb in ax.get_xticklabels():
                    lb.set_ha("center")
                    lb.set_rotation_mode("anchor")
                ax.grid(axis="y", alpha=0.25)

                fig.tight_layout(pad=0.15)
                out = OUT_DIR / "boxplots" / f"box_{g}_{metric}_{vk}.pdf"
                _fix_linear_ticks(ax)
                fig.savefig(out, bbox_inches="tight", pad_inches=0.01)
                plt.close(fig)
                count += 1
    return count


def aggregate_for_rank(df):
    rows = []
    for g in GROUPS:
        dg = df[df["group"] == g]
        for a in ALGO_ORDER:
            da = dg[dg["algo"] == a]
            rows.append(
                {
                    "group": g,
                    "algo": a,
                    "mr_raw": da["mr"].mean(),
                    "bmr_raw": da["bmr"].mean(),
                    "mr_rel": da["mr_rel"].mean(),
                    "bmr_rel": da["bmr_rel"].mean(),
                    "mr_w": da["mr_w"].sum(),
                    "bmr_w": da["bmr_w"].sum(),
                    "mr_rel_w": da["mr_rel_w"].sum(),
                    "bmr_rel_w": da["bmr_rel_w"].sum(),
                }
            )
    return pd.DataFrame(rows)


def rank_series(vals_by_algo):
    ordered = sorted(vals_by_algo.items(), key=lambda kv: (kv[1], kv[0]))
    return {algo: i + 1 for i, (algo, _) in enumerate(ordered)}


def load_rank_md_data():
    lines = ROBUSTNESS_MD.read_text(encoding="utf-8").splitlines()
    section_to_key = {
        "## MR 平均值 排名": "mr_raw",
        "## BMR 平均值 排名": "bmr_raw",
        "## MR 加权平均值 排名": "mr_w",
        "## BMR 加权平均值 排名": "bmr_w",
        "## MR 相对LRU比例 排名": "mr_rel",
        "## BMR 相对LRU比例 排名": "bmr_rel",
        "## MR 加权相对LRU比例 排名": "mr_rel_w",
        "## BMR 加权相对LRU比例 排名": "bmr_rel_w",
    }
    out = {}
    for i, line in enumerate(lines):
        key = section_to_key.get(line.strip())
        if key is None:
            continue
        h, rows, _ = _parse_md_table(lines, i)
        if not h:
            continue
        idx = {k: j for j, k in enumerate(h)}
        if "group" not in idx:
            continue
        table = {a: [] for a in ALGO_ORDER}
        for r in rows:
            g = r[idx["group"]]
            if g.startswith("**") or g not in GROUPS:
                continue
            for a in ALGO_ORDER:
                col_name = a
                if a not in idx and a == "ThreeLCache-target":
                    col_name = next((c for c in ("ThreeLCache-target", "ThreeLCache-OMR", "ThreeLCache") if c in idx), None)
                elif a not in idx:
                    col_name = None
                if col_name is None:
                    table[a].append(np.nan)
                else:
                    j = idx[col_name]
                    table[a].append(parse_num(r[j]) if j < len(r) else np.nan)
        out[key] = table
    return out


def save_ranklines(agg):
    rank_data_dir = OUT_DIR / "ranklines" / "data"
    rank_data_dir.mkdir(parents=True, exist_ok=True)

    metric_map = {
        "mr_raw": "Object miss ratio raw",
        "mr_w": "Object miss ratio weighted",
        "mr_rel": "Object miss ratio relative to LRU",
        "mr_rel_w": "Object miss ratio relative to LRU weighted",
        "bmr_raw": "Byte miss ratio raw",
        "bmr_w": "Byte miss ratio weighted",
        "bmr_rel": "Byte miss ratio relative to LRU",
        "bmr_rel_w": "Byte miss ratio relative to LRU weighted",
    }

    rank_md_data = load_rank_md_data()

    marker_map = {
        "LRU": "o",
        "LHD": "s",
        "ARC": "^",
        "Sieve": "D",
        "S3FIFO-0.1000-2": "P",
        "WTinyLFU-w0.01-SLRU": "X",
        "LeCaR": "v",
        "Cacheus": "<",
        "GLCache": ">",
        "LRB-BMR": "*",
        "ThreeLCache-target": "h",
        "best_LOH": "8",
    }

    count = 0
    for col, title in metric_map.items():
        if col in rank_md_data:
            rank_mat = rank_md_data[col]
        else:
            rank_mat = {a: [] for a in ALGO_ORDER}
            for g in GROUPS:
                sub = agg[agg["group"] == g]
                r = rank_series({row["algo"]: float(row[col]) for _, row in sub.iterrows()})
                for a in ALGO_ORDER:
                    rank_mat[a].append(r[a])

        rank_df = pd.DataFrame({"algo": ALGO_ORDER, "algo_display": [DISPLAY_NAME[a] for a in ALGO_ORDER]})
        for i, g in enumerate(GROUPS):
            rank_df[g] = [rank_mat[a][i] for a in ALGO_ORDER]
        rank_df.to_csv(rank_data_dir / f"rank_{col}.csv", index=False)

        fig, ax = plt.subplots(figsize=(18, 9), dpi=150)
        x = np.arange(len(GROUPS), dtype=float) + 0.65
        color_map = {
            "LRU": "#E41A1C",              # red
            "LHD": "#4169E1",              # royal blue
            "ARC": "#00BFFF",              # deep sky blue
            "Sieve": "#FF7F00",            # orange
            "S3FIFO-0.1000-2": "#800080",  # purple
            "WTinyLFU-w0.01-SLRU": "#008B8B",  # dark cyan
            "LeCaR": "#8B4513",            # saddle brown
            "Cacheus": "#FF69B4",          # hot pink
            "GLCache": "#2E8B57",          # sea green
            "LRB-BMR": "#9ACD32",          # yellow green
            "ThreeLCache-target": "#006400",  # dark green
            "best_LOH": "#8B0000",         # dark red
        }
        for a in ALGO_ORDER:
            lw = 2.4 if a in ("best_LOH", "LRU") else 1.4
            alpha = 0.95 if a == "best_LOH" else 0.8
            ax.plot(
                x,
                rank_mat[a],
                marker=marker_map[a],
                color=color_map[a],
                linewidth=lw,
                alpha=alpha,
                markersize=12,
                label=DISPLAY_NAME[a],
            )
            # Replace legend by in-plot left labels next to each line.
            x_text = x[0] - 0.09
            y_text = rank_mat[a][0]
            ax.text(
                x_text,
                y_text,
                DISPLAY_NAME[a],
                fontsize=FONT_LEGEND,
                fontweight="bold",
                color=color_map[a],
                ha="right",
                va="center",
                clip_on=True,
            )

        ax.set_xticks(x)
        ax.set_xticklabels([GROUP_LABEL.get(g, g) for g in GROUPS], rotation=20, fontsize=FONT_TICK, fontweight="bold")
        ax.set_ylabel("Rank", fontsize=FONT_LABEL, fontweight="bold")
        ax.set_ylim(len(ALGO_ORDER) + 0.5, 0.5)
        ax.set_xlim(-0.15, x[-1] + 0.35)
        ax.set_yticks(np.arange(1, len(ALGO_ORDER) + 1, 2))
        ax.grid(axis="y", alpha=0.25)
        ax.tick_params(axis="y", labelsize=FONT_TICK)
        for lb in ax.get_yticklabels():
            lb.set_fontweight("bold")

        fig.tight_layout(rect=(0.03, 0, 1, 1))
        fig.savefig(OUT_DIR / "ranklines" / f"rank_{col}.pdf")
        plt.close(fig)
        count += 1
    return count


def _set_dualaxis_ticks(ax, lim):
    lim = max(0.2, math.ceil(lim / 0.2) * 0.2)
    ax.set_xlim(-lim, lim)
    # 两侧共用 0 刻度，步长 0.2，不加 ±0.05 偏移刻度
    ticks = np.arange(-lim, lim + 1e-9, 0.2)
    ticks = sorted(set([round(t, 4) for t in ticks]))
    ax.set_xticks(ticks)
    ax.set_xticklabels(
        ["0" if abs(v) < 1e-9 else f"{abs(v):.1f}" for v in ticks],
        fontsize=FONT_TICK,
        fontweight="bold",
    )


def load_robustness_md_dual_data():
    """Read per-group per-algo values from ROBUSTNESS_MD, excluding cloudphysics."""
    lines = ROBUSTNESS_MD.read_text(encoding="utf-8").splitlines()
    section_to_key = {
        "## MR Norm Score（按组，绝对值）": "mr_raw",
        "## BMR Norm Score（按组，绝对值）": "bmr_raw",
        "## MR Norm Score（按组，加权值）": "mr_w",
        "## BMR Norm Score（按组，加权值）": "bmr_w",
        "## MR Norm Score（按组，相对LRU）": "mr_rel",
        "## BMR Norm Score（按组，相对LRU）": "bmr_rel",
        "## MR Norm Score（按组，加权相对LRU）": "mr_rel_w",
        "## BMR Norm Score（按组，加权相对LRU）": "bmr_rel_w",
    }
    tables = {}
    for i, line in enumerate(lines):
        key = section_to_key.get(line.strip())
        if key is None:
            continue
        h, rows, _ = _parse_md_table(lines, i)
        if not h:
            continue
        idx = {k: j for j, k in enumerate(h)}
        if "group" not in idx:
            continue
        per_algo = {a: [] for a in ALGO_ORDER}
        for r in rows:
            g = r[idx["group"]]
            if g.startswith("**") or g in ("cloudphysics", "avg", "avg rank"):
                continue
            for a in ALGO_ORDER:
                col_name = a
                if a not in idx:
                    # Try ThreeLCache aliases
                    if a == "ThreeLCache-target":
                        col_name = next((c for c in ("ThreeLCache-target", "ThreeLCache-OMR", "ThreeLCache") if c in idx), None)
                    else:
                        col_name = None
                else:
                    col_name = a
                if col_name is None:
                    per_algo[a].append(np.nan)
                else:
                    j = idx[col_name]
                    per_algo[a].append(parse_num(r[j]) if j < len(r) else np.nan)
        tables[key] = per_algo
    return tables


def save_dualaxis(agg):
    dual_data_dir = OUT_DIR / "dualaxis" / "data"
    dual_data_dir.mkdir(parents=True, exist_ok=True)

    pairs = [
        ("mr_raw", "bmr_raw", "Robustness Score", "avg_raw"),
        ("mr_w", "bmr_w", "Robustness Score", "avg_weighted"),
        ("mr_rel", "bmr_rel", "Robustness Score", "avg_relative"),
        ("mr_rel_w", "bmr_rel_w", "Robustness Score", "avg_relative_weighted"),
    ]

    count = 0
    algo_label = [DISPLAY_NAME[a] for a in ALGO_ORDER]
    md_data = load_robustness_md_dual_data()

    for c1, c2, title, tag in pairs:
        if c1 in md_data and c2 in md_data:
            m1_arr = np.array([np.nanmean(md_data[c1][a]) if md_data[c1][a] else np.nan for a in ALGO_ORDER])
            m2_arr = np.array([np.nanmean(md_data[c2][a]) if md_data[c2][a] else np.nan for a in ALGO_ORDER])
        else:
            m1_arr = agg.groupby("algo")[c1].mean().reindex(ALGO_ORDER).values
            m2_arr = agg.groupby("algo")[c2].mean().reindex(ALGO_ORDER).values
        m1 = pd.Series(m1_arr, index=ALGO_ORDER)
        m2 = pd.Series(m2_arr, index=ALGO_ORDER)

        pd.DataFrame(
            {
                "algo": ALGO_ORDER,
                "algo_display": algo_label,
                "mr_value": m1.values,
                "bmr_value": m2.values,
            }
        ).to_csv(dual_data_dir / f"dual_{tag}.csv", index=False)

        y = np.arange(len(ALGO_ORDER))
        fig, ax = plt.subplots(figsize=(12, 7), dpi=150)
        # 左 MR，右 BMR
        ax.barh(y, -m1.values, color="#2E86AB", alpha=0.85)
        ax.barh(y, m2.values, color="#F18F01", alpha=0.75)
        ax.set_yticks(y)
        ax.set_yticklabels(algo_label, fontsize=FONT_TICK, fontweight="bold")
        lim = max(float(np.nanmax(np.abs(m1.values))), float(np.nanmax(np.abs(m2.values)))) * 1.15
        _set_dualaxis_ticks(ax, lim)
        # 中心分界线
        ax.axvline(0, color="black", linewidth=1.0, alpha=0.8)
        ax.grid(axis="x", alpha=0.25)
        _annotate_zero_bars(ax, m1.values, m2.values, lim)
        _add_dual_side_labels(ax, "OMR", "BMR")
        fig.tight_layout(rect=(0, 0.14, 1, 1))
        fig.savefig(OUT_DIR / "dualaxis" / f"dual_{tag}.pdf")
        plt.close(fig)
        count += 1
    return count


def _parse_md_table(lines, start_idx):
    i = start_idx + 1
    while i < len(lines) and not lines[i].startswith("|"):
        i += 1
    if i >= len(lines):
        return [], [], i

    header = split_md_row(lines[i])
    i += 1
    if i < len(lines) and lines[i].startswith("|"):
        i += 1

    rows = []
    while i < len(lines) and lines[i].startswith("|"):
        rows.append(split_md_row(lines[i]))
        i += 1
    return header, rows, i


def load_norm_abs_tables():
    lines = ROBUSTNESS_MD.read_text(encoding="utf-8").splitlines()
    wanted = {
        "## MR Norm Score（按组，绝对值）": "mr",
        "## BMR Norm Score（按组，绝对值）": "bmr",
    }
    out = {}

    for i, line in enumerate(lines):
        key = wanted.get(line.strip())
        if not key:
            continue
        h, rows, _ = _parse_md_table(lines, i)
        if not h:
            continue
        idx = {k: j for j, k in enumerate(h)}
        if "group" not in idx:
            continue

        table = {}
        for r in rows:
            g = r[idx["group"]]
            if g.startswith("**"):
                continue
            vals = {}
            for a in ALGO_ORDER:
                if a in idx and idx[a] < len(r):
                    vals[a] = parse_num(r[idx[a]])
            table[g] = vals
        out[key] = table

    return out


def save_dualaxis_norm_abs():
    tabs = load_norm_abs_tables()
    mr_tab = tabs.get("mr", {})
    bmr_tab = tabs.get("bmr", {})
    groups = [g for g in GROUPS if g in mr_tab and g in bmr_tab]
    if not groups:
        return 0

    algo_label = [DISPLAY_NAME[a] for a in ALGO_ORDER]
    dual_data_dir = OUT_DIR / "dualaxis" / "data"
    dual_data_dir.mkdir(parents=True, exist_ok=True)

    mr_vals = []
    bmr_vals = []
    for a in ALGO_ORDER:
        mr_arr = np.array([mr_tab[g].get(a, np.nan) for g in groups], dtype=float)
        bmr_arr = np.array([bmr_tab[g].get(a, np.nan) for g in groups], dtype=float)
        mr_vals.append(float(np.nanmean(mr_arr)))
        bmr_vals.append(float(np.nanmean(bmr_arr)))

    mr_vals = np.array(mr_vals, dtype=float)
    bmr_vals = np.array(bmr_vals, dtype=float)

    pd.DataFrame(
        {
            "algo": ALGO_ORDER,
            "algo_display": algo_label,
            "mr_norm_abs_avg": mr_vals,
            "bmr_norm_abs_avg": bmr_vals,
        }
    ).to_csv(dual_data_dir / "dual_norm_abs_avg.csv", index=False)

    lim = max(float(np.nanmax(np.abs(mr_vals))), float(np.nanmax(np.abs(bmr_vals)))) * 1.15

    y = np.arange(len(ALGO_ORDER))
    fig, ax = plt.subplots(figsize=(12, 7), dpi=150)
    # 左 MR，右 BMR
    ax.barh(y, -mr_vals, color="#2E86AB", alpha=0.85)
    ax.barh(y, bmr_vals, color="#F18F01", alpha=0.75)
    ax.set_yticks(y)
    ax.set_yticklabels(algo_label, fontsize=FONT_TICK, fontweight="bold")
    _set_dualaxis_ticks(ax, lim)
    # 中心分界线
    ax.axvline(0, color="black", linewidth=1.0, alpha=0.8)
    ax.grid(axis="x", alpha=0.25)
    _annotate_zero_bars(ax, mr_vals, bmr_vals, lim)
    _add_dual_side_labels(ax, "OMR", "BMR")
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    fig.savefig(OUT_DIR / "dualaxis" / "dual_norm_abs_avg.pdf")
    plt.close(fig)

    return 1


def q_stats(vals):
    arr = np.array(vals, dtype=float)
    if arr.size == 0:
        return {
            "p10": np.nan,
            "p25": np.nan,
            "median": np.nan,
            "mean": np.nan,
            "p75": np.nan,
            "p90": np.nan,
        }
    return {
        "p10": float(np.percentile(arr, 10)),
        "p25": float(np.percentile(arr, 25)),
        "median": float(np.percentile(arr, 50)),
        "mean": float(np.mean(arr)),
        "p75": float(np.percentile(arr, 75)),
        "p90": float(np.percentile(arr, 90)),
    }


def mean_group_q_stats(df_algo, col):
    stats_by_group = []
    for group in GROUPS:
        vals = df_algo[df_algo["group"] == group][col].dropna().values
        if len(vals) == 0:
            continue
        stats_by_group.append(q_stats(vals))

    if not stats_by_group:
        return {
            "p10": np.nan,
            "p25": np.nan,
            "median": np.nan,
            "mean": np.nan,
            "p75": np.nan,
            "p90": np.nan,
        }

    out = {}
    for key in ["p10", "p25", "median", "mean", "p75", "p90"]:
        vals = [s[key] for s in stats_by_group if np.isfinite(s[key])]
        out[key] = float(np.mean(vals)) if vals else np.nan
    return out


def save_percentiles(df):
    pct_data_dir = OUT_DIR / "percentiles" / "data"
    pct_data_dir.mkdir(parents=True, exist_ok=True)

    variants = [
        ("mr", "OMR", "mr_raw"),
        ("mr_rel", "Relative OMR", "mr_relative"),
        ("bmr", "BMR", "bmr_raw"),
        ("bmr_rel", "Relative BMR", "bmr_relative"),
    ]

    marks = [
        ("p10", "o", "#FF0000"),  # 大红
        ("p25", "s", "#F28E2B"),  # 中橙
        ("median", "D", "#F6E58D"),  # 浅黄
        ("mean", "X", "#A8E6A3"),  # 浅绿
        ("p75", "^", "#2AA198"),  # 中青
        ("p90", "P", "#0B3C8A"),  # 深蓝
    ]

    all_tables = {"pooled": {}, "group_mean": {}}
    count = 0

    modes = [
        ("pooled", "All traces pooled", q_stats, "percentile_{tag}.csv", "percentile_{tag}.pdf"),
        (
            "group_mean",
            "Mean of per-group percentiles",
            mean_group_q_stats,
            "percentile_groupmean_{tag}.csv",
            "percentile_groupmean_{tag}.pdf",
        ),
    ]

    for mode_key, subtitle, stats_fn, csv_pat, pdf_pat in modes:
        for col, title, tag in variants:
            rec = []
            by_algo = {}
            for a in PLOT_ALGOS_NO_LRU:
                df_algo = df[df["algo"] == a]
                s = stats_fn(df_algo, col) if stats_fn is mean_group_q_stats else stats_fn(df_algo[col].dropna().values)
                by_algo[a] = s
                row = {"algo": a, "algo_display": DISPLAY_NAME[a]}
                row.update(s)
                rec.append(row)
            tab = pd.DataFrame(rec)
            all_tables[mode_key][tag] = tab
            csv_name = csv_pat.format(tag=tag)
            tab.to_csv(OUT_DIR / "data" / csv_name, index=False)
            tab.to_csv(pct_data_dir / csv_name, index=False)

            fig, ax = plt.subplots(figsize=(15, 7), dpi=150)
            x = np.arange(len(PLOT_ALGOS_NO_LRU))
            for i, (k, mk, c) in enumerate(marks):
                y = _safe_scatter_vals([by_algo[a][k] for a in PLOT_ALGOS_NO_LRU])
                ax.scatter(x, y, marker=mk, color=c, s=60, label=k)

            ax.set_xticks(x)
            ax.set_xticklabels([DISPLAY_NAME[a] for a in PLOT_ALGOS_NO_LRU], rotation=35, fontsize=FONT_TICK, fontweight="bold")
            ax.set_xlim(-0.7, len(PLOT_ALGOS_NO_LRU) - 0.3)
            ylabel = title if mode_key == "group_mean" else f"{title}\n{subtitle}"
            ax.set_ylabel(ylabel, fontsize=FONT_LABEL, fontweight="bold", labelpad=16)
            ax.set_yscale("linear")
            ax.yaxis.set_major_locator(ticker.NullLocator())
            ax.yaxis.set_major_formatter(ticker.NullFormatter())
            ax.yaxis.set_minor_locator(ticker.NullLocator())
            ax.tick_params(axis="y", labelsize=FONT_TICK)
            for lb in ax.get_yticklabels():
                lb.set_fontweight("bold")
            ax.grid(axis="y", alpha=0.25)
            lg = ax.legend(
                ncol=6,
                fontsize=FONT_LEGEND,
                loc="lower center",
                bbox_to_anchor=(0.5, 1.0),
                frameon=False,
                columnspacing=0.55,
                handletextpad=0.25,
                labelspacing=0.2,
                borderaxespad=0.15,
                markerscale=0.9,
            )
            for t in lg.get_texts():
                t.set_fontweight("bold")
            fig.tight_layout(rect=(0.08, 0, 1, 0.87))
            _fix_linear_ticks(ax)
            fig.savefig(OUT_DIR / "percentiles" / pdf_pat.format(tag=tag))
            plt.close(fig)
            count += 1

    return count, all_tables


def md_table(df):
    cols = list(df.columns)
    lines = []
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "|".join(["---"] * len(cols)) + "|")
    for _, r in df.iterrows():
        row = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                row.append(f"{v:.6f}")
            else:
                row.append(str(v))
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def write_doc(percentile_tables, counts):
    lines = []
    lines.append("# 20260423 图表与分位数统计")
    lines.append("")
    lines.append("- 口径: 6组 = alibabaBlock, metaCDN, metaKV, tencentBlock, tencentPhoto, wiki")
    lines.append("- 排除: cloudphysics, twitter")
    lines.append("- 算法顺序: LRU, LHD, ARC, SIEVE, S3-FIFO, WTinyLFU, LeCaR, CACHEUS, GL-Cache, LRB, 3L-Cache, RSD")
    lines.append(f"- 数据源(组内明细): {SRC_DIR} 各组 表1/表4/表5")
    lines.append(f"- 数据源(汇总MR/BMR): {BASELINE_MD}")
    lines.append(f"- 数据源(norm score): {ROBUSTNESS_MD}")
    lines.append("- 说明: weighted 系列为按组内 trace 的 n_req 归一化权重进行加权")
    lines.append("")
    lines.append("## 图数量")
    lines.append("")
    lines.append(f"- 箱线图: {counts['boxplots']}")
    lines.append(f"- 排名折线图: {counts['ranklines']}")
    lines.append(f"- 双轴条形图: {counts['dualaxis']}")
    lines.append(f"- 分位数图: {counts['percentiles']}")
    lines.append("")
    lines.append("## 分位数统计表")
    lines.append("")
    name_map = {
        "mr_raw": "MR 原始值",
        "mr_relative": "MR 相对值",
        "bmr_raw": "BMR 原始值",
        "bmr_relative": "BMR 相对值",
    }
    mode_map = {
        "pooled": "所有 trace 混合后直接计算 percentile",
        "group_mean": "先按 trace 组分别计算 percentile，再对各组 percentile 取平均",
    }
    for mode_key, mode_title in mode_map.items():
        lines.append(f"### {mode_title}")
        lines.append("")
        for k, title in name_map.items():
            lines.append(f"#### {title}")
            lines.append("")
            cols = ["algo_display", "p10", "p25", "median", "mean", "p75", "p90"]
            lines.append(md_table(percentile_tables[mode_key][k][cols]))
            lines.append("")

    DOC_OUT.write_text("\n".join(lines), encoding="utf-8")


def main():
    make_dirs()

    frames = []
    for g in GROUPS:
        frames.append(parse_group(g))
    df = pd.concat(frames, ignore_index=True)
    df = enrich(df)

    df.to_csv(OUT_DIR / "data" / "per_trace_metrics.csv", index=False)

    agg = aggregate_for_rank(df)
    agg.to_csv(OUT_DIR / "data" / "group_algo_aggregates.csv", index=False)

    n1 = save_boxplots(df)
    n2 = save_ranklines(agg)
    n3 = save_dualaxis(agg)
    n3b = save_dualaxis_norm_abs()
    n4, pct_tabs = save_percentiles(df)

    write_doc(
        pct_tabs,
        {
            "boxplots": n1,
            "ranklines": n2,
            "dualaxis": n3 + n3b,
            "percentiles": n4,
        },
    )

    print(f"boxplots={n1}, ranklines={n2}, dualaxis={n3 + n3b} (base={n3}, norm_abs={n3b}), percentiles={n4}")
    print(f"out_dir={OUT_DIR}")
    print(f"doc={DOC_OUT}")


if __name__ == "__main__":
    main()
