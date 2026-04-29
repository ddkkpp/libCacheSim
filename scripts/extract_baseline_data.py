#!/usr/bin/env python3
"""
从 8 个 per-group 文档的表4(Baseline MR) 和表5(Baseline BMR) 提取全部 per-trace 数据，
连同表1的 n_req，输出为统一的 CSV 数据文件。

同时计算 4 个维度: 原始值、加权值(n_req)、相对LRU值、加权相对LRU值。
还输出 per-group 的分位数统计（p10/p25/median/mean/p75/p90）。
"""

import re, os, sys, csv, json
from pathlib import Path
from collections import defaultdict
import numpy as np

DOC_DIR = Path("docs/20260415-ablation-per-group")

GROUPS = ["alibabaBlock", "cloudphysics", "metaCDN", "metaKV",
          "tencentBlock", "tencentPhoto", "twitter", "wiki"]

# v3 列名 -> 显示名（用户指定顺序）
ALGO_MAP = {
    "LRU": "LRU", "LHD": "LHD", "ARC": "ARC", "Sieve": "SIEVE",
    "S3FIFO-0.1000-2": "S3-FIFO", "WTinyLFU-w0.01-SLRU": "WTinyLFU",
    "LeCaR": "LeCaR", "Cacheus": "CACHEUS", "GLCache": "GL-Cache",
    "LRB-BMR": "LRB", "ThreeLCache-BMR": "3L-Cache", "best_LOH": "RSD",
}
# 用户指定顺序
ALGO_ORDER = ["LRU", "LHD", "ARC", "SIEVE", "S3-FIFO", "WTinyLFU",
              "LeCaR", "CACHEUS", "GL-Cache", "LRB", "3L-Cache", "RSD"]

# 原始列名 (在文档表格中)
RAW_ALGOS = ["ARC", "Cacheus", "GDSF", "GLCache", "LHD", "LRU", "LeCaR",
             "S3FIFO-0.1000-2", "Sieve", "WTinyLFU-w0.01-SLRU", "LRB-BMR",
             "ThreeLCache-BMR", "best_LOH"]

# 去除 GDSF 后的列名
KEPT_ALGOS = [a for a in RAW_ALGOS if a != "GDSF"]


def parse_n_req(doc_lines):
    """从表1提取每条 trace 的 n_req。返回 {trace_name: int}"""
    n_req = {}
    in_table1 = False
    for line in doc_lines:
        if "## 表1" in line:
            in_table1 = True
            continue
        if in_table1 and line.startswith("## "):
            break
        if not in_table1:
            continue
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        parts = [p for p in parts if p]
        if len(parts) < 3:
            continue
        trace = parts[0]
        if trace in ("trace", "---") or trace.startswith("---"):
            continue
        if trace.startswith("**"):
            continue
        raw_nreq = parts[1].replace(",", "").replace(" ", "")
        try:
            n_req[trace] = int(raw_nreq)
        except ValueError:
            continue
    return n_req


def parse_baseline_table(doc_lines, table_marker):
    """
    解析 Baseline MR/BMR 表，返回 per-trace 数据。
    table_marker 如 "Baseline MR" 或 "Baseline BMR"
    返回 [{trace, algo1_val, algo2_val, ...}, ...]
    只保留 KEPT_ALGOS 列。
    """
    in_table = False
    header_cols = None
    rows = []
    for line in doc_lines:
        if table_marker in line and line.strip().startswith("##"):
            in_table = True
            continue
        if in_table and line.strip().startswith("##") and table_marker not in line:
            break
        if not in_table:
            continue
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        parts = [p for p in parts if p]
        if len(parts) < 3:
            continue
        if parts[0] == "trace":
            header_cols = parts
            continue
        if parts[0].startswith("---"):
            continue
        # 跳过汇总行
        if parts[0].startswith("**"):
            continue
        if header_cols is None:
            continue
        trace = parts[0]
        row = {"trace": trace}
        for i, col_name in enumerate(header_cols):
            if i == 0:
                continue
            if i < len(parts):
                raw = parts[i].replace("**", "").strip()
                try:
                    row[col_name] = float(raw)
                except ValueError:
                    row[col_name] = None
        rows.append(row)
    return rows


def main():
    out_dir = DOC_DIR / "data"
    out_dir.mkdir(exist_ok=True)

    # 存储所有数据
    all_data = []  # list of dicts

    for group in GROUPS:
        md_path = DOC_DIR / f"{group}.md"
        if not md_path.exists():
            print(f"WARNING: {md_path} not found, skip")
            continue
        doc_lines = md_path.read_text().splitlines()

        # 1. 解析 n_req
        n_req_map = parse_n_req(doc_lines)

        # 2. 解析 Baseline MR 和 BMR
        mr_rows = parse_baseline_table(doc_lines, "Baseline MR")
        bmr_rows = parse_baseline_table(doc_lines, "Baseline BMR")

        # 构建 bmr lookup
        bmr_lookup = {}
        for row in bmr_rows:
            bmr_lookup[row["trace"]] = row

        # 3. 合并
        for mr_row in mr_rows:
            trace = mr_row["trace"]
            nreq = n_req_map.get(trace, None)
            bmr_row = bmr_lookup.get(trace, {})

            for raw_algo in KEPT_ALGOS:
                display = ALGO_MAP[raw_algo]
                mr_val = mr_row.get(raw_algo)
                bmr_val = bmr_row.get(raw_algo)
                lru_mr = mr_row.get("LRU")
                lru_bmr = bmr_row.get("LRU")

                record = {
                    "group": group,
                    "trace": trace,
                    "n_req": nreq,
                    "algo_raw": raw_algo,
                    "algo": display,
                    "MR": mr_val,
                    "BMR": bmr_val,
                }
                # 相对 LRU
                if mr_val is not None and lru_mr is not None and lru_mr > 0:
                    record["MR_rel_LRU"] = mr_val / lru_mr
                else:
                    record["MR_rel_LRU"] = None
                if bmr_val is not None and lru_bmr is not None and lru_bmr > 0:
                    record["BMR_rel_LRU"] = bmr_val / lru_bmr
                else:
                    record["BMR_rel_LRU"] = None

                all_data.append(record)

        print(f"  {group}: {len(mr_rows)} traces, {len(n_req_map)} n_req entries")

    # 4. 写 CSV
    csv_path = out_dir / "all_traces_baseline.csv"
    fields = ["group", "trace", "n_req", "algo_raw", "algo", "MR", "BMR", "MR_rel_LRU", "BMR_rel_LRU"]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for rec in all_data:
            w.writerow(rec)
    print(f"\n写入 {csv_path}: {len(all_data)} 行")

    # 5. 计算 per-group 分位数统计
    # 维度: MR, BMR, MR_rel_LRU, BMR_rel_LRU
    #   + 加权版：MR_wavg, BMR_wavg, MR_rel_LRU_wavg, BMR_rel_LRU_wavg
    # 分位数: p10, p25, median, mean, p75, p90

    metrics = ["MR", "BMR", "MR_rel_LRU", "BMR_rel_LRU"]
    quantiles = [0.10, 0.25, 0.50, 0.75, 0.90]
    q_names = ["p10", "p25", "median", "p75", "p90"]

    # 按 (group, algo) 分组
    grouped = defaultdict(lambda: defaultdict(list))  # (group, algo) -> metric -> [values]
    grouped_nreq = defaultdict(lambda: defaultdict(list))  # (group, algo) -> metric -> [(val, nreq)]

    for rec in all_data:
        key = (rec["group"], rec["algo"])
        for m in metrics:
            if rec[m] is not None:
                grouped[key][m].append(rec[m])
                if rec["n_req"] is not None:
                    grouped_nreq[key][m].append((rec[m], rec["n_req"]))

    # 输出 per-group 分位数表
    stat_rows = []
    for group in GROUPS:
        for algo in ALGO_ORDER:
            key = (group, algo)
            for m in metrics:
                vals = grouped[key].get(m, [])
                if not vals:
                    continue
                arr = np.array(vals)
                row = {
                    "group": group,
                    "algo": algo,
                    "metric": m,
                    "n": len(arr),
                    "mean": float(np.mean(arr)),
                }
                for q, qn in zip(quantiles, q_names):
                    row[qn] = float(np.quantile(arr, q))
                stat_rows.append(row)

    stat_csv = out_dir / "per_group_quantiles.csv"
    stat_fields = ["group", "algo", "metric", "n", "mean"] + q_names
    with open(stat_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=stat_fields)
        w.writeheader()
        for row in stat_rows:
            w.writerow(row)
    print(f"写入 {stat_csv}: {len(stat_rows)} 行")

    # 6. 计算全部 trace 合并的分位数统计（所有 trace 放在一起，不按 group 分组）
    all_grouped = defaultdict(lambda: defaultdict(list))  # algo -> metric -> [values]
    for rec in all_data:
        algo = rec["algo"]
        for m in metrics:
            if rec[m] is not None:
                all_grouped[algo][m].append(rec[m])

    global_stat_rows = []
    for algo in ALGO_ORDER:
        for m in metrics:
            vals = all_grouped[algo].get(m, [])
            if not vals:
                continue
            arr = np.array(vals)
            row = {
                "algo": algo,
                "metric": m,
                "n": len(arr),
                "mean": float(np.mean(arr)),
            }
            for q, qn in zip(quantiles, q_names):
                row[qn] = float(np.quantile(arr, q))
            global_stat_rows.append(row)

    global_csv = out_dir / "global_quantiles.csv"
    global_fields = ["algo", "metric", "n", "mean"] + q_names
    with open(global_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=global_fields)
        w.writeheader()
        for row in global_stat_rows:
            w.writerow(row)
    print(f"写入 {global_csv}: {len(global_stat_rows)} 行")

    # 7. 加权分位数（全 trace 合并）
    # 对于加权版，先计算加权平均
    # 同时对 per-trace 数据加上 n_req 列写到 CSV，后续画图脚本可自行计算
    # 这里直接输出加权统计的 per-group summary

    weighted_rows = []
    for group in GROUPS:
        for algo in ALGO_ORDER:
            key = (group, algo)
            for m in metrics:
                pairs = grouped_nreq[key].get(m, [])
                if not pairs:
                    continue
                vals = np.array([p[0] for p in pairs])
                weights = np.array([p[1] for p in pairs], dtype=float)
                if weights.sum() == 0:
                    continue
                w_norm = weights / weights.sum()
                w_mean = float(np.sum(vals * w_norm))
                w_std = float(np.sqrt(np.sum(w_norm * (vals - w_mean) ** 2)))
                weighted_rows.append({
                    "group": group,
                    "algo": algo,
                    "metric": m,
                    "n": len(vals),
                    "w_mean": w_mean,
                    "w_std": w_std,
                })

    w_csv = out_dir / "per_group_weighted.csv"
    w_fields = ["group", "algo", "metric", "n", "w_mean", "w_std"]
    with open(w_csv, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=w_fields)
        wr.writeheader()
        for row in weighted_rows:
            wr.writerow(row)
    print(f"写入 {w_csv}: {len(weighted_rows)} 行")

    print("\n全部数据提取完成！")


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent.parent)
    main()
