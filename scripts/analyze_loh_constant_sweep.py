#!/usr/bin/env python3
"""解析 `sweep_loh_constant_weights.sh` 生成的日志，汇总固定权重的 miss ratio。

自动识别两类日志位置 / 命名：

1) 旧版：
     - 目录: runs/
     - 文件名: loh_const_meta_w1_w2_w3_w4_w5_w6.log

2) 新版（推荐）：
     - 目录: runs/constant_weight/
     - 文件名: loh_const_<trace_basename>_ratio<CACHE_RATIO>_n<NUM_REQ>_w1_w2_w3_w4_w5_w6.log

日志内容中应包含 cachesim 的一行：
        "miss ratio X, byte miss ratio Y"

输出：
    - 标准输出打印 CSV：w1,...,w6,miss_ratio,byte_miss_ratio

用法：
    cd /home/dingkp/libCacheSim
    python3 scripts/analyze_loh_constant_sweep.py > constant_sweep.csv
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs"
NEW_DIR = RUNS_DIR / "constant_weight"

LINE_RE = re.compile(r"miss ratio ([0-9]*\.[0-9]+), byte miss ratio ([0-9]*\.[0-9]+)")



def parse_weights_from_name(name: str):
    """从文件名解析 6 个整数权重。

    兼容两种命名：
      - loh_const_meta_w1_w2_w3_w4_w5_w6.log
      - loh_const_<trace>_ratioX_nY_w1_w2_w3_w4_w5_w6.log
    """
    base = name
    if base.endswith(".log"):
        base = base[:-4]
    parts = base.split("_")
    # 最后 6 个是权重整数
    if len(parts) < 7:
        return None
    try:
        ws = [int(x) for x in parts[-6:]]
        return ws
    except Exception:
        return None


def main() -> None:
    if not RUNS_DIR.exists():
        print(f"runs 目录不存在: {RUNS_DIR}", file=sys.stderr)
        sys.exit(1)

    # 优先使用 runs/constant_weight 下的新日志；若为空，则退回旧的 runs 根目录。
    paths = []
    if NEW_DIR.exists():
        paths.extend(sorted(NEW_DIR.glob("loh_const_*.log")))
    if not paths:
        paths.extend(sorted(RUNS_DIR.glob("loh_const_meta_*.log")))

    if not paths:
        print("未在 runs/constant_weight 或 runs/ 下找到 loh_const_* 日志", file=sys.stderr)
        sys.exit(1)

    print("w1,w2,w3,w4,w5,w6,miss_ratio,byte_miss_ratio")
    for log_path in paths:
        ws = parse_weights_from_name(log_path.name)
        if ws is None:
            continue
        miss = None
        byte_miss = None
        try:
            with log_path.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    m = LINE_RE.search(line)
                    if m:
                        miss = m.group(1)
                        byte_miss = m.group(2)
        except Exception as e:
            print(f"读取 {log_path} 失败: {e}", file=sys.stderr)
            continue

        if miss is None:
            continue

        print(",".join([
            *(str(x) for x in ws),
            miss,
            byte_miss,
        ]))


if __name__ == "__main__":
    main()
