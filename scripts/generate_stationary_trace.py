#!/usr/bin/env python3
"""
生成可控“平稳”访问轨迹（CSV），用于验证基线算法：

- 模式 lfu：固定 Zipf(popularity α) + i.i.d. 采样，频率主导 → LFU/WTinyLFU 应占优
- 模式 lru：固定会话/突发过程，强时间局部性（短重用距离）→ LRU/2Q/ARC 更占优
- 模式 hybrid：按固定权重混合两种过程，参数不随时间变化，整体平稳

输出格式（无表头）：
  time,obj_id,size,next_access
其中 next_access 固定写 -1 以兼容现有 CSV 读取器。

注意：
- 采用流式写入，支持千万级请求（--num-requests）而不占用过多内存。
- 尺寸分布默认 Pareto（可选 lognormal），参数固定保证平稳。
- 与 cachesim 对接时，trace_type 使用 "csv"，并传入 trace-type-params：
    --trace-type-params "time-col=1,obj-id-col=2,obj-size-col=3,has-header=false,delimiter=,"
"""

import argparse
import math
import os
import random
import sys
from typing import Iterator, Tuple

try:
    import numpy as np
except Exception:
    np = None  # 尽量避免强依赖；仅用于采样 Zipf 快速路径


def iter_sizes(dist: str, mean: int, pareto_alpha: float = 1.2, logn_sigma: float = 1.0) -> Iterator[int]:
    """生成对象大小（字节）。保持参数常量以保证平稳。

    - pareto: X = xm * U^{-1/alpha}，这里选 xm 使均值约等于 mean
    - lognormal: 调整 mu 使均值约 mean
    """
    if dist == "pareto":
        alpha = pareto_alpha
        # Pareto 的均值 = alpha * xm / (alpha - 1)  => xm = mean * (alpha-1)/alpha
        xm = max(1.0, mean * (alpha - 1.0) / alpha)

        while True:
            u = random.random()
            x = xm / (u ** (1.0 / alpha))
            yield int(max(1, round(x)))
    elif dist == "lognormal":
        sigma = max(1e-6, float(logn_sigma))
        # 对数正态均值 E[X] = exp(mu + sigma^2/2) => mu = ln(mean) - sigma^2/2
        mu = math.log(max(1.0, float(mean))) - (sigma * sigma) / 2.0
        while True:
            z = random.gauss(0.0, 1.0)
            x = math.exp(mu + sigma * z)
            yield int(max(1, round(x)))
    else:
        # 常数大小（调试）
        while True:
            yield int(mean)


def zipf_sampler(n_obj: int, alpha: float) -> Iterator[int]:
    """Zipf 受欢迎度的对象采样器（返回 [0, n_obj) 的对象 id）。"""
    if np is not None:
        # 预先构造概率并累计（避免每步排序），n 对象可达百万级仍可用
        ranks = np.arange(1, n_obj + 1, dtype=np.float64)
        probs = 1.0 / np.power(ranks, alpha)
        probs /= probs.sum()
        cdf = np.cumsum(probs)
        rng = np.random.default_rng()
        while True:
            u = rng.random()
            idx = int(np.searchsorted(cdf, u, side="left"))
            yield idx
    else:
        # 退化实现：按 rank 权重轮盘赌（O(n_obj)），适合小规模
        weights = [1.0 / ((i + 1) ** alpha) for i in range(n_obj)]
        s = sum(weights)
        weights = [w / s for w in weights]
        acc = []
        run = 0.0
        for w in weights:
            run += w
            acc.append(run)
        while True:
            u = random.random()
            lo, hi = 0, n_obj - 1
            while lo < hi:
                mid = (lo + hi) // 2
                if u <= acc[mid]:
                    hi = mid
                else:
                    lo = mid + 1
            yield lo


def lru_bursty_sampler(n_obj: int, p_new: float, session_len_mean: int) -> Iterator[int]:
    """基于会话/突发的 LRU 友好采样器。

    过程：
      - 以概率 p_new 开启新对象的会话（选择随机对象），否则继续当前会话对象
      - 当前会话长度为几何分布，期望 session_len_mean（短重用距离）
    """
    current_obj = None
    remaining = 0
    while True:
        if current_obj is None or remaining <= 0 or random.random() < p_new:
            current_obj = random.randrange(n_obj)
            # 几何分布：E[L] ≈ session_len_mean
            p = 1.0 / max(1, session_len_mean)
            # 生成 L >= 1
            u = random.random()
            remaining = max(1, int(math.ceil(math.log(1 - u) / math.log(1 - p))))
        remaining -= 1
        yield current_obj


def generate_trace(
    filename: str,
    num_requests: int,
    mode: str,
    n_objects: int,
    size_mean: int,
    size_dist: str = "pareto",
    zipf_alpha: float = 1.1,
    p_new: float = 0.05,
    session_len_mean: int = 20,
) -> None:
    """按给定模式生成轨迹并写入 CSV（无表头）。"""
    mode = mode.lower()
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

    size_iter = iter_sizes(size_dist, mean=size_mean)

    if mode == "lfu":
        obj_iter = zipf_sampler(n_objects, zipf_alpha)
    elif mode == "lru":
        obj_iter = lru_bursty_sampler(n_objects, p_new=p_new, session_len_mean=session_len_mean)
    elif mode == "hybrid":
        zipf_iter = zipf_sampler(n_objects, zipf_alpha)
        burst_iter = lru_bursty_sampler(n_objects, p_new=p_new, session_len_mean=session_len_mean)
        def _hybrid():
            while True:
                if random.random() < 0.5:
                    yield next(zipf_iter)
                else:
                    yield next(burst_iter)
        obj_iter = _hybrid()
    else:
        raise ValueError(f"unknown mode: {mode}")

    with open(filename, "w") as f:
        t = 0
        for _ in range(num_requests):
            obj_id = next(obj_iter)
            size = next(size_iter)
            # 统一使用 1-based 显示/避免与 0 冲突，可加偏移 1000
            f.write(f"{t},{obj_id + 1000},{size},-1\n")
            t += 1


def main():
    p = argparse.ArgumentParser(description="Generate stationary synthetic traces (CSV)")
    p.add_argument("--output", "-o", required=True, help="output CSV path")
    p.add_argument("--mode", choices=["lfu", "lru", "hybrid"], required=True)
    p.add_argument("--num-requests", type=int, default=1_000_000)
    p.add_argument("--n-objects", type=int, default=100_000)
    p.add_argument("--size-mean", type=int, default=64 * 1024)
    p.add_argument("--size-dist", choices=["pareto", "lognormal", "const"], default="pareto")
    p.add_argument("--zipf-alpha", type=float, default=1.1)
    p.add_argument("--p-new", type=float, default=0.05, help="probability to start a new session (lru mode)")
    p.add_argument("--session-len-mean", type=int, default=20)
    args = p.parse_args()

    generate_trace(
        filename=args.output,
        num_requests=args.num_requests,
        mode=args.mode,
        n_objects=args.n_objects,
        size_mean=args.size_mean,
        size_dist=args.size_dist,
        zipf_alpha=args.zipf_alpha,
        p_new=args.p_new,
        session_len_mean=args.session_len_mean,
    )
    print(f"Generated trace: {args.output}")
    print("Use with cachesim: trace_type=csv and --trace-type-params 'time-col=1,obj-id-col=2,obj-size-col=3,has-header=false,delimiter=,'")


if __name__ == "__main__":
    main()
