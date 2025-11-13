#!/usr/bin/env python3
"""
基线算法基准工具：对给定 trace 运行 cachesim 多种算法并汇总 miss ratio。

使用方式（示例）：
  python3 scripts/bench_baselines.py \
    --trace /path/to/lfu.csv \
    --sizes 50mb 100mb 200mb \
    --algos LRU,LFU,WTinyLFU,ARC,Sieve,S3FIFO,3Lcache \
    --num-req 1000000

要求：已构建 _build_dbg/bin/cachesim，可直接从仓库根运行。
trace 类型为 csv，参数固定为 time-col=1,obj-id-col=2,obj-size-col=3。
"""

import argparse
import os
import re
import subprocess
from typing import Dict, List, Tuple


def run_cachesim(trace: str, size: str, algo: str, num_req: int = -1) -> Tuple[bool, str, str]:
    trace_type = "csv"
    trace_params = "time-col=1,obj-id-col=2,obj-size-col=3,obj-id-is-num=1,has-header=false,delimiter=,"
    cmd = [
        "_build_dbg/bin/cachesim",
        trace,
        trace_type,
        algo,
        size,
        f"--trace-type-params={trace_params}",
        "-v", "1",
    ]
    # WTinyLFU 默认主缓存为 SLRU，会在某些 trace 上触发断言；这里强制改为 LRU 以稳定评测
    if algo.lower() == "wtinylfu":
        cmd.append("-e")
        cmd.append("main-cache=LRU,window-size=0.01")
    if num_req and num_req > 0:
        cmd.append(f"--num-req={num_req}")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return (res.returncode == 0, res.stdout, " ")


def parse_miss_ratio(output: str) -> Tuple[float, float]:
    # 在输出中搜索 miss ratio 与 byte miss ratio
    mr = None
    bmr = None
    for line in output.splitlines():
        if "miss ratio" in line and "byte miss ratio" in line:
            m = re.search(r"miss ratio\s+([0-9.]+), byte miss ratio\s+([0-9.]+)", line)
            if m:
                mr = float(m.group(1))
                bmr = float(m.group(2))
                break
    return mr if mr is not None else float("nan"), bmr if bmr is not None else float("nan")


def bench(trace: str, sizes: List[str], algos: List[str], num_req: int) -> Dict[str, Dict[str, Tuple[float, float]]]:
    table: Dict[str, Dict[str, Tuple[float, float]]] = {}
    for algo in algos:
        table[algo] = {}
        for size in sizes:
            ok, out, _ = run_cachesim(trace, size, algo, num_req)
            mr, bmr = parse_miss_ratio(out)
            table[algo][size] = (mr, bmr)
            print(f"{algo:10s} size={size:8s} miss={mr:.4f} byte_miss={bmr:.4f}")
    return table


def main():
    p = argparse.ArgumentParser(description="Benchmark baseline algorithms on a CSV trace")
    p.add_argument("--trace", required=True)
    p.add_argument("--sizes", default=["0.1,0.001"])  # 兼容 cachesim 的 size 解析
    p.add_argument("--algos", default="LRU,LFU,ARC,LHD,GDSF,WTinyLFU,ARC,Sieve,S3FIFO,Cacheus,3Lcache")
    p.add_argument("--num-req", type=int, default=-1)
    args = p.parse_args()

    algos = [a.strip() for a in args.algos.split(",") if a.strip()]
    bench(args.trace, args.sizes, algos, args.num_req)


if __name__ == "__main__":
    main()
