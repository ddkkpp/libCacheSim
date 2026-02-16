#!/usr/bin/env python3
"""Stream-parse Actor-Critic logs to evaluate reward/penalty signal learnability.

Designed for very large `ac_sb3_*.log` files (100MB+). Uses only stdlib.

It extracts:
- penalty_scale (first occurrence of `penalty_scale=`)
- per-finalize `penalty_data: X items` (counts + zero ratio)
- `final_reward (after clip) = ...` (clip saturation + min/max/mean)
- `penalty (weighted) = ...` (min/max/mean)
- last `FINAL_CORRECTIONS: ... correct_on_finalized=... total_finalized=...`

Outputs a concise per-scale aggregate summary.
"""

from __future__ import annotations

import argparse
import glob
import math
import os
import random
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import DefaultDict, Dict, Iterable, List, Optional, Tuple


RE_PENALTY_SCALE = re.compile(r"penalty_scale\s*=\s*([^\s,]+)")
RE_PENALTY_DATA = re.compile(r"penalty_data:\s*(\d+)\s*items")
RE_REWARD_BEFORE_CLIP = re.compile(r"reward \(before clip\)\s*[:=]\s*([-+0-9.eE]+)")
RE_FINAL_REWARD = re.compile(r"final_reward \(after clip\)\s*[:=]\s*([-+0-9.eE]+)")
RE_PENALTY_WEIGHTED = re.compile(r"penalty \(weighted\)\s*[:=]\s*([-+0-9.eE]+)")
RE_CORR_ON_FINALIZED = re.compile(r"correct_on_finalized=(\d+)")
RE_CORR_FINALIZED_TOTAL = re.compile(r"(?:total_finalized|finalize)=(\d+)")
RE_FINAL_CORR_PROP = re.compile(r"FINAL_CORRECTIONS:.*?prop_on_finalized=([-+0-9.eE]+)")

RE_LOH_KV = re.compile(r"\b([A-Z0-9_./-]+):\s*([^\s]+)")
RE_LOWER_KV = re.compile(r"\b([a-z0-9_]+)=([^\s,]+)")
RE_UPPER_EQ = re.compile(r"\b([A-Z][A-Z0-9_]+)=([^\s,]+)")
RE_PENALTY_SCALE_MODE = re.compile(r"Penalty scale mode:\s*([^\s,]+)")

# Some logs print scale-specific tuning inline, e.g.
#   penalty_scale=survival, bins=64, q=0.900, min_count=3, dmax=500
#   penalty_scale=log_compressed, dmax=200
RE_PENALTY_SURVIVAL_TUNING = re.compile(
    r"penalty_scale\s*=\s*survival.*?\bbins=(\d+).*?\bq=([-+0-9.eE]+).*?\bmin_count=(\d+).*?\bdmax=([-+0-9.eE]+)"
)
RE_PENALTY_LOGCOMP_TUNING = re.compile(r"penalty_scale\s*=\s*log_compressed.*?\bdmax=([-+0-9.eE]+)")

RE_RB_REWARD = re.compile(r"\[ReplayBuffer\].*?\breward=([-+0-9.eE]+)")
RE_IMMEDIATE_REWARD = re.compile(r"Immediate reward:\s*([-+0-9.eE]+)")

RE_REWARD_TO_FINAL = re.compile(r"Reward[→\-]>?Final")


def _safe_float(text: str) -> Optional[float]:
    try:
        value = float(text)
    except Exception:
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


@dataclass
class RunningStats:
    count: int = 0
    sum: float = 0.0
    min: float = float("inf")
    max: float = float("-inf")

    def add(self, value: float) -> None:
        self.count += 1
        self.sum += value
        if value < self.min:
            self.min = value
        if value > self.max:
            self.max = value

    @property
    def mean(self) -> Optional[float]:
        if self.count == 0:
            return None
        return self.sum / self.count


def _reservoir_add(sample: List[float], value: float, seen: int, capacity: int, rng: random.Random) -> None:
    if capacity <= 0:
        return
    if len(sample) < capacity:
        sample.append(value)
        return
    j = rng.randrange(seen)
    if j < capacity:
        sample[j] = value


def _quantiles_from_sample(sample: List[float], probs: Iterable[float]) -> Dict[float, Optional[float]]:
    if not sample:
        return {p: None for p in probs}
    data = sorted(sample)
    n = len(data)

    out: Dict[float, Optional[float]] = {}
    for p in probs:
        if n == 1:
            out[p] = data[0]
            continue
        # linear interpolation between closest ranks
        idx = p * (n - 1)
        lo = int(math.floor(idx))
        hi = int(math.ceil(idx))
        if lo == hi:
            out[p] = data[lo]
        else:
            frac = idx - lo
            out[p] = data[lo] * (1.0 - frac) + data[hi] * frac
    return out


def _bin_edges_reward() -> List[float]:
    # reward(after clip) is typically in [-1, 1]
    return [-1.0000000000001, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0000000000001]


def _bin_edges_penalty() -> List[float]:
    # penalty(weighted) is >=0 and may be large for survival/log_compressed
    return [
        -1e-12,
        0.0,
        1e-6,
        1e-5,
        1e-4,
        1e-3,
        1e-2,
        1e-1,
        1.0,
        10.0,
        100.0,
        1000.0,
        1e9,
    ]


def _bin_index(value: float, edges: List[float]) -> int:
    # returns i for bin [edges[i], edges[i+1])
    # edges assumed sorted
    lo = 0
    hi = len(edges) - 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if value < edges[mid]:
            hi = mid
        else:
            lo = mid
    return max(0, min(len(edges) - 2, lo))


def _format_hist(hist: Dict[int, int], topk: int = 10, show_all_if_distinct_le: int = 20) -> str:
    if not hist:
        return "n/a"
    total = sum(hist.values())
    if total <= 0:
        return "n/a"
    distinct = len(hist)
    if distinct <= show_all_if_distinct_le:
        items = sorted(hist.items(), key=lambda kv: kv[0])
        parts = [f"{k}:{100.0*v/total:.2f}%" for k, v in items]
        return f"distinct={distinct} " + " ".join(parts)
    items = sorted(hist.items(), key=lambda kv: (-kv[1], kv[0]))[:topk]
    parts = [f"{k}:{100.0*v/total:.2f}%" for k, v in items]
    return f"distinct={distinct} top{topk}=" + " ".join(parts)


def _format_bins(edges: List[float], counts: List[int]) -> str:
    total = sum(counts)
    if total <= 0:
        return "n/a"
    parts = []
    for i, c in enumerate(counts):
        if c == 0:
            continue
        a = edges[i]
        b = edges[i + 1]
        parts.append(f"[{a:g},{b:g}):{100.0*c/total:.2f}%")
    return " ".join(parts) if parts else "n/a"


def _is_penalty_related_key(key: str) -> bool:
    k = key.lower()
    if "penalty" in k:
        return True
    # scale-specific tuning keys may not include the word 'penalty'
    if k in {"dmax", "bins", "q", "min_count"}:
        return True
    if key in {
        "LOH_REWARD_W_PENALTY",
        "LOH_REWARD_USE_PENALTY",
        "LOH_PENALTY_MODE/LOH_PENALTY_SCALE",
        "Penalty",
    }:
        return True
    return False


def _get_penalty_formula(params: Dict[str, str]) -> Optional[str]:
    # Prefer the replay-buffer print, then fall back to Reward Config env dump.
    return params.get("penalty_reward_formula") or params.get("LOH_PENALTY_REWARD_FORMULA")


def _get_penalty_scale(metrics: FileMetrics) -> str:
    return (
        metrics.penalty_scale
        or metrics.penalty_params.get("LOH_PENALTY_MODE/LOH_PENALTY_SCALE")
        or metrics.penalty_params.get("LOH_PENALTY_SCALE")
        or "<unknown>"
    )


def _get_penalty_cutoff(params: Dict[str, str]) -> Optional[str]:
    return params.get("penalty_cutoff") or params.get("LOH_PENALTY_CUTOFF")


def _compact_cfg(params: Dict[str, str]) -> str:
    # Keep this short: it’s meant to explain why same-scale runs can differ.
    bits: List[str] = []
    wpen = params.get("LOH_REWARD_W_PENALTY")
    if wpen:
        bits.append(f"w_pen={wpen}")
    formula = _get_penalty_formula(params)
    if formula:
        bits.append(f"formula={formula}")
    cutoff = _get_penalty_cutoff(params)
    if cutoff:
        bits.append(f"cutoff={cutoff}")
    # tuning (mostly for survival/log_compressed)
    dmax = params.get("dmax") or params.get("penalty_dmax")
    if dmax:
        bits.append(f"dmax={dmax}")
    q = params.get("q")
    if q:
        bits.append(f"q={q}")
    bins = params.get("bins")
    if bins:
        bits.append(f"bins={bins}")
    min_count = params.get("min_count")
    if min_count:
        bits.append(f"min_count={min_count}")
    return ", ".join(bits) if bits else "(no cfg found in log)"


@dataclass
class FileMetrics:
    path: str
    penalty_scale: Optional[str] = None

    penalty_params: Dict[str, str] = field(default_factory=dict)

    penalty_enabled: Optional[bool] = None

    has_reward_to_final: bool = False

    penalty_data_count: int = 0
    penalty_data_zero: int = 0
    penalty_data_hist: Dict[int, int] = field(default_factory=dict)

    immediate_reward: RunningStats = field(default_factory=RunningStats)
    immediate_reward_eq_pos1: int = 0
    immediate_reward_eq_neg1: int = 0
    immediate_reward_eq_zero: int = 0
    immediate_reward_bins: List[int] = field(default_factory=lambda: [0] * (len(_bin_edges_reward()) - 1))
    immediate_reward_sample: List[float] = field(default_factory=list)

    reward_before_clip: RunningStats = field(default_factory=RunningStats)
    reward_before_sample: List[float] = field(default_factory=list)

    final_reward: RunningStats = field(default_factory=RunningStats)
    final_reward_eq_pos1: int = 0
    final_reward_eq_neg1: int = 0
    final_reward_eq_zero: int = 0
    final_reward_bins: List[int] = field(default_factory=lambda: [0] * (len(_bin_edges_reward()) - 1))
    final_reward_sample: List[float] = field(default_factory=list)

    penalty_weighted: RunningStats = field(default_factory=RunningStats)
    penalty_weighted_bins: List[int] = field(default_factory=lambda: [0] * (len(_bin_edges_penalty()) - 1))
    penalty_weighted_sample: List[float] = field(default_factory=list)

    final_corrections_correct_on_finalized: Optional[int] = None
    final_corrections_total_finalized: Optional[int] = None
    final_corrections_prop_on_finalized: Optional[float] = None


@dataclass
class ScaleAgg:
    files: int = 0

    penalty_data_count: int = 0
    penalty_data_zero: int = 0
    penalty_data_hist: Dict[int, int] = field(default_factory=dict)

    immediate_reward: RunningStats = field(default_factory=RunningStats)
    immediate_reward_eq_pos1: int = 0
    immediate_reward_eq_neg1: int = 0
    immediate_reward_eq_zero: int = 0
    immediate_reward_bins: List[int] = field(default_factory=lambda: [0] * (len(_bin_edges_reward()) - 1))

    reward_before_clip: RunningStats = field(default_factory=RunningStats)

    final_reward: RunningStats = field(default_factory=RunningStats)
    final_reward_eq_pos1: int = 0
    final_reward_eq_neg1: int = 0
    final_reward_eq_zero: int = 0
    final_reward_bins: List[int] = field(default_factory=lambda: [0] * (len(_bin_edges_reward()) - 1))

    penalty_weighted: RunningStats = field(default_factory=RunningStats)
    penalty_weighted_bins: List[int] = field(default_factory=lambda: [0] * (len(_bin_edges_penalty()) - 1))

    final_corrections_correct_on_finalized: int = 0
    final_corrections_total_finalized: int = 0
    final_corrections_prop_sum: float = 0.0
    final_corrections_prop_count: int = 0
    final_corrections_files_with_stats: int = 0


def parse_log_file(path: str, *, header_only: bool, max_header_lines: int) -> FileMetrics:
    metrics = FileMetrics(path=path)

    reward_edges = _bin_edges_reward()
    pen_edges = _bin_edges_penalty()
    rng = random.Random(hash(path) & 0xFFFFFFFF)
    seen_reward_before = 0
    seen_immediate_reward = 0
    seen_final_reward = 0
    seen_penalty_weighted = 0

    try:
        with open(path, "r", errors="replace") as f:
            for line_idx, line in enumerate(f, 1):
                if not metrics.has_reward_to_final and RE_REWARD_TO_FINAL.search(line):
                    metrics.has_reward_to_final = True

                # Capture scale-specific tuning even if the rest of config is missing.
                m = RE_PENALTY_SURVIVAL_TUNING.search(line)
                if m:
                    metrics.penalty_params.setdefault("bins", m.group(1))
                    metrics.penalty_params.setdefault("q", m.group(2))
                    metrics.penalty_params.setdefault("min_count", m.group(3))
                    metrics.penalty_params.setdefault("dmax", m.group(4))
                m = RE_PENALTY_LOGCOMP_TUNING.search(line)
                if m:
                    metrics.penalty_params.setdefault("dmax", m.group(1))

                # Collect penalty-related configuration parameters.
                # NOTE: scanning with multiple finditer() per line is expensive on huge logs.
                # We therefore only do the key/value extraction in the first max_header_lines.
                if line_idx <= max_header_lines:
                    # We keep first-seen value per key.
                    for m in RE_LOH_KV.finditer(line):
                        k = m.group(1)
                        v = m.group(2).rstrip(")]}>,")
                        if _is_penalty_related_key(k) and k not in metrics.penalty_params:
                            metrics.penalty_params[k] = v

                    for m in RE_LOWER_KV.finditer(line):
                        k = m.group(1)
                        v = m.group(2).rstrip(")]}>,")
                        if _is_penalty_related_key(k) and k not in metrics.penalty_params:
                            metrics.penalty_params[k] = v

                    for m in RE_UPPER_EQ.finditer(line):
                        k = m.group(1)
                        v = m.group(2).rstrip(")]}>,")
                        if _is_penalty_related_key(k) and k not in metrics.penalty_params:
                            metrics.penalty_params[k] = v

                if metrics.penalty_scale is None:
                    m = RE_PENALTY_SCALE.search(line)
                    if m:
                        metrics.penalty_scale = m.group(1)

                if metrics.penalty_scale is None:
                    m = RE_PENALTY_SCALE_MODE.search(line)
                    if m:
                        metrics.penalty_scale = m.group(1)

                if metrics.penalty_enabled is None:
                    # Prefer explicit LOH_ENABLE_PENALTY if present
                    v = metrics.penalty_params.get("LOH_ENABLE_PENALTY")
                    if v is not None:
                        metrics.penalty_enabled = (v.strip() == "1")

                if header_only and line_idx >= max_header_lines:
                    break

                m = RE_RB_REWARD.search(line)
                if m:
                    value = _safe_float(m.group(1))
                    if value is not None:
                        metrics.immediate_reward.add(value)
                        seen_immediate_reward += 1
                        _reservoir_add(metrics.immediate_reward_sample, value, seen_immediate_reward, 20000, rng)
                        metrics.immediate_reward_bins[_bin_index(value, reward_edges)] += 1
                        if abs(value - 1.0) <= 1e-12:
                            metrics.immediate_reward_eq_pos1 += 1
                        elif abs(value + 1.0) <= 1e-12:
                            metrics.immediate_reward_eq_neg1 += 1
                        elif abs(value) <= 1e-12:
                            metrics.immediate_reward_eq_zero += 1
                    continue

                m = RE_IMMEDIATE_REWARD.search(line)
                if m:
                    value = _safe_float(m.group(1))
                    if value is not None:
                        metrics.immediate_reward.add(value)
                        seen_immediate_reward += 1
                        _reservoir_add(metrics.immediate_reward_sample, value, seen_immediate_reward, 20000, rng)
                        metrics.immediate_reward_bins[_bin_index(value, reward_edges)] += 1
                        if abs(value - 1.0) <= 1e-12:
                            metrics.immediate_reward_eq_pos1 += 1
                        elif abs(value + 1.0) <= 1e-12:
                            metrics.immediate_reward_eq_neg1 += 1
                        elif abs(value) <= 1e-12:
                            metrics.immediate_reward_eq_zero += 1
                    continue

                m = RE_REWARD_BEFORE_CLIP.search(line)
                if m:
                    value = _safe_float(m.group(1))
                    if value is not None:
                        metrics.reward_before_clip.add(value)
                        seen_reward_before += 1
                        _reservoir_add(metrics.reward_before_sample, value, seen_reward_before, 20000, rng)
                    continue

                m = RE_PENALTY_DATA.search(line)
                if m:
                    metrics.penalty_data_count += 1
                    items = int(m.group(1))
                    metrics.penalty_data_hist[items] = metrics.penalty_data_hist.get(items, 0) + 1
                    if items == 0:
                        metrics.penalty_data_zero += 1
                    continue

                m = RE_FINAL_REWARD.search(line)
                if m:
                    value = _safe_float(m.group(1))
                    if value is not None:
                        metrics.final_reward.add(value)
                        seen_final_reward += 1
                        _reservoir_add(metrics.final_reward_sample, value, seen_final_reward, 20000, rng)
                        metrics.final_reward_bins[_bin_index(value, reward_edges)] += 1
                        if abs(value - 1.0) <= 1e-12:
                            metrics.final_reward_eq_pos1 += 1
                        elif abs(value + 1.0) <= 1e-12:
                            metrics.final_reward_eq_neg1 += 1
                        elif abs(value) <= 1e-12:
                            metrics.final_reward_eq_zero += 1
                    continue

                m = RE_PENALTY_WEIGHTED.search(line)
                if m:
                    value = _safe_float(m.group(1))
                    if value is not None:
                        metrics.penalty_weighted.add(value)
                        seen_penalty_weighted += 1
                        _reservoir_add(metrics.penalty_weighted_sample, value, seen_penalty_weighted, 20000, rng)
                        metrics.penalty_weighted_bins[_bin_index(value, pen_edges)] += 1
                    continue

                # Infer penalty enabled if log didn't print it explicitly but we saw penalty_data.
                if metrics.penalty_enabled is None and metrics.penalty_data_count > 0:
                    metrics.penalty_enabled = True

                if "FINAL_CORRECTIONS" in line:
                    m_on = RE_CORR_ON_FINALIZED.search(line)
                    m_tot = RE_CORR_FINALIZED_TOTAL.search(line)
                    if m_on and m_tot:
                        # take last one in file
                        metrics.final_corrections_correct_on_finalized = int(m_on.group(1))
                        metrics.final_corrections_total_finalized = int(m_tot.group(1))

                m = RE_FINAL_CORR_PROP.search(line)
                if m:
                    prop = _safe_float(m.group(1))
                    if prop is not None:
                        # take last one in file
                        metrics.final_corrections_prop_on_finalized = prop

    except FileNotFoundError:
        raise
    except Exception as e:
        raise RuntimeError(f"failed to parse {path}: {e}") from e

    return metrics


def add_to_agg(agg: ScaleAgg, fm: FileMetrics) -> None:
    agg.files += 1

    agg.penalty_data_count += fm.penalty_data_count
    agg.penalty_data_zero += fm.penalty_data_zero
    for k, v in fm.penalty_data_hist.items():
        agg.penalty_data_hist[k] = agg.penalty_data_hist.get(k, 0) + v

    agg.immediate_reward.count += fm.immediate_reward.count
    agg.immediate_reward.sum += fm.immediate_reward.sum
    agg.immediate_reward.min = min(agg.immediate_reward.min, fm.immediate_reward.min)
    agg.immediate_reward.max = max(agg.immediate_reward.max, fm.immediate_reward.max)
    agg.immediate_reward_eq_pos1 += fm.immediate_reward_eq_pos1
    agg.immediate_reward_eq_neg1 += fm.immediate_reward_eq_neg1
    agg.immediate_reward_eq_zero += fm.immediate_reward_eq_zero
    for i, c in enumerate(fm.immediate_reward_bins):
        agg.immediate_reward_bins[i] += c

    agg.reward_before_clip.count += fm.reward_before_clip.count
    agg.reward_before_clip.sum += fm.reward_before_clip.sum
    agg.reward_before_clip.min = min(agg.reward_before_clip.min, fm.reward_before_clip.min)
    agg.reward_before_clip.max = max(agg.reward_before_clip.max, fm.reward_before_clip.max)

    agg.final_reward.count += fm.final_reward.count
    agg.final_reward.sum += fm.final_reward.sum
    agg.final_reward.min = min(agg.final_reward.min, fm.final_reward.min)
    agg.final_reward.max = max(agg.final_reward.max, fm.final_reward.max)
    agg.final_reward_eq_pos1 += fm.final_reward_eq_pos1
    agg.final_reward_eq_neg1 += fm.final_reward_eq_neg1
    agg.final_reward_eq_zero += fm.final_reward_eq_zero
    for i, c in enumerate(fm.final_reward_bins):
        agg.final_reward_bins[i] += c

    agg.penalty_weighted.count += fm.penalty_weighted.count
    agg.penalty_weighted.sum += fm.penalty_weighted.sum
    agg.penalty_weighted.min = min(agg.penalty_weighted.min, fm.penalty_weighted.min)
    agg.penalty_weighted.max = max(agg.penalty_weighted.max, fm.penalty_weighted.max)
    for i, c in enumerate(fm.penalty_weighted_bins):
        agg.penalty_weighted_bins[i] += c

    if (
        fm.final_corrections_correct_on_finalized is not None
        and fm.final_corrections_total_finalized is not None
        and fm.final_corrections_total_finalized > 0
    ):
        agg.final_corrections_files_with_stats += 1
        agg.final_corrections_correct_on_finalized += fm.final_corrections_correct_on_finalized
        agg.final_corrections_total_finalized += fm.final_corrections_total_finalized

    if fm.final_corrections_prop_on_finalized is not None:
        agg.final_corrections_prop_sum += fm.final_corrections_prop_on_finalized
        agg.final_corrections_prop_count += 1


def _pct(num: int, den: int) -> Optional[float]:
    if den <= 0:
        return None
    return 100.0 * num / den


def _fmt_pct(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}%"


def _fmt_float(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{value:.6g}"


def _glob_files(patterns: List[str]) -> List[str]:
    out: List[str] = []
    for pat in patterns:
        if pat.lower().endswith(".md") and os.path.exists(pat):
            # Allow feeding a previously generated report to avoid re-scanning huge globs.
            # Accept both:
            #   - **ac_sb3_...log** (old report format)
            #   - - ac_sb3_...log  (manifest format)
            rx_bold = re.compile(r"^- \*\*(ac_sb3_[^*]+\.log)\*\*\s*$")
            rx_bullet = re.compile(r"^-\s+(ac_sb3_\S+\.log)\s*$")
            try:
                with open(pat, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        s = line.rstrip("\n")
                        m = rx_bold.match(s)
                        if m:
                            out.append(m.group(1))
                            continue
                        m = rx_bullet.match(s)
                        if m:
                            out.append(m.group(1))
            except OSError:
                pass
            continue

        matches = glob.glob(pat)
        if matches:
            out.extend(matches)
        else:
            # also allow passing exact paths
            if os.path.exists(pat):
                out.append(pat)
    # de-dupe stable order
    seen = set()
    uniq = []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return sorted(uniq)


def _total_size_bytes(paths: List[str]) -> int:
    total = 0
    for p in paths:
        try:
            total += os.path.getsize(p)
        except OSError:
            continue
    return total


def _fmt_bytes(num: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(num)
    for u in units:
        if value < 1024.0 or u == units[-1]:
            if u == "B":
                return f"{int(value)}{u}"
            return f"{value:.2f}{u}"
        value /= 1024.0
    return f"{value:.2f}PB"


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "patterns",
        nargs="+",
        help="Glob patterns or file paths, e.g. ac_sb3_0204*_3m_*.log",
    )
    ap.add_argument(
        "--name-contains",
        default=None,
        help="Only include files whose path contains this substring.",
    )
    ap.add_argument(
        "--show-files",
        action="store_true",
        help="Print per-file metrics (for debugging).",
    )
    ap.add_argument(
        "--report-md",
        default=None,
        help="Write a detailed per-scale/per-file Markdown report to this path.",
    )
    ap.add_argument(
        "--only-penalty-final",
        action="store_true",
        help="Only include logs with LOH_ENABLE_PENALTY=1 and at least one [Reward→Final] block.",
    )
    ap.add_argument(
        "--rank-clip-sat",
        type=int,
        default=0,
        help="If >0, print top N files by final_reward clip saturation (|final_reward|==1).",
    )
    ap.add_argument(
        "--progress-every",
        type=int,
        default=25,
        help="Print progress every N files (0 disables).",
    )
    ap.add_argument(
        "--header-only",
        action="store_true",
        help="Only parse the first N lines of each file to extract config; do not scan full file for distributions.",
    )
    ap.add_argument(
        "--max-header-lines",
        type=int,
        default=8000,
        help="How many lines to scan for config in each file (also used by --header-only).",
    )
    args = ap.parse_args(argv)

    paths = _glob_files(args.patterns)
    if args.name_contains:
        paths = [p for p in paths if args.name_contains in p]

    if not paths:
        print("No files matched.", file=sys.stderr)
        return 2

    total_bytes = _total_size_bytes(paths)
    t0 = time.time()
    print(f"[scan] files={len(paths)} total={_fmt_bytes(total_bytes)}")
    if args.name_contains:
        print(f"[scan] name_contains={args.name_contains!r}")
    if args.only_penalty_final:
        print("[scan] filter=only penalty=1 and has [Reward→Final]")
    if args.header_only:
        print(f"[scan] mode=header-only max_header_lines={args.max_header_lines}")

    by_scale: Dict[str, ScaleAgg] = defaultdict(ScaleAgg)
    unknown_scale: ScaleAgg = ScaleAgg()
    files_by_scale: DefaultDict[str, List[FileMetrics]] = defaultdict(list)

    kept_paths: List[str] = []
    kept_files: List[FileMetrics] = []
    for i, path in enumerate(paths, 1):
        if args.progress_every and (i == 1 or i % args.progress_every == 0):
            elapsed = max(1e-9, time.time() - t0)
            rate = i / elapsed
            print(f"[scan] {i}/{len(paths)} ({rate:.2f} files/s) {path}")

        fm = parse_log_file(path, header_only=args.header_only, max_header_lines=args.max_header_lines)

        if args.only_penalty_final:
            if fm.penalty_enabled is not True:
                continue
            if (not args.header_only) and (not fm.has_reward_to_final):
                continue
            kept_paths.append(path)

        kept_files.append(fm)

        # Determine scale label: if penalty is disabled, group separately.
        if fm.penalty_enabled is False:
            scale = "<penalty_disabled>"
        else:
            scale = _get_penalty_scale(fm)
        if scale == "<unknown>":
            add_to_agg(unknown_scale, fm)
        else:
            add_to_agg(by_scale[scale], fm)

        if args.report_md:
            files_by_scale[scale].append(fm)

        if args.show_files:
            pr0 = _pct(fm.penalty_data_zero, fm.penalty_data_count)
            sat = _pct(fm.final_reward_eq_pos1 + fm.final_reward_eq_neg1, fm.final_reward.count)
            rb_min = None if fm.reward_before_clip.count == 0 else fm.reward_before_clip.min
            rb_max = None if fm.reward_before_clip.count == 0 else fm.reward_before_clip.max
            print(
                f"{i:4d}/{len(paths)} {scale:14s} pd0={_fmt_pct(pr0):>8s} "
                f"sat={_fmt_pct(sat):>8s} rb=[{_fmt_float(rb_min)},{_fmt_float(rb_max)}] "
                f"final_mean={_fmt_float(fm.final_reward.mean):>10s} "
                f"pen_mean={_fmt_float(fm.penalty_weighted.mean):>10s} {path}"
            )
            if fm.penalty_enabled is not False:
                print(f"       cfg: {_compact_cfg(fm.penalty_params)}")

    elapsed = max(1e-9, time.time() - t0)
    print(f"[scan] done: parsed={len(kept_files)} elapsed={elapsed:.1f}s")

    if args.rank_clip_sat and kept_files:
        if args.header_only:
            print("\n# Top files by clip_sat (skipped: header-only mode)")
        else:
            def clip_sat_pct(fm: FileMetrics) -> float:
                den = fm.final_reward.count
                if den <= 0:
                    return -1.0
                num = fm.final_reward_eq_pos1 + fm.final_reward_eq_neg1
                return 100.0 * num / den

            ranked = sorted(kept_files, key=lambda fm: (clip_sat_pct(fm), fm.final_reward.count), reverse=True)
            topn = max(0, min(args.rank_clip_sat, len(ranked)))
            print("")
            print(f"# Top {topn} files by clip_sat")
            for fm in ranked[:topn]:
                sat = clip_sat_pct(fm)
                rb_min = None if fm.reward_before_clip.count == 0 else fm.reward_before_clip.min
                rb_max = None if fm.reward_before_clip.count == 0 else fm.reward_before_clip.max
                scale = _get_penalty_scale(fm)
                wpen = fm.penalty_params.get("LOH_REWARD_W_PENALTY") or fm.penalty_params.get("LOH_REWARD_W_PENALTY:")
                formula = _get_penalty_formula(fm.penalty_params)
                cutoff = _get_penalty_cutoff(fm.penalty_params)
                dmax = fm.penalty_params.get("dmax") or fm.penalty_params.get("penalty_dmax")
                q = fm.penalty_params.get("q")
                print(
                    f"clip_sat={sat:6.2f}% scale={scale:12s} w_pen={wpen or 'n/a':>6s} "
                    f"formula={formula or 'n/a':>10s} cutoff={cutoff or 'n/a':>6s} "
                    f"dmax={dmax or 'n/a':>6s} q={q or 'n/a':>6s} "
                    f"rb=[{_fmt_float(rb_min)},{_fmt_float(rb_max)}] n_final={fm.final_reward.count} {fm.path}"
                )

    print("# Reward/Penalty Signal Summary (by penalty_scale)")
    if args.only_penalty_final:
        print(f"files: {len(kept_paths)} (filtered from {len(paths)})")
        print("filter: only penalty=1 and has [Reward→Final]")
    else:
        print(f"files: {len(paths)}")

    def emit(scale: str, agg: ScaleAgg) -> None:
        if args.header_only:
            # In header-only mode we don't scan distributions; only show file count.
            print("\nscale: " + scale)
            print(f"  files: {agg.files}")
            return

        pd0 = _pct(agg.penalty_data_zero, agg.penalty_data_count)
        sat = _pct(agg.final_reward_eq_pos1 + agg.final_reward_eq_neg1, agg.final_reward.count)
        zero = _pct(agg.final_reward_eq_zero, agg.final_reward.count)

        imm_sat = _pct(
            agg.immediate_reward_eq_pos1 + agg.immediate_reward_eq_neg1,
            agg.immediate_reward.count,
        )

        final_min = None if agg.final_reward.count == 0 else agg.final_reward.min
        final_max = None if agg.final_reward.count == 0 else agg.final_reward.max
        pen_min = None if agg.penalty_weighted.count == 0 else agg.penalty_weighted.min
        pen_max = None if agg.penalty_weighted.count == 0 else agg.penalty_weighted.max

        late_ratio = _pct(agg.final_corrections_correct_on_finalized, agg.final_corrections_total_finalized)
        late_prop_mean = (
            None
            if agg.final_corrections_prop_count == 0
            else 100.0 * (agg.final_corrections_prop_sum / agg.final_corrections_prop_count)
        )

        print("")
        print(f"scale: {scale}")
        print(f"  files: {agg.files}")
        print(
            f"  immediate_reward: n={agg.immediate_reward.count}, mean={_fmt_float(agg.immediate_reward.mean)}, "
            f"min={_fmt_float(agg.immediate_reward.min if agg.immediate_reward.count else None)}, "
            f"max={_fmt_float(agg.immediate_reward.max if agg.immediate_reward.count else None)}, "
            f"clip_sat={_fmt_pct(imm_sat)}"
        )
        print(
            f"  penalty_data: n={agg.penalty_data_count}, zero={agg.penalty_data_zero} ({_fmt_pct(pd0)})"
        )
        print(
            f"  final_reward: n={agg.final_reward.count}, mean={_fmt_float(agg.final_reward.mean)}, "
            f"min={_fmt_float(final_min)}, max={_fmt_float(final_max)}, "
            f"clip_sat={_fmt_pct(sat)}, zero={_fmt_pct(zero)}"
        )
        print(
            f"  penalty_weighted: n={agg.penalty_weighted.count}, mean={_fmt_float(agg.penalty_weighted.mean)}, "
            f"min={_fmt_float(pen_min)}, max={_fmt_float(pen_max)}"
        )
        print(
            f"  late_corrections: by_counts={_fmt_pct(late_ratio)} (from {agg.final_corrections_files_with_stats} files), "
            f"prop_mean={_fmt_pct(late_prop_mean)} (from {agg.final_corrections_prop_count} files)"
        )

    for scale in sorted(by_scale.keys()):
        emit(scale, by_scale[scale])

    if unknown_scale.files:
        emit("<unknown>", unknown_scale)

    if args.report_md:
        reward_edges = _bin_edges_reward()
        pen_edges = _bin_edges_penalty()
        lines: List[str] = []
        lines.append("# AC Reward/Penalty Signal Detailed Report")
        lines.append("")

        lines.append("## Inputs")
        lines.append("")
        lines.append(f"- patterns: {' '.join(args.patterns)}")
        if args.name_contains:
            lines.append(f"- name_contains: {args.name_contains}")
        lines.append(f"- only_penalty_final: {int(bool(args.only_penalty_final))}")
        lines.append(f"- rank_clip_sat: {args.rank_clip_sat}")
        lines.append(f"- progress_every: {args.progress_every}")
        lines.append(f"- header_only: {int(bool(args.header_only))}")
        lines.append(f"- max_header_lines: {args.max_header_lines}")
        lines.append("")

        # File manifest: this is the main way to know exactly which logs were analyzed.
        lines.append("## File Manifest")
        lines.append("")
        manifest = kept_paths if args.only_penalty_final else paths
        lines.append(f"- count: {len(manifest)}")
        lines.append("")
        for p in manifest:
            lines.append(f"- {p}")
        lines.append("")

        if args.only_penalty_final:
            lines.append(f"files: {len(kept_paths)} (filtered from {len(paths)})")
            lines.append("filter: only penalty=1 and has [Reward→Final]")
        else:
            lines.append(f"files: {len(paths)}")
        lines.append("")

        for scale in sorted(files_by_scale.keys()):
            fms = files_by_scale[scale]
            lines.append(f"## penalty_scale = {scale}")
            lines.append("")

            # aggregate summary for this scale (skipped in header-only mode)
            if not args.header_only:
                agg = by_scale.get(scale) if scale != "<unknown>" else unknown_scale
                if agg:
                    pd0 = _pct(agg.penalty_data_zero, agg.penalty_data_count)
                    sat = _pct(agg.final_reward_eq_pos1 + agg.final_reward_eq_neg1, agg.final_reward.count)
                    lines.append("**Summary**")
                    lines.append(
                        f"- immediate_reward: n={agg.immediate_reward.count}, mean={_fmt_float(agg.immediate_reward.mean)}, bins={_format_bins(reward_edges, agg.immediate_reward_bins)}"
                    )
                    lines.append(
                        f"- penalty_data: n={agg.penalty_data_count}, zero={agg.penalty_data_zero} ({_fmt_pct(pd0)}), hist={_format_hist(agg.penalty_data_hist)}"
                    )
                    lines.append(
                        f"- final_reward(after clip): n={agg.final_reward.count}, mean={_fmt_float(agg.final_reward.mean)}, min={_fmt_float(agg.final_reward.min if agg.final_reward.count else None)}, max={_fmt_float(agg.final_reward.max if agg.final_reward.count else None)}, clip_sat={_fmt_pct(sat)}"
                    )
                    lines.append(
                        f"- final_reward bins: {_format_bins(reward_edges, agg.final_reward_bins)}"
                    )
                    lines.append(
                        f"- penalty(weighted) bins: {_format_bins(pen_edges, agg.penalty_weighted_bins)}"
                    )
                    lines.append("")

            lines.append("**Files**")
            lines.append("")
            for fm in sorted(fms, key=lambda x: x.path):
                pd0 = _pct(fm.penalty_data_zero, fm.penalty_data_count)
                sat = _pct(fm.final_reward_eq_pos1 + fm.final_reward_eq_neg1, fm.final_reward.count)

                if not args.header_only:
                    q_final = _quantiles_from_sample(fm.final_reward_sample, [0.5, 0.9, 0.99])
                    q_pen = _quantiles_from_sample(fm.penalty_weighted_sample, [0.5, 0.9, 0.99])
                    q_before = _quantiles_from_sample(fm.reward_before_sample, [0.5, 0.9, 0.99])
                    q_imm = _quantiles_from_sample(fm.immediate_reward_sample, [0.5, 0.9, 0.99])

                # compact params string (penalty-related)
                params_items = sorted(fm.penalty_params.items())
                params_str = "<br>".join([f"{k}={v}" for k, v in params_items]) if params_items else "(none)"

                lines.append(f"- **{fm.path}**")
                if fm.penalty_enabled is not False:
                    lines.append(f"  - cfg: {_compact_cfg(fm.penalty_params)}")
                lines.append(f"  - params: {params_str}")
                if not args.header_only:
                    if fm.penalty_enabled is False:
                        lines.append("  - note: penalty disabled (so penalty_data/final_reward may be absent)")
                    elif fm.penalty_enabled is None:
                        lines.append("  - note: penalty enabled/disabled not found in log")
                    lines.append(
                        f"  - penalty_data: n={fm.penalty_data_count}, zero={fm.penalty_data_zero} ({_fmt_pct(pd0)}), hist={_format_hist(fm.penalty_data_hist)}"
                    )
                    lines.append(
                        f"  - immediate_reward: n={fm.immediate_reward.count}, mean={_fmt_float(fm.immediate_reward.mean)}, min={_fmt_float(fm.immediate_reward.min if fm.immediate_reward.count else None)}, max={_fmt_float(fm.immediate_reward.max if fm.immediate_reward.count else None)}, p50={_fmt_float(q_imm[0.5])}, p90={_fmt_float(q_imm[0.9])}, p99={_fmt_float(q_imm[0.99])}"
                    )
                    lines.append(
                        f"  - immediate_reward bins: {_format_bins(reward_edges, fm.immediate_reward_bins)}"
                    )
                    lines.append(
                        f"  - reward(before clip): n={fm.reward_before_clip.count}, mean={_fmt_float(fm.reward_before_clip.mean)}, min={_fmt_float(fm.reward_before_clip.min if fm.reward_before_clip.count else None)}, max={_fmt_float(fm.reward_before_clip.max if fm.reward_before_clip.count else None)}, p50={_fmt_float(q_before[0.5])}, p90={_fmt_float(q_before[0.9])}, p99={_fmt_float(q_before[0.99])}"
                    )
                    lines.append(
                        f"  - final_reward(after clip): n={fm.final_reward.count}, mean={_fmt_float(fm.final_reward.mean)}, min={_fmt_float(fm.final_reward.min if fm.final_reward.count else None)}, max={_fmt_float(fm.final_reward.max if fm.final_reward.count else None)}, clip_sat={_fmt_pct(sat)}, p50={_fmt_float(q_final[0.5])}, p90={_fmt_float(q_final[0.9])}, p99={_fmt_float(q_final[0.99])}"
                    )
                    lines.append(
                        f"  - final_reward bins: {_format_bins(reward_edges, fm.final_reward_bins)}"
                    )
                    lines.append(
                        f"  - penalty(weighted): n={fm.penalty_weighted.count}, mean={_fmt_float(fm.penalty_weighted.mean)}, min={_fmt_float(fm.penalty_weighted.min if fm.penalty_weighted.count else None)}, max={_fmt_float(fm.penalty_weighted.max if fm.penalty_weighted.count else None)}, p50={_fmt_float(q_pen[0.5])}, p90={_fmt_float(q_pen[0.9])}, p99={_fmt_float(q_pen[0.99])}"
                    )
                    lines.append(
                        f"  - penalty bins: {_format_bins(pen_edges, fm.penalty_weighted_bins)}"
                    )

            lines.append("")

        with open(args.report_md, "w", encoding="utf-8") as out:
            out.write("\n".join(lines))
        print("")
        print(f"[report] wrote: {args.report_md}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
