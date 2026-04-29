#!/usr/bin/env python3
import argparse
import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median


LINE_RE = re.compile(
    r"^(?P<trace>\S+)\s+(?P<algo>\S+)\s+cache size\s+"
    r"(?P<size>[0-9.]+)(?P<unit>KiB|MiB|GiB),\s+"
    r"(?P<req>[0-9,]+)\s+req,\s+miss ratio\s+(?P<mr>[0-9.]+),\s+"
    r"byte miss ratio\s+(?P<bmr>[0-9.]+),\s+throughput\s+"
    r"(?P<thr>[0-9.]+)\s+MQPS(?:,\s+runtime\s+(?P<runtime>[0-9.]+)\s+sec)?"
)

UNIT_TO_BYTES = {
    "KiB": 1024,
    "MiB": 1024 * 1024,
    "GiB": 1024 * 1024 * 1024,
}


def size_to_bytes(size: float, unit: str) -> float:
    return size * UNIT_TO_BYTES[unit]


def canonical_trace_id(trace_path: str) -> str:
    name = Path(trace_path).name
    suffixes = [
        ".oracleGeneral.zst",
        ".oracleGeneral",
        ".zst",
        ".csv",
        ".txt",
    ]
    for s in suffixes:
        if name.endswith(s):
            name = name[: -len(s)]
    return name


def parse_result_line(line: str):
    m = LINE_RE.match(line.strip())
    if not m:
        return None
    gd = m.groupdict()
    size = float(gd["size"])
    unit = gd["unit"]
    return {
        "trace_path": gd["trace"],
        "trace_id": canonical_trace_id(gd["trace"]),
        "algo": gd["algo"],
        "cache_size_bytes": size_to_bytes(size, unit),
        "cache_size_display": f"{gd['size']}{unit}",
        "mr": float(gd["mr"]),
        "bmr": float(gd["bmr"]),
        "runtime": float(gd["runtime"]) if gd.get("runtime") else None,
    }


def read_single_line_result(path: Path):
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return None
    first_line = text.splitlines()[0]
    return parse_result_line(first_line)


def build_loh_map(result_dir: Path):
    data = {}
    bad_files = []
    for fp in sorted(result_dir.glob("*.cachesim")):
        parsed = read_single_line_result(fp)
        if parsed is None:
            bad_files.append(fp.name)
            continue
        data[fp.name] = parsed
    return data, bad_files


def build_baseline_index(baseline_dir: Path):
    by_trace = defaultdict(list)
    bad_lines = 0
    files_seen = 0
    for fp in sorted(baseline_dir.glob("*.cachesim")):
        files_seen += 1
        text = fp.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            parsed = parse_result_line(line)
            if parsed is None:
                bad_lines += 1
                continue
            by_trace[parsed["trace_id"]].append(parsed)
    return by_trace, files_seen, bad_lines


def dataset_name(trace_id: str) -> str:
    if trace_id.startswith("tencentBlock_"):
        return "tencentBlock"
    if trace_id.startswith("alibabaBlock_"):
        return "alibabaBlock"
    if trace_id.startswith("wiki_"):
        return "wiki"
    if trace_id.startswith("meta_"):
        return "meta"
    return "other"


def rel_impr(base_val: float, loh_val: float):
    if base_val <= 0:
        return None
    return (base_val - loh_val) / base_val


def fmt_pct(x):
    if x is None:
        return "N/A"
    return f"{x * 100:.2f}%"


def fmt_float(x, n=6):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "N/A"
    return f"{x:.{n}f}"


def summarize(args):
    mr_dir = Path(args.mr_dir)
    bmr_dir = Path(args.bmr_dir)
    baseline_dir = Path(args.baseline_dir)
    out_md = Path(args.out_md)
    out_csv = Path(args.out_csv)

    mr_map, mr_bad = build_loh_map(mr_dir)
    bmr_map, bmr_bad = build_loh_map(bmr_dir)
    base_by_trace, base_file_count, base_bad_lines = build_baseline_index(baseline_dir)

    file_names = sorted(set(mr_map.keys()) & set(bmr_map.keys()))
    only_mr = sorted(set(mr_map.keys()) - set(bmr_map.keys()))
    only_bmr = sorted(set(bmr_map.keys()) - set(mr_map.keys()))

    rows = []
    no_baseline_trace = []
    no_cache_match = []

    algo_stats = defaultdict(lambda: {
        "count": 0,
        "mr_wins": 0,
        "bmr_wins": 0,
        "mr_impr": [],
        "bmr_impr": [],
    })

    ds_counter = Counter()

    for name in file_names:
        mr_rec = mr_map[name]
        bmr_rec = bmr_map[name]

        trace_id = mr_rec["trace_id"]
        loh_cache = mr_rec["cache_size_bytes"]
        loh_mr = mr_rec["mr"]
        loh_bmr = bmr_rec["bmr"]
        ds_counter[dataset_name(trace_id)] += 1

        candidates = [x for x in base_by_trace.get(trace_id, []) if x["algo"] != "LOH"]
        if not candidates:
            no_baseline_trace.append(trace_id)
            continue

        best_per_algo = {}
        for c in candidates:
            rel_diff = abs(c["cache_size_bytes"] - loh_cache) / loh_cache
            if rel_diff > args.cache_tol:
                continue
            algo = c["algo"]
            old = best_per_algo.get(algo)
            if old is None or rel_diff < old["rel_diff"]:
                rec = dict(c)
                rec["rel_diff"] = rel_diff
                best_per_algo[algo] = rec

        if not best_per_algo:
            no_cache_match.append(trace_id)
            continue

        algo_recs = list(best_per_algo.values())
        best_mr_rec = min(algo_recs, key=lambda x: x["mr"])
        best_bmr_rec = min(algo_recs, key=lambda x: x["bmr"])

        row = {
            "file": name,
            "trace": trace_id,
            "dataset": dataset_name(trace_id),
            "cache_size_mib": loh_cache / (1024 * 1024),
            "loh_mr": loh_mr,
            "loh_bmr": loh_bmr,
            "loh_mr_runtime": mr_rec["runtime"],
            "loh_bmr_runtime": bmr_rec["runtime"],
            "baseline_best_mr": best_mr_rec["mr"],
            "baseline_best_mr_algo": best_mr_rec["algo"],
            "baseline_best_bmr": best_bmr_rec["bmr"],
            "baseline_best_bmr_algo": best_bmr_rec["algo"],
            "mr_gain_vs_best": rel_impr(best_mr_rec["mr"], loh_mr),
            "bmr_gain_vs_best": rel_impr(best_bmr_rec["bmr"], loh_bmr),
            "matched_algo_count": len(algo_recs),
        }
        rows.append(row)

        for rec in algo_recs:
            algo = rec["algo"]
            st = algo_stats[algo]
            st["count"] += 1
            if loh_mr < rec["mr"]:
                st["mr_wins"] += 1
            if loh_bmr < rec["bmr"]:
                st["bmr_wins"] += 1
            mi = rel_impr(rec["mr"], loh_mr)
            bi = rel_impr(rec["bmr"], loh_bmr)
            if mi is not None:
                st["mr_impr"].append(mi)
            if bi is not None:
                st["bmr_impr"].append(bi)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "file",
                "trace",
                "dataset",
                "cache_size_mib",
                "loh_mr",
                "loh_bmr",
                "loh_mr_runtime",
                "loh_bmr_runtime",
                "baseline_best_mr",
                "baseline_best_mr_algo",
                "baseline_best_bmr",
                "baseline_best_bmr_algo",
                "mr_gain_vs_best",
                "bmr_gain_vs_best",
                "matched_algo_count",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    loh_mr_vals = [r["loh_mr"] for r in rows]
    loh_bmr_vals = [r["loh_bmr"] for r in rows]
    base_mr_vals = [r["baseline_best_mr"] for r in rows]
    base_bmr_vals = [r["baseline_best_bmr"] for r in rows]
    mr_gains = [r["mr_gain_vs_best"] for r in rows if r["mr_gain_vs_best"] is not None]
    bmr_gains = [r["bmr_gain_vs_best"] for r in rows if r["bmr_gain_vs_best"] is not None]

    algo_table = []
    for algo, st in algo_stats.items():
        c = st["count"]
        algo_table.append(
            {
                "algo": algo,
                "count": c,
                "mr_win_rate": st["mr_wins"] / c if c else None,
                "bmr_win_rate": st["bmr_wins"] / c if c else None,
                "mr_impr": mean(st["mr_impr"]) if st["mr_impr"] else None,
                "bmr_impr": mean(st["bmr_impr"]) if st["bmr_impr"] else None,
            }
        )
    algo_table.sort(key=lambda x: (-x["count"], x["algo"]))

    md_lines = []
    md_lines.append("# 20260422-autocompound-cache0001-ready 结果汇总（截至当前已完成）")
    md_lines.append("")
    md_lines.append(f"**MR 结果目录**: `{mr_dir}`")
    md_lines.append(f"**BMR 结果目录**: `{bmr_dir}`")
    md_lines.append(f"**Baseline 目录**: `{baseline_dir}`")
    md_lines.append(f"**Baseline 匹配规则**: cache size 相对误差 <= {args.cache_tol * 100:.1f}%")
    md_lines.append("")
    md_lines.append("## 1. 覆盖与匹配情况")
    md_lines.append("")
    md_lines.append(f"- MR 文件数: {len(mr_map)}")
    md_lines.append(f"- BMR 文件数: {len(bmr_map)}")
    md_lines.append(f"- MR∩BMR（可合并）: {len(file_names)}")
    md_lines.append(f"- 仅 MR: {len(only_mr)}")
    md_lines.append(f"- 仅 BMR: {len(only_bmr)}")
    md_lines.append(f"- baseline 文件数: {base_file_count}")
    md_lines.append(f"- 成功匹配 baseline（trace+cache）: {len(rows)}")
    md_lines.append(f"- baseline trace 缺失: {len(no_baseline_trace)}")
    md_lines.append(f"- baseline cache 不在容差内: {len(no_cache_match)}")
    md_lines.append("")
    md_lines.append("## 2. 全局指标（LOH vs 最优 baseline）")
    md_lines.append("")
    if rows:
        md_lines.append(
            f"- LOH MR 平均/中位: {mean(loh_mr_vals):.6f} / {median(loh_mr_vals):.6f}"
        )
        md_lines.append(
            f"- 最优 baseline MR 平均/中位: {mean(base_mr_vals):.6f} / {median(base_mr_vals):.6f}"
        )
        md_lines.append(
            f"- LOH BMR 平均/中位: {mean(loh_bmr_vals):.6f} / {median(loh_bmr_vals):.6f}"
        )
        md_lines.append(
            f"- 最优 baseline BMR 平均/中位: {mean(base_bmr_vals):.6f} / {median(base_bmr_vals):.6f}"
        )
        md_lines.append(
            f"- 相对最优 baseline 的 MR 改善均值/中位: {fmt_pct(mean(mr_gains))} / {fmt_pct(median(mr_gains))}"
        )
        md_lines.append(
            f"- 相对最优 baseline 的 BMR 改善均值/中位: {fmt_pct(mean(bmr_gains))} / {fmt_pct(median(bmr_gains))}"
        )
    else:
        md_lines.append("- 无可用匹配结果，无法统计。")

    md_lines.append("")
    md_lines.append("## 3. 数据集分布（已成功匹配）")
    md_lines.append("")
    md_lines.append("| dataset | count |")
    md_lines.append("|---|---:|")
    for ds, c in sorted(Counter([r["dataset"] for r in rows]).items()):
        md_lines.append(f"| {ds} | {c} |")

    md_lines.append("")
    md_lines.append("## 4. 对比算法胜率（按覆盖排序）")
    md_lines.append("")
    md_lines.append("| algo | 覆盖数 | MR胜率 | BMR胜率 | MR平均改善 | BMR平均改善 |")
    md_lines.append("|---|---:|---:|---:|---:|---:|")
    for rec in algo_table[: args.top_algos]:
        md_lines.append(
            "| {algo} | {count} | {mr_win} | {bmr_win} | {mr_impr} | {bmr_impr} |".format(
                algo=rec["algo"],
                count=rec["count"],
                mr_win=fmt_pct(rec["mr_win_rate"]),
                bmr_win=fmt_pct(rec["bmr_win_rate"]),
                mr_impr=fmt_pct(rec["mr_impr"]),
                bmr_impr=fmt_pct(rec["bmr_impr"]),
            )
        )

    md_lines.append("")
    md_lines.append("## 5. 说明")
    md_lines.append("")
    md_lines.append(
        "- LOH 使用 MR 目录中的 `miss ratio` 与 BMR 目录中的 `byte miss ratio`，两者按同名结果文件合并。"
    )
    md_lines.append(
        "- baseline 在同 trace 下按算法分别选择最接近 cache size 且误差不超过阈值的记录。"
    )
    md_lines.append(
        "- `*_details.csv` 提供逐 trace 明细，可用于后续按组/按算法继续细分。"
    )
    if mr_bad or bmr_bad or base_bad_lines:
        md_lines.append("")
        md_lines.append("## 6. 解析告警")
        md_lines.append("")
        md_lines.append(f"- MR 解析失败文件数: {len(mr_bad)}")
        md_lines.append(f"- BMR 解析失败文件数: {len(bmr_bad)}")
        md_lines.append(f"- baseline 无法识别行数: {base_bad_lines}")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Summarize auto-compound LOH results")
    parser.add_argument(
        "--mr-dir",
        default="tmp/20260422-autocompound-cache0001-ready/mr/results",
    )
    parser.add_argument(
        "--bmr-dir",
        default="tmp/20260422-autocompound-cache0001-ready/bmr/results",
    )
    parser.add_argument(
        "--baseline-dir",
        default="/home/丁坤鹏/libCacheSim/result",
    )
    parser.add_argument(
        "--cache-tol",
        type=float,
        default=0.05,
        help="relative cache-size tolerance",
    )
    parser.add_argument(
        "--out-md",
        default="docs/20260423-autocompound-cache0001-summary.md",
    )
    parser.add_argument(
        "--out-csv",
        default="docs/20260423-autocompound-cache0001-summary_details.csv",
    )
    parser.add_argument("--top-algos", type=int, default=20)
    args = parser.parse_args()
    summarize(args)


if __name__ == "__main__":
    main()
