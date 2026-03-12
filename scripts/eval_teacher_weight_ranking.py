#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np


def load_groups(csv_path: Path) -> List[List[dict]]:
    rows = list(csv.DictReader(csv_path.open("r", newline="")))
    groups: List[List[dict]] = []
    cur: List[dict] = []
    cur_seq = None

    for row in rows:
        seq = int(row["evict_seq"])
        if cur_seq is None:
            cur_seq = seq
        if seq != cur_seq:
            if cur:
                groups.append(cur)
            cur = [row]
            cur_seq = seq
        else:
            cur.append(row)

    if cur:
        groups.append(cur)
    return groups


def parse_weights(weights_str: str) -> np.ndarray:
    vals = [float(x.strip()) for x in weights_str.split(",")]
    if len(vals) != 6:
        raise ValueError(f"weights must have 6 values, got {len(vals)}")
    return np.array(vals, dtype=np.float64)


def evaluate(groups: List[List[dict]], w: np.ndarray) -> Dict[str, float]:
    hit1 = hit3 = hit5 = hit10 = 0
    mrr = 0.0
    avg_rank_pct = 0.0

    for g in groups:
        x = np.array(
            [[float(r[f"feature{i}"]) for i in range(6)] for r in g],
            dtype=np.float64,
        )
        belady = np.array([int(r["belady_key"]) for r in g], dtype=np.int64)
        teacher_set = set(np.where(belady == belady.max())[0].tolist())

        logits = x @ w
        order = np.argsort(-logits)

        if int(order[0]) in teacher_set:
            hit1 += 1
        if teacher_set & set(order[: min(3, len(order))].tolist()):
            hit3 += 1
        if teacher_set & set(order[: min(5, len(order))].tolist()):
            hit5 += 1
        if teacher_set & set(order[: min(10, len(order))].tolist()):
            hit10 += 1

        rank = 1
        for idx in order:
            if int(idx) in teacher_set:
                break
            rank += 1

        mrr += 1.0 / rank
        avg_rank_pct += (len(order) - rank) / max(len(order) - 1, 1)

    n = max(len(groups), 1)
    return {
        "hit@1": hit1 / n,
        "hit@3": hit3 / n,
        "hit@5": hit5 / n,
        "hit@10": hit10 / n,
        "mrr": mrr / n,
        "avg_rank_pct": avg_rank_pct / n,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluate fixed weights against teacher labels (Belady key) on teacher_samples.csv")
    ap.add_argument("--csv", required=True, help="Path to teacher_samples.csv")
    ap.add_argument(
        "--weight",
        action="append",
        default=[],
        help="One weight spec in form name=w1,w2,w3,w4,w5,w6. Can be repeated.",
    )
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    if not args.weight:
        raise ValueError("Please provide at least one --weight name=w1,...,w6")

    weights: List[Tuple[str, np.ndarray]] = []
    for item in args.weight:
        if "=" not in item:
            raise ValueError(f"invalid weight spec: {item}")
        name, ws = item.split("=", 1)
        weights.append((name.strip(), parse_weights(ws.strip())))

    groups = load_groups(csv_path)
    cand_sizes = np.array([len(g) for g in groups], dtype=np.float64)
    tie_sizes = np.array([
        int(
            np.sum(
                np.array([int(r["belady_key"]) for r in g], dtype=np.int64)
                == np.max(np.array([int(r["belady_key"]) for r in g], dtype=np.int64))
            )
        )
        for g in groups
    ])

    print(f"groups={len(groups)} avg_cand={cand_sizes.mean():.2f} median_cand={np.median(cand_sizes):.1f} avg_tie={tie_sizes.mean():.2f}")
    for name, w in weights:
        m = evaluate(groups, w)
        print(
            f"{name}: "
            f"Hit@1={m['hit@1']:.4f} Hit@3={m['hit@3']:.4f} Hit@5={m['hit@5']:.4f} Hit@10={m['hit@10']:.4f} "
            f"MRR={m['mrr']:.4f} AvgRankPct={m['avg_rank_pct']:.4f}"
        )


if __name__ == "__main__":
    main()
