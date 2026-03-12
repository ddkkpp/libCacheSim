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


def _transform_score_features(
    raw_feat: np.ndarray,
    score_use_compound: bool,
    score_use_irt: bool,
    feature_log1p: bool,
    use_heuristic_signs: bool,
    apply_sign_to_features: bool,
) -> np.ndarray:
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


def _parse_feature_mask(mask_str: str | None) -> np.ndarray | None:
    if not mask_str:
        return None
    vals = [float(x.strip()) for x in mask_str.split(",")]
    if len(vals) != 6:
        raise ValueError(f"feature-mask must have 6 values, got {len(vals)}")
    return np.array(vals, dtype=np.float32)


def _pairwise_loss(
    logits: torch.Tensor,
    y: np.ndarray,
    pairwise_samples: int,
) -> torch.Tensor:
    y_t = torch.from_numpy(y)
    pos_idx = torch.where(y_t > 0)[0]
    neg_idx = torch.where(y_t <= 0)[0]
    if len(pos_idx) == 0 or len(neg_idx) == 0:
        return torch.tensor(0.0, dtype=logits.dtype, device=logits.device)

    p = pos_idx[torch.randint(0, len(pos_idx), (1,))][0]
    if pairwise_samples > 0 and len(neg_idx) > pairwise_samples:
        perm = torch.randperm(len(neg_idx))[:pairwise_samples]
        sampled_neg = neg_idx[perm]
    else:
        sampled_neg = neg_idx

    pos_logit = logits[p]
    neg_logits = logits[sampled_neg]
    # Encourage pos > neg; softplus(neg-pos) is smooth hinge-like surrogate
    return F.softplus(neg_logits - pos_logit).mean()


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
        mask = (keys_np == m)
        probs = mask.astype(np.float32) / mask.sum()
        return x, probs
    else:
        if fallback_label < 0 or fallback_label >= x.shape[0]:
            return None
        probs = np.zeros(x.shape[0], dtype=np.float32)
        probs[fallback_label] = 1.0
        return x, probs

def load_groups(
    csv_path: str,
    max_groups: int = 0,
    score_use_compound: bool = False,
    score_use_irt: bool = True,
    feature_log1p: bool = True,
    use_heuristic_signs: bool = True,
    apply_sign_to_features: bool = True,
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
                use_heuristic_signs=use_heuristic_signs,
                apply_sign_to_features=apply_sign_to_features,
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


def load_groups_multi_balanced(
    csv_paths: List[str],
    max_groups: int,
    seed: int,
    score_use_compound: bool,
    score_use_irt: bool,
    feature_log1p: bool,
    use_heuristic_signs: bool,
    apply_sign_to_features: bool,
) -> List[Tuple[np.ndarray, np.ndarray]]:
    if not csv_paths:
        return []

    all_groups_by_trace: List[List[Tuple[np.ndarray, np.ndarray]]] = []
    for p in csv_paths:
        groups = load_groups(
            p,
            max_groups=0,
            score_use_compound=score_use_compound,
            score_use_irt=score_use_irt,
            feature_log1p=feature_log1p,
            use_heuristic_signs=use_heuristic_signs,
            apply_sign_to_features=apply_sign_to_features,
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


def iter_groups(
    csv_path: str,
    max_groups: int = 0,
    score_use_compound: bool = False,
    score_use_irt: bool = True,
    feature_log1p: bool = True,
    use_heuristic_signs: bool = True,
    apply_sign_to_features: bool = True,
):
    count = 0
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
                use_heuristic_signs=use_heuristic_signs,
                apply_sign_to_features=apply_sign_to_features,
            )
            if cur_seq is None:
                cur_seq = seq

            if seq != cur_seq:
                item = _finalize_group(cur_rows)
                if item is not None:
                    yield item
                    count += 1
                    if max_groups > 0 and count >= max_groups:
                        return
                cur_rows = []
                cur_seq = seq

            bk_str = row.get("belady_key", "")
            cur_rows.append((cand_idx, feat, is_teacher, bk_str))

        if cur_rows:
            item = _finalize_group(cur_rows)
            if item is not None:
                yield item


def train_linear_ranker(
    groups: List[Tuple[np.ndarray, np.ndarray]],
    epochs: int,
    batch_groups: int,
    lr: float,
    weight_decay: float,
    seed: int,
    pairwise_lambda: float,
    pairwise_samples: int,
    feature_mask: np.ndarray | None,
    l1_lambda: float,
    nonnegative: bool,
    entropy_lambda: float,
) -> np.ndarray:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    w = torch.nn.Parameter(torch.zeros(6, dtype=torch.float32))
    optimizer = torch.optim.Adam([w], lr=lr, weight_decay=weight_decay)
    mask_t = torch.from_numpy(feature_mask) if feature_mask is not None else None

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
                if mask_t is not None:
                    x = x * mask_t
                logits = x @ w
                target = torch.from_numpy(y).unsqueeze(0)
                group_loss = F.cross_entropy(logits.unsqueeze(0), target)
                if pairwise_lambda > 0:
                    group_loss = group_loss + pairwise_lambda * _pairwise_loss(
                        logits, y, pairwise_samples=pairwise_samples
                    )
                if l1_lambda > 0:
                    group_loss = group_loss + l1_lambda * torch.norm(w, p=1)
                loss = loss + group_loss
                used += 1

                pred = int(torch.argmax(logits).item())
                if y[pred] > 0:
                    correct += 1
                total += 1
                total_loss += float(group_loss.item())

            if used > 0:
                loss = loss / used
                if entropy_lambda > 0:
                    p = torch.softmax(w, dim=0)
                    loss = loss + entropy_lambda * torch.sum(p * torch.log(p + 1e-12))
                loss.backward()
                optimizer.step()
                if nonnegative:
                    with torch.no_grad():
                        w.clamp_(min=0.0)

        avg_loss = total_loss / max(total, 1)
        acc = correct / max(total, 1)
        print(f"[epoch {epoch:03d}] groups={total} loss={avg_loss:.6f} top1={acc:.4f}")

    return w.detach().cpu().numpy()


def compute_top1_groups(groups: List[Tuple[np.ndarray, np.ndarray]], weights: np.ndarray) -> float:
    correct = 0
    total = 0
    w = weights.astype(np.float32)
    for x_np, y in groups:
        logits = x_np @ w
        pred = int(np.argmax(logits))
        if y[pred] > 0:
            correct += 1
        total += 1
    return correct / max(total, 1)


def compute_top1_csv(csv_path: str, max_groups: int, weights: np.ndarray) -> float:
    correct = 0
    total = 0
    w = weights.astype(np.float32)
    for x_np, y in iter_groups(csv_path, max_groups=max_groups):
        logits = x_np @ w
        pred = int(np.argmax(logits))
        if y[pred] > 0:
            correct += 1
        total += 1
    return correct / max(total, 1)


def train_linear_ranker_stream(
    csv_path: str,
    max_groups: int,
    epochs: int,
    batch_groups: int,
    lr: float,
    weight_decay: float,
    seed: int,
    pairwise_lambda: float,
    pairwise_samples: int,
    feature_mask: np.ndarray | None,
    l1_lambda: float,
    nonnegative: bool,
    entropy_lambda: float,
) -> np.ndarray:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    w = torch.nn.Parameter(torch.zeros(6, dtype=torch.float32))
    optimizer = torch.optim.Adam([w], lr=lr, weight_decay=weight_decay)
    mask_t = torch.from_numpy(feature_mask) if feature_mask is not None else None

    for epoch in range(1, epochs + 1):
        total_loss = 0.0
        total = 0
        correct = 0
        used_in_batch = 0
        batch_loss = 0.0

        optimizer.zero_grad()

        for x_np, y in iter_groups(csv_path, max_groups=max_groups):
            x = torch.from_numpy(x_np)
            if mask_t is not None:
                x = x * mask_t
            logits = x @ w
            target = torch.from_numpy(y).unsqueeze(0)
            group_loss = F.cross_entropy(logits.unsqueeze(0), target)
            if pairwise_lambda > 0:
                group_loss = group_loss + pairwise_lambda * _pairwise_loss(
                    logits, y, pairwise_samples=pairwise_samples
                )
            if l1_lambda > 0:
                group_loss = group_loss + l1_lambda * torch.norm(w, p=1)
            batch_loss = batch_loss + group_loss
            used_in_batch += 1

            pred = int(torch.argmax(logits).item())
            if y[pred] > 0:
                correct += 1
            total += 1
            total_loss += float(group_loss.item())

            if used_in_batch >= batch_groups:
                step_loss = batch_loss / used_in_batch
                if entropy_lambda > 0:
                    p = torch.softmax(w, dim=0)
                    step_loss = step_loss + entropy_lambda * torch.sum(p * torch.log(p + 1e-12))
                step_loss.backward()
                optimizer.step()
                if nonnegative:
                    with torch.no_grad():
                        w.clamp_(min=0.0)
                optimizer.zero_grad()
                used_in_batch = 0
                batch_loss = 0.0

        if used_in_batch > 0:
            step_loss = batch_loss / used_in_batch
            if entropy_lambda > 0:
                p = torch.softmax(w, dim=0)
                step_loss = step_loss + entropy_lambda * torch.sum(p * torch.log(p + 1e-12))
            step_loss.backward()
            optimizer.step()
            if nonnegative:
                with torch.no_grad():
                    w.clamp_(min=0.0)
            optimizer.zero_grad()

        avg_loss = total_loss / max(total, 1)
        acc = correct / max(total, 1)
        print(f"[epoch {epoch:03d}] groups={total} loss={avg_loss:.6f} top1={acc:.4f}")

    return w.detach().cpu().numpy()


def main() -> None:
    parser = argparse.ArgumentParser(description="Train linear LOH teacher ranker from exported Belady labels")
    parser.add_argument("--csv", required=True, help="Path to teacher CSV exported by LOH_TEACHER_EXPORT_PATH")
    parser.add_argument(
        "--csv-list",
        type=str,
        default="",
        help="Optional comma-separated CSV paths for multi-trace balanced training",
    )
    parser.add_argument("--out", required=True, help="Output weights text file (comma-separated 6 values)")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-groups", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-2)
    parser.add_argument("--weight-decay", type=float, default=1e-6)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-groups", type=int, default=200000)
    parser.add_argument("--pairwise-lambda", type=float, default=0.0)
    parser.add_argument("--pairwise-samples", type=int, default=16)
    parser.add_argument("--l1-lambda", type=float, default=0.0)
    parser.add_argument("--entropy-lambda", type=float, default=0.0, help="Weight entropy regularization strength to avoid single-dimension collapse")
    parser.add_argument("--nonnegative", action="store_true", help="Project weights to nonnegative after each update")
    parser.add_argument(
        "--feature-mask",
        type=str,
        default="",
        help="Optional 6-dim mask, e.g. '1,0,1,0,0,0'",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream CSV and train online (low memory). Re-reads CSV each epoch.",
    )
    parser.add_argument(
        "--eval-final-top1",
        action="store_true",
        help="After training, compute top1 using the final weights on the same dataset.",
    )
    parser.add_argument("--l1-normalize", action="store_true", help="Normalize absolute sum of weights to 1")
    parser.add_argument("--score-use-compound", type=int, default=-1, help="Match deployment score mode; -1 means read env/default")
    parser.add_argument("--score-use-irt", type=int, default=-1, help="Match deployment score mode; -1 means read env/default")
    parser.add_argument("--feature-log1p", type=int, default=-1, help="Use log1p-mode compound transform; -1 means read env/default")
    parser.add_argument("--use-heuristic-signs", type=int, default=-1, help="Use heuristic signs in non-compound mode; -1 means read env/default")
    parser.add_argument("--apply-sign-to-features", type=int, default=1, help="Apply deployment sign semantics into training features")
    args = parser.parse_args()
    feature_mask = _parse_feature_mask(args.feature_mask)

    score_use_compound = bool(_env_int("LOH_SCORE_USE_COMPOUND", 0) if args.score_use_compound < 0 else args.score_use_compound)
    score_use_irt = bool(_env_int("LOH_SCORE_USE_IRT", 1) if args.score_use_irt < 0 else args.score_use_irt)
    feature_log1p = bool(_env_int("LOH_FEATURE_LOG1P", 1) if args.feature_log1p < 0 else args.feature_log1p)
    use_heuristic_signs = bool(_env_int("LOH_USE_HEURISTIC_SIGNS", 1) if args.use_heuristic_signs < 0 else args.use_heuristic_signs)
    apply_sign_to_features = bool(args.apply_sign_to_features)
    if score_use_compound:
        score_use_irt = False

    print(
        f"[score-space] compound={int(score_use_compound)} irt={int(score_use_irt)} "
        f"log1p={int(feature_log1p)} heuristic_signs={int(use_heuristic_signs)} "
        f"apply_sign_to_features={int(apply_sign_to_features)}"
    )

    csv_paths = [x.strip() for x in args.csv_list.split(",") if x.strip()]
    use_multi_trace = len(csv_paths) > 0
    if use_multi_trace and args.stream:
        raise ValueError("--stream is not supported together with --csv-list")

    if use_multi_trace:
        print(f"Multi-trace balanced training on {len(csv_paths)} traces")
        for p in csv_paths:
            print(f"  - {p}")
        groups = load_groups_multi_balanced(
            csv_paths=csv_paths,
            max_groups=args.max_groups,
            seed=args.seed,
            score_use_compound=score_use_compound,
            score_use_irt=score_use_irt,
            feature_log1p=feature_log1p,
            use_heuristic_signs=use_heuristic_signs,
            apply_sign_to_features=apply_sign_to_features,
        )
        if not groups:
            raise RuntimeError("No valid groups loaded from multi-trace CSV list")
        print(f"Loaded {len(groups)} balanced groups from csv-list")
        weights = train_linear_ranker(
            groups,
            epochs=args.epochs,
            batch_groups=args.batch_groups,
            lr=args.lr,
            weight_decay=args.weight_decay,
            seed=args.seed,
            pairwise_lambda=args.pairwise_lambda,
            pairwise_samples=args.pairwise_samples,
            feature_mask=feature_mask,
            l1_lambda=args.l1_lambda,
            nonnegative=args.nonnegative,
            entropy_lambda=args.entropy_lambda,
        )

        if args.eval_final_top1:
            final_top1 = compute_top1_groups(groups, weights=weights)
            print(f"[final] top1={final_top1:.4f} (balanced final weights)")
    elif args.stream:
        print(f"Streaming groups from {args.csv}")
        weights = train_linear_ranker_stream(
            args.csv,
            max_groups=args.max_groups,
            epochs=args.epochs,
            batch_groups=args.batch_groups,
            lr=args.lr,
            weight_decay=args.weight_decay,
            seed=args.seed,
            pairwise_lambda=args.pairwise_lambda,
            pairwise_samples=args.pairwise_samples,
            feature_mask=feature_mask,
            l1_lambda=args.l1_lambda,
            nonnegative=args.nonnegative,
            entropy_lambda=args.entropy_lambda,
        )

        if args.eval_final_top1:
            final_top1 = compute_top1_csv(args.csv, max_groups=args.max_groups, weights=weights)
            print(f"[final] top1={final_top1:.4f} (final weights)")
    else:
        groups = load_groups(
            args.csv,
            args.max_groups,
            score_use_compound=score_use_compound,
            score_use_irt=score_use_irt,
            feature_log1p=feature_log1p,
            use_heuristic_signs=use_heuristic_signs,
            apply_sign_to_features=apply_sign_to_features,
        )
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
            pairwise_lambda=args.pairwise_lambda,
            pairwise_samples=args.pairwise_samples,
            feature_mask=feature_mask,
            l1_lambda=args.l1_lambda,
            nonnegative=args.nonnegative,
            entropy_lambda=args.entropy_lambda,
        )

        if args.eval_final_top1:
            final_top1 = compute_top1_groups(groups, weights=weights)
            print(f"[final] top1={final_top1:.4f} (final weights)")

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
