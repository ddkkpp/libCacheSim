#!/usr/bin/env python3
"""
滑动窗口平稳性诊断：对 CSV 轨迹计算以下指标并输出摘要：

- 每窗请求数（rate）
- Top-K 热点占比（按对象访问次数）与相邻窗口 Jaccard@K
- Rank-Frequency 拟合 Zipf 斜率 alpha（log-log 线性回归）
- 对象大小分布的分位数（p50/p90/p99）稳定性

输入 CSV（无表头）：time,obj_id,size,next_access
与本仓库生成器输出保持一致；也可通过 --params 明确列索引。
"""

import argparse
import csv
import math
import os
from collections import Counter, deque
from typing import List, Tuple

import numpy as np


def fit_zipf_alpha(freqs: np.ndarray) -> float:
    # freqs: 排序后的频率（降序）
    ranks = np.arange(1, len(freqs) + 1, dtype=np.float64)
    y = np.log(freqs + 1e-9)
    x = -np.log(ranks)
    A = np.vstack([x, np.ones_like(x)]).T
    alpha, _b = np.linalg.lstsq(A, y, rcond=None)[0]
    return float(alpha)


def jaccard(a: List[int], b: List[int]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / max(1, len(sa | sb))


def window_iter(path: str, window: int, step: int, cols=(0, 1, 2)):
    t_idx, id_idx, size_idx = cols
    with open(path, "r") as f:
        rdr = csv.reader(f)
        buf = deque(maxlen=window)
        for row in rdr:
            try:
                t = int(row[t_idx])
                oid = int(row[id_idx])
                size = int(row[size_idx])
            except Exception:
                continue
            buf.append((t, oid, size))
            if len(buf) == window:
                yield list(buf)
                # 滑动 step 条
                for _ in range(step):
                    if buf:
                        buf.popleft()


def analyze(path: str, window: int, step: int, topk: int, cols: Tuple[int, int, int]):
    prev_topk = None
    out = []
    for win in window_iter(path, window, step, cols):
        oids = [x[1] for x in win]
        sizes = np.array([x[2] for x in win], dtype=np.int64)
        cnt = Counter(oids)
        freqs = np.array(sorted(cnt.values(), reverse=True), dtype=np.float64)
        alpha = fit_zipf_alpha(freqs[: max(10, min(1000, len(freqs)))]) if len(freqs) > 10 else float("nan")
        top = [oid for oid, _ in cnt.most_common(topk)]
        top_share = sum(cnt[oid] for oid in top) / max(1, len(win))
        jac = jaccard(prev_topk, top) if prev_topk is not None else 1.0
        prev_topk = top
        out.append(
            dict(
                n=len(win),
                topk_share=top_share,
                jaccard_topk=jac,
                zipf_alpha=alpha,
                size_p50=float(np.percentile(sizes, 50)),
                size_p90=float(np.percentile(sizes, 90)),
                size_p99=float(np.percentile(sizes, 99)),
            )
        )
    return out


def summarize(stats: List[dict]):
    import numpy as _np

    def agg(key):
        arr = _np.array([d[key] for d in stats if not math.isnan(d[key])], dtype=float)
        if arr.size == 0:
            return dict(mean=float("nan"), std=float("nan"))
        return dict(mean=float(arr.mean()), std=float(arr.std(ddof=1)) if arr.size > 1 else 0.0)

    keys = ["topk_share", "jaccard_topk", "zipf_alpha", "size_p50", "size_p90", "size_p99"]
    return {k: agg(k) for k in keys}


def main():
    p = argparse.ArgumentParser(description="Stationarity diagnostics on CSV trace")
    p.add_argument("--trace", required=True)
    p.add_argument("--window", type=int, default=100_000)
    p.add_argument("--step", type=int, default=100_000)
    p.add_argument("--topk", type=int, default=100)
    p.add_argument("--cols", default="1,2,3", help="time,obj_id,size column indices (1-based)")
    args = p.parse_args()

    cols = tuple(int(x) - 1 for x in args.cols.split(","))
    stats = analyze(args.trace, args.window, args.step, args.topk, cols)
    summary = summarize(stats)

    print("Windows analyzed:", len(stats))
    for k, v in summary.items():
        print(f"{k}: mean={v['mean']:.4g}, std={v['std']:.4g}")


if __name__ == "__main__":
    main()
