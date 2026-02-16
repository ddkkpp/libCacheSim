#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Infer LOH feature weight preferences (w1..w6) from analysis artifacts.

Inputs (expected to exist under repo root):
- analysis/summary.json
- analysis/<trace>.reqRate_w300
- analysis/<trace>.reuse

Outputs:
- Prints a compact per-trace metrics table
- Emits a heuristic normalized weight suggestion for:
  w1..w6 = recency, frequency, size, irt1, irt2, irt3

This script is intentionally dependency-free (no numpy/pandas) to keep it easy
to run in the existing environment.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ANALYSIS_DIR = os.path.join(REPO_ROOT, "analysis")
SUMMARY_JSON = os.path.join(ANALYSIS_DIR, "summary.json")


@dataclass
class RunningStats:
    n: int = 0
    mean: float = 0.0
    m2: float = 0.0
    min_v: float = float("inf")
    max_v: float = float("-inf")

    def add(self, x: float) -> None:
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self.m2 += delta * delta2
        if x < self.min_v:
            self.min_v = x
        if x > self.max_v:
            self.max_v = x

    @property
    def var(self) -> float:
        if self.n < 2:
            return 0.0
        return self.m2 / (self.n - 1)

    @property
    def std(self) -> float:
        return math.sqrt(self.var)

    @property
    def cv(self) -> float:
        if self.mean == 0:
            return float("inf") if self.std > 0 else 0.0
        return self.std / abs(self.mean)


def _iter_ints_from_comma_line(line: str) -> Iterable[int]:
    """Yield ints from a comma-separated line without allocating a big list."""
    value = 0
    sign = 1
    in_num = False
    for ch in line:
        if ch == "-":
            sign = -1
        elif "0" <= ch <= "9":
            in_num = True
            value = value * 10 + (ord(ch) - 48)
        else:
            if in_num:
                yield sign * value
            value = 0
            sign = 1
            in_num = False
    if in_num:
        yield sign * value


def _quantile_from_sorted(values_sorted: Sequence[float], q: float) -> float:
    if not values_sorted:
        return 0.0
    if q <= 0:
        return float(values_sorted[0])
    if q >= 1:
        return float(values_sorted[-1])
    # linear interpolation
    pos = (len(values_sorted) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(values_sorted[lo])
    w = pos - lo
    return float(values_sorted[lo] * (1.0 - w) + values_sorted[hi] * w)


def _safe_div(a: float, b: float) -> float:
    if b == 0:
        return 0.0
    return a / b


def parse_reqrate_w300(path: str) -> Dict[str, object]:
    """Parse *.reqRate_w300 and compute volatility + cold-start proxies."""
    section_to_key = {
        "# req rate": "req",
        "# byte rate": "byte",
        "# obj rate": "obj",
        "# first seen obj": "cold_obj",
    }

    data: Dict[str, List[int]] = {}
    current_key: Optional[str] = None

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                current_key = None
                for prefix, key in section_to_key.items():
                    if line.startswith(prefix):
                        current_key = key
                        data.setdefault(key, [])
                        break
                continue

            if current_key is None:
                continue

            # Most files store the whole series on a single huge line.
            series = data[current_key]
            for v in _iter_ints_from_comma_line(line):
                series.append(int(v))

    req = data.get("req", [])
    byte = data.get("byte", [])
    obj = data.get("obj", [])
    cold_obj = data.get("cold_obj", [])

    # Compute volatility metrics.
    req_stats = RunningStats()
    byte_stats = RunningStats()
    bpr_stats = RunningStats()  # bytes per request
    abs_delta_req_stats = RunningStats()  # mean abs diff

    bytes_per_req: List[float] = []
    for i, r in enumerate(req):
        req_stats.add(float(r))
        if i > 0:
            abs_delta_req_stats.add(abs(float(r) - float(req[i - 1])))
        if i < len(byte):
            byte_stats.add(float(byte[i]))
            bpr = _safe_div(float(byte[i]), float(r)) if r != 0 else 0.0
            bpr_stats.add(bpr)
            bytes_per_req.append(bpr)

    # Cold start ratio: cold_obj / obj
    cold_ratio: List[float] = []
    if obj and cold_obj:
        n = min(len(obj), len(cold_obj))
        for i in range(n):
            cold_ratio.append(_safe_div(float(cold_obj[i]), float(obj[i])))

    # Percentiles for quick comparison.
    req_sorted = sorted(float(x) for x in req)
    bpr_sorted = sorted(bytes_per_req)
    cold_sorted = sorted(cold_ratio)

    p = lambda arr, q: _quantile_from_sorted(arr, q)

    return {
        "n_windows": len(req),
        "req_mean": req_stats.mean,
        "req_cv": req_stats.cv,
        "req_p50": p(req_sorted, 0.50),
        "req_p90": p(req_sorted, 0.90),
        "req_p99": p(req_sorted, 0.99),
        "req_zero_frac": _safe_div(sum(1 for x in req if x == 0), len(req)) if req else 0.0,
        "req_abs_delta_mean": abs_delta_req_stats.mean,
        "byte_mean": byte_stats.mean,
        "byte_cv": byte_stats.cv,
        "bpr_mean": bpr_stats.mean,
        "bpr_cv": bpr_stats.cv,
        "bpr_p50": p(bpr_sorted, 0.50),
        "bpr_p90": p(bpr_sorted, 0.90),
        "cold_obj_ratio_mean": sum(cold_ratio) / len(cold_ratio) if cold_ratio else 0.0,
        "cold_obj_ratio_p90": p(cold_sorted, 0.90) if cold_sorted else 0.0,
        "cold_obj_ratio_p99": p(cold_sorted, 0.99) if cold_sorted else 0.0,
    }


def parse_reuse_hist(path: str, granularity_seconds: int = 5) -> Dict[str, object]:
    """Parse *.reuse histogram and compute reuse-time quantiles + bucket shares."""
    # Lines are: "reuse_bin:freq" (bin in units of granularity_seconds)
    pairs: List[Tuple[int, int]] = []
    total = 0

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            k_str, v_str = line.split(":", 1)
            try:
                reuse_bin = int(k_str)
                freq = int(v_str)
            except ValueError:
                continue
            if freq <= 0 or reuse_bin < 0:
                continue
            pairs.append((reuse_bin, freq))
            total += freq

    pairs.sort(key=lambda kv: kv[0])

    def quantile(q: float) -> float:
        if total <= 0:
            return 0.0
        target = q * total
        cum = 0
        for reuse_bin, freq in pairs:
            cum += freq
            if cum >= target:
                return float(reuse_bin * granularity_seconds)
        return float(pairs[-1][0] * granularity_seconds) if pairs else 0.0

    def share_le(seconds: int) -> float:
        if total <= 0:
            return 0.0
        threshold_bin = seconds // granularity_seconds
        cum = 0
        for reuse_bin, freq in pairs:
            if reuse_bin <= threshold_bin:
                cum += freq
            else:
                break
        return cum / total

    p50 = quantile(0.50)
    p90 = quantile(0.90)
    p99 = quantile(0.99)

    # Bucket shares for IRT split.
    le_1h = share_le(3600)
    le_1d = share_le(86400)
    le_7d = share_le(86400 * 7)

    share_0_1h = le_1h
    share_1h_1d = max(0.0, le_1d - le_1h)
    share_gt_1d = max(0.0, 1.0 - le_1d)

    # A simple spread metric (log-scale) to avoid huge numbers dominating.
    spread = math.log1p(p99) - math.log1p(max(p50, 1e-9))

    return {
        "reuse_events": total,
        "reuse_p50_s": p50,
        "reuse_p90_s": p90,
        "reuse_p99_s": p99,
        "reuse_spread_log": spread,
        "reuse_share_0_1h": share_0_1h,
        "reuse_share_1h_1d": share_1h_1d,
        "reuse_share_gt_1d": share_gt_1d,
        "reuse_share_le_7d": le_7d,
    }


def _minmax_norm(values: Dict[str, float]) -> Dict[str, float]:
    if not values:
        return {}
    finite = [v for v in values.values() if math.isfinite(v)]
    if not finite:
        return {k: 0.0 for k in values}
    lo = min(finite)
    hi = max(finite)
    if hi == lo:
        return {k: 0.0 for k in values}
    out: Dict[str, float] = {}
    for k, v in values.items():
        if not math.isfinite(v):
            out[k] = 1.0
        else:
            out[k] = (v - lo) / (hi - lo)
    return out


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def infer_weights(
    traces: Sequence[str],
    trace_types: Optional[Dict[str, str]] = None,
) -> Tuple[Dict[str, Dict[str, object]], Dict[str, List[float]]]:
    with open(SUMMARY_JSON, "r", encoding="utf-8") as f:
        summary = json.load(f)

    per_trace: Dict[str, Dict[str, object]] = {}

    for t in traces:
        base = os.path.basename(t)
        req_path = os.path.join(ANALYSIS_DIR, f"{base}.reqRate_w300")
        reuse_path = os.path.join(ANALYSIS_DIR, f"{base}.reuse")
        if not os.path.exists(req_path):
            raise FileNotFoundError(req_path)
        if not os.path.exists(reuse_path):
            raise FileNotFoundError(reuse_path)

        s = summary.get(base, {})
        station = s.get("stationarity", {})
        topk = s.get("topk", {})

        req_m = parse_reqrate_w300(req_path)
        reuse_m = parse_reuse_hist(reuse_path)

        ttype = None
        if trace_types:
            ttype = trace_types.get(base)
        per_trace[base] = {
            "summary": s,
            "stationarity": station,
            "stationarity_labels": s.get("stationarity_labels", {}),
            "topk": topk,
            "reqrate": req_m,
            "reuse": reuse_m,
            "trace_type": ttype,
        }

    # Build feature-importance scores per trace (heuristic, but grounded).
    # We compute min-max normalization across traces to keep comparable scale.
    jaccard_mean = {t: float(per_trace[t]["stationarity"].get("jaccard_topk", {}).get("mean", 0.0)) for t in per_trace}
    zipf = {t: float(per_trace[t]["stationarity"].get("zipf_alpha", {}).get("mean", per_trace[t]["summary"].get("zipf_alpha", 0.0))) for t in per_trace}
    top1pct = {t: float(per_trace[t]["topk"].get("top1pct", 0.0)) for t in per_trace}
    size_p99_mean = {t: float(per_trace[t]["stationarity"].get("size_p99", {}).get("mean", 0.0)) for t in per_trace}
    size_p99_cv = {
        t: _safe_div(
            float(per_trace[t]["stationarity"].get("size_p99", {}).get("std", 0.0)),
            max(1.0, float(per_trace[t]["stationarity"].get("size_p99", {}).get("mean", 0.0))),
        )
        for t in per_trace
    }

    req_cv = {t: float(per_trace[t]["reqrate"].get("req_cv", 0.0)) for t in per_trace}
    req_abs_delta = {t: float(per_trace[t]["reqrate"].get("req_abs_delta_mean", 0.0)) for t in per_trace}
    cold_ratio = {t: float(per_trace[t]["reqrate"].get("cold_obj_ratio_mean", 0.0)) for t in per_trace}
    bpr_cv = {t: float(per_trace[t]["reqrate"].get("bpr_cv", 0.0)) for t in per_trace}
    reuse_spread = {t: float(per_trace[t]["reuse"].get("reuse_spread_log", 0.0)) for t in per_trace}
    reuse_short = {t: float(per_trace[t]["reuse"].get("reuse_share_0_1h", 0.0)) for t in per_trace}

    norm = {
        "inv_jaccard": _minmax_norm({t: 1.0 - jaccard_mean[t] for t in per_trace}),
        "jaccard": _minmax_norm(jaccard_mean),
        "zipf": _minmax_norm(zipf),
        "top1pct": _minmax_norm(top1pct),
        "size_p99_mean": _minmax_norm({t: math.log1p(size_p99_mean[t]) for t in per_trace}),
        "size_p99_cv": _minmax_norm(size_p99_cv),
        "req_cv": _minmax_norm(req_cv),
        "req_abs_delta": _minmax_norm(req_abs_delta),
        "cold_ratio": _minmax_norm(cold_ratio),
        "bpr_cv": _minmax_norm(bpr_cv),
        "reuse_spread": _minmax_norm(reuse_spread),
        "reuse_short": _minmax_norm(reuse_short),
    }

    weights: Dict[str, List[float]] = {}

    for t in per_trace:
        ttype = per_trace[t].get("trace_type")

        # Recency importance rises with identity churn, burstiness, cold-start pressure, and short reuse.
        recency_score = (
            0.35 * norm["inv_jaccard"][t]
            + 0.25 * norm["req_cv"][t]
            + 0.20 * norm["cold_ratio"][t]
            + 0.20 * norm["reuse_short"][t]
        )

        # Type hint: block traces generally have fixed or narrow size distribution,
        # so size is less discriminative; recency/IRT matter more.
        if ttype == "block":
            recency_score *= 1.20

        # Frequency importance rises with skew (top1pct/zipf) and is helped by stable identity.
        freq_score = (
            0.45 * norm["top1pct"][t]
            + 0.35 * norm["zipf"][t]
            + 0.20 * (1.0 - norm["inv_jaccard"][t])
        )

        if ttype == "block":
            freq_score *= 0.85

        # Size importance rises with large size tail and bpr volatility.
        size_score = (
            0.50 * norm["size_p99_mean"][t]
            + 0.20 * norm["size_p99_cv"][t]
            + 0.30 * norm["bpr_cv"][t]
        )

        if ttype == "block":
            size_score *= 0.10

        # IRT importance rises when reuse distribution is broad and traffic is non-stationary.
        irt_total = (
            0.50 * norm["reuse_spread"][t]
            + 0.25 * norm["req_abs_delta"][t]
            + 0.25 * norm["inv_jaccard"][t]
        )

        if ttype == "block":
            irt_total *= 1.25

        # Split IRT importance across irt1/2/3 using reuse buckets.
        share_0_1h = float(per_trace[t]["reuse"].get("reuse_share_0_1h", 0.0))
        share_1h_1d = float(per_trace[t]["reuse"].get("reuse_share_1h_1d", 0.0))
        share_gt_1d = float(per_trace[t]["reuse"].get("reuse_share_gt_1d", 0.0))

        # Make sure split sums to 1 (or fallback to equal).
        ssum = share_0_1h + share_1h_1d + share_gt_1d
        if ssum <= 1e-12:
            share_0_1h = share_1h_1d = share_gt_1d = 1.0 / 3.0
        else:
            share_0_1h /= ssum
            share_1h_1d /= ssum
            share_gt_1d /= ssum

        irt1 = irt_total * (0.60 * share_0_1h + 0.25 * share_1h_1d + 0.15 * share_gt_1d)
        irt2 = irt_total * (0.25 * share_0_1h + 0.55 * share_1h_1d + 0.20 * share_gt_1d)
        irt3 = irt_total * (0.15 * share_0_1h + 0.20 * share_1h_1d + 0.65 * share_gt_1d)

        raw = [
            _clamp(recency_score, 0.0, 1.0),
            _clamp(freq_score, 0.0, 1.0),
            _clamp(size_score, 0.0, 1.0),
            _clamp(irt1, 0.0, 1.0),
            _clamp(irt2, 0.0, 1.0),
            _clamp(irt3, 0.0, 1.0),
        ]
        total_raw = sum(raw)
        if total_raw <= 0:
            weights[t] = [1 / 6.0] * 6
        else:
            weights[t] = [x / total_raw for x in raw]

    return per_trace, weights


def load_trace_types(types_file: Optional[str]) -> Dict[str, str]:
    if not types_file:
        return {}
    path = types_file
    if not os.path.isabs(path):
        path = os.path.join(REPO_ROOT, path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    out: Dict[str, str] = {}
    for k, v in (data or {}).items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        vv = v.strip().lower()
        if vv in ("object", "block", "kv"):
            out[k] = vv
    return out


def _fmt_seconds(seconds: float) -> str:
    if seconds <= 0:
        return "0"
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds/60:.1f}m"
    if seconds < 86400:
        return f"{seconds/3600:.2f}h"
    return f"{seconds/86400:.2f}d"


def render_markdown(per_trace: Dict[str, Dict[str, object]], weights: Dict[str, List[float]]) -> str:
    lines: List[str] = []
    lines.append("# LOH trace 特征偏好（从 analysis 推断）\n")
    lines.append("说明：w1..w6 = recency / frequency / size / irt1 / irt2 / irt3（见 LOH.c FEATURE_DIM 注释）。\n")
    lines.append("本报告基于 analysis 的聚合统计（summary.json、reqRate_w300、reuse histogram），给出可复现的启发式建议，不等价于最优解。\n")

    for t in sorted(per_trace.keys()):
        s = per_trace[t]["summary"]
        ttype = per_trace[t].get("trace_type")
        station = per_trace[t]["stationarity"]
        labels = per_trace[t].get("stationarity_labels", {})
        topk = per_trace[t]["topk"]
        rr = per_trace[t]["reqrate"]
        reuse = per_trace[t]["reuse"]
        w = weights[t]

        lines.append(f"## {t}\n")
        lines.append("**概况**\n")
        if ttype:
            lines.append(f"- trace_type={ttype}\n")
        lines.append(f"- total_req={int(s.get('total_req', 0)):,}, total_obj={int(s.get('total_obj', 0)):,}, zipf_alpha={float(s.get('zipf_alpha', 0.0)):.3f}\n")
        lines.append(f"- stationarity_labels: distribution={labels.get('distribution')}, identity={labels.get('identity')}, size={labels.get('size')}\n")
        lines.append(f"- topk(top1/top10/top100/top1pct)={topk.get('top1',0):.4f}/{topk.get('top10',0):.4f}/{topk.get('top100',0):.4f}/{topk.get('top1pct',0):.4f}\n")

        lines.append("**reqRate_w300（300s 窗口）**\n")
        lines.append(
            "- req_mean={:.2f}, req_cv={:.3f}, p50/p90/p99={:.0f}/{:.0f}/{:.0f}, zero_frac={:.3f}, mean|Δreq|={:.2f}\n".format(
                float(rr.get("req_mean", 0.0)),
                float(rr.get("req_cv", 0.0)),
                float(rr.get("req_p50", 0.0)),
                float(rr.get("req_p90", 0.0)),
                float(rr.get("req_p99", 0.0)),
                float(rr.get("req_zero_frac", 0.0)),
                float(rr.get("req_abs_delta_mean", 0.0)),
            )
        )
        lines.append(
            "- bytes/req mean={:.2f}, cv={:.3f}, p50/p90={:.2f}/{:.2f}; cold_obj_ratio mean={:.3f}, p90={:.3f}\n".format(
                float(rr.get("bpr_mean", 0.0)),
                float(rr.get("bpr_cv", 0.0)),
                float(rr.get("bpr_p50", 0.0)),
                float(rr.get("bpr_p90", 0.0)),
                float(rr.get("cold_obj_ratio_mean", 0.0)),
                float(rr.get("cold_obj_ratio_p90", 0.0)),
            )
        )

        lines.append("**reuse（复用间隔，granularity=5）**\n")
        lines.append(
            "- reuse_p50/p90/p99={} / {} / {} (spread_log={:.3f})\n".format(
                _fmt_seconds(float(reuse.get("reuse_p50_s", 0.0))),
                _fmt_seconds(float(reuse.get("reuse_p90_s", 0.0))),
                _fmt_seconds(float(reuse.get("reuse_p99_s", 0.0))),
                float(reuse.get("reuse_spread_log", 0.0)),
            )
        )
        lines.append(
            "- reuse share: <=1h={:.3f}, 1h-1d={:.3f}, >1d={:.3f}, <=7d={:.3f}\n".format(
                float(reuse.get("reuse_share_0_1h", 0.0)),
                float(reuse.get("reuse_share_1h_1d", 0.0)),
                float(reuse.get("reuse_share_gt_1d", 0.0)),
                float(reuse.get("reuse_share_le_7d", 0.0)),
            )
        )

        lines.append("**建议权重（归一化，w1..w6）**\n")
        lines.append(
            "- w=[{:.3f}, {:.3f}, {:.3f}, {:.3f}, {:.3f}, {:.3f}]\n".format(
                w[0], w[1], w[2], w[3], w[4], w[5]
            )
        )
        lines.append("\n")

    return "".join(lines)


def render_text(per_trace: Dict[str, Dict[str, object]], weights: Dict[str, List[float]]) -> str:
    lines: List[str] = []
    for t in sorted(per_trace.keys()):
        rr = per_trace[t]["reqrate"]
        reuse = per_trace[t]["reuse"]
        ttype = per_trace[t].get("trace_type")
        w = weights[t]
        lines.append(f"{t}:" + (f" type={ttype}" if ttype else ""))
        lines.append(
            "  req_cv={:.3f} cold_ratio={:.3f} reuse_p50={} reuse_p99={} -> w=[{:.3f},{:.3f},{:.3f},{:.3f},{:.3f},{:.3f}]".format(
                float(rr.get("req_cv", 0.0)),
                float(rr.get("cold_obj_ratio_mean", 0.0)),
                _fmt_seconds(float(reuse.get("reuse_p50_s", 0.0))),
                _fmt_seconds(float(reuse.get("reuse_p99_s", 0.0))),
                w[0],
                w[1],
                w[2],
                w[3],
                w[4],
                w[5],
            )
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--traces",
        nargs="*",
        default=[
            "meta_reag.oracleGeneral.zst",
            "wiki_2019t.oracleGeneral.zst",
            "1063.oracleGeneral.zst",
        ],
        help="Trace base names (as used under analysis/).",
    )
    ap.add_argument(
        "--format",
        choices=["text", "md"],
        default="text",
        help="Output format.",
    )
    ap.add_argument(
        "--write",
        default=None,
        help="Write output to this file (in addition to stdout).",
    )
    ap.add_argument(
        "--types-file",
        default=None,
        help="Optional JSON mapping of trace base name -> type (object/block/kv).",
    )

    args = ap.parse_args()

    trace_types = load_trace_types(args.types_file)
    per_trace, weights = infer_weights(args.traces, trace_types=trace_types)

    if args.format == "md":
        out = render_markdown(per_trace, weights)
    else:
        out = render_text(per_trace, weights)

    print(out, end="")

    if args.write:
        out_path = args.write
        if not os.path.isabs(out_path):
            out_path = os.path.join(REPO_ROOT, out_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
