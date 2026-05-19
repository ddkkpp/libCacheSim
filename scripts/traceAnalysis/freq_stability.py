"""
plot frequency stability over request windows

This is intended to complement pop_rank.
pop_rank shows whether a trace is heavy-tailed globally,
while this script shows whether the hot-object ranking stays stable over time.

The figure contains two panels:
1. adjacent-window Top-K overlap
2. adjacent-window Jensen-Shannon divergence of the full request distribution

usage examples:
python3 traceAnalysis/freq_stability.py trace.csv --trace-format csv
python3 traceAnalysis/freq_stability.py trace.oracleGeneral.zst --trace-format oracleGeneral --num-req 10000000
"""

import math
import os
from pathlib import Path
import subprocess
import sys
from collections import Counter
from typing import Iterator, Hashable, List, Tuple

import matplotlib.pyplot as plt
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from utils.plot_utils import FIG_DIR, FIG_TYPE
from utils.trace_utils import extract_dataname


def detect_trace_format(trace_path: str) -> str:
    lower = trace_path.lower()
    if lower.endswith(".csv") or lower.endswith(".txt"):
        return "csv"
    return "oracleGeneral"


def iter_csv_obj_ids(
    trace_path: str,
    obj_id_col: int,
    delimiter: str,
    has_header: bool,
    num_req: int,
) -> Iterator[Hashable]:
    with open(trace_path, "r", encoding="utf-8") as ifile:
        if has_header:
            next(ifile, None)

        n_seen = 0
        for line in ifile:
            line = line.strip()
            if not line:
                continue
            fields = line.split(delimiter)
            yield fields[obj_id_col - 1]
            n_seen += 1
            if num_req > 0 and n_seen >= num_req:
                break


def resolve_traceprint() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    candidates = [
        repo_root / "_build_rel" / "bin" / "tracePrint",
        repo_root / "_build_dbg" / "bin" / "tracePrint",
        repo_root / "_build" / "bin" / "tracePrint",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError("tracePrint not found in _build_rel/bin, _build_dbg/bin, or _build/bin")


def build_traceprint_env(traceprint: str) -> dict:
    build_dir = Path(traceprint).resolve().parents[1]
    lib_dirs = [
        str(build_dir),
        str(build_dir / "libCacheSim" / "bin" / "traceUtils"),
    ]
    env = os.environ.copy()
    current = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = ":".join(lib_dirs + ([current] if current else []))
    return env


def iter_oracle_general_obj_ids(trace_path: str, trace_format: str, num_req: int) -> Iterator[str]:
    traceprint = resolve_traceprint()
    command = [
        traceprint,
        trace_path,
        trace_format,
        "--field-delimiter",
        ",",
        "--num-req",
        str(num_req),
    ]
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=build_traceprint_env(traceprint),
    )
    if proc.stdout is None:
        raise RuntimeError("failed to open tracePrint stdout pipe")

    try:
        for line in proc.stdout:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split(",")
            if len(fields) < 2:
                continue
            yield fields[1]
    finally:
        if proc.stdout is not None:
            proc.stdout.close()
        stderr_text = ""
        if proc.stderr is not None:
            stderr_text = proc.stderr.read().strip()
            proc.stderr.close()
        return_code = proc.wait()
        if return_code != 0:
            raise RuntimeError(f"tracePrint failed with code {return_code}: {stderr_text}")


def iter_obj_ids(
    trace_path: str,
    trace_format: str,
    obj_id_col: int,
    delimiter: str,
    has_header: bool,
    num_req: int,
) -> Iterator[Hashable]:
    if trace_format == "csv":
        yield from iter_csv_obj_ids(trace_path, obj_id_col, delimiter, has_header, num_req)
        return

    if trace_format in {"oracleGeneral", "oracleGeneralBin"}:
        yield from iter_oracle_general_obj_ids(trace_path, trace_format, num_req)
        return

    raise ValueError(f"unsupported trace format: {trace_format}")


def collect_window_counters(
    trace_path: str,
    trace_format: str,
    window_req: int,
    obj_id_col: int,
    delimiter: str,
    has_header: bool,
    num_req: int,
) -> Tuple[List[Counter], int]:
    counters: List[Counter] = []
    current = Counter()
    n_seen = 0

    for obj_id in iter_obj_ids(
        trace_path,
        trace_format,
        obj_id_col,
        delimiter,
        has_header,
        num_req,
    ):
        current[obj_id] += 1
        n_seen += 1
        if n_seen % window_req == 0:
            counters.append(current)
            current = Counter()

    if current:
        counters.append(current)

    return counters, n_seen


def topk_overlap(counter_a: Counter, counter_b: Counter, top_k: int) -> float:
    top_a = {obj for obj, _ in counter_a.most_common(top_k)}
    top_b = {obj for obj, _ in counter_b.most_common(top_k)}
    denom = max(1, min(top_k, len(top_a), len(top_b)))
    return len(top_a & top_b) / denom


def js_divergence(counter_a: Counter, counter_b: Counter) -> float:
    total_a = sum(counter_a.values())
    total_b = sum(counter_b.values())
    if total_a == 0 or total_b == 0:
        return 0.0

    js = 0.0
    for key in set(counter_a) | set(counter_b):
        p = counter_a.get(key, 0) / total_a
        q = counter_b.get(key, 0) / total_b
        m = 0.5 * (p + q)
        if p > 0:
            js += 0.5 * p * math.log2(p / m)
        if q > 0:
            js += 0.5 * q * math.log2(q / m)
    return js


def build_metrics(window_counters: List[Counter], top_k: int) -> Tuple[np.ndarray, np.ndarray]:
    overlaps = []
    divergences = []
    for left, right in zip(window_counters, window_counters[1:]):
        overlaps.append(topk_overlap(left, right, top_k))
        divergences.append(js_divergence(left, right))
    return np.array(overlaps, dtype=float), np.array(divergences, dtype=float)


def compute_frequency_stability(
    trace_path: str,
    trace_format: str = "auto",
    window_req: int = 100_000,
    top_k: int = 128,
    num_req: int = -1,
    obj_id_col: int = 2,
    delimiter: str = ",",
    has_header: bool = False,
    figname_prefix: str = "",
) -> dict:
    if trace_format == "auto":
        trace_format = detect_trace_format(trace_path)
    if not figname_prefix:
        figname_prefix = extract_dataname(trace_path)

    window_counters, n_seen = collect_window_counters(
        trace_path,
        trace_format,
        window_req,
        obj_id_col,
        delimiter,
        has_header,
        num_req,
    )
    if len(window_counters) < 2:
        raise ValueError("need at least two windows to plot frequency stability")

    overlaps, divergences = build_metrics(window_counters, top_k)
    x = np.arange(2, len(window_counters) + 1, dtype=int)
    return {
        "trace_path": trace_path,
        "trace_format": trace_format,
        "figname_prefix": figname_prefix,
        "window_req": window_req,
        "top_k": top_k,
        "requests": n_seen,
        "window_count": len(window_counters),
        "x": x,
        "overlaps": overlaps,
        "divergences": divergences,
    }


def plot_frequency_stability(
    trace_path: str,
    trace_format: str = "auto",
    window_req: int = 100_000,
    top_k: int = 128,
    num_req: int = -1,
    obj_id_col: int = 2,
    delimiter: str = ",",
    has_header: bool = False,
    figname_prefix: str = "",
    output_dir: str = FIG_DIR,
    fig_type: str = FIG_TYPE,
    show_summary_title: bool = False,
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    metrics = compute_frequency_stability(
        trace_path,
        trace_format=trace_format,
        window_req=window_req,
        top_k=top_k,
        num_req=num_req,
        obj_id_col=obj_id_col,
        delimiter=delimiter,
        has_header=has_header,
        figname_prefix=figname_prefix,
    )
    overlaps = metrics["overlaps"]
    divergences = metrics["divergences"]
    x = metrics["x"]
    figname_prefix = metrics["figname_prefix"]
    trace_format = metrics["trace_format"]
    n_seen = metrics["requests"]
    window_count = metrics["window_count"]

    fig, axes = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

    axes[0].plot(x, overlaps, color="#1f77b4", marker="o", markersize=4)
    axes[0].axhline(float(np.mean(overlaps)), color="#1f77b4", linestyle="--", alpha=0.35)
    axes[0].set_ylim(0.0, 1.0)
    axes[0].set_ylabel(f"Adjacent Top-{top_k} overlap", fontweight="bold")
    axes[0].grid(alpha=0.25)

    axes[1].plot(x, divergences, color="#d62728", marker="o", markersize=4)
    axes[1].axhline(float(np.mean(divergences)), color="#d62728", linestyle="--", alpha=0.35)
    axes[1].set_ylabel("Adjacent JSD", fontweight="bold")
    axes[1].set_xlabel(f"Window index ({window_req} requests per window)", fontweight="bold")
    axes[1].grid(alpha=0.25)

    if show_summary_title:
        fig.suptitle(
            f"Frequency Stability: {figname_prefix}\n"
            f"mean overlap={np.mean(overlaps):.3f}, mean JSD={np.mean(divergences):.3f}, windows={window_count}",
            fontweight="bold",
        )
    fig.tight_layout()

    outpath = os.path.join(output_dir, f"{figname_prefix}_freq_stability.{fig_type}")
    fig.savefig(outpath, bbox_inches="tight")
    plt.close(fig)

    print(
        f"trace={figname_prefix} format={trace_format} requests={n_seen} windows={window_count} "
        f"mean_overlap={np.mean(overlaps):.6f} median_overlap={np.median(overlaps):.6f} "
        f"mean_jsd={np.mean(divergences):.6f} median_jsd={np.median(divergences):.6f} fig={outpath}"
    )
    return outpath


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("trace_path", type=str, help="path to the input trace")
    ap.add_argument(
        "--trace-format",
        type=str,
        default="auto",
        choices=["auto", "csv", "oracleGeneral", "oracleGeneralBin"],
        help="input trace format",
    )
    ap.add_argument(
        "--window-req",
        type=int,
        default=100_000,
        help="number of requests per analysis window",
    )
    ap.add_argument(
        "--top-k",
        type=int,
        default=128,
        help="Top-K hot objects used for overlap",
    )
    ap.add_argument(
        "--num-req",
        type=int,
        default=-1,
        help="optional request limit for large traces",
    )
    ap.add_argument(
        "--obj-id-col",
        type=int,
        default=2,
        help="object id column for csv traces, 1-based",
    )
    ap.add_argument(
        "--delimiter",
        type=str,
        default=",",
        help="field delimiter for csv traces",
    )
    ap.add_argument(
        "--has-header",
        action="store_true",
        help="csv trace has a header row",
    )
    ap.add_argument(
        "--figname-prefix",
        type=str,
        default="",
        help="figure name prefix",
    )
    ap.add_argument(
        "--output-dir",
        type=str,
        default=FIG_DIR,
        help="output directory",
    )
    ap.add_argument(
        "--fig-type",
        type=str,
        default=FIG_TYPE,
        help="figure type",
    )
    ap.add_argument(
        "--show-summary-title",
        action="store_true",
        help="show mean summary text above the figure",
    )
    args = ap.parse_args()

    plot_frequency_stability(
        args.trace_path,
        trace_format=args.trace_format,
        window_req=args.window_req,
        top_k=args.top_k,
        num_req=args.num_req,
        obj_id_col=args.obj_id_col,
        delimiter=args.delimiter,
        has_header=args.has_header,
        figname_prefix=args.figname_prefix,
        output_dir=args.output_dir,
        fig_type=args.fig_type,
        show_summary_title=args.show_summary_title,
    )
