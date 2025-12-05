#!/usr/bin/env python3
"""解析 runs/constant_weight_refine 下的 refine 日志，找出最佳权重。

日志命名：
    runs/constant_weight_refine/loh_const_refine_<ts>_<trace>_idX.log
日志内容中包含：
    "miss ratio X, byte miss ratio Y"

输出：
    CSV 到 stdout: id,w1,w2,w3,w4,w5,w6,miss_ratio,byte_miss_ratio

用法：
    cd /home/dingkp/libCacheSim
    python3 scripts/analyze_loh_constant_refine.py > constant_refine.csv
"""

from __future__ import annotations

import csv
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFINE_DIR = ROOT / "runs" / "constant_weight_refine"
LINE_RE = re.compile(r"miss ratio ([0-9]*\.[0-9]+), byte miss ratio ([0-9]*\.[0-9]+)")


def parse_header_weights(log_path: Path):
    """从 log 头部找到 Fixed weights 行（loh_constant_weights.py 的启动打印）.

    例如：
        [loh_constant_weights] 启动常数策略，权重 = [0.3, 0.2, ...]
    若找不到，返回 None。
    """
    try:
        with log_path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "[loh_constant_weights]" in line and "权重" in line:
                    # 简单提取中括号中的数字
                    start = line.find("[")
                    end = line.find("]", start + 1)
                    if start >= 0 and end > start:
                        inside = line[start + 1 : end]
                        try:
                            vals = [float(x.strip()) for x in inside.split(",") if x.strip()]
                            if len(vals) == 6:
                                return vals
                        except Exception:
                            pass
                # 头部扫描一定行数即可
                if f.tell() > 4096:
                    break
    except Exception:
        return None
    return None


def main() -> None:
    if not REFINE_DIR.exists():
        print(f"refine 目录不存在: {REFINE_DIR}", file=sys.stderr)
        sys.exit(1)

    logs = sorted(REFINE_DIR.glob("loh_const_refine_*.log"))
    if not logs:
        print("未在 runs/constant_weight_refine 下找到 loh_const_refine_*.log", file=sys.stderr)
        sys.exit(1)

    rows = []
    for log_path in logs:
        miss = None
        byte = None
        try:
            with log_path.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    m = LINE_RE.search(line)
                    if m:
                        miss = float(m.group(1))
                        byte = float(m.group(2))
        except Exception as e:
            print(f"读取 {log_path} 失败: {e}", file=sys.stderr)
            continue

        if miss is None:
            continue

        # 从文件名提取 idX
        base = log_path.stem  # loh_const_refine_..._idX
        parts = base.split("_")
        wid = parts[-1] if parts else base

        # 尝试解析 header 中的实际浮点权重（归一化后）
        weights = parse_header_weights(log_path) or [float("nan")] * 6

        rows.append({
            "id": wid,
            "w1": weights[0],
            "w2": weights[1],
            "w3": weights[2],
            "w4": weights[3],
            "w5": weights[4],
            "w6": weights[5],
            "miss_ratio": miss,
            "byte_miss_ratio": byte,
        })

    if not rows:
        print("未能从 refine 日志中解析到 miss_ratio", file=sys.stderr)
        sys.exit(1)

    # 输出 CSV
    writer = csv.DictWriter(sys.stdout, fieldnames=[
        "id", "w1", "w2", "w3", "w4", "w5", "w6", "miss_ratio", "byte_miss_ratio",
    ])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)


if __name__ == "__main__":
    main()
