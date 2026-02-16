#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import glob
import os
import re
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


RE_KV = re.compile(r"\b([A-Z][A-Z0-9_]+)=([^\s]+)")


def _safe_float(s: str) -> Optional[float]:
    try:
        if s is None:
            return None
        s = str(s).strip()
        if not s or s.upper() == "NA":
            return None
        return float(s)
    except Exception:
        return None


def _safe_int(s: str) -> Optional[int]:
    try:
        if s is None:
            return None
        s = str(s).strip()
        if not s or s.upper() == "NA":
            return None
        return int(s)
    except Exception:
        return None


def _parse_config_kv(config: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not config:
        return out
    for m in RE_KV.finditer(config):
        out[m.group(1)] = m.group(2)
    return out


def _trace_label(trace_file: str) -> str:
    tf = (trace_file or "").strip()
    if tf.endswith("data/MetaCDN/meta_reag.oracleGeneral.zst"):
        return "meta_reag"
    if tf.endswith("data/WikiCDN/wiki_2019t.oracleGeneral.zst"):
        return "wiki_2019t"
    if tf.endswith("data/TencentCBS/1063.oracleGeneral.zst"):
        return "1063"
    base = os.path.basename(tf)
    if base.endswith(".zst"):
        base = base[: -len(".zst")]
    return base or "<unknown>"


@dataclass
class Row:
    trace_label: str
    trace_file: str
    cache_ratio: str
    idx: str
    rep: str
    seed: str
    run_timestamp: str
    exit_code: int
    miss_ratio: Optional[float]
    byte_miss_ratio: Optional[float]
    throughput_mqps: Optional[float]
    compound: Optional[int]
    irt: Optional[int]
    softmax: Optional[int]
    signs: Optional[int]
    config: str

    @property
    def mode(self) -> str:
        if self.compound == 1:
            return "compound=1"
        if self.compound == 0 and self.irt == 0:
            return "compound=0,irt=0"
        if self.compound is None and self.irt is None:
            return "<unset>"
        return f"compound={self.compound},irt={self.irt}"


def _iter_results(paths: Iterable[str]) -> List[Row]:
    rows: List[Row] = []
    for path in paths:
        with open(path, newline="") as f:
            r = csv.DictReader(f)
            for d in r:
                config = (d.get("config") or "").strip()
                kv = _parse_config_kv(config)
                compound = _safe_int(kv.get("LOH_SCORE_USE_COMPOUND"))
                irt = _safe_int(kv.get("LOH_SCORE_USE_IRT"))
                softmax = _safe_int(kv.get("LOH_USE_SOFTMAX"))
                signs = _safe_int(kv.get("LOH_USE_HEURISTIC_SIGNS"))

                trace_file = (d.get("trace_file") or "").strip()
                rows.append(
                    Row(
                        trace_label=_trace_label(trace_file),
                        trace_file=trace_file,
                        cache_ratio=(d.get("cache_ratio") or "").strip(),
                        idx=(d.get("idx") or "").strip(),
                        rep=(d.get("rep") or "").strip(),
                        seed=(d.get("seed") or "").strip(),
                        run_timestamp=(d.get("run_timestamp") or "").strip(),
                        exit_code=_safe_int(d.get("exit_code")) or 0,
                        miss_ratio=_safe_float(d.get("miss_ratio")),
                        byte_miss_ratio=_safe_float(d.get("byte_miss_ratio")),
                        throughput_mqps=_safe_float(d.get("throughput_mqps")),
                        compound=compound,
                        irt=irt,
                        softmax=softmax,
                        signs=signs,
                        config=config,
                    )
                )
    return rows


def _write_csv(rows: List[Row], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "trace",
                "mode",
                "compound",
                "irt",
                "softmax",
                "signs",
                "miss_ratio",
                "byte_miss_ratio",
                "throughput_mqps",
                "exit_code",
                "run_timestamp",
                "config",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r.trace_label,
                    r.mode,
                    r.compound,
                    r.irt,
                    r.softmax,
                    r.signs,
                    "" if r.miss_ratio is None else f"{r.miss_ratio:.6f}",
                    "" if r.byte_miss_ratio is None else f"{r.byte_miss_ratio:.6f}",
                    "" if r.throughput_mqps is None else f"{r.throughput_mqps:.4f}",
                    r.exit_code,
                    r.run_timestamp,
                    r.config,
                ]
            )


def _write_md(rows: List[Row], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    # Sort: trace -> mode -> softmax -> signs
    rows = sorted(
        rows,
        key=lambda r: (
            r.trace_label,
            0 if r.mode == "compound=1" else 1,
            0 if (r.softmax or 0) == 0 else 1,
            0 if (r.signs or 0) == 0 else 1,
            r.run_timestamp,
        ),
    )

    def fmt(x: Optional[float], nd: int) -> str:
        if x is None:
            return "NA"
        return f"{x:.{nd}f}"

    with open(out_path, "w") as f:
        f.write("# compound/softmax/sign matrix summary\n\n")
        f.write("说明：\n")
        f.write("- softmax 对应 `LOH_USE_SOFTMAX`（Python 端动作映射）。\n")
        f.write("- signs 对应 `LOH_USE_HEURISTIC_SIGNS`（C 端评分符号修正）。\n")
        f.write("- 注意：当 `LOH_SCORE_USE_COMPOUND=1` 时，LOH.c 中 signs 对评分不生效（可能导致 signs=0/1 结果相同）。\n\n")

        f.write(
            "|trace|mode|softmax|signs|miss_ratio|byte_miss_ratio|thr_mqps|exit|run_timestamp|\n"
        )
        f.write("|---|---|---:|---:|---:|---:|---:|---:|---|\n")
        for r in rows:
            f.write(
                "|{trace}|{mode}|{softmax}|{signs}|{mr}|{bmr}|{thr}|{exit}|{ts}|\n".format(
                    trace=r.trace_label,
                    mode=r.mode,
                    softmax="NA" if r.softmax is None else r.softmax,
                    signs="NA" if r.signs is None else r.signs,
                    mr=fmt(r.miss_ratio, 6),
                    bmr=fmt(r.byte_miss_ratio, 6),
                    thr=fmt(r.throughput_mqps, 4),
                    exit=r.exit_code,
                    ts=r.run_timestamp,
                )
            )


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", help="Path to one results.csv")
    ap.add_argument("--results-glob", help="Glob for multiple results.csv")
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args(argv)

    paths: List[str] = []
    if args.results:
        paths.append(args.results)
    if args.results_glob:
        paths.extend(sorted(glob.glob(args.results_glob)))

    paths = [p for p in paths if p and os.path.isfile(p)]
    if not paths:
        print("No results.csv files found.", file=sys.stderr)
        return 2

    rows = _iter_results(paths)
    _write_csv(rows, args.out_csv)
    _write_md(rows, args.out_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
