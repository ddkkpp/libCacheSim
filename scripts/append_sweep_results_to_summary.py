#!/usr/bin/env python3
# Append sweep results (results.csv) into 20260129-LOH_TESTED_CONFIGS_SUMMARY.md under the matching "## Trace: ..." section.
# Design goals:
# - Only add tests (markdown table rows). No narrative.
# - Idempotent: avoid inserting duplicate rows for the same results file + idx.
# - Insert before <!-- ROOT_LOGS_BEGIN --> within the trace section.

from __future__ import annotations

import argparse
import csv
import os
from typing import Dict, List, Tuple


TABLE_HEADER = "| 测试项 | OMR | BMR | 关键开关（从 results.csv 摘要） | 目录 / 结果 |"
TABLE_SEP = "| --- | ---: | ---: | --- | --- |"

# Backward-compat: older table layout had the results link in the 2nd column.
OLD_TABLE_HEADER = "| 测试项 | 目录 / 结果 | OMR | BMR | 关键开关（从 results.csv 摘要） |"
OLD_TABLE_SEP = "| --- | --- | ---: | ---: | --- |"


def parse_cfg_summary(cfg: str) -> str:
    kv: Dict[str, str] = {}
    for part in cfg.split():
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        kv[k.strip()] = v.strip()

    ordered_keys = [
        "LOH_RL_ALGO",
        "LOH_USE_SOFTMAX",
        "LOH_SCORE_MODEL",
        "LOH_SCORE_USE_COMPOUND",
        "LOH_SCORE_COMPOUND_V2",
        "LOH_FEATURE_LOG1P",
        "LOH_ENABLE_FEATURE_NORMALIZATION",
        "LOH_SOFTMAX_TEMP",
        "LOH_ACTION_BOUND",
        "LOH_ACTION_SCALE",
        "RL_UPDATE_INTERVAL",
        "LOH_MISS_RATIO_WEIGHT",
        "LOH_REWARD_SCALE",
        "LOH_INCLUDE_CACHE_FEATURES",
        "LOH_INCLUDE_HIT_MISS_FEATURES",
    ]

    parts: List[str] = []
    for k in ordered_keys:
        if k in kv:
            short_k = {
                "LOH_RL_ALGO": "algo",
                "LOH_USE_SOFTMAX": "softmax",
                "LOH_SCORE_MODEL": "score",
                "LOH_SCORE_USE_COMPOUND": "cpd",
                "LOH_SCORE_COMPOUND_V2": "cpd2",
                "LOH_FEATURE_LOG1P": "log1p",
                "LOH_ENABLE_FEATURE_NORMALIZATION": "norm",
                "LOH_SOFTMAX_TEMP": "temp",
                "LOH_ACTION_BOUND": "bound",
                "LOH_ACTION_SCALE": "scale",
                "RL_UPDATE_INTERVAL": "riu",
                "LOH_MISS_RATIO_WEIGHT": "mrw",
                "LOH_REWARD_SCALE": "rscale",
                "LOH_INCLUDE_CACHE_FEATURES": "cacheF",
                "LOH_INCLUDE_HIT_MISS_FEATURES": "hitmissF",
            }.get(k, k)
            parts.append(f"{short_k}={kv[k]}")

    return " ".join(parts)


def read_results(results_csv: str) -> List[Dict[str, str]]:
    with open(results_csv, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def find_trace_section(lines: List[str], trace_file: str) -> Tuple[int, int]:
    """Return (start_idx, end_idx_exclusive) for the trace section.

    The section starts at a line exactly "## Trace: <trace_file>".
    It ends at the next "## Trace:" or EOF.
    """
    header = f"## Trace: {trace_file}".rstrip()
    start = -1
    for i, line in enumerate(lines):
        if line.rstrip() == header:
            start = i
            break

    if start == -1:
        return (-1, -1)

    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## Trace: "):
            end = j
            break

    return (start, end)


def ensure_trace_section(lines: List[str], trace_file: str) -> Tuple[int, int]:
    start, end = find_trace_section(lines, trace_file)
    if start != -1:
        return (start, end)

    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"

    if lines and lines[-1].strip() != "":
        lines.append("\n")

    start = len(lines)
    lines.append(f"## Trace: {trace_file}\n")
    lines.append("\n")
    lines.append("### 近期测试\n")
    lines.append("\n")
    lines.append(TABLE_HEADER + "\n")
    lines.append(TABLE_SEP + "\n")
    lines.append("\n")
    lines.append("<!-- ROOT_LOGS_BEGIN -->\n")
    lines.append("\n")
    lines.append("<!-- ROOT_LOGS_END -->\n")

    end = len(lines)
    return (start, end)


def find_insertion_point(lines: List[str], start: int, end: int) -> int:
    """Insert before <!-- ROOT_LOGS_BEGIN --> if present; else before end."""
    for i in range(start, end):
        if lines[i].rstrip() == "<!-- ROOT_LOGS_BEGIN -->":
            return i
    return end


def ensure_tests_table(lines: List[str], start: int, insert_at: int) -> int:
    """Ensure a tests table exists between start and insert_at; return row-insert index after the separator."""
    header_idx = -1
    sep_idx = -1

    for i in range(start, insert_at):
        if lines[i].rstrip() in (TABLE_HEADER, OLD_TABLE_HEADER):
            header_idx = i
            break

    if header_idx != -1:
        for j in range(header_idx + 1, insert_at):
            if lines[j].rstrip() in (TABLE_SEP, OLD_TABLE_SEP):
                sep_idx = j
                break
        if sep_idx == -1:
            # Table header exists but separator missing; add it.
            lines.insert(header_idx + 1, TABLE_SEP + "\n")
            sep_idx = header_idx + 1
        return sep_idx + 1

    # No table yet: create a minimal tests subsection and table.
    # Place it right before insert_at.
    block = [
        "### 近期测试\n",
        "\n",
        TABLE_HEADER + "\n",
        TABLE_SEP + "\n",
    ]
    for k, line in enumerate(block):
        lines.insert(insert_at + k, line)

    return insert_at + len(block)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary-md", required=True)
    ap.add_argument("--trace", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--sweep-id", required=True)
    ap.add_argument("--results-link", default=None, help="Link to show in markdown; default computed from --results")
    args = ap.parse_args()

    summary_md = args.summary_md
    trace_file = args.trace
    results_csv = args.results
    sweep_id = args.sweep_id

    # Prefer workspace-relative link if possible
    results_link = args.results_link
    if not results_link:
        repo_root = os.getcwd()
        try:
            results_link = os.path.relpath(results_csv, repo_root)
        except Exception:
            results_link = results_csv

    rows = read_results(results_csv)

    with open(summary_md, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    start, end = ensure_trace_section(lines, trace_file)
    insert_at = find_insertion_point(lines, start, end)
    row_insert_at = ensure_tests_table(lines, start, insert_at)

    # Detect which table layout is present in this trace section.
    # - new: link column at the end
    # - old: link column at the 2nd position
    table_layout = "new"
    for i in range(start, insert_at):
        s = lines[i].rstrip()
        if s == TABLE_HEADER:
            table_layout = "new"
            break
        if s == OLD_TABLE_HEADER:
            table_layout = "old"
            break

    # Build a fast duplicate set
    existing = set()
    for line in lines[start:insert_at]:
        if results_link in line:
            existing.add(line.strip())

    new_lines: List[str] = []
    for r in rows:
        if r.get("exit_code") != "0":
            continue
        idx = r.get("idx", "")
        omr = r.get("miss_ratio", "NA")
        bmr = r.get("byte_miss_ratio", "NA")
        cfg = r.get("config", "")
        cfg_summary = parse_cfg_summary(cfg)

        test_name = f"{sweep_id}#{idx}"
        if table_layout == "old":
            md_line = f"| {test_name} | [{results_link}]({results_link}) | {omr} | {bmr} | {cfg_summary} |\n"
        else:
            md_line = f"| {test_name} | {omr} | {bmr} | {cfg_summary} | [{results_link}]({results_link}) |\n"

        # Skip duplicates by exact line or by (link + sweep#idx) presence
        if md_line.strip() in existing:
            continue
        # Also avoid duplicates if same sweep_id#idx already exists
        if any(test_name in ln and results_link in ln for ln in lines[start:insert_at]):
            continue

        new_lines.append(md_line)

    if new_lines:
        for offset, nl in enumerate(new_lines):
            lines.insert(row_insert_at + offset, nl)

    with open(summary_md, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
