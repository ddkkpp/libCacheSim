#!/usr/bin/env python3
"""Merge sweep results (miss ratios) with AC reward/penalty statistics.

Inputs:
  - sweeps/<id>/results.csv (from scripts/sweep_loh_rl_sb3.sh)
  - sweeps/<id>/ac_reward_penalty_report.md (from scripts/analyze_ac_reward_signal.py)

Outputs:
  - summary CSV + Markdown table keyed by run_timestamp.

This script does NOT scan raw .log; it only parses the already-generated MD report.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class AcStats:
    penalty_scale: Optional[str] = None
    penalty_formula: Optional[str] = None
    w_penalty: Optional[float] = None
    clip_sat_pct: Optional[float] = None
    penalty_zero_pct: Optional[float] = None
    final_reward_mean: Optional[float] = None
    reward_before_min: Optional[float] = None
    reward_before_max: Optional[float] = None
    penalty_mean: Optional[float] = None


RE_FILE = re.compile(r"^- \*\*(ac_sb3_[^*]+\.log)\*\*$")
RE_SCALE = re.compile(r"^##\s+penalty_scale\s*=\s*(.+?)\s*$")

RE_CFG_WPEN = re.compile(r"\bcfg:.*?\bw_pen=([0-9.]+)")
RE_CFG_FORMULA = re.compile(r"\bcfg:.*?\bformula=([a-zA-Z0-9_]+)")

RE_PARAM_WPEN = re.compile(r"\bLOH_REWARD_W_PENALTY=([-+0-9.eE]+)")
RE_PARAM_FORMULA = re.compile(r"\bpenalty_reward_formula=([a-zA-Z0-9_]+)|\bLOH_PENALTY_REWARD_FORMULA=([a-zA-Z0-9_]+)")
RE_PENALTY_DATA_ZERO = re.compile(r"\bpenalty_data:.*?\bzero=\d+\s*\(([0-9.]+)%\)")
RE_FINAL_REWARD = re.compile(r"\bfinal_reward\(after clip\):.*?\bmean=([-+0-9.eE]+).*?\bclip_sat=([0-9.]+)%")
RE_REWARD_BEFORE_MINMAX = re.compile(r"\breward\(before clip\):.*?\bmin=([-+0-9.eE]+).*?\bmax=([-+0-9.eE]+)")
RE_PENALTY_WEIGHTED_MEAN = re.compile(r"\bpenalty\(weighted\):\s*n=\d+,\s*mean=([-+0-9.eE]+)")


def _safe_float(s: Optional[str]) -> Optional[float]:
    if s is None:
        return None
    try:
        return float(s)
    except Exception:
        return None


def parse_ac_report(path: Path) -> Dict[str, AcStats]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    out: Dict[str, AcStats] = {}

    cur_scale: Optional[str] = None
    cur_file: Optional[str] = None
    cur_block: List[str] = []

    def flush_block():
        nonlocal cur_file, cur_block, cur_scale
        if not cur_file:
            cur_block = []
            return
        blk = "\n".join(cur_block)
        st = AcStats(penalty_scale=cur_scale)

        # formula & w_penalty
        m = RE_CFG_FORMULA.search(blk)
        if m:
            st.penalty_formula = m.group(1)
        m = RE_PARAM_FORMULA.search(blk)
        if m and not st.penalty_formula:
            st.penalty_formula = m.group(1) or m.group(2)

        m = RE_CFG_WPEN.search(blk)
        if m:
            st.w_penalty = _safe_float(m.group(1))
        if st.w_penalty is None:
            m = RE_PARAM_WPEN.search(blk)
            if m:
                st.w_penalty = _safe_float(m.group(1))

        # stats
        m = RE_PENALTY_DATA_ZERO.search(blk)
        if m:
            st.penalty_zero_pct = _safe_float(m.group(1))

        m = RE_FINAL_REWARD.search(blk)
        if m:
            st.final_reward_mean = _safe_float(m.group(1))
            st.clip_sat_pct = _safe_float(m.group(2))

        m = RE_REWARD_BEFORE_MINMAX.search(blk)
        if m:
            st.reward_before_min = _safe_float(m.group(1))
            st.reward_before_max = _safe_float(m.group(2))

        m = RE_PENALTY_WEIGHTED_MEAN.search(blk)
        if m:
            st.penalty_mean = _safe_float(m.group(1))

        out[cur_file] = st
        cur_block = []

    for line in lines:
        m = RE_SCALE.match(line)
        if m:
            flush_block()
            cur_scale = m.group(1).strip()
            cur_file = None
            continue

        m = RE_FILE.match(line)
        if m:
            flush_block()
            cur_file = m.group(1).strip()
            cur_block = [line]
            continue

        if cur_file is not None:
            cur_block.append(line)

    flush_block()
    return out


def md_escape(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True, help="sweeps/<id>/results.csv")
    ap.add_argument("--ac-report", required=True, help="sweeps/<id>/ac_reward_penalty_report.md")
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args()

    results_path = Path(args.results)
    report_path = Path(args.ac_report)
    out_csv = Path(args.out_csv)
    out_md = Path(args.out_md)

    ac_stats = parse_ac_report(report_path)

    rows_out: List[dict] = []
    with results_path.open(newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            run_ts = (row.get("run_timestamp") or "").strip()
            if not run_ts:
                continue
            ac_log_name = f"ac_sb3_{run_ts}.log"
            st = ac_stats.get(ac_log_name, AcStats())

            rows_out.append(
                {
                    "idx": row.get("idx", ""),
                    "rep": row.get("rep", ""),
                    "seed": row.get("seed", ""),
                    "run_timestamp": run_ts,
                    "exit_code": row.get("exit_code", ""),
                    "miss_ratio": row.get("miss_ratio", ""),
                    "byte_miss_ratio": row.get("byte_miss_ratio", ""),
                    "throughput_mqps": row.get("throughput_mqps", ""),
                    "penalty_scale": st.penalty_scale or "",
                    "penalty_formula": st.penalty_formula or "",
                    "w_penalty": "" if st.w_penalty is None else f"{st.w_penalty}",
                    "penalty_zero_pct": "" if st.penalty_zero_pct is None else f"{st.penalty_zero_pct}",
                    "clip_sat_pct": "" if st.clip_sat_pct is None else f"{st.clip_sat_pct}",
                    "final_reward_mean": "" if st.final_reward_mean is None else f"{st.final_reward_mean}",
                    "reward_before_min": "" if st.reward_before_min is None else f"{st.reward_before_min}",
                    "reward_before_max": "" if st.reward_before_max is None else f"{st.reward_before_max}",
                    "penalty_mean": "" if st.penalty_mean is None else f"{st.penalty_mean}",
                    "config": row.get("config", ""),
                }
            )

    # Write CSV
    fields = list(rows_out[0].keys()) if rows_out else []
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows_out:
            w.writerow(row)

    # Write Markdown (simple table)
    headers = [
        "run_timestamp",
        "exit_code",
        "miss_ratio",
        "byte_miss_ratio",
        "penalty_scale",
        "penalty_formula",
        "w_penalty",
        "penalty_zero_pct",
        "clip_sat_pct",
        "final_reward_mean",
    ]
    out_md.parent.mkdir(parents=True, exist_ok=True)
    with out_md.open("w", encoding="utf-8") as f:
        f.write("# Penalty sweep summary\n\n")
        f.write(f"- results: {results_path.name}\n")
        f.write(f"- ac report: {report_path.name}\n\n")
        f.write("|" + "|".join(headers) + "|\n")
        f.write("|" + "|".join(["---"] * len(headers)) + "|\n")
        for row in rows_out:
            f.write(
                "|"
                + "|".join(md_escape(str(row.get(h, ""))) for h in headers)
                + "|\n"
            )

    print(f"wrote: {out_csv}")
    print(f"wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
