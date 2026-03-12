#!/usr/bin/env python3
import argparse
import csv
import os
import random
from typing import List, Tuple

import numpy as np
import torch
import torch.nn.functional as F


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except Exception:
        return default


def _transform_score_features(raw_feat: np.ndarray, score_use_compound: bool, score_use_irt: bool, feature_log1p: bool, use_heuristic_signs: bool, apply_sign_to_features: bool) -> np.ndarray:
    rec = float(raw_feat[0])
    freq = float(raw_feat[1])
    size = float(raw_feat[2])
    irt1 = float(raw_feat[3])
    irt2 = float(raw_feat[4])
    irt3 = float(raw_feat[5])

    out = np.zeros(6, dtype=np.float32)
    sign = np.ones(6, dtype=np.float32)

    if score_use_compound:
        eps = 1e-12
        safe_rec = rec if abs(rec) > eps else (eps if rec >= 0.0 else -eps)
        safe_size = size if abs(size) > eps else (eps if size >= 0.0 else -eps)
        if feature_log1p:
            freq_recency = freq / safe_rec
            freq_size = freq / safe_size
            recency_size = rec * size
            sign[:] = np.array([-1.0, 1.0, -1.0, 1.0, 1.0, -1.0], dtype=np.float32)
        else:
            freq_recency = freq * rec
            freq_size = freq * size
            recency_size = rec * size
            sign[:] = 1.0
        out[:] = np.array([rec, freq, size, freq_recency, freq_size, recency_size], dtype=np.float32)
    else:
        if score_use_irt:
            out[:] = np.array([rec, freq, size, irt1, irt2, irt3], dtype=np.float32)
        else:
            out[:] = np.array([rec, freq, size, 0.0, 0.0, 0.0], dtype=np.float32)
        if use_heuristic_signs:
            sign[:] = np.array([-1.0, 1.0, -1.0, -1.0, -1.0, -1.0], dtype=np.float32)
        else:
            sign[:] = 1.0

    if apply_sign_to_features:
        out = out * sign
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


def load_groups(csv_path: str, score_use_compound: bool, score_use_irt: bool, feature_log1p: bool, use_heuristic_signs: bool, apply_sign_to_features: bool) -> List[Tuple[np.ndarray, np.ndarray]]:
    groups: List[Tuple[np.ndarray, np.ndarray]] = []
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        cur_seq = None
        cur_rows: List[Tuple[int, np.ndarray, int, str]] = []
        for row in reader:
            seq = int(row["evict_seq"])
            cand_idx = int(row["cand_idx"])
            is_teacher = int(row["is_teacher"])
            raw_feat = np.array([
                float(row["feature0"]),
                float(row["feature1"]),
                float(row["feature2"]),
                float(row["feature3"]),
                float(row["feature4"]),
                float(row["feature5"]),
            ], dtype=np.float32)
            feat = _transform_score_features(raw_feat, score_use_compound, score_use_irt, feature_log1p, use_heuristic_signs, apply_sign_to_features)

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


def train_robust(
    trace_groups: List[List[Tuple[np.ndarray, np.ndarray]]],
    epochs: int,
    batch_groups: int,
    lr: float,
    weight_decay: float,
    seed: int,
    robust_lambda: float,
    nonnegative: bool,
    normalize_sum1: bool,
    init_vec: np.ndarray | None,
) -> np.ndarray:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if init_vec is None:
        w = torch.nn.Parameter(torch.zeros(6, dtype=torch.float32))
    else:
        w = torch.nn.Parameter(torch.from_numpy(init_vec.astype(np.float32)).clone())
    optimizer = torch.optim.Adam([w], lr=lr, weight_decay=weight_decay)

    n_traces = len(trace_groups)
    min_len = min(len(g) for g in trace_groups)
    steps = max(1, min_len // batch_groups)

    for epoch in range(1, epochs + 1):
        per_trace_order = []
        for groups in trace_groups:
            idx = list(range(len(groups)))
            random.shuffle(idx)
            per_trace_order.append(idx[: min_len])

        total_loss = 0.0
        total = 0
        correct = 0

        for step in range(steps):
            optimizer.zero_grad()
            trace_losses = []

            for ti in range(n_traces):
                groups = trace_groups[ti]
                idx_slice = per_trace_order[ti][step * batch_groups : (step + 1) * batch_groups]
                if not idx_slice:
                    continue

                loss_t = 0.0
                used = 0
                for gi in idx_slice:
                    x_np, y = groups[gi]
                    x = torch.from_numpy(x_np)
                    logits = x @ w
                    target = torch.from_numpy(y).unsqueeze(0)
                    group_loss = F.cross_entropy(logits.unsqueeze(0), target)
                    loss_t = loss_t + group_loss
                    used += 1

                    pred = int(torch.argmax(logits).item())
                    if y[pred] > 0:
                        correct += 1
                    total += 1
                    total_loss += float(group_loss.item())

                if used > 0:
                    trace_losses.append(loss_t / used)

            if not trace_losses:
                continue

            stack = torch.stack(trace_losses)
            obj = torch.mean(stack) + robust_lambda * torch.max(stack)
            obj.backward()
            optimizer.step()
            with torch.no_grad():
                if nonnegative:
                    w.data.clamp_(min=0.0)
                if normalize_sum1:
                    s = torch.sum(w.data)
                    if float(s.item()) > 0.0:
                        w.data.div_(s)

        avg_loss = total_loss / max(total, 1)
        acc = correct / max(total, 1)
        print(f"[epoch {epoch:03d}] groups={total} loss={avg_loss:.6f} top1={acc:.4f}")

    return w.detach().cpu().numpy()


def eval_top1(groups: List[Tuple[np.ndarray, np.ndarray]], w: np.ndarray) -> float:
    correct = 0
    total = 0
    for x_np, y in groups:
        logits = x_np @ w.astype(np.float32)
        pred = int(np.argmax(logits))
        if y[pred] > 0:
            correct += 1
        total += 1
    return correct / max(total, 1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Robust multi-trace linear teacher ranker")
    ap.add_argument("--csv-list", required=True, help="Comma-separated CSV list")
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--batch-groups", type=int, default=256)
    ap.add_argument("--lr", type=float, default=0.01)
    ap.add_argument("--weight-decay", type=float, default=1e-6)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-groups", type=int, default=30000)
    ap.add_argument("--robust-lambda", type=float, default=0.5)
    ap.add_argument("--nonnegative", type=int, default=1)
    ap.add_argument("--normalize-sum1", type=int, default=1)
    ap.add_argument("--init-weights", type=str, default="")
    args = ap.parse_args()

    score_use_compound = bool(_env_int("LOH_SCORE_USE_COMPOUND", 0))
    score_use_irt = bool(_env_int("LOH_SCORE_USE_IRT", 1))
    feature_log1p = bool(_env_int("LOH_FEATURE_LOG1P", 1))
    use_heuristic_signs = bool(_env_int("LOH_USE_HEURISTIC_SIGNS", 1))
    if score_use_compound:
        score_use_irt = False

    csv_paths = [x.strip() for x in args.csv_list.split(",") if x.strip()]
    if not csv_paths:
        raise ValueError("empty csv-list")

    trace_groups: List[List[Tuple[np.ndarray, np.ndarray]]] = []
    for p in csv_paths:
        gs = load_groups(p, score_use_compound, score_use_irt, feature_log1p, use_heuristic_signs, True)
        if args.max_groups > 0 and len(gs) > args.max_groups:
            gs = gs[: args.max_groups]
        if not gs:
            raise RuntimeError(f"no valid groups: {p}")
        trace_groups.append(gs)
        print(f"loaded {len(gs)} groups: {p}")

    init_vec = None
    if args.init_weights:
        if os.path.isfile(args.init_weights):
            with open(args.init_weights, "r", newline="") as f:
                txt = f.read().strip()
        else:
            txt = args.init_weights.strip()
        vals = [float(x) for x in txt.split(",") if x.strip() != ""]
        if len(vals) != 6:
            raise ValueError("--init-weights must contain exactly 6 values")
        init_vec = np.array(vals, dtype=np.float32)

    w = train_robust(
        trace_groups=trace_groups,
        epochs=args.epochs,
        batch_groups=args.batch_groups,
        lr=args.lr,
        weight_decay=args.weight_decay,
        seed=args.seed,
        robust_lambda=args.robust_lambda,
        nonnegative=bool(args.nonnegative),
        normalize_sum1=bool(args.normalize_sum1),
        init_vec=init_vec,
    )

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="") as f:
        f.write(",".join(f"{x:.12g}" for x in w.tolist()) + "\n")

    for i, gs in enumerate(trace_groups):
        print(f"[final trace{i}] top1={eval_top1(gs, w):.4f}")
    print("Trained weights:", ",".join(f"{x:.6f}" for x in w.tolist()))
    print(f"Saved: {args.out}")


if __name__ == "__main__":
    main()
