#!/usr/bin/env python3
"""Summarize penalty-enabled LOH RL runs from ac_sb3_0203+ logs.

This script scans logs/ac_sb3_020[3-9]*.log, picks runs that actually
enabled penalty (marker: "LOH_ENABLE_PENALTY=1"), pairs them with
cachesim logs, and emits a Markdown summary.

Designed to be fast on huge logs:
- Reads only the first N lines from ac_sb3 logs.
- Reads only the last chunk from cachesim logs.
"""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
LOG_ROOT = ROOT / "logs"


@dataclass
class RunSummary:
    run_id: str
    ac_log: Path
    cachesim_log: Optional[Path]

    # core
    trace_path: Optional[str] = None
    cache_size_bytes: Optional[int] = None
    working_set_bytes: Optional[int] = None
    cache_ratio: Optional[float] = None
    num_req: Optional[int] = None
    seed: Optional[int] = None

    # toggles
    algo: Optional[str] = None
    score_model: Optional[str] = None
    score_use_irt: Optional[int] = None
    score_use_compound: Optional[int] = None
    use_softmax: Optional[int] = None
    action_scale: Optional[float] = None
    dual_channel: Optional[int] = None
    feature_log1p: Optional[int] = None
    use_heuristic_signs: Optional[int] = None

    # penalty config
    enable_penalty: Optional[int] = None
    penalty_mode_scale: Optional[str] = None
    penalty_reward_formula: Optional[str] = None
    penalty_scale_detail: Optional[str] = None
    reward_use_penalty: Optional[int] = None
    reward_w_penalty: Optional[float] = None
    reward_use_original: Optional[int] = None
    penalty_dmax: Optional[int] = None
    penalty_cutoff: Optional[int] = None
    survival_quantile: Optional[float] = None
    survival_bins: Optional[int] = None
    survival_mincount: Optional[int] = None

    # results
    miss_ratio: Optional[float] = None
    byte_miss_ratio: Optional[float] = None

    # optional baseline
    baseline_run_id: Optional[str] = None
    baseline_miss_ratio: Optional[float] = None
    baseline_byte_miss_ratio: Optional[float] = None


def read_head_lines(path: Path, max_lines: int) -> List[str]:
    lines: List[str] = []
    try:
        with path.open("r", errors="ignore") as f:
            for _ in range(max_lines):
                line = f.readline()
                if not line:
                    break
                lines.append(line.rstrip("\n"))
    except FileNotFoundError:
        return []
    return lines


def read_tail_text(path: Path, max_bytes: int) -> str:
    try:
        with path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            start = max(0, size - max_bytes)
            f.seek(start)
            data = f.read()
        return data.decode(errors="ignore")
    except FileNotFoundError:
        return ""


_RE_FLOAT = r"[-+]?(?:\d+\.\d+|\d+)(?:[eE][-+]?\d+)?"


def parse_ac_config(lines: List[str], out: RunSummary) -> None:
    text = "\n".join(lines)

    def m_int(pattern: str) -> Optional[int]:
        m = re.search(pattern, text)
        if not m:
            return None
        try:
            return int(m.group(1))
        except Exception:
            return None

    def m_float(pattern: str) -> Optional[float]:
        m = re.search(pattern, text)
        if not m:
            return None
        try:
            return float(m.group(1))
        except Exception:
            return None

    def m_str(pattern: str) -> Optional[str]:
        m = re.search(pattern, text)
        return m.group(1).strip() if m else None

    # enable_penalty marker
    out.enable_penalty = 1 if "LOH_ENABLE_PENALTY=1" in text else 0

    out.algo = m_str(r"\bLOH_RL_ALGO:\s*([A-Za-z0-9_]+)")

    # core toggles from config prints
    out.score_model = m_str(r"\[LOH CONFIG\] Score model: ([^\s]+)\b")
    out.dual_channel = 1 if "Dual-channel action space: ENABLED" in text else (0 if "Dual-channel action space: DISABLED" in text else None)
    out.use_softmax = 1 if "Softmax activation: ENABLED" in text else (0 if "Softmax activation: DISABLED" in text else None)

    out.score_use_irt = m_int(r"LOH_SCORE_USE_IRT=(\d+)")
    out.score_use_compound = m_int(r"LOH_SCORE_USE_COMPOUND=(\d+)")

    out.feature_log1p = m_int(r"\bLOH_FEATURE_LOG1P:\s*(\d+)")
    out.use_heuristic_signs = m_int(r"LOH_USE_HEURISTIC_SIGNS=(\d+)")

    # action scale from 'Action space' line
    out.action_scale = m_float(r"\bLOH_ACTION_SCALE=({f})".format(f=_RE_FLOAT))

    # seed
    out.seed = m_int(r"\bLOH_SEED:\s*(\d+)")

    # reward/penalty config lines (present only when penalty enabled)
    out.penalty_mode_scale = m_str(r"\bLOH_PENALTY_MODE/LOH_PENALTY_SCALE:\s*([^\n]+)")
    out.reward_use_penalty = m_int(r"\bLOH_REWARD_USE_PENALTY:\s*(\d+)")
    out.reward_w_penalty = m_float(r"\bLOH_REWARD_W_PENALTY:\s*({f})".format(f=_RE_FLOAT))
    out.reward_use_original = m_int(r"\bLOH_REWARD_USE_ORIGINAL:\s*(\d+)")

    # replay buffer prints often include formula/scale details
    out.penalty_reward_formula = m_str(r"\bpenalty_reward_formula=([a-zA-Z0-9_]+)")
    out.penalty_scale_detail = m_str(r"\bpenalty_scale=([^\n]+)")

    # other optional env-derived fields (only if printed)
    out.penalty_dmax = m_int(r"\bLOH_PENALTY_DMAX\s*[:=]\s*(\d+)")
    out.penalty_cutoff = m_int(r"\bLOH_PENALTY_CUTOFF\s*[:=]\s*(\d+)")
    out.survival_quantile = m_float(r"\bLOH_SURVIVAL_QUANTILE\s*[:=]\s*({f})".format(f=_RE_FLOAT))
    out.survival_bins = m_int(r"\bLOH_SURVIVAL_BINS\s*[:=]\s*(\d+)")
    out.survival_mincount = m_int(r"\bLOH_SURVIVAL_MINCOUNT\s*[:=]\s*(\d+)")


def parse_cachesim_tail(text: str, out: RunSummary) -> None:
    # final miss ratios: take last occurrence
    hits = list(re.finditer(r"miss ratio\s+({f}),\s+byte miss ratio\s+({f})".format(f=_RE_FLOAT), text))
    if hits:
        last = hits[-1]
        out.miss_ratio = float(last.group(1))
        out.byte_miss_ratio = float(last.group(2))


def parse_cachesim_head(lines: List[str], out: RunSummary) -> None:
    text = "\n".join(lines)

    m = re.search(r"trace path:\s*([^,\n]+)", text)
    if m:
        out.trace_path = m.group(1).strip()

    m = re.search(r"\bCache size:\s*(\d+)", text)
    if m:
        out.cache_size_bytes = int(m.group(1))

    # working set size bytes
    m = re.search(r"working set size: .*? byte\s*(\d+)", text)
    if m:
        out.working_set_bytes = int(m.group(1))

    # user-capped request count
    m = re.search(r"processed\s+(\d+)\s+requests capped by the user", text)
    if m:
        out.num_req = int(m.group(1))


def compute_ratio(out: RunSummary) -> None:
    if out.cache_size_bytes is not None and out.working_set_bytes:
        try:
            out.cache_ratio = out.cache_size_bytes / out.working_set_bytes
        except Exception:
            out.cache_ratio = None


def find_penalty_runs() -> List[RunSummary]:
    # use filename heuristics to avoid scanning huge logs: look for *_p1_* or *pen*
    candidates = sorted(LOG_ROOT.glob("ac_sb3_020[3-9]*p1*.log"))
    runs: List[RunSummary] = []
    for ac in candidates:
        run_id = ac.name[len("ac_sb3_") : -len(".log")]
        cachesim = ac.parent / f"cachesim_sb3_{run_id}.log"
        runs.append(RunSummary(run_id=run_id, ac_log=ac, cachesim_log=cachesim if cachesim.exists() else None))
    return runs


def _seed_suffix(seed: Optional[int]) -> Optional[str]:
    if seed is None:
        return None
    return f"s{seed}"


def baseline_candidates(run: RunSummary) -> List[str]:
    """Heuristically find matching p0 runs for a p1 run.

    We prefer the shortest filename that matches:
    - same date prefix (e.g. 0204)
    - same high-level trace token in run_id (e.g. 1063, meta_reag)
    - same seed suffix (s124)
    - contains '_p0_' or '_p0'
    """
    parts = run.run_id.split("_")
    if not parts:
        return []

    date_prefix = parts[0]
    seed_suf = _seed_suffix(run.seed)
    # try to pick a trace token: for most runs it's the 3rd component (0204_3m_1063_...)
    trace_token = parts[2] if len(parts) >= 3 else None

    globs: List[str] = []
    if seed_suf and trace_token:
        globs.append(f"cachesim_sb3_{date_prefix}_*_{trace_token}_p0*_{seed_suf}.log")
        globs.append(f"cachesim_sb3_{date_prefix}_*_{trace_token}_p0_{seed_suf}.log")
        globs.append(f"cachesim_sb3_{date_prefix}_*_{trace_token}_p0_{seed_suf}_*.log")
    if seed_suf:
        globs.append(f"cachesim_sb3_{date_prefix}_*p0*_{seed_suf}.log")

    cand: List[Path] = []
    for g in globs:
        cand.extend(LOG_ROOT.glob(g))

    # filter out self (if any) and dedupe
    uniq: Dict[str, Path] = {}
    for p in cand:
        rid = p.name[len("cachesim_sb3_") : -len(".log")]
        if rid == run.run_id:
            continue
        uniq[rid] = p

    # prefer shortest run_id, then lexical
    return [k for k, _ in sorted(uniq.items(), key=lambda kv: (len(kv[0]), kv[0]))]


def parse_run(run: RunSummary, head_lines: int, tail_bytes: int) -> None:
    ac_head = read_head_lines(run.ac_log, head_lines)
    parse_ac_config(ac_head, run)

    if run.cachesim_log is not None:
        cs_head = read_head_lines(run.cachesim_log, head_lines)
        parse_cachesim_head(cs_head, run)
        tail_text = read_tail_text(run.cachesim_log, tail_bytes)
        parse_cachesim_tail(tail_text, run)
        compute_ratio(run)


def load_baseline_metrics(run_id: str, tail_bytes: int) -> Tuple[Optional[float], Optional[float]]:
    path = LOG_ROOT / f"cachesim_sb3_{run_id}.log"
    if not path.exists():
        return None, None
    text = read_tail_text(path, tail_bytes)
    hits = list(re.finditer(r"miss ratio\s+({f}),\s+byte miss ratio\s+({f})".format(f=_RE_FLOAT), text))
    if not hits:
        return None, None
    last = hits[-1]
    return float(last.group(1)), float(last.group(2))


def fmt_opt(v: object) -> str:
    return "-" if v is None else str(v)


def fmt_float(v: Optional[float], digits: int = 6) -> str:
    if v is None:
        return "-"
    return f"{v:.{digits}f}"


def fmt_ratio(v: Optional[float]) -> str:
    if v is None:
        return "-"
    return f"{v:.4f}"


def md_escape(s: str) -> str:
    return s.replace("|", "\\|")


def to_markdown(runs: List[RunSummary]) -> str:
    lines: List[str] = []
    lines.append("# LOH Penalty Runs Summary (0203+)")
    lines.append("")
    lines.append("本文件自动从 0203 之后的日志中筛选 `LOH_ENABLE_PENALTY=1` 的 run，并汇总 penalty 相关配置与最终 miss/byte-miss 结果。")
    lines.append("")

    # group by trace
    by_trace: Dict[str, List[RunSummary]] = {}
    for r in runs:
        trace = r.trace_path or "(unknown trace)"
        by_trace.setdefault(trace, []).append(r)

    for trace, trs in sorted(by_trace.items(), key=lambda x: x[0]):
        lines.append(f"## Trace: {trace}")
        lines.append("")
        lines.append("| run_id | req | seed | cache_ratio | softmax | irt | compound | penalty_mode | formula | scale_detail | use_pen | w_pen | miss | byte_miss | baseline(run_id) | Δmiss | Δbyte_miss |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---|---|---|---:|---:|---:|---:|---|---:|---:|")
        for r in sorted(trs, key=lambda x: x.run_id):
            base = r.baseline_run_id
            dmiss = (r.miss_ratio - r.baseline_miss_ratio) if (r.miss_ratio is not None and r.baseline_miss_ratio is not None) else None
            dbyte = (r.byte_miss_ratio - r.baseline_byte_miss_ratio) if (r.byte_miss_ratio is not None and r.baseline_byte_miss_ratio is not None) else None
            lines.append(
                "| {run_id} | {req} | {seed} | {ratio} | {soft} | {irt} | {cpd} | {pmode} | {form} | {sdetail} | {usepen} | {wpen} | {miss} | {bmiss} | {base} | {dmiss} | {dbyte} |".format(
                    run_id=md_escape(r.run_id),
                    req=fmt_opt(r.num_req),
                    seed=fmt_opt(r.seed),
                    ratio=fmt_ratio(r.cache_ratio),
                    soft=fmt_opt(r.use_softmax),
                    irt=fmt_opt(r.score_use_irt),
                    cpd=fmt_opt(r.score_use_compound),
                    pmode=md_escape(r.penalty_mode_scale or "-"),
                    form=md_escape(r.penalty_reward_formula or "-"),
                    sdetail=md_escape(r.penalty_scale_detail or "-"),
                    usepen=fmt_opt(r.reward_use_penalty),
                    wpen=fmt_float(r.reward_w_penalty, 3) if r.reward_w_penalty is not None else "-",
                    miss=fmt_float(r.miss_ratio, 6),
                    bmiss=fmt_float(r.byte_miss_ratio, 6),
                    base=md_escape(base) if base else "-",
                    dmiss=fmt_float(dmiss, 6) if dmiss is not None else "-",
                    dbyte=fmt_float(dbyte, 6) if dbyte is not None else "-",
                )
            )
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append("- `baseline(run_id)` 规则：若 `run_id` 包含 `_p1_`，则尝试将其替换为 `_p0_` 寻找对应 baseline cachesim 日志。")
    lines.append("- `Δmiss/Δbyte_miss` = 当前 - baseline（若 baseline 存在）。")
    lines.append("- 若某些 penalty 细分参数未出现在 Python 日志头部，则表格中显示为 `-`（脚本只读取日志的前若干行以提速）。")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--head-lines", type=int, default=260)
    ap.add_argument("--tail-bytes", type=int, default=2_000_000)
    ap.add_argument("--out", type=str, default=str(ROOT / "20260205-LOH_PENALTY_RUNS_0203_PLUS.md"))
    args = ap.parse_args()

    runs = find_penalty_runs()

    parsed: List[RunSummary] = []
    for r in runs:
        parse_run(r, head_lines=args.head_lines, tail_bytes=args.tail_bytes)
        if r.enable_penalty != 1:
            continue

        # baseline: best-effort heuristic search
        cands = baseline_candidates(r)
        if cands:
            base_id = cands[0]
            r.baseline_run_id = base_id
            bm, bb = load_baseline_metrics(base_id, tail_bytes=args.tail_bytes)
            r.baseline_miss_ratio = bm
            r.baseline_byte_miss_ratio = bb

        parsed.append(r)

    md = to_markdown(parsed)
    out_path = Path(args.out)
    out_path.write_text(md, encoding="utf-8")
    print(f"wrote: {out_path}")
    print(f"runs: {len(parsed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
