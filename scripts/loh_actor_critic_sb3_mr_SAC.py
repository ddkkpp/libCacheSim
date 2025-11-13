#!/usr/bin/env python3
# Print actual script filename at runtime (dynamic)
import os, sys
_loh_script_name = os.path.basename(__file__) if '__file__' in globals() and __file__ else (os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else '<unknown>')
print(f"[LOH SCRIPT] { _loh_script_name }")

"""Minimal SAC wrapper that reuses the PPO-based environment, callback and training logic.

This wrapper constructs the environment, builds a SAC model via
`loh_actor_critic_sb3_mr_PPO.create_model` and calls
`loh_actor_critic_sb3_mr_PPO.run_training` so we don't duplicate reset/step/callback code.
"""

import os
from datetime import datetime
import argparse
import numpy as np
from stable_baselines3.common.noise import NormalActionNoise

import loh_actor_critic_sb3_mr_PPO as base


def main():
    parser = argparse.ArgumentParser(description="LOH Actor-Critic SAC (wrapper)")
    parser.add_argument("--miss-ratio-weight", type=float, default=1.0)
    parser.add_argument("--tensorboard-log", type=str, default="")
    args = parser.parse_args()

    byte_miss_ratio_weight = 1.0 - args.miss_ratio_weight

    # ------------------ Seed handling (ENV only) ------------------
    # Only read seed from environment variables. Priority: LOH_RL_SEED > SEED
    seed = None
    loh_seed_raw = os.environ.get("LOH_RL_SEED")
    if loh_seed_raw is not None and loh_seed_raw != "":
        try:
            seed = int(loh_seed_raw)
        except Exception:
            seed = None
    else:
        seed_raw = os.environ.get("SEED")
        if seed_raw is not None and seed_raw != "":
            try:
                seed = int(seed_raw)
            except Exception:
                seed = None

    if seed is not None:
        try:
            import random as _random
            _random.seed(seed)
        except Exception:
            pass
        try:
            np.random.seed(seed)
        except Exception:
            pass
        try:
            import torch as _torch
            _torch.manual_seed(seed)
            if _torch.cuda.is_available():
                _torch.cuda.manual_seed_all(seed)
        except Exception:
            pass
        if base.LOH_DEBUG_BASIC():
            print(f"Using random seed = {seed} (applied to random/numpy/torch) via environment")
    # ---------------- end seed handling -----------------

    timestamp = os.environ.get("RUN_TIMESTAMP") or datetime.now().strftime("%m%d_%H%M%S")
    run_dir = f"./runs/{timestamp}"
    os.makedirs(run_dir, exist_ok=True)

    tensorboard_log = args.tensorboard_log or os.path.join(run_dir, "tensorboard")
    os.makedirs(tensorboard_log, exist_ok=True)

    # 读取共享内存键并传入环境
    try:
        shm_key = int(os.environ.get("LOH_SHM_KEY", os.environ.get("SHM_KEY", "9876")))
    except Exception:
        shm_key = 9876
    env = base.LohEnv(shm_key=shm_key, miss_ratio_weight=args.miss_ratio_weight, byte_miss_ratio_weight=byte_miss_ratio_weight)

    # 仅将 TD3 噪声类默认改为 SB3 默认；SAC 其他默认保持原脚本设置（可用环境变量覆盖）
    sac_kwargs = dict(
        buffer_size=int(os.environ.get("SAC_BUFFER_SIZE", "100000")),   # 原脚本默认 100000
        batch_size=int(os.environ.get("SAC_BATCH_SIZE", "256")),        # 原=SB3 默认
        gamma=float(os.environ.get("SAC_GAMMA", "0.99")),                # 原=SB3 默认
        tau=float(os.environ.get("SAC_TAU", "0.005")),                  # 原=SB3 默认
        learning_rate=float(os.environ.get("SAC_LEARNING_RATE", "0.0003")),  # 原=SB3 默认 3e-4
        train_freq=(int(os.environ.get("SAC_TRAIN_FREQ", "16")), "step"),    # 原脚本默认 16
        gradient_steps=int(os.environ.get("SAC_GRADIENT_STEPS", "1")),   # 原=SB3 默认
        learning_starts=int(os.environ.get("SAC_LEARNING_STARTS", "3000")),   # 原脚本默认 3000
        ent_coef=os.environ.get("SAC_ENT_COEF", "auto"),
        tensorboard_log=tensorboard_log,
        policy_kwargs=dict(net_arch=[256, 256], activation_fn=base.torch.nn.ReLU),
    )

    model = base.create_model("SAC", env, tensorboard_log=tensorboard_log, algo_kwargs=sac_kwargs)

    if base.LOH_DEBUG_BASIC():
        print("[MR-SAC] Resolved config (from model):")
        print(f"  shm_key: {shm_key}")
        print(f"  miss_ratio_weight: {args.miss_ratio_weight:.3f}")
        print(f"  byte_miss_ratio_weight: {byte_miss_ratio_weight:.3f}")
        print(f"  buffer_size: {getattr(model, 'buffer_size', 'N/A')}  # original default 100000")
        print(f"  batch_size: {getattr(model, 'batch_size', 'N/A')}   # SB3 default 256")
        print(f"  learning_rate: {getattr(model, 'learning_rate', 'N/A')}  # SB3 default 3e-4")
        print(f"  gamma: {getattr(model, 'gamma', 'N/A')}   # SB3 default 0.99")
        print(f"  tau: {getattr(model, 'tau', 'N/A')}      # SB3 default 0.005")
        print(f"  train_freq: {getattr(model, 'train_freq', 'N/A')}  # original default (16, 'step')")
        print(f"  gradient_steps: {getattr(model, 'gradient_steps', 'N/A')}  # SB3 default 1")
        print(f"  learning_starts: {getattr(model, 'learning_starts', 'N/A')}  # original default 3000")
        print(f"  ent_coef: {getattr(model, 'ent_coef', 'N/A')}  # SB3 default 'auto'")

    base.run_training(model, env, run_dir)


if __name__ == "__main__":
    main()
