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


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except Exception:
        return default


def _transform_score_features(
    raw_feat: np.ndarray,
    score_use_compound: bool,
    score_use_irt: bool,
    feature_log1p: bool,
) -> np.ndarray:
    rec = float(raw_feat[0])
    freq = float(raw_feat[1])
    size = float(raw_feat[2])
    irt1 = float(raw_feat[3])
    irt2 = float(raw_feat[4])
    irt3 = float(raw_feat[5])

    out = np.zeros(6, dtype=np.float32)
    if score_use_compound:
        eps = 1e-12
        safe_rec = rec if abs(rec) > eps else (eps if rec >= 0.0 else -eps)
        safe_size = size if abs(size) > eps else (eps if size >= 0.0 else -eps)
        if feature_log1p:
            freq_recency = freq / safe_rec
            freq_size = freq / safe_size
            recency_size = rec * size
        else:
            freq_recency = freq * rec
            freq_size = freq * size
            recency_size = rec * size
        out[:] = np.array([rec, freq, size, freq_recency, freq_size, recency_size], dtype=np.float32)
    else:
        if score_use_irt:
            out[:] = np.array([rec, freq, size, irt1, irt2, irt3], dtype=np.float32)
        else:
            out[:] = np.array([rec, freq, size, 0.0, 0.0, 0.0], dtype=np.float32)
    return out


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


def load_groups(
    csv_path: str,
    score_use_compound: bool,
    score_use_irt: bool,
    feature_log1p: bool,
) -> List[Tuple[np.ndarray, np.ndarray]]:
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
            raw_feat = np.array(
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
            feat = _transform_score_features(
                raw_feat=raw_feat,
                score_use_compound=score_use_compound,
                score_use_irt=score_use_irt,
                feature_log1p=feature_log1p,
            )
            if cur_seq is None:
                cur_seq = seq
            if seq != cur_seq:
                item = _finalize_group(cur_rows)
                if item is not None:
                    groups.append(item)
                cur_rows = []
                cur_seq = seq
            bk_str = row.get("belady_key", "")
            cur_rows.append((cand_idx, feat, is_teacher, bk_str))

        if cur_rows:
            item = _finalize_group(cur_rows)
            if item is not None:
                groups.append(item)
    return groups


def load_groups_multi_balanced(
    csv_paths: List[str],
    max_groups: int,
    seed: int,
    score_use_compound: bool,
    score_use_irt: bool,
    feature_log1p: bool,
) -> List[Tuple[np.ndarray, np.ndarray]]:
    all_groups_by_trace: List[List[Tuple[np.ndarray, np.ndarray]]] = []
    for p in csv_paths:
        groups = load_groups(
            p,
            score_use_compound=score_use_compound,
            score_use_irt=score_use_irt,
            feature_log1p=feature_log1p,
        )
        if not groups:
            raise RuntimeError(f"No valid groups loaded from CSV: {p}")
        all_groups_by_trace.append(groups)

    n_trace = len(all_groups_by_trace)
    min_count = min(len(g) for g in all_groups_by_trace)
    if max_groups > 0:
        per_trace = max(1, max_groups // n_trace)
        use_per_trace = min(min_count, per_trace)
    else:
        use_per_trace = min_count

    rng = random.Random(seed)
    merged: List[Tuple[np.ndarray, np.ndarray]] = []
    for groups in all_groups_by_trace:
        if len(groups) <= use_per_trace:
            chosen = groups
        else:
            idx = rng.sample(range(len(groups)), use_per_trace)
            chosen = [groups[i] for i in idx]
        merged.extend(chosen)

    rng.shuffle(merged)
    return merged


class OneHiddenMLP(nn.Module):
    def __init__(self, hidden: int):
        super().__init__()
        self.fc1 = nn.Linear(6, hidden)
        self.fc2 = nn.Linear(hidden, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = F.relu(self.fc1(x))
        return self.fc2(h).squeeze(-1)


def train_mlp(
    groups: List[Tuple[np.ndarray, np.ndarray]],
    hidden: int,
    epochs: int,
    batch_groups: int,
    lr: float,
    weight_decay: float,
    seed: int,
) -> OneHiddenMLP:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    model = OneHiddenMLP(hidden=hidden)
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


def export_params_for_c(model: OneHiddenMLP) -> np.ndarray:
    # C 端 loh_mlp_eval 期望顺序：W1(H*D), b1(H), W2(H), b2(1)
    with torch.no_grad():
        w1 = model.fc1.weight.detach().cpu().numpy().astype(np.float64)  # [H,6]
        b1 = model.fc1.bias.detach().cpu().numpy().astype(np.float64)    # [H]
        w2 = model.fc2.weight.detach().cpu().numpy().astype(np.float64)  # [1,H]
        b2 = model.fc2.bias.detach().cpu().numpy().astype(np.float64)    # [1]

    flat = np.concatenate([
        w1.reshape(-1),
        b1.reshape(-1),
        w2.reshape(-1),
        b2.reshape(-1),
    ])
    return flat


def main() -> None:
    ap = argparse.ArgumentParser(description="Train one-hidden teacher MLP and export C-compatible LOH_FIXED_MLP_PARAMS")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--csv-list", type=str, default="", help="Comma-separated CSV paths for balanced multi-trace training")
    ap.add_argument("--out", required=True, help="Output txt containing comma-separated MLP params")
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--batch-groups", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--weight-decay", type=float, default=1e-6)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-groups", type=int, default=30000)
    ap.add_argument("--hidden", type=int, default=16)
    ap.add_argument("--score-use-compound", type=int, default=-1)
    ap.add_argument("--score-use-irt", type=int, default=-1)
    ap.add_argument("--feature-log1p", type=int, default=-1)
    args = ap.parse_args()

    score_use_compound = bool(_env_int("LOH_SCORE_USE_COMPOUND", 0) if args.score_use_compound < 0 else args.score_use_compound)
    score_use_irt = bool(_env_int("LOH_SCORE_USE_IRT", 1) if args.score_use_irt < 0 else args.score_use_irt)
    feature_log1p = bool(_env_int("LOH_FEATURE_LOG1P", 1) if args.feature_log1p < 0 else args.feature_log1p)
    if score_use_compound:
        score_use_irt = False
    print(
        f"[score-space] compound={int(score_use_compound)} irt={int(score_use_irt)} log1p={int(feature_log1p)}"
    )

    csv_paths = [x.strip() for x in args.csv_list.split(",") if x.strip()]
    if csv_paths:
        groups = load_groups_multi_balanced(
            csv_paths=csv_paths,
            max_groups=args.max_groups,
            seed=args.seed,
            score_use_compound=score_use_compound,
            score_use_irt=score_use_irt,
            feature_log1p=feature_log1p,
        )
        print(f"Loaded {len(groups)} balanced groups from {len(csv_paths)} traces")
    else:
        groups = load_groups(
            args.csv,
            score_use_compound=score_use_compound,
            score_use_irt=score_use_irt,
            feature_log1p=feature_log1p,
        )
        if args.max_groups > 0 and len(groups) > args.max_groups:
            groups = groups[: args.max_groups]
        print(f"Loaded {len(groups)} groups from {args.csv}")

    if not groups:
        raise RuntimeError("No valid groups loaded")

    model = train_mlp(
        groups=groups,
        hidden=args.hidden,
        epochs=args.epochs,
        batch_groups=args.batch_groups,
        lr=args.lr,
        weight_decay=args.weight_decay,
        seed=args.seed,
    )

    params = export_params_for_c(model)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="") as f:
        f.write(",".join(f"{x:.12g}" for x in params.tolist()) + "\n")

    print(f"Exported params: len={len(params)} hidden={args.hidden}")
    print(f"Saved: {args.out}")


if __name__ == "__main__":
    main()
