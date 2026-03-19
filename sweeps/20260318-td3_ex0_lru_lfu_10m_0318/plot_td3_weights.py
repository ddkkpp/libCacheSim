#!/usr/bin/env python3
import argparse
import csv
import os
import re
from typing import List, Tuple


def parse_weights_from_log(path: str) -> List[Tuple[int, List[float]]]:
    # 兼容 numpy 打印格式：可能无逗号、可能跨行。
    pattern = re.compile(r"\[Step\s+(\d+)\]\s+Weights:\s+\[([^\]]+)\]", re.S)
    float_pat = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")
    rows: List[Tuple[int, List[float]]] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    for m in pattern.finditer(text):
        step = int(m.group(1))
        vec_txt = m.group(2)
        nums = float_pat.findall(vec_txt)
        if not nums:
            continue
        vals = [float(x) for x in nums]
        rows.append((step, vals))
    return rows


def write_csv(rows: List[Tuple[int, List[float]]], out_csv: str) -> None:
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    max_dim = 0
    for _, v in rows:
        if len(v) > max_dim:
            max_dim = len(v)
    header = ["step"] + [f"w{i}" for i in range(max_dim)]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for step, vec in rows:
            w.writerow([step] + vec + [""] * (max_dim - len(vec)))


def try_plot(rows: List[Tuple[int, List[float]]], out_png: str, title: str) -> bool:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return False

    if not rows:
        return False

    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    max_dim = max(len(v) for _, v in rows)
    xs = [s for s, _ in rows]

    plt.figure(figsize=(11, 6))
    for i in range(max_dim):
        ys = []
        for _, vec in rows:
            ys.append(vec[i] if i < len(vec) else float("nan"))
        plt.plot(xs, ys, linewidth=1.2, label=f"w{i}")

    plt.xlabel("step")
    plt.ylabel("weight value")
    plt.title(title)
    plt.grid(alpha=0.25)
    plt.legend(ncol=4, fontsize=8)
    plt.tight_layout()
    plt.savefig(out_png, dpi=140)
    plt.close()
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract and plot TD3 weight-change curve from log")
    ap.add_argument("--log", required=True)
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--out-png", required=True)
    ap.add_argument("--title", default="TD3 Ex0 weight curve")
    args = ap.parse_args()

    rows = parse_weights_from_log(args.log)
    write_csv(rows, args.out_csv)
    ok = try_plot(rows, args.out_png, args.title)

    print(f"parsed_points={len(rows)}")
    print(f"csv={args.out_csv}")
    if ok:
        print(f"png={args.out_png}")
    else:
        print("png=SKIPPED (matplotlib unavailable or no data)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
