#!/usr/bin/env python3
import argparse
import csv
import os
import random
from typing import List, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def _finalize_group(rows: List[Tuple[int, np.ndarray, int, str]]) -> Tuple[np.ndarray, np.ndarray] | None:
    if not rows:
        return None
    rows_sorted = sorted(rows, key=lambda x: x[0])
    features = []
    keys = []
    fallback_label = -1
    for idx, (_, feat, is_teacher, bk_str) in enumerate(rows_sorted):
        features.append(feat)
        if bk_str:
            keys.append(np.int64(bk_str))
        if is_teacher == 1:
            fallback_label = idx

    if not features:
        return None
    x = np.stack(features, axis=0)

    if len(keys) == len(rows_sorted):
        keys_np = np.array(keys, dtype=np.int64)
        m = np.max(keys_np)
        mask = keys_np == m
        probs = mask.astype(np.float32) / mask.sum()
        return x, probs

    if fallback_label < 0 or fallback_label >= x.shape[0]:
        return None
    probs = np.zeros(x.shape[0], dtype=np.float32)
    probs[fallback_label] = 1.0
    return x, probs


def load_groups(csv_path: str, max_groups: int = 0) -> List[Tuple[np.ndarray, np.ndarray]]:
    groups: List[Tuple[np.ndarray, np.ndarray]] = []
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

        cur_seq = None
        cur_rows: List[Tuple[int, np.ndarray, int, str]] = []
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
            if cur_seq is None:
                cur_seq = seq
            if seq != cur_seq:
                item = _finalize_group(cur_rows)
                if item is not None:
                    groups.append(item)
                    if max_groups > 0 and len(groups) >= max_groups:
                        return groups
                cur_rows = []
                cur_seq = seq
            bk_str = row.get("belady_key", "")
            cur_rows.append((cand_idx, feat, is_teacher, bk_str))

        if cur_rows:
            item = _finalize_group(cur_rows)
            if item is not None:
                groups.append(item)

    if max_groups > 0 and len(groups) > max_groups:
        groups = groups[:max_groups]
    return groups


class MLPScorer(nn.Module):
    def __init__(self, hidden: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(6, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def train_mlp(
    groups: List[Tuple[np.ndarray, np.ndarray]],
    epochs: int,
    batch_groups: int,
    lr: float,
    weight_decay: float,
    seed: int,
    hidden: int,
) -> MLPScorer:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    model = MLPScorer(hidden=hidden)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)

    order = list(range(len(groups)))
    for epoch in range(1, epochs + 1):
        random.shuffle(order)
        total_loss = 0.0
        total = 0
        correct = 0

        for start in range(0, len(groups), batch_groups):
            batch_idx = order[start : start + batch_groups]
            optimizer.zero_grad()
            loss = 0.0
            used = 0

            for gi in batch_idx:
                x_np, y = groups[gi]
                x = torch.from_numpy(x_np)
                logits = model(x)
                target = torch.from_numpy(y).unsqueeze(0)
                group_loss = F.cross_entropy(logits.unsqueeze(0), target)
                loss = loss + group_loss
                used += 1

                pred = int(torch.argmax(logits).item())
                if y[pred] > 0:
                    correct += 1
                total += 1
                total_loss += float(group_loss.item())

            if used > 0:
                (loss / used).backward()
                optimizer.step()

        avg_loss = total_loss / max(total, 1)
        acc = correct / max(total, 1)
        print(f"[mlp epoch {epoch:03d}] groups={total} loss={avg_loss:.6f} top1={acc:.4f}")

    return model


def distill_to_linear_no_prior(
    groups: List[Tuple[np.ndarray, np.ndarray]],
    model: MLPScorer,
) -> np.ndarray:
    xs = []
    ys = []
    model.eval()
    with torch.no_grad():
        for x_np, _ in groups:
            x_t = torch.from_numpy(x_np)
            y_t = model(x_t).cpu().numpy()
            xs.append(x_np.astype(np.float64))
            ys.append(y_t.astype(np.float64))

    X = np.concatenate(xs, axis=0)
    Y = np.concatenate(ys, axis=0)

    w, *_ = np.linalg.lstsq(X, Y, rcond=None)
    return w.astype(np.float64)


def eval_linear(groups: List[Tuple[np.ndarray, np.ndarray]], w: np.ndarray) -> float:
    correct = 0
    total = 0
    for x_np, y in groups:
        logits = x_np @ w
        pred = int(np.argmax(logits))
        if y[pred] > 0:
            correct += 1
        total += 1
    return correct / max(total, 1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Train MLP teacher ranker then distill to 6-dim linear weights (no prior)")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True, help="Output distilled 6 weights txt")
    ap.add_argument("--epochs", type=int, default=16)
    ap.add_argument("--batch-groups", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--weight-decay", type=float, default=1e-6)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-groups", type=int, default=120000)
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--ridge", type=float, default=0.0, help="Deprecated: must be 0.0 (no-prior distillation)")
    args = ap.parse_args()

    if abs(args.ridge) > 0.0:
        raise ValueError("--ridge is not allowed in no-prior mode; set --ridge 0")

    groups = load_groups(args.csv, args.max_groups)
    if not groups:
        raise RuntimeError("No valid groups loaded from CSV")

    print(f"Loaded {len(groups)} groups from {args.csv}")
    model = train_mlp(
        groups=groups,
        epochs=args.epochs,
        batch_groups=args.batch_groups,
        lr=args.lr,
        weight_decay=args.weight_decay,
        seed=args.seed,
        hidden=args.hidden,
    )

    w = distill_to_linear_no_prior(groups, model)
    top1 = eval_linear(groups, w)
    print(f"[distilled_no_prior] top1={top1:.4f}")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="") as f:
        f.write(",".join(f"{x:.12g}" for x in w.tolist()) + "\n")

    print("Distilled weights:", ",".join(f"{x:.6f}" for x in w.tolist()))
    print(f"Saved: {args.out}")


if __name__ == "__main__":
    main()
