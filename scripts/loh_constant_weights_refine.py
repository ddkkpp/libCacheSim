#!/usr/bin/env python3
"""根据 constant_sweep.csv 的前 N 个最优解，构造一批局部细粒度权重候选。

输入：
    argv[1]: constant_sweep.csv 路径
    argv[2]: TOP_N（选取前多少个解，按 miss_ratio 升序）
    argv[3]: RUN_TS（用于日志命名，shell 侧透传）
    argv[4]: SHORT_TRACE（trace 名缩写，用于日志命名，shell 侧透传）
    argv[5]: OUT_DIR（输出目录，仅用于日志命名，shell 侧创建）

输出（stdout）：
    若干行，每行形如：
        idX,w1,w2,w3,w4,w5,w6
    其中 w1..w6 为浮点数（未归一化，loh_constant_weights.py 内部会归一化）。

策略：
    - 从 constant_sweep.csv 取 miss_ratio 最小的前 N 个解（去重）；
    - 对于每个基础权重向量 w_base，用一组选定的比例因子 alpha 在其方向上生成若干候选：
          w = alpha * w_base
      由于 loh_constant_weights.py 会做归一化，alpha 不影响最终方向；
      但我们可以在 w_base 周围做轻微扰动，让方向发生小变化：
          w = w_base + eps * noise
      这里采用简单的离散扰动：对每个维度加上 {-1,0,1} 的小整数，然后截断为非负。

    - 为了控制数量：
        * 每个 base 解生成 1 个“原始方向” + 若干个稀疏扰动解（例如 6~10 个）。

注意：
    - 这里假设原始 constant_sweep.csv 中 w1..w6 是整数 0/1/2。
"""

from __future__ import annotations

import csv
import math
import os
import random
import sys
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class WeightRecord:
    w: Tuple[int, int, int, int, int, int]
    miss_ratio: float
    byte_miss_ratio: float


def load_top_n(csv_path: str, top_n: int) -> List[WeightRecord]:
    records: List[WeightRecord] = []
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                w = (
                    int(row["w1"]),
                    int(row["w2"]),
                    int(row["w3"]),
                    int(row["w4"]),
                    int(row["w5"]),
                    int(row["w6"]),
                )
                miss = float(row["miss_ratio"])
                byte_miss = float(row["byte_miss_ratio"])
            except Exception:
                continue
            records.append(WeightRecord(w=w, miss_ratio=miss, byte_miss_ratio=byte_miss))

    # 按 miss_ratio 排序，取前 top_n
    records.sort(key=lambda r: r.miss_ratio)

    # 去重：相同 w 只保留一条
    seen = set()
    unique: List[WeightRecord] = []
    for r in records:
        if r.w in seen:
            continue
        seen.add(r.w)
        unique.append(r)
        if len(unique) >= top_n:
            break

    return unique


def generate_perturbations(base_w: Tuple[int, int, int, int, int, int], per_base: int = 8) -> List[Tuple[float, ...]]:
    """围绕 base_w 生成若干浮点扰动候选。

    - 保证非负；
    - 避免全 0；
    - 返回的是未归一化向量，后续由 loh_constant_weights.py 归一化。
    """

    w = list(base_w)
    candidates: List[Tuple[float, ...]] = []

    # 1) 原始方向（整数向量）
    if any(v != 0 for v in w):
        candidates.append(tuple(float(v) for v in w))

    # 2) 简单整数扰动：对每个维度加 {-1,0,1} 中的一个，生成 per_base 个样本
    #    步长较小，保持“局部搜索”性质。
    rng = random.Random(20251119)
    attempts = 0
    while len(candidates) < per_base + 1 and attempts < per_base * 10:
        attempts += 1
        pert = []
        for v in w:
            delta = rng.choice([-1, 0, 1])
            new_v = max(0, v + delta)
            pert.append(float(new_v))
        if all(val == 0.0 for val in pert):
            continue
        tup = tuple(pert)
        if tup in candidates:
            continue
        candidates.append(tup)

    return candidates


def main(argv: List[str]) -> None:
    if len(argv) < 3:
        print("Usage: loh_constant_weights_refine.py constant_sweep.csv TOP_N RUN_TS SHORT_TRACE OUT_DIR", file=sys.stderr)
        sys.exit(1)

    csv_path = argv[1]
    top_n = int(argv[2])

    # RUN_TS / SHORT_TRACE / OUT_DIR 目前只用于命名和调试，这里不直接使用，
    # 但仍然按位置接收，便于以后扩展。
    # run_ts = argv[3]
    # short_trace = argv[4]
    # out_dir = argv[5]

    if not os.path.exists(csv_path):
        print(f"constant_sweep.csv 不存在: {csv_path}", file=sys.stderr)
        sys.exit(1)

    tops = load_top_n(csv_path, top_n)
    if not tops:
        print("constant_sweep.csv 中没有有效记录", file=sys.stderr)
        sys.exit(1)

    # 输出格式：idX,w1,w2,w3,w4,w5,w6
    # id 用于在日志名中区分不同候选。
    wid = 0
    for rec in tops:
        base_w = rec.w
        cands = generate_perturbations(base_w, per_base=8)
        for cand in cands:
            wid += 1
            w_str = ",".join(f"{v:.6f}" for v in cand)
            print(f"id{wid},{w_str}")


if __name__ == "__main__":
    main(sys.argv)
