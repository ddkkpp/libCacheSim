#!/usr/bin/env python3
"""Collect root-level cachesim/ac sb3 logs and inject them into LOH_TESTED_CONFIGS_SUMMARY.md.

This script is intentionally conservative:
- Only considers root-level files matching cachesim_sb3_MMDD_HHMMSS.log
- Extracts metrics from the *final* 'LOH-OMR ... miss ratio ... byte miss ratio ... throughput ... MQPS' line
- Extracts a small set of config lines from the head of cachesim/ac logs
- Filters to req>=3,000,000 (to avoid tiny sanity runs dominating the summary)

Usage:
  python3 scripts/collect_root_logs_into_summary.py
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_MD = REPO_ROOT / "LOH_TESTED_CONFIGS_SUMMARY.md"


@dataclass(frozen=True)
class RootRun:
    date_yyyymmdd: str
    mmdd_hhmmss: str
    trace_path: str
    req_count: int
    omr: str
    bmr: str
    mqps: str
    cachesim_log: str
    ac_log: str | None
    rl_update_interval: int | None
    miss_ratio_weight: float | None
    byte_miss_ratio_weight: float | None
    score_model: str | None
    log1p: int | None
    reciprocal: int | None
    normalize: int | None
    use_irt: int | None
    use_cpd: int | None
    cache_feat: int | None
    cand_feat: int | None
    state_request_dim: int | None
    state_active_dim: int | None
    algo: str | None
    batch_size: int | None
    learning_rate: str | None
    gamma: str | None
    ent_coef: str | None
    reward_weights: str | None
    penalty_weights: str | None
    state_dim: int | None
    cachesim_notes: list[str]
    ac_notes: list[str]


_MMDD_HHMMSS_RE = re.compile(r"^cachesim_sb3_(?P<mmdd>\d{4})_(?P<hhmmss>\d{6})\.log$")

_METRIC_RE = re.compile(
    r"(?P<trace>\S+)\s+LOH-OMR\b.*?,\s*(?P<req>\d+)\s+req,\s*miss ratio\s+(?P<omr>\d+\.\d+),\s+byte miss ratio\s+(?P<bmr>\d+\.\d+),\s+throughput\s+(?P<mqps>\d+\.\d+)\s+MQPS",
    re.IGNORECASE,
)

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def run_cmd(args: list[str]) -> str:
    return subprocess.check_output(args, text=True, errors="replace")


def infer_year_for_mmdd(mmdd: str) -> int:
    today = date.today()  # current date in environment
    current_mmdd = f"{today.month:02d}{today.day:02d}"
    # If mmdd is "later" than today (e.g. 1112 when today is 0131), it belongs to previous year.
    return today.year - 1 if mmdd > current_mmdd else today.year


def to_yyyymmdd(mmdd: str) -> str:
    year = infer_year_for_mmdd(mmdd)
    return f"{year}{mmdd}"


def extract_last_metric_line(log_path: Path) -> tuple[str, int, str, str, str] | None:
    # Use tail to avoid scanning huge logs in Python.
    try:
        tail_text = run_cmd(["tail", "-n", "20000", str(log_path)])
    except Exception:
        return None

    last_match = None
    for raw in tail_text.splitlines():
        line = strip_ansi(raw)
        match = _METRIC_RE.search(line)
        if match:
            last_match = match

    if not last_match:
        return None

    return (
        strip_ansi(last_match.group("trace")).strip(),
        int(last_match.group("req")),
        last_match.group("omr"),
        last_match.group("bmr"),
        last_match.group("mqps"),
    )


def normalize_trace_path(raw: str) -> str:
    s = strip_ansi(raw).strip()
    m = re.search(r"(data/\S+)", s)
    return m.group(1) if m else s


def head_grep_lines(log_path: Path, pattern: re.Pattern[str], max_lines: int) -> list[str]:
    try:
        head_text = run_cmd(["head", "-n", str(max_lines), str(log_path)])
    except Exception:
        return []

    lines: list[str] = []
    for raw in head_text.splitlines():
        line = strip_ansi(raw).strip()
        if not line:
            continue
        if pattern.search(line):
            lines.append(line)
    return lines


def head_lines(log_path: Path, max_lines: int) -> list[str]:
    try:
        head_text = run_cmd(["head", "-n", str(max_lines), str(log_path)])
    except Exception:
        return []
    return [strip_ansi(line).rstrip("\n") for line in head_text.splitlines()]


def parse_cachesim_cfg(
    lines: list[str],
) -> tuple[
    int | None,
    float | None,
    float | None,
    str | None,
    int | None,
    int | None,
    int | None,
    int | None,
    int | None,
    int | None,
    int | None,
    int | None,
    list[str],
]:
    rl_update_interval: int | None = None
    mr_w: float | None = None
    bmr_w: float | None = None
    score_model: str | None = None
    log1p: int | None = None
    reciprocal: int | None = None
    normalize: int | None = None
    use_irt: int | None = None
    use_cpd: int | None = None
    cache_feat: int | None = None
    cand_feat: int | None = None
    state_request_dim: int | None = None
    state_active_dim: int | None = None
    notes: list[str] = []

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        # Restrict most parsing to the LOH INIT block to avoid catching unrelated debug lines.
        is_loh_init = "[LOH INIT]" in line

        m = re.search(r"\brl_update_interval=(\d+)", line)
        if m and rl_update_interval is None:
            rl_update_interval = int(m.group(1))

        m = re.search(
            r"Set\s+miss_ratio_weight=(?P<mr>\d+(?:\.\d+)?),\s*byte_miss_ratio_weight=(?P<bmr>\d+(?:\.\d+)?)",
            line,
            re.IGNORECASE,
        )
        if m and mr_w is None and bmr_w is None:
            try:
                mr_w = float(m.group("mr"))
                bmr_w = float(m.group("bmr"))
            except ValueError:
                pass

        if is_loh_init and score_model is None:
            m = re.search(r"LOH_SCORE_MODEL=\(default\s+([^\)]+)\)", line)
            if m:
                score_model = m.group(1).strip()

        if is_loh_init:
            m = re.search(r"feature mode:\s*LOG1P=(\d+),\s*RECIPROCAL=(\d+),\s*NORMALIZE=(\d+)", line, re.IGNORECASE)
            if m:
                if log1p is None:
                    log1p = int(m.group(1))
                if reciprocal is None:
                    reciprocal = int(m.group(2))
                if normalize is None:
                    normalize = int(m.group(3))

            m = re.search(r"Score feature mode:\s*USE_IRT=(\d+),\s*USE_COMPOUND=(\d+)", line, re.IGNORECASE)
            if m:
                if use_irt is None:
                    use_irt = int(m.group(1))
                if use_cpd is None:
                    use_cpd = int(m.group(2))

            m = re.search(
                r"Runtime state dims:.*?CACHE=(\d+),\s*CAND=(\d+).*?REQUEST=(\d+)\s*->\s*ACTIVE=(\d+)",
                line,
                re.IGNORECASE,
            )
            if m:
                if cache_feat is None:
                    cache_feat = int(m.group(1))
                if cand_feat is None:
                    cand_feat = int(m.group(2))
                if state_request_dim is None:
                    state_request_dim = int(m.group(3))
                if state_active_dim is None:
                    state_active_dim = int(m.group(4))

        # Keep a few high-signal notes but exclude IPC/sync chatter.
        if is_loh_init and re.search(r"AvgTopK enabled|Wait mode|Size data structure", line, re.IGNORECASE):
            notes.append(line)

    return (
        rl_update_interval,
        mr_w,
        bmr_w,
        score_model,
        log1p,
        reciprocal,
        normalize,
        use_irt,
        use_cpd,
        cache_feat,
        cand_feat,
        state_request_dim,
        state_active_dim,
        notes[:4],
    )


def parse_ac_cfg(lines: list[str]) -> tuple[
    str | None,
    int | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    int | None,
    list[str],
]:
    algo: str | None = None
    batch_size: int | None = None
    learning_rate: str | None = None
    gamma: str | None = None
    ent_coef: str | None = None
    reward_weights: str | None = None
    penalty_weights: str | None = None
    state_dim: int | None = None
    notes: list[str] = []

    def keep_note(line: str) -> None:
        if len(notes) < 4:
            notes.append(line)

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        # Drop noisy warnings / stack traces.
        if re.search(r"UserWarning|site-packages|Traceback\s*\(", line, re.IGNORECASE):
            continue
        if line.startswith("/") and ".py:" in line:
            continue

        # Explicitly exclude IPC/sync-related lines.
        if re.search(r"\bIPC config\b|poll_sleep_us|semaphore_requested", line, re.IGNORECASE):
            continue

        m = re.search(r"LOH RL Agent: Using\s+(SAC|TD3|PPO|A2C|TQC)\b", line)
        if m and algo is None:
            algo = m.group(1)
            continue

        m = re.search(r"\-\s*algorithm:\s*(.+)$", line, re.IGNORECASE)
        if m and algo is None:
            algo = m.group(1).strip()
            continue

        m = re.search(r"\-\s*batch_size:\s*(\d+)", line, re.IGNORECASE)
        if m and batch_size is None:
            batch_size = int(m.group(1))
            continue

        m = re.search(r"\-\s*learning_rate:\s*([^\s]+)", line, re.IGNORECASE)
        if m and learning_rate is None:
            learning_rate = m.group(1)
            continue

        m = re.search(r"\-\s*gamma:\s*([^\s]+)", line, re.IGNORECASE)
        if m and gamma is None:
            gamma = m.group(1)
            continue

        m = re.search(r"\-\s*ent_coef:\s*([^\s]+)", line, re.IGNORECASE)
        if m and ent_coef is None:
            ent_coef = m.group(1)
            continue

        m = re.search(r"Reward weights:\s*(.+)$", line, re.IGNORECASE)
        if m and reward_weights is None:
            reward_weights = m.group(1).strip()
            continue

        m = re.search(r"Penalty weights:\s*(.+)$", line, re.IGNORECASE)
        if m and penalty_weights is None:
            penalty_weights = m.group(1).strip()
            continue

        m = re.search(r"Using\s+(\d+)-dimensional state vector", line, re.IGNORECASE)
        if m and state_dim is None:
            state_dim = int(m.group(1))
            continue

        if re.search(r"policy|net_arch|layers", line, re.IGNORECASE):
            keep_note(line)

    return (
        algo,
        batch_size,
        learning_rate,
        gamma,
        ent_coef,
        reward_weights,
        penalty_weights,
        state_dim,
        notes,
    )


def collect_root_runs() -> list[RootRun]:
    root = REPO_ROOT
    cachesim_logs = sorted(root.glob("cachesim_sb3_????_??????.log"))

    runs: list[RootRun] = []
    for log_path in cachesim_logs:
        name = log_path.name
        match = _MMDD_HHMMSS_RE.match(name)
        if not match:
            continue

        mmdd = match.group("mmdd")
        hhmmss = match.group("hhmmss")
        yyyymmdd = to_yyyymmdd(mmdd)

        metric = extract_last_metric_line(log_path)
        if not metric:
            continue

        trace_path_raw, req_count, omr, bmr, mqps = metric
        trace_path = normalize_trace_path(trace_path_raw)

        # Keep only req >= 3,000,000
        if req_count < 3_000_000:
            continue

        cachesim_head = head_lines(log_path, max_lines=800)
        (
            rl_update_interval,
            mr_w,
            bmr_w,
            score_model,
            log1p,
            reciprocal,
            normalize,
            use_irt,
            use_cpd,
            cache_feat,
            cand_feat,
            state_request_dim,
            state_active_dim,
            cachesim_notes,
        ) = parse_cachesim_cfg(cachesim_head)

        ac_name = f"ac_sb3_{mmdd}_{hhmmss}.log"
        ac_path = root / ac_name
        algo: str | None = None
        batch_size: int | None = None
        learning_rate: str | None = None
        gamma: str | None = None
        ent_coef: str | None = None
        reward_weights: str | None = None
        penalty_weights: str | None = None
        state_dim: int | None = None
        ac_notes: list[str] = []
        if ac_path.exists():
            ac_head = head_lines(ac_path, max_lines=400)
            (
                algo,
                batch_size,
                learning_rate,
                gamma,
                ent_coef,
                reward_weights,
                penalty_weights,
                state_dim,
                ac_notes,
            ) = parse_ac_cfg(ac_head)

        runs.append(
            RootRun(
                date_yyyymmdd=yyyymmdd,
                mmdd_hhmmss=f"{mmdd}_{hhmmss}",
                trace_path=trace_path,
                req_count=req_count,
                omr=omr,
                bmr=bmr,
                mqps=mqps,
                cachesim_log=log_path.name,
                ac_log=ac_path.name if ac_path.exists() else None,
                rl_update_interval=rl_update_interval,
                miss_ratio_weight=mr_w,
                byte_miss_ratio_weight=bmr_w,
                score_model=score_model,
                log1p=log1p,
                reciprocal=reciprocal,
                normalize=normalize,
                use_irt=use_irt,
                use_cpd=use_cpd,
                cache_feat=cache_feat,
                cand_feat=cand_feat,
                state_request_dim=state_request_dim,
                state_active_dim=state_active_dim,
                algo=algo,
                batch_size=batch_size,
                learning_rate=learning_rate,
                gamma=gamma,
                ent_coef=ent_coef,
                reward_weights=reward_weights,
                penalty_weights=penalty_weights,
                state_dim=state_dim,
                cachesim_notes=cachesim_notes,
                ac_notes=ac_notes,
            )
        )

    # newest -> oldest
    runs.sort(key=lambda r: (r.date_yyyymmdd, r.mmdd_hhmmss), reverse=True)
    return runs


def trace_short_id(trace_path: str) -> str:
    # for the global index table
    if "MetaCDN" in trace_path:
        return "MetaCDN/meta_reag"
    if "WikiCDN" in trace_path and "wiki_2019t" in trace_path:
        return "WikiCDN/wiki_2019t"
    if "WikiCDN" in trace_path and "wiki_2016u" in trace_path:
        return "WikiCDN/wiki_2016u"
    if "TencentCBS" in trace_path or "1063" in trace_path:
        return "TencentCBS/1063"
    return Path(trace_path).name


def normalize_trace_header(trace_path: str) -> str:
    return f"## Trace: {trace_path}"


def build_cfg_short(r: RootRun) -> str:
    parts: list[str] = []
    if r.algo:
        parts.append(r.algo.split()[0])
    if r.score_model:
        parts.append(f"score={r.score_model}")
    if r.log1p is not None:
        parts.append(f"log1p={r.log1p}")
    if r.normalize is not None:
        parts.append(f"norm={r.normalize}")
    if r.use_cpd is not None:
        parts.append(f"cpd={r.use_cpd}")
    if r.use_irt is not None:
        parts.append(f"irt={r.use_irt}")
    if r.cache_feat is not None:
        parts.append(f"cacheF={r.cache_feat}")
    if r.cand_feat is not None:
        parts.append(f"candF={r.cand_feat}")
    if r.rl_update_interval is not None:
        parts.append(f"int={r.rl_update_interval}")
    return " ".join(parts) if parts else "—"


def build_index_block(runs: list[RootRun]) -> str:
    lines: list[str] = []
    lines.append("\n<!-- ROOT_LOG_INDEX_BEGIN -->")
    lines.append("\n### 根目录日志索引（cachesim_sb3_MMDD_HHMMSS.log）\n")
    lines.append("说明：扫描仓库根目录下 `cachesim_sb3_MMDD_HHMMSS.log` / `ac_sb3_MMDD_HHMMSS.log`，按文件名推断日期（基于当前日期跨年），并从日志末尾的 `LOH-OMR ... miss ratio ... byte miss ratio ... throughput ... MQPS` 汇总行提取 OMR/BMR/MQPS。\n")
    lines.append("只保留 `req>=3000000` 的 runs；trace 内再按 `req` 分组。\n")
    lines.append("| date | run | trace | req | OMR | BMR | MQPS | cfg | ref | note |")
    lines.append("|---:|---|---|---:|---:|---:|---:|---|---|---|")

    for r in runs:
        trace_id = trace_short_id(r.trace_path)
        ref_parts = [f"[cs]({r.cachesim_log})"]
        if r.ac_log:
            ref_parts.append(f"[ac]({r.ac_log})")
        ref = " ".join(ref_parts)

        cfg_short = build_cfg_short(r)

        lines.append(
            f"| {r.date_yyyymmdd} | {r.mmdd_hhmmss} | {trace_id} | {r.req_count} | {r.omr} | {r.bmr} | {r.mqps} | {cfg_short} | {ref} |  |"
        )

    lines.append("\n<!-- ROOT_LOG_INDEX_END -->\n")
    return "\n".join(lines) + "\n"


def build_trace_block(trace_runs: list[RootRun]) -> str:
    lines: list[str] = []
    lines.append("\n<!-- ROOT_LOGS_BEGIN -->")
    lines.append(f"\n### 根目录日志（{len(trace_runs)} 条，req>=3000000）\n")

    runs_by_req: dict[int, list[RootRun]] = {}
    for r in trace_runs:
        runs_by_req.setdefault(r.req_count, []).append(r)

    for req, req_runs in sorted(runs_by_req.items(), key=lambda kv: kv[0], reverse=True):
        lines.append(f"#### req={req}（{len(req_runs)} 条）\n")
        lines.append("| date | run | OMR | BMR | MQPS | cfg | ref | note |")
        lines.append("|---:|---|---:|---:|---:|---|---|---|")

        for r in req_runs:
            ref_parts = [f"[cs]({r.cachesim_log})"]
            if r.ac_log:
                ref_parts.append(f"[ac]({r.ac_log})")
            ref = " ".join(ref_parts)
            cfg_short = build_cfg_short(r)
            lines.append(f"| {r.date_yyyymmdd} | {r.mmdd_hhmmss} | {r.omr} | {r.bmr} | {r.mqps} | {cfg_short} | {ref} |  |")

        lines.append("")
        lines.append(f"##### 逐日志明细（req={req}）\n")

        for r in req_runs:
            lines.append(f"**{r.mmdd_hhmmss}**（{r.date_yyyymmdd}）\n")
            lines.append(f"- 结果：OMR={r.omr}，BMR={r.bmr}，MQPS={r.mqps}")
            lines.append(f"- logs：[{r.cachesim_log}]({r.cachesim_log})" + (f" / [{r.ac_log}]({r.ac_log})" if r.ac_log else ""))

            cachesim_kv: list[str] = []
            cachesim_kv.append(f"req={r.req_count}")
            if r.rl_update_interval is not None:
                cachesim_kv.append(f"int={r.rl_update_interval}")
            if r.miss_ratio_weight is not None and r.byte_miss_ratio_weight is not None:
                cachesim_kv.append(f"mr_w={r.miss_ratio_weight:.3f} bmr_w={r.byte_miss_ratio_weight:.3f}")
            if r.score_model:
                cachesim_kv.append(f"score={r.score_model}")
            if r.log1p is not None:
                cachesim_kv.append(f"log1p={r.log1p}")
            if r.reciprocal is not None:
                cachesim_kv.append(f"recip={r.reciprocal}")
            if r.normalize is not None:
                cachesim_kv.append(f"norm={r.normalize}")
            if r.use_irt is not None:
                cachesim_kv.append(f"irt={r.use_irt}")
            if r.use_cpd is not None:
                cachesim_kv.append(f"cpd={r.use_cpd}")
            if r.cache_feat is not None:
                cachesim_kv.append(f"cacheF={r.cache_feat}")
            if r.cand_feat is not None:
                cachesim_kv.append(f"candF={r.cand_feat}")
            if r.state_request_dim is not None and r.state_active_dim is not None:
                cachesim_kv.append(f"state={r.state_request_dim}->{r.state_active_dim}")
            if cachesim_kv or r.cachesim_notes:
                lines.append(f"- cachesim：{'；'.join(cachesim_kv) if cachesim_kv else '—'}")
                for n in r.cachesim_notes:
                    lines.append(f"  - {n}")

            rl_kv: list[str] = []
            if r.algo:
                rl_kv.append(f"algo={r.algo}")
            if r.batch_size is not None:
                rl_kv.append(f"batch={r.batch_size}")
            if r.learning_rate:
                rl_kv.append(f"lr={r.learning_rate}")
            if r.gamma:
                rl_kv.append(f"gamma={r.gamma}")
            if r.ent_coef:
                rl_kv.append(f"ent={r.ent_coef}")
            if r.state_dim is not None:
                rl_kv.append(f"state={r.state_dim}")
            if r.reward_weights:
                rl_kv.append(f"reward=({r.reward_weights})")
            if r.penalty_weights:
                rl_kv.append(f"penalty=({r.penalty_weights})")
            if rl_kv or r.ac_notes:
                lines.append(f"- RL：{'；'.join(rl_kv) if rl_kv else '—'}")
                for n in r.ac_notes:
                    lines.append(f"  - {n}")
            lines.append("")

    lines.append("\n<!-- ROOT_LOGS_END -->\n")

    return "\n".join(lines) + "\n"


def remove_existing_injected_blocks(md_text: str) -> str:
    # Remove marker-based blocks (preferred).
    md_text = re.sub(r"<!-- ROOT_LOG_INDEX_BEGIN -->.*?<!-- ROOT_LOG_INDEX_END -->\s*", "", md_text, flags=re.DOTALL)
    md_text = re.sub(r"<!-- ROOT_LOGS_BEGIN -->.*?<!-- ROOT_LOGS_END -->\s*", "", md_text, flags=re.DOTALL)

    # Remove previous global root-log index block.
    md_text = re.sub(
        r"\n### 根目录日志索引[\(（][^\n]*[\)）]\n.*?(?=\n## Trace:|\Z)",
        "\n",
        md_text,
        flags=re.DOTALL,
    )
    md_text = re.sub(
        r"\n### 根目录日志索引（补齐 20251212 之前）\n.*?(?=\n## Trace:|\Z)",
        "\n",
        md_text,
        flags=re.DOTALL,
    )

    # Remove legacy per-trace injected blocks that were inserted right before '#### 逐 sweep 细表'.
    md_text = re.sub(
        r"\n### 根目录日志（\d+[^\n]*\)\n.*?(?=\n#### 逐 sweep 细表)",
        "\n",
        md_text,
        flags=re.DOTALL,
    )

    # Remove previous appendix block (assumed appended to the end).
    md_text = re.sub(
        r"\n## 附录：根目录日志（其它 traces）\n.*\Z",
        "\n",
        md_text,
        flags=re.DOTALL,
    )
    return md_text


def inject_blocks(md_text: str, runs: list[RootRun]) -> str:
    md_text = remove_existing_injected_blocks(md_text)

    # 1) global index injection (before first '## Trace:')
    index_block = build_index_block(runs)
    first_trace_pos = md_text.find("\n## Trace:")
    if first_trace_pos == -1:
        md_text = md_text + "\n" + index_block
    else:
        md_text = md_text[:first_trace_pos] + "\n" + index_block + md_text[first_trace_pos:]

    # 2) per-trace injection: insert before the first '#### 逐 sweep 细表' within each trace section (when present)
    runs_by_header: dict[str, list[RootRun]] = {}
    for r in runs:
        header = normalize_trace_header(r.trace_path)
        runs_by_header.setdefault(header, []).append(r)

    unknown_runs: list[tuple[str, list[RootRun]]] = []

    for header, trace_runs in runs_by_header.items():
        header_pos = md_text.find(header)
        if header_pos == -1:
            unknown_runs.append((header, trace_runs))
            continue

        after_header = md_text[header_pos:]
        marker = "#### 逐 sweep 细表"
        marker_pos = after_header.find(marker)
        if marker_pos == -1:
            unknown_runs.append((header, trace_runs))
            continue

        inject_pos = header_pos + marker_pos

        # If a previous root-log block exists in this trace section, remove it before reinserting.
        existing_pos = md_text.find("\n### 根目录日志（", header_pos, inject_pos)
        if existing_pos != -1:
            md_text = md_text[:existing_pos] + md_text[inject_pos:]
            inject_pos = existing_pos

        md_text = md_text[:inject_pos] + build_trace_block(trace_runs) + md_text[inject_pos:]

    # 3) Any runs whose trace section doesn't exist (or lacks the marker) go to an appendix.
    if unknown_runs:
        md_text += "\n## 附录：根目录日志（其它 traces）\n"
        for header, trace_runs in sorted(unknown_runs, key=lambda x: x[0]):
            md_text += f"\n{header}\n"
            md_text += build_trace_block(trace_runs)

    return md_text


def main() -> int:
    if not SUMMARY_MD.exists():
        raise SystemExit(f"Missing {SUMMARY_MD}")

    runs = collect_root_runs()
    if not runs:
        print("No eligible root logs found (need req>=3,000,000 and a parsable LOH-OMR summary line).")
        return 0

    md_text = SUMMARY_MD.read_text(encoding="utf-8", errors="replace")
    updated = inject_blocks(md_text, runs)

    if updated == md_text:
        print("No changes made (blocks may already exist).")
        return 0

    SUMMARY_MD.write_text(updated, encoding="utf-8")
    print(f"Updated {SUMMARY_MD} with {len(runs)} root log runs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
