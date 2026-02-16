#!/usr/bin/env python3
import argparse
import csv
import math
import os
import random
from collections import defaultdict
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn.functional as F


def load_groups(csv_path: str, max_groups: int = 0) -> List[Tuple[np.ndarray, int]]:
    grouped: Dict[int, List[Tuple[int, np.ndarray, int]]] = defaultdict(list)
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        required = {
            "evict_seq",
            "cand_idx",
            "is_teacher",
            "feature0",
            "feature1",
            "feature2",
            "feature3",
            "feature4",
            "feature5",
        }
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing columns: {sorted(missing)}")

        for row in reader:
            seq = int(row["evict_seq"])
            cand_idx = int(row["cand_idx"])
            is_teacher = int(row["is_teacher"])
            feat = np.array(
                [
                    float(row["feature0"]),
                    float(row["feature1"]),
                    float(row["feature2"]),
                    float(row["feature3"]),
                    float(row["feature4"]),
                    float(row["feature5"]),
                ],
                dtype=np.float32,
            )
            grouped[seq].append((cand_idx, feat, is_teacher))

    groups: List[Tuple[np.ndarray, int]] = []
    for seq in sorted(grouped.keys()):
        rows = grouped[seq]
        rows_sorted = sorted(rows, key=lambda x: x[0])
        features = []
        label = -1
        for idx, (_, feat, is_teacher) in enumerate(rows_sorted):
            features.append(feat)
            if is_teacher == 1:
                label = idx
        if label < 0:
            continue
        x = np.stack(features, axis=0)
        if label >= x.shape[0]:
            continue
        groups.append((x, label))

    if max_groups > 0:
        groups = groups[:max_groups]
    return groups


def train_linear_ranker(
    groups: List[Tuple[np.ndarray, int]],
    epochs: int,
    batch_groups: int,
    lr: float,
    weight_decay: float,
    seed: int,
) -> np.ndarray:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    w = torch.nn.Parameter(torch.zeros(6, dtype=torch.float32))
    optimizer = torch.optim.Adam([w], lr=lr, weight_decay=weight_decay)

    n = len(groups)
    order = list(range(n))

    for epoch in range(1, epochs + 1):
        random.shuffle(order)
        total_loss = 0.0
        total = 0
        correct = 0

        for start in range(0, n, batch_groups):
            batch_idx = order[start : start + batch_groups]
            optimizer.zero_grad()
            loss = 0.0
            used = 0

            for gi in batch_idx:
                x_np, y = groups[gi]
                x = torch.from_numpy(x_np)
                logits = x @ w
                target = torch.tensor([y], dtype=torch.long)
                group_loss = F.cross_entropy(logits.unsqueeze(0), target)
                loss = loss + group_loss
                used += 1

                pred = int(torch.argmax(logits).item())
                if pred == y:
                    correct += 1
                total += 1
                total_loss += float(group_loss.item())

            if used > 0:
                loss = loss / used
                loss.backward()
                optimizer.step()

        avg_loss = total_loss / max(total, 1)
        acc = correct / max(total, 1)
        print(f"[epoch {epoch:03d}] groups={total} loss={avg_loss:.6f} top1={acc:.4f}")

    return w.detach().cpu().numpy()


def main() -> None:
    parser = argparse.ArgumentParser(description="Train linear LOH teacher ranker from exported Belady labels")
    parser.add_argument("--csv", required=True, help="Path to teacher CSV exported by LOH_TEACHER_EXPORT_PATH")
    parser.add_argument("--out", required=True, help="Output weights text file (comma-separated 6 values)")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-groups", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-2)
    parser.add_argument("--weight-decay", type=float, default=1e-6)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-groups", type=int, default=0)
    parser.add_argument("--l1-normalize", action="store_true", help="Normalize absolute sum of weights to 1")
    args = parser.parse_args()

    groups = load_groups(args.csv, args.max_groups)
    if not groups:
        raise RuntimeError("No valid groups loaded from CSV")

    print(f"Loaded {len(groups)} groups from {args.csv}")
    weights = train_linear_ranker(
        groups,
        epochs=args.epochs,
        batch_groups=args.batch_groups,
        lr=args.lr,
        weight_decay=args.weight_decay,
        seed=args.seed,
    )

    if args.l1_normalize:
        s = float(np.sum(np.abs(weights)))
        if s > 1e-12:
            weights = weights / s

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="") as f:
        f.write(",".join(f"{x:.12g}" for x in weights.tolist()) + "\n")

    print("Trained weights:", ",".join(f"{x:.6f}" for x in weights.tolist()))
    print(f"Saved: {args.out}")
    print("Use with: export LOH_FIXED_WEIGHTS='w1,w2,w3,w4,w5,w6'")


if __name__ == "__main__":
    main()
