#!/usr/bin/env python3
import argparse
import os
import random
from typing import List, Tuple

import numpy as np
import torch
import torch.nn.functional as F

from train_loh_teacher_ranker import (
    _env_int,
    _parse_feature_mask,
    compute_top1_groups,
    load_groups,
    load_groups_multi_balanced,
)


def train_linear_ranker_reinforce(
    groups: List[Tuple[np.ndarray, np.ndarray]],
    episodes: int,
    batch_groups: int,
    lr: float,
    weight_decay: float,
    seed: int,
    feature_mask: np.ndarray | None,
    entropy_coef: float,
    baseline_momentum: float,
    reward_mode: str,
    l1_lambda: float,
    nonnegative: bool,
    temperature: float,
    eval_interval: int,
) -> np.ndarray:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    w = torch.nn.Parameter(torch.zeros(6, dtype=torch.float32))
    optimizer = torch.optim.Adam([w], lr=lr, weight_decay=weight_decay)
    mask_t = torch.from_numpy(feature_mask) if feature_mask is not None else None

    n = len(groups)
    baseline = 0.0

    for ep in range(1, episodes + 1):
        batch_idx = np.random.randint(0, n, size=(batch_groups,))

        log_probs = []
        entropies = []
        rewards = []

        for gi in batch_idx:
            x_np, y_np = groups[int(gi)]
            x = torch.from_numpy(x_np)
            if mask_t is not None:
                x = x * mask_t

            logits = (x @ w) / max(temperature, 1e-6)
            probs = torch.softmax(logits, dim=0)
            dist = torch.distributions.Categorical(probs=probs)
            act = dist.sample()

            if reward_mode == "soft":
                r = float(y_np[int(act.item())])
            else:
                r = 1.0 if y_np[int(act.item())] > 0 else 0.0

            log_probs.append(dist.log_prob(act))
            entropies.append(dist.entropy())
            rewards.append(r)

        rewards_t = torch.tensor(rewards, dtype=torch.float32)
        batch_reward = float(rewards_t.mean().item())
        baseline = baseline_momentum * baseline + (1.0 - baseline_momentum) * batch_reward
        advantages = rewards_t - baseline

        log_probs_t = torch.stack(log_probs)
        entropies_t = torch.stack(entropies)

        loss_pg = -(log_probs_t * advantages.detach()).mean()
        loss = loss_pg - entropy_coef * entropies_t.mean()
        if l1_lambda > 0:
            loss = loss + l1_lambda * torch.norm(w, p=1)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        if nonnegative:
            with torch.no_grad():
                w.clamp_(min=0.0)

        if ep == 1 or ep % eval_interval == 0 or ep == episodes:
            cur_w = w.detach().cpu().numpy()
            top1 = compute_top1_groups(groups, cur_w)
            print(
                f"[episode {ep:05d}] reward={batch_reward:.4f} baseline={baseline:.4f} "
                f"loss={float(loss.item()):.6f} top1={top1:.4f}"
            )

    return w.detach().cpu().numpy()


def main() -> None:
    parser = argparse.ArgumentParser(description="Train linear LOH teacher ranker with RL (REINFORCE) from exported Belady labels")
    parser.add_argument("--csv", required=True, help="Path to teacher CSV exported by LOH_TEACHER_EXPORT_PATH")
    parser.add_argument(
        "--csv-list",
        type=str,
        default="",
        help="Optional comma-separated CSV paths for multi-trace balanced training",
    )
    parser.add_argument("--out", required=True, help="Output weights text file (comma-separated 6 values)")

    parser.add_argument("--episodes", type=int, default=3000)
    parser.add_argument("--batch-groups", type=int, default=512)
    parser.add_argument("--lr", type=float, default=3e-3)
    parser.add_argument("--weight-decay", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-groups", type=int, default=200000)

    parser.add_argument("--entropy-coef", type=float, default=1e-2)
    parser.add_argument("--baseline-momentum", type=float, default=0.95)
    parser.add_argument("--reward-mode", choices=["hard", "soft"], default="hard")
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--eval-interval", type=int, default=100)

    parser.add_argument("--l1-lambda", type=float, default=0.0)
    parser.add_argument("--nonnegative", action="store_true", help="Project weights to nonnegative after each update")
    parser.add_argument(
        "--feature-mask",
        type=str,
        default="",
        help="Optional 6-dim mask, e.g. '1,0,1,0,0,0'",
    )
    parser.add_argument("--l1-normalize", action="store_true", help="Normalize absolute sum of weights to 1")
    parser.add_argument(
        "--eval-final-top1",
        action="store_true",
        help="After training, compute top1 using the final weights on training groups.",
    )

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

    if use_multi_trace:
        print(f"Multi-trace balanced RL training on {len(csv_paths)} traces")
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

    weights = train_linear_ranker_reinforce(
        groups=groups,
        episodes=args.episodes,
        batch_groups=args.batch_groups,
        lr=args.lr,
        weight_decay=args.weight_decay,
        seed=args.seed,
        feature_mask=feature_mask,
        entropy_coef=args.entropy_coef,
        baseline_momentum=args.baseline_momentum,
        reward_mode=args.reward_mode,
        l1_lambda=args.l1_lambda,
        nonnegative=args.nonnegative,
        temperature=args.temperature,
        eval_interval=max(args.eval_interval, 1),
    )

    if args.l1_normalize:
        s = float(np.sum(np.abs(weights)))
        if s > 1e-12:
            weights = weights / s

    if args.eval_final_top1:
        final_top1 = compute_top1_groups(groups, weights=weights)
        print(f"[final] top1={final_top1:.4f} (final weights)")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="") as f:
        f.write(",".join(f"{x:.12g}" for x in weights.tolist()) + "\n")

    print("Trained RL weights:", ",".join(f"{x:.6f}" for x in weights.tolist()))
    print(f"Saved: {args.out}")
    print("Use with: export LOH_FIXED_WEIGHTS='w1,w2,w3,w4,w5,w6'")


if __name__ == "__main__":
    main()
