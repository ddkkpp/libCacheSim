#!/usr/bin/env python3
"""Analyze LOH penalty-related runs from markdown summaries.

Inputs:
  - 20260129-LOH_TESTED_CONFIGS_SUMMARY.md (main source of metrics)
  - 20260205-LOH_PENALTY_RUNS_0203_PLUS.md (optional: curated penalty table; used for coverage only)

Outputs:
  - Markdown report to stdout.

This script is intentionally dependency-free (stdlib only).
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class RunRow:
    date: str
    run_id: str
    trace: str
    req: int
    miss: float
    byte_miss: float
    cfg: str


@dataclass(frozen=True)
class PenaltyParams:
    pen: Optional[str]
    pen_mode: Optional[str]
    w_pen: Optional[float]
    r_use_pen: Optional[int]
    penonly: Optional[int]
    formula: Optional[str]


_PEN_MODES = {"reciprocal", "log", "survival", "linear"}


@dataclass(frozen=True)
class PenaltyRunView:
    source: str  # tested_summary | penalty_0203_plus
    date: str
    run_id: str
    trace: str
    req: int
    miss: float
    byte_miss: float
    cfg: str
    pen: PenaltyParams
    posnet: Optional[int]
    seed: Optional[int]


def drop_cfg_keys(cfg: str, keys: Sequence[str]) -> str:
    """Drop `k=v` tokens from a cfg string for display/signature purposes."""

    keyset = set(keys)
    out: List[str] = []
    for t in cfg.split():
        if "=" in t:
            k, _v = t.split("=", 1)
            if k in keyset:
                continue
        out.append(t)
    return _norm_space(" ".join(out))


def _strip_wbr(text: str) -> str:
    return text.replace("<wbr>", "")


def _as_int(s: str) -> Optional[int]:
    s = s.strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _as_float(s: str) -> Optional[float]:
    s = s.strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def _parse_md_table_rows(md_text: str) -> Iterable[List[str]]:
    """Yield markdown table rows as list of raw columns.

    This is permissive and will pick up rows from multiple tables in the file.
    """
    for line in md_text.splitlines():
        line = line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        # Skip separators like |---|---|
        if re.fullmatch(r"\|\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|", line):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        yield cols


def load_tested_configs(path: Path) -> List[RunRow]:
    text = path.read_text(encoding="utf-8", errors="replace")

    rows: List[RunRow] = []
    for cols in _parse_md_table_rows(text):
        # Two variants exist in this repo:
        #   A) date | run_id | trace | req | miss | byte_miss | cfg | logs | notes
        #   B) date | run_id | miss | byte_miss | cfg | logs | notes
        if len(cols) < 6:
            continue

        if cols[0].lower() in {"date", "日期", "day"}:
            continue

        date = cols[0]
        run_id = _strip_wbr(cols[1])

        if not run_id or run_id.lower() == "run_id":
            continue

        # Heuristic: if cols[2] looks like a float, we're in variant B.
        miss_idx = 2
        trace = ""
        req = None

        if len(cols) >= 9 and re.search(r"/", cols[2]):
            # Variant A
            trace = cols[2]
            req = _as_int(cols[3])
            miss_idx = 4
            cfg_idx = 6
        else:
            # Variant B (trace/req omitted)
            # We'll try to infer trace/req from run_id later (not possible reliably),
            # so we only keep rows that have explicit trace/req (variant A).
            continue

        miss = _as_float(cols[miss_idx])
        byte_miss = _as_float(cols[miss_idx + 1])
        cfg = cols[cfg_idx] if len(cols) > cfg_idx else ""
        cfg = _norm_space(cfg)

        # Some rows omit seed=... in cfg, but the run_id often contains `_sNNN_`.
        # Add it to cfg to improve baseline matching.
        if "seed=" not in cfg:
            m_seed = re.search(r"(?:^|_)s(?P<seed>\d+)(?:_|$)", run_id)
            if m_seed:
                cfg = _norm_space(cfg + f" seed={m_seed.group('seed')}")

        if req is None or miss is None or byte_miss is None:
            continue

        rows.append(
            RunRow(
                date=_norm_space(date),
                run_id=_norm_space(run_id),
                trace=_norm_space(trace),
                req=req,
                miss=miss,
                byte_miss=byte_miss,
                cfg=cfg,
            )
        )

    return rows


def parse_cfg_kv(cfg: str) -> Dict[str, str]:
    """Parse key=value tokens from cfg string."""
    out: Dict[str, str] = {}
    for m in re.finditer(r"(?P<k>[A-Za-z_][A-Za-z0-9_]*)=(?P<v>[^\s]+)", cfg):
        out[m.group("k")] = m.group("v")
    return out


def penalty_params_from_cfg(cfg: str) -> PenaltyParams:
    kv = parse_cfg_kv(cfg)

    pen = kv.get("pen")
    formula = kv.get("formula")

    pen_mode = None
    if pen in _PEN_MODES:
        pen_mode = pen

    w_pen = _as_float(kv.get("w_pen", ""))
    r_use_pen = _as_int(kv.get("r_use_pen", ""))
    penonly = _as_int(kv.get("penonly", ""))

    return PenaltyParams(
        pen=pen,
        pen_mode=pen_mode,
        w_pen=w_pen,
        r_use_pen=r_use_pen,
        penonly=penonly,
        formula=formula,
    )


def is_penalty_enabled(p: PenaltyParams) -> bool:
    if p.pen is None:
        return False
    if p.pen in {"0", "false", "False"}:
        return False
    return True


def signature_without_penalty(cfg: str, *, ignore_formula: bool) -> str:
    """Build a comparable signature by removing penalty-only knobs.

    If ignore_formula=True, also remove formula=... so that we can match more
    baselines (but this mixes formula changes into the comparison).
    """
    tokens = cfg.split()
    filtered: List[str] = []
    for t in tokens:
        if t.startswith("pen="):
            continue
        if t.startswith("w_pen="):
            continue
        if t.startswith("r_use_pen="):
            continue
        if t.startswith("penonly="):
            continue
        if ignore_formula and t.startswith("formula="):
            continue
        filtered.append(t)
    return " ".join(filtered)


def signature_relaxed(cfg: str) -> str:
    """Signature for baseline coverage under a relaxed definition.

    User intent (current workflow):
      - ignore seed differences
      - treat formula/net(v2)/net2 and penonly as *penalty-related* knobs
      - still distinguish other important knobs (softmax vs linear, irt/cpd/state,
        diag/signs/posnet, etc.)

    This function removes a broader set of keys than signature_without_penalty().
    """

    # NOTE: `posnet` is treated as a non-config tag in this workflow.
    ignore_keys = {"pen", "w_pen", "r_use_pen", "penonly", "formula", "seed", "posnet"}

    words: List[str] = []
    seen_words = set()
    kv_pairs: List[Tuple[str, str]] = []

    for token in cfg.split():
        if "=" in token:
            k, v = token.split("=", 1)
            if k in ignore_keys:
                continue
            kv_pairs.append((k, v))
        else:
            if token not in seen_words:
                seen_words.add(token)
                words.append(token)

    kv_pairs.sort(key=lambda x: (x[0], x[1]))
    return " ".join(words + [f"{k}={v}" for k, v in kv_pairs])


@dataclass(frozen=True)
class BaselineNeed:
    trace: str
    req: int
    signature: str
    n_penalty: int
    example_penalty_run_id: str
    example_penalty_cfg: str


def compute_baseline_needs_relaxed(rows: Sequence[RunRow]) -> Tuple[
    List[BaselineNeed],
    Dict[Tuple[str, int], List[Tuple[str, int]]],
    int,
    int,
]:
    """Compute missing baseline signatures under signature_relaxed().

    Returns:
      - missing needs list
      - per (trace,req) signature counts for penalty rows
      - total penalty rows considered (tested_summary)
      - total baseline rows considered (tested_summary)
    """

    buckets: Dict[Tuple[str, int, str], Dict[str, List[RunRow]]] = {}
    # structure: key -> {"penalty": [...], "baseline": [...]}
    total_penalty = 0
    total_baseline = 0

    for r in rows:
        p = penalty_params_from_cfg(r.cfg)
        sig = signature_relaxed(r.cfg)
        key = (r.trace, r.req, sig)
        slot = buckets.setdefault(key, {"penalty": [], "baseline": []})
        if is_penalty_enabled(p):
            slot["penalty"].append(r)
            total_penalty += 1
        else:
            slot["baseline"].append(r)
            total_baseline += 1

    needs: List[BaselineNeed] = []
    per_bucket_sig_counts: Dict[Tuple[str, int], Dict[str, int]] = {}

    for (trace, req, sig), slot in buckets.items():
        if not slot["penalty"]:
            continue
        per_bucket_sig_counts.setdefault((trace, req), {})[sig] = len(slot["penalty"])

        if slot["baseline"]:
            continue

        example = slot["penalty"][0]
        needs.append(
            BaselineNeed(
                trace=trace,
                req=req,
                signature=sig,
                n_penalty=len(slot["penalty"]),
                example_penalty_run_id=example.run_id,
                example_penalty_cfg=example.cfg,
            )
        )

    # convert signature-count dict to stable list for rendering
    bucket_sigs: Dict[Tuple[str, int], List[Tuple[str, int]]] = {}
    for k, d in per_bucket_sig_counts.items():
        bucket_sigs[k] = sorted(d.items(), key=lambda x: (-x[1], x[0]))

    needs.sort(key=lambda n: (n.trace, n.req, -n.n_penalty, n.signature))
    return needs, bucket_sigs, total_penalty, total_baseline


@dataclass
class DeltaRow:
    trace: str
    req: int
    run_id: str
    baseline_id: str
    baseline_cfg: str
    cfg: str
    pen: PenaltyParams
    miss: float
    byte_miss: float
    base_miss: float
    base_byte_miss: float

    @property
    def d_miss(self) -> float:
        return self.miss - self.base_miss

    @property
    def d_byte(self) -> float:
        return self.byte_miss - self.base_byte_miss


def compute_deltas(
    rows: Sequence[RunRow],
    *,
    match_date: bool,
    ignore_formula: bool,
) -> Tuple[List[DeltaRow], List[str]]:
    """Compute penalty-vs-baseline deltas.

    Baseline definition:
      - same (trace, req, signature_without_penalty(cfg))
      - penalty disabled (no pen= or pen=0)
      - if multiple baselines exist: choose minimal miss as baseline
    """

    # Group rows by comparison key.
    #
    # IMPORTANT: Matching across different dates can be misleading because the
    # experiment harness / defaults may have changed. By default, we only match
    # within the same date.
    groups: Dict[Tuple[str, str, int, str], List[RunRow]] = {}
    for r in rows:
        date_key = r.date if match_date else "*"
        key = (date_key, r.trace, r.req, signature_without_penalty(r.cfg, ignore_formula=ignore_formula))
        groups.setdefault(key, []).append(r)

    warnings: List[str] = []
    deltas: List[DeltaRow] = []

    for (_date_key, trace, req, sig), lst in groups.items():
        baselines: List[RunRow] = []
        penalties: List[RunRow] = []

        for r in lst:
            p = penalty_params_from_cfg(r.cfg)
            if is_penalty_enabled(p):
                penalties.append(r)
            else:
                baselines.append(r)

        if not penalties or not baselines:
            continue

        baseline = min(baselines, key=lambda x: x.miss)
        base_id = baseline.run_id

        for r in penalties:
            p = penalty_params_from_cfg(r.cfg)
            deltas.append(
                DeltaRow(
                    trace=trace,
                    req=req,
                    run_id=r.run_id,
                    baseline_id=base_id,
                    baseline_cfg=baseline.cfg,
                    cfg=r.cfg,
                    pen=p,
                    miss=r.miss,
                    byte_miss=r.byte_miss,
                    base_miss=baseline.miss,
                    base_byte_miss=baseline.byte_miss,
                )
            )

    return deltas, warnings


def fmt_f(x: float, digits: int = 6) -> str:
    return f"{x:.{digits}f}"


def fmt_signed(x: float, digits: int = 6) -> str:
    return f"{x:+.{digits}f}"


def md_escape(text: str) -> str:
    return text.replace("|", "\\|")


def md_wbr(text: str) -> str:
    """Insert HTML <wbr> break opportunities to reduce horizontal scrolling.

    GitHub/VS Code markdown preview typically honors <wbr> inside table cells.
    Keep this conservative to avoid changing semantics.
    """

    if not text:
        return text
    # Add breaks after common separators.
    text = text.replace("/", "/<wbr>")
    text = text.replace("_", "_<wbr>")
    text = text.replace(",", ",<wbr>")
    # Add breaks between tokens while preserving spaces.
    text = text.replace(" ", " <wbr>")
    return text


def cfg_to_pre_lines(cfg: str) -> str:
    """Format cfg for narrow display in <pre> blocks.

    One token per line avoids horizontal scrolling.
    """

    cfg = _norm_space(cfg)
    if not cfg:
        return ""
    return "\n".join(cfg.split())


def cfg_to_table_multiline(cfg: str, *, tokens_per_line: int = 6) -> str:
    """Format cfg inside a markdown table cell using <br> line breaks."""

    cfg = _norm_space(cfg)
    if not cfg:
        return ""
    toks = cfg.split()
    out_lines: List[str] = []
    for i in range(0, len(toks), max(1, tokens_per_line)):
        out_lines.append(" ".join(toks[i : i + tokens_per_line]))
    return "<br>".join(out_lines)


def short_source(source: str) -> str:
    return {"tested_summary": "ts", "penalty_0203_plus": "p0203"}.get(source, source)


def short_date(date: str) -> str:
    d = (date or "").strip()
    if d in {"-", ""}:
        return "-"
    m = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", d)
    if m:
        return f"{m.group(2)}{m.group(3)}"
    return d


def short_trace(trace: str) -> str:
    t = (trace or "").strip()
    if not t:
        return "-"
    # Prefer the last path segment (or dataset id)
    if "/" in t:
        last = t.split("/")[-1]
    else:
        last = t
    # drop common extensions
    last = re.sub(r"\.(zst|csv|txt)$", "", last)
    return last


def short_req(req: int) -> str:
    if req == 3_000_000:
        return "3M"
    if req % 1_000_000 == 0:
        return f"{req // 1_000_000}M"
    if req % 1_000 == 0:
        return f"{req // 1_000}k"
    return str(req)


def short_run_id(run_id: str, *, head: int = 14, tail: int = 8) -> str:
    r = (run_id or "").strip()
    if len(r) <= head + 1 + tail:
        return r
    return f"{r[:head]}…{r[-tail:]}"


def _pen_disp(p: PenaltyParams) -> str:
    return p.pen_mode or (p.pen or "-")


def _w_pen_disp(p: PenaltyParams) -> str:
    return "-" if p.w_pen is None else str(p.w_pen)


def _int_disp(x: Optional[int]) -> str:
    return "-" if x is None else str(x)


def _str_disp(x: Optional[str]) -> str:
    return "-" if (x is None or x == "") else x


def load_penalty_0203_plus(path: Path) -> List[PenaltyRunView]:
    """Load penalty-enabled rows from 20260205-LOH_PENALTY_RUNS_0203_PLUS.md.

    This table is curated and includes columns like use_pen/pen_mode/w_pen.
    We only keep rows where use_pen==1.
    """

    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    hdr_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("|run_id|") and "|use_pen|" in line and "|pen_mode|" in line:
            hdr_idx = i
            break
    if hdr_idx is None:
        return []

    header = [c.strip() for c in lines[hdr_idx].strip().strip("|").split("|")]
    out: List[PenaltyRunView] = []

    j = hdr_idx + 2
    while j < len(lines) and lines[j].strip().startswith("|"):
        cols = [c.strip() for c in lines[j].strip().strip("|").split("|")]
        if len(cols) < len(header):
            cols += [""] * (len(header) - len(cols))
        cols = cols[: len(header)]
        row = dict(zip(header, cols))
        j += 1

        use_pen = row.get("use_pen", "").strip()
        if use_pen != "1":
            continue

        run_id = _norm_space(row.get("run_id", ""))
        trace = _norm_space(row.get("trace", ""))
        req = _as_int(row.get("req", ""))
        miss = _as_float(row.get("miss", ""))
        byte_miss = _as_float(row.get("byte_miss", ""))
        if not run_id or req is None or miss is None or byte_miss is None:
            continue

        pen_mode = row.get("pen_mode", "").strip()
        pen = pen_mode if pen_mode in _PEN_MODES else "1"
        w_pen = _as_float(row.get("w_pen", ""))
        formula = row.get("formula", "").strip() or None

        # build a pseudo cfg for readability
        seed = _as_int(row.get("seed", ""))
        softmax = row.get("softmax", "").strip()
        log1p = row.get("log1p", "").strip()
        irt = row.get("irt", "").strip()
        compound = row.get("compound", "").strip()
        pseudo = ["SAC"]
        if softmax == "1":
            pseudo.append("softmax")
        pseudo.append(f"irt={irt}" if irt else "irt=?")
        pseudo.append(f"cpd={compound}" if compound else "cpd=?")
        pseudo.append("pen=1")
        pseudo.append(f"r_use_pen=1")
        if pen_mode in _PEN_MODES:
            pseudo.append(f"pen={pen_mode}")
        if w_pen is not None:
            pseudo.append(f"w_pen={w_pen}")
        if formula:
            pseudo.append(f"formula={formula}")
        if seed is not None:
            pseudo.append(f"seed={seed}")
        cfg = " ".join(pseudo)

        params = PenaltyParams(
            pen=pen,
            pen_mode=pen_mode if pen_mode in _PEN_MODES else None,
            w_pen=w_pen,
            r_use_pen=1,
            penonly=None,
            formula=formula,
        )
        out.append(
            PenaltyRunView(
                source="penalty_0203_plus",
                date="-",
                run_id=run_id,
                trace=trace,
                req=req,
                miss=miss,
                byte_miss=byte_miss,
                cfg=cfg,
                pen=params,
                posnet=None,
                seed=seed,
            )
        )

    return out


def build_penalty_views_from_tested(rows: Sequence[RunRow]) -> List[PenaltyRunView]:
    out: List[PenaltyRunView] = []
    for r in rows:
        params = penalty_params_from_cfg(r.cfg)
        if not is_penalty_enabled(params):
            continue

        kv = parse_cfg_kv(r.cfg)
        posnet = _as_int(kv.get("posnet", ""))
        seed = _as_int(kv.get("seed", ""))

        out.append(
            PenaltyRunView(
                source="tested_summary",
                date=r.date,
                run_id=r.run_id,
                trace=r.trace,
                req=r.req,
                miss=r.miss,
                byte_miss=r.byte_miss,
                cfg=r.cfg,
                pen=params,
                posnet=posnet,
                seed=seed,
            )
        )
    return out


def render_all_penalty_runs(views: Sequence[PenaltyRunView], *, tested_rows: Sequence[RunRow]) -> str:
    lines: List[str] = []
    lines.append("# LOH penalty runs 汇总（无Δ，仅配置+结果 / 自动生成）")
    lines.append("")

    total = len(views)
    by_source: Dict[str, int] = {}
    for v in views:
        by_source[v.source] = by_source.get(v.source, 0) + 1

    uniq_ids = len({v.run_id for v in views})
    lines.append(f"总计 penalty-enabled runs = **{total}**（去重 run_id = **{uniq_ids}**）")
    lines.append("\n".join([f"- {k}: {by_source[k]}" for k in sorted(by_source.keys())]))
    lines.append("")

    lines.append("## 全量明细")
    lines.append("")
    lines.append(
        "|src|date|trace|miss|byte_miss|req|run|pen|w_pen|formula|r_use_pen|penonly|seed|cfg|"
    )
    lines.append("|---|---|---|---:|---:|---:|---|---|---:|---|---:|---:|---:|---|")

    def sort_key(v: PenaltyRunView):
        return (v.trace, v.req, v.date, v.run_id)

    for v in sorted(views, key=sort_key):
        cfg_disp = drop_cfg_keys(v.cfg, ["posnet"])
        cfg_cell = cfg_to_table_multiline(cfg_disp, tokens_per_line=6)
        lines.append(
            "|"
            + "|".join(
                [
                    md_escape(short_source(v.source)),
                    md_escape(short_date(v.date)),
                    md_escape(short_trace(v.trace)),
                    fmt_f(v.miss),
                    fmt_f(v.byte_miss),
                    md_escape(short_req(v.req)),
                    md_escape(short_run_id(v.run_id)),
                    md_escape(_pen_disp(v.pen)),
                    md_escape(_w_pen_disp(v.pen)),
                    md_escape(_str_disp(v.pen.formula)),
                    md_escape(_int_disp(v.pen.r_use_pen)),
                    md_escape(_int_disp(v.pen.penonly)),
                    md_escape(_int_disp(v.seed)),
                    md_escape(cfg_cell),
                ]
            )
            + "|"
        )

    lines.append("")

    # Highlight: (formula net/net2/*net*) + w_pen in {2,3} (no posnet condition)
    lines.append("## 重点子集：formula=net/net2 且 w_pen=2/3")
    lines.append("")
    subset: List[PenaltyRunView] = []
    for v in views:
        if v.pen.w_pen not in (2.0, 3.0):
            continue
        f = (v.pen.formula or "")
        if not (f.startswith("net") or f == "net2"):
            continue
        subset.append(v)

    lines.append(f"匹配到 runs = **{len(subset)}**")
    lines.append("")
    if subset:
        lines.append("|date|trace|req|miss|byte_miss|run|pen|w_pen|formula|cfg|")
        lines.append("|---|---|---:|---:|---:|---|---|---:|---|---|")
        for v in sorted(subset, key=sort_key):
            cfg_disp = drop_cfg_keys(v.cfg, ["posnet"])
            cfg_cell = cfg_to_table_multiline(cfg_disp, tokens_per_line=6)
            lines.append(
                "|"
                + "|".join(
                    [
                        md_escape(short_date(v.date)),
                        md_escape(short_trace(v.trace)),
                        md_escape(short_req(v.req)),
                        fmt_f(v.miss),
                        fmt_f(v.byte_miss),
                        md_escape(short_run_id(v.run_id)),
                        md_escape(_pen_disp(v.pen)),
                        md_escape(_w_pen_disp(v.pen)),
                        md_escape(_str_disp(v.pen.formula)),
                        md_escape(cfg_cell),
                    ]
                )
                + "|"
            )
        lines.append("")
    else:
        lines.append("未匹配到（可能 posnet/pen/formula/w_pen 字段不在 cfg 里或记录为 NA）。")
        lines.append("")

    # Baseline coverage under relaxed signature
    needs, bucket_sigs, total_penalty, total_baseline = compute_baseline_needs_relaxed(tested_rows)
    lines.append("## baseline 对齐检查（忽略 seed + 把 formula/penonly 视为 penalty 相关）")
    lines.append("")
    lines.append(
        "口径：对 cfg 生成 relaxed signature，移除 `pen/w_pen/r_use_pen/penonly/formula/seed` 后对齐；" \
        "另外忽略 `posnet`（视为标签）；其余开关（如 softmax/linear、irt/cpd/state、diag/signs 等）必须一致。"
    )
    lines.append("")
    lines.append(
        f"tested_summary 中：penalty 行数 = **{total_penalty}**，baseline 行数 = **{total_baseline}**；" \
        f"缺少 baseline 的去重签名数 = **{len(needs)}**"
    )
    lines.append("")

    # Only focus on 3M request per current workflow.
    req_focus = 3_000_000
    needs_3m = [n for n in needs if n.req == req_focus]
    bucket_sigs_3m = {(trace, req): sigs for (trace, req), sigs in bucket_sigs.items() if req == req_focus}

    # De-duplicate missing needs by trace (1 baseline per trace is enough for this checklist).
    needs_3m_by_trace: Dict[str, BaselineNeed] = {}
    for n in needs_3m:
        if n.trace not in needs_3m_by_trace:
            needs_3m_by_trace[n.trace] = n
        else:
            cur = needs_3m_by_trace[n.trace]
            # keep the one covering more penalty rows, tie-break by signature
            if (n.n_penalty, n.signature) > (cur.n_penalty, cur.signature):
                needs_3m_by_trace[n.trace] = n
    needs_3m_min = [needs_3m_by_trace[t] for t in sorted(needs_3m_by_trace.keys())]

    varied = sorted(
        [(trace, req, len(sigs)) for (trace, req), sigs in bucket_sigs_3m.items()],
        key=lambda x: (-x[2], x[0], x[1]),
    )
    lines.append(f"### 其它配置是否统一？（仅 req={req_focus}；按 trace+req 统计 penalty 的 signature 种类数）")
    lines.append("")
    lines.append("|trace|req|penalty_signatures|")
    lines.append("|---|---:|---:|")
    for trace, req, n_sig in varied:
        lines.append(f"|{md_escape(short_trace(trace))}|{md_escape(short_req(req))}|{n_sig}|")
    lines.append("")

    lines.append("说明：`n_penalty` = 在 tested_summary 中，命中该签名的 penalty 行数（同一签名下可能有多条 penalty 配置/不同 w_pen/formula）。")
    lines.append("")

    if needs_3m_min:
        lines.append(f"### 缺少 baseline 的签名（仅 req={req_focus}；按 trace 去重后最小补跑集合）")
        lines.append("")
        lines.append("|trace|req|n_penalty|example_penalty_run|signature(relaxed)|example_penalty_cfg|")
        lines.append("|---|---:|---:|---|---|---|")
        for n in needs_3m_min:
            cfg_disp = drop_cfg_keys(n.example_penalty_cfg, ["posnet"])
            cfg_cell = cfg_to_table_multiline(cfg_disp, tokens_per_line=6)
            lines.append(
                "|"
                + "|".join(
                    [
                        md_escape(short_trace(n.trace)),
                        md_escape(short_req(n.req)),
                        str(n.n_penalty),
                        md_escape(short_run_id(n.example_penalty_run_id)),
                        md_escape(n.signature),
                        md_escape(cfg_cell),
                    ]
                )
                + "|"
            )
        lines.append("")
    else:
        lines.append("### 缺少 baseline 的签名")
        lines.append("")
        lines.append(
            f"未发现缺失（仅 req={req_focus}；在该 relaxed 口径下，所有 penalty signature 都能在 tested_summary 找到 pen=0 对照）。"
        )
        lines.append("")

    return "\n".join(lines) + "\n"


def render_report(deltas: Sequence[DeltaRow], max_rows: int = 30) -> str:
    lines: List[str] = []
    lines.append("# LOH penalty 参数效果分析（自动生成）")
    lines.append("")
    lines.append(f"统计样本：可对齐 baseline 的 penalty runs = **{len(deltas)}**")
    lines.append("")

    if not deltas:
        lines.append("未找到可对齐 baseline 的 penalty runs（可能是 baseline 签名无法匹配）。")
        return "\n".join(lines) + "\n"

    # Best/worst overall by Δmiss
    sorted_by_dm = sorted(deltas, key=lambda x: x.d_miss)

    def render_table(title: str, rows: Sequence[DeltaRow]):
        lines.append(f"## {title}")
        lines.append("")
        lines.append(
            "|trace|req|run_id|baseline|baseline_miss|baseline_byte|Δmiss|Δbyte|pen|w_pen|formula|r_use_pen|penonly|cfg|"
        )
        lines.append("|---|---:|---|---|---:|---:|---:|---:|---|---:|---|---:|---:|---|")
        for r in rows:
            pen_disp = r.pen.pen_mode or (r.pen.pen or "-")
            w_pen = "-" if r.pen.w_pen is None else str(r.pen.w_pen)
            formula = r.pen.formula or "-"
            r_use_pen = "-" if r.pen.r_use_pen is None else str(r.pen.r_use_pen)
            penonly = "-" if r.pen.penonly is None else str(r.pen.penonly)
            lines.append(
                "|"
                + "|".join(
                    [
                        md_escape(r.trace),
                        str(r.req),
                        md_escape(r.run_id),
                        md_escape(r.baseline_id),
                        fmt_f(r.base_miss),
                        fmt_f(r.base_byte_miss),
                        fmt_signed(r.d_miss),
                        fmt_signed(r.d_byte),
                        md_escape(pen_disp),
                        w_pen,
                        md_escape(formula),
                        r_use_pen,
                        penonly,
                        md_escape(r.cfg),
                    ]
                )
                + "|"
            )
        lines.append("")

    render_table(f"整体最优（按 Δmiss 排序，Top {min(max_rows, len(sorted_by_dm))}）", sorted_by_dm[:max_rows])
    render_table(
        f"整体最差（按 Δmiss 排序，Bottom {min(max_rows, len(sorted_by_dm))}）",
        list(reversed(sorted_by_dm[-max_rows:])),
    )

    # Best per (trace, req)
    best_by_bucket: Dict[Tuple[str, int], DeltaRow] = {}
    for r in deltas:
        k = (r.trace, r.req)
        if k not in best_by_bucket or r.d_miss < best_by_bucket[k].d_miss:
            best_by_bucket[k] = r

    lines.append("## 每个 trace+req 的最优 penalty 配置")
    lines.append("")
    lines.append("|trace|req|best_run|baseline|Δmiss|Δbyte|pen|w_pen|formula|cfg|")
    lines.append("|---|---:|---|---|---:|---:|---|---:|---|---|")
    for (trace, req), r in sorted(best_by_bucket.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        pen_disp = r.pen.pen_mode or (r.pen.pen or "-")
        w_pen = "-" if r.pen.w_pen is None else str(r.pen.w_pen)
        formula = r.pen.formula or "-"
        lines.append(
            "|"
            + "|".join(
                [
                    md_escape(trace),
                    str(req),
                    md_escape(r.run_id),
                    md_escape(r.baseline_id),
                    fmt_signed(r.d_miss),
                    fmt_signed(r.d_byte),
                    md_escape(pen_disp),
                    w_pen,
                    md_escape(formula),
                    md_escape(r.cfg),
                ]
            )
            + "|"
        )
    lines.append("")

    # Aggregate by (pen_mode, w_pen, formula)
    agg: Dict[Tuple[str, str, str], List[DeltaRow]] = {}
    for r in deltas:
        pen_mode = r.pen.pen_mode or (r.pen.pen or "-")
        w_pen = "-" if r.pen.w_pen is None else str(r.pen.w_pen)
        formula = r.pen.formula or "-"
        agg.setdefault((pen_mode, w_pen, formula), []).append(r)

    summary = []
    for k, lst in agg.items():
        avg_dm = sum(x.d_miss for x in lst) / len(lst)
        avg_db = sum(x.d_byte for x in lst) / len(lst)
        summary.append((avg_dm, avg_db, len(lst), k))

    summary.sort(key=lambda t: (t[0], -t[2]))

    lines.append("## 参数组合的平均效果（按 Δmiss 均值排序）")
    lines.append("")
    lines.append("|pen|w_pen|formula|n|avg_Δmiss|avg_Δbyte|")
    lines.append("|---|---:|---|---:|---:|---:|")
    for avg_dm, avg_db, n, (pen_mode, w_pen, formula) in summary[: min(50, len(summary))]:
        lines.append(
            f"|{md_escape(pen_mode)}|{w_pen}|{md_escape(formula)}|{n}|{fmt_signed(avg_dm)}|{fmt_signed(avg_db)}|"
        )
    lines.append("")

    return "\n".join(lines) + "\n"


def render_coverage(rows: Sequence[RunRow], *, max_rows: int = 80) -> str:
    """Render a coverage summary for penalty-enabled rows."""

    penalty_rows = []
    for r in rows:
        p = penalty_params_from_cfg(r.cfg)
        if is_penalty_enabled(p):
            penalty_rows.append((r, p))

    lines: List[str] = []
    lines.append("# LOH penalty 覆盖情况（自动生成）")
    lines.append("")
    lines.append(f"penalty enabled 的 runs（来自 tested summary）= **{len(penalty_rows)}**")
    lines.append("")

    # Unique combos by key knobs
    combos: Dict[Tuple[str, int, str, str, str, str, str], int] = {}
    for r, p in penalty_rows:
        pen_disp = p.pen_mode or (p.pen or "-")
        w_pen = "-" if p.w_pen is None else str(p.w_pen)
        formula = p.formula or "-"
        r_use_pen = "-" if p.r_use_pen is None else str(p.r_use_pen)
        penonly = "-" if p.penonly is None else str(p.penonly)

        key = (r.trace, r.req, pen_disp, w_pen, formula, r_use_pen, penonly)
        combos[key] = combos.get(key, 0) + 1

    lines.append("## 去重后的参数组合（trace+req+pen+w_pen+formula+r_use_pen+penonly）")
    lines.append("")
    lines.append("|trace|req|pen|w_pen|formula|r_use_pen|penonly|n|")
    lines.append("|---|---:|---|---:|---|---:|---:|---:|")

    # sort by trace, req, pen, w_pen
    def _sort_key(k: Tuple[str, int, str, str, str, str, str]):
        trace, req, pen, w_pen, formula, r_use_pen, penonly = k
        w = float(w_pen) if w_pen not in ("-", "") else -1.0
        return (trace, req, pen, w, formula, r_use_pen, penonly)

    for k in sorted(combos.keys(), key=_sort_key)[:max_rows]:
        trace, req, pen, w_pen, formula, r_use_pen, penonly = k
        lines.append(
            f"|{md_escape(trace)}|{req}|{md_escape(pen)}|{w_pen}|{md_escape(formula)}|{r_use_pen}|{penonly}|{combos[k]}|"
        )

    if len(combos) > max_rows:
        lines.append("")
        lines.append(f"（仅展示前 {max_rows} 条；实际去重组合数 = {len(combos)}）")

    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--tested",
        type=Path,
        default=Path("20260129-LOH_TESTED_CONFIGS_SUMMARY.md"),
        help="Path to 20260129-LOH_TESTED_CONFIGS_SUMMARY.md",
    )
    ap.add_argument(
        "--coverage-only",
        action="store_true",
        help="Only output penalty coverage checklist",
    )
    ap.add_argument(
        "--all-penalty",
        action="store_true",
        help="Output all penalty-enabled runs (config + metrics; no deltas)",
    )
    ap.add_argument(
        "--max-rows",
        type=int,
        default=30,
        help="Rows to show for best/worst tables",
    )
    ap.add_argument(
        "--no-match-date",
        action="store_true",
        help="Allow matching penalty runs to baselines from different dates (NOT recommended)",
    )
    ap.add_argument(
        "--ignore-formula",
        action="store_true",
        help="Ignore formula=... when matching baselines (mixes formula changes into Δ)",
    )

    args = ap.parse_args(argv)

    rows = load_tested_configs(args.tested)
    if args.coverage_only:
        print(render_coverage(rows), end="")
        return 0

    views: List[PenaltyRunView] = []
    views.extend(build_penalty_views_from_tested(rows))
    views.extend(load_penalty_0203_plus(Path("20260205-LOH_PENALTY_RUNS_0203_PLUS.md")))
    # default behavior: all-penalty report unless user explicitly wants deltas
    if args.all_penalty or True:
        print(render_all_penalty_runs(views, tested_rows=rows), end="")
        return 0

    # Unreachable currently; kept for future delta report revival.
    # deltas, _warnings = compute_deltas(
    #     rows,
    #     match_date=(not args.no_match_date),
    #     ignore_formula=args.ignore_formula,
    # )
    # print(render_report(deltas, max_rows=args.max_rows), end="")
    # return 0


if __name__ == "__main__":
    raise SystemExit(main())
