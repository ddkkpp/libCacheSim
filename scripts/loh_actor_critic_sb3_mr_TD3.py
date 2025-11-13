

#!/usr/bin/env python3
# Print actual script filename at runtime (dynamic)
import os, sys
_loh_script_name = os.path.basename(__file__) if '__file__' in globals() and __file__ else (os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else '<unknown>')
print(f"[LOH SCRIPT] { _loh_script_name }")

"""Minimal TD3 wrapper that reuses the PPO-based environment, callback and training logic.

This wrapper constructs the environment, builds a TD3 model via
`loh_actor_critic_sb3_mr_PPO.create_model` and calls
`loh_actor_critic_sb3_mr_PPO.run_training` so we don't duplicate reset/step/callback code.
"""

import os
import argparse
from datetime import datetime
import numpy as np
from stable_baselines3.common.noise import NormalActionNoise

import loh_actor_critic_sb3_mr_PPO as base


def main():
    parser = argparse.ArgumentParser(description="LOH Actor-Critic TD3 (wrapper)")
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

    # 使用“之前代码默认”作为基础，仅对三项噪声采用 SB3 默认；其余均可被环境变量覆盖
    # 之前代码默认（与 SAC 脚本风格一致）：
    # - buffer_size=100000, learning_starts=3000, train_freq=(16, 'step')
    # - batch_size=256, learning_rate=3e-4, gamma=0.99, tau=0.005, gradient_steps=1
    # - policy_delay=2（与 SB3 相同），policy net_arch=[256,256], activation=ReLU
    td3_kwargs = dict(
        buffer_size=int(os.environ.get("TD3_BUFFER_SIZE", "10000")),
        batch_size=int(os.environ.get("TD3_BATCH_SIZE", "256")),
        learning_rate=float(os.environ.get("TD3_LEARNING_RATE", "0.0003")),
        gamma=float(os.environ.get("TD3_GAMMA", "0.99")),
        tau=float(os.environ.get("TD3_TAU", "0.005")),
        learning_starts=int(os.environ.get("TD3_LEARNING_STARTS", "3000")),
        train_freq=(int(os.environ.get("TD3_TRAIN_FREQ", "16")), "step"),
        gradient_steps=int(os.environ.get("TD3_GRADIENT_STEPS", "1")),
        policy_delay=int(os.environ.get("TD3_POLICY_DELAY", "2")),
        policy_kwargs=dict(net_arch=[256, 256], activation_fn=base.torch.nn.ReLU),
        tensorboard_log=tensorboard_log,
    )
    # 三项噪声：保持 SB3 默认（target_policy_noise=0.2, target_noise_clip=0.5, action_noise=None），允许环境变量覆盖前两项
    def _maybe_set(name, key, cast):
        raw = os.environ.get(name)
        if raw is None or raw == "":
            return
        try:
            td3_kwargs[key] = cast(raw)
        except Exception:
            pass
    _maybe_set("TD3_TARGET_POLICY_NOISE", "target_policy_noise", float)
    _maybe_set("TD3_TARGET_NOISE_CLIP", "target_noise_clip", float)

    # 可选 action noise：仅当 TD3_ACTION_NOISE 提供时才注入
    exploration_sigma_raw = os.environ.get("TD3_ACTION_NOISE")
    if exploration_sigma_raw is not None and exploration_sigma_raw != "":
        try:
            action_dim = env.action_space.shape[0]
            exploration_sigma=float(exploration_sigma_raw)
            action_noise = NormalActionNoise(mean=np.zeros(action_dim), sigma=exploration_sigma * np.ones(action_dim))
            td3_kwargs["action_noise"] = action_noise
        except Exception:
            pass
    # Always create the model (ensure `model` exists regardless of whether action_noise was provided)
    model = base.create_model("TD3", env, tensorboard_log=tensorboard_log, algo_kwargs=td3_kwargs)

    if base.LOH_DEBUG_BASIC():
        def _fmt_noise(n):
            try:
                import numpy as _np
                if n is None:
                    return "None"
                name = n.__class__.__name__
                sigma = getattr(n, 'sigma', None)
                if sigma is not None:
                    try:
                        val = float(_np.array(sigma).reshape(-1)[0])
                        return f"{name}(sigma~{val:.4f})"
                    except Exception:
                        return f"{name}(sigma=...)"
                return name
            except Exception:
                return str(n)

        print("[MR-TD3] Resolved config (from model):")
        print(f"  shm_key: {shm_key}")
        print(f"  miss_ratio_weight: {args.miss_ratio_weight:.3f}")
        print(f"  byte_miss_ratio_weight: {byte_miss_ratio_weight:.3f}")
        print(f"   - buffer_size: {getattr(model, 'buffer_size', 'N/A')}  # previous default 100000")
        print(f"   - learning_starts: {getattr(model, 'learning_starts', 'N/A')}  # previous default 3000")
        print(f"   - batch_size: {getattr(model, 'batch_size', 'N/A')}   # previous/SB3 default 256")
        print(f"   - learning_rate: {getattr(model, 'learning_rate', 'N/A')}  # previous/SB3 default 3e-4")
        print(f"   - gamma: {getattr(model, 'gamma', 'N/A')}   # previous/SB3 default 0.99")
        print(f"   - tau: {getattr(model, 'tau', 'N/A')}      # previous/SB3 default 0.005")
        print(f"   - train_freq: {getattr(model, 'train_freq', 'N/A')}  # previous default (16, 'step')")
        print(f"   - gradient_steps: {getattr(model, 'gradient_steps', 'N/A')}  # previous/SB3 default 1")
        print(f"   - policy_delay: {getattr(model, 'policy_delay', 'N/A')}  # previous/SB3 default 2")
        # policy/net arch best-effort
        pol = getattr(model, 'policy', None)
        if pol is not None:
            net_arch = getattr(pol, 'net_arch', None)
            print(f"   - policy.class: {pol.__class__.__name__}")
            print(f"   - policy.net_arch: {net_arch if net_arch is not None else 'N/A'}")
        # noises from model
        print(f"   - target_policy_noise: {getattr(model, 'target_policy_noise', 'N/A')}  # SB3 default 0.2 (env-overridable)")
        print(f"   - target_noise_clip: {getattr(model, 'target_noise_clip', 'N/A')}    # SB3 default 0.5 (env-overridable)")
        print(f"   - action_noise: {_fmt_noise(getattr(model, 'action_noise', None))}  # SB3 default None")
    if base.LOH_DEBUG_BASIC():
        def _fmt_noise(n):
            try:
                import numpy as _np
                if n is None:
                    return "None"
                name = n.__class__.__name__
                sigma = getattr(n, 'sigma', None)
                if sigma is not None:
                    try:
                        val = float(_np.array(sigma).reshape(-1)[0])
                        return f"{name}(sigma~{val:.4f})"
                    except Exception:
                        return f"{name}(sigma=...)"
                return name
            except Exception:
                return str(n)

        print("[MR-TD3] Resolved config (from model):")
        print(f"  shm_key: {shm_key}")
        print(f"  miss_ratio_weight: {args.miss_ratio_weight:.3f}")
        print(f"  byte_miss_ratio_weight: {byte_miss_ratio_weight:.3f}")
        print("  TD3 hyperparameters:")
        print(f"   - buffer_size: {getattr(model, 'buffer_size', 'N/A')}  # previous default 100000")
        print(f"   - batch_size: {getattr(model, 'batch_size', 'N/A')}   # previous/SB3 default 256")
        print(f"   - learning_rate: {getattr(model, 'learning_rate', 'N/A')}  # previous/SB3 default 3e-4")
        print(f"   - gamma: {getattr(model, 'gamma', 'N/A')}   # previous/SB3 default 0.99")
        print(f"   - tau: {getattr(model, 'tau', 'N/A')}      # previous/SB3 default 0.005")
        print(f"   - train_freq: {getattr(model, 'train_freq', 'N/A')}  # previous default (16, 'step')")
        print(f"   - gradient_steps: {getattr(model, 'gradient_steps', 'N/A')}  # previous/SB3 default 1")
        print(f"   - learning_starts: {getattr(model, 'learning_starts', 'N/A')}  # previous default 3000")
        print(f"   - policy_delay: {getattr(model, 'policy_delay', 'N/A')}  # previous/SB3 default 2")
        print(f"   - target_policy_noise: {getattr(model, 'target_policy_noise', 'N/A')}  # SB3 default 0.2 (env-overridable)")
        print(f"   - target_noise_clip: {getattr(model, 'target_noise_clip', 'N/A')}    # SB3 default 0.5 (env-overridable)")
        print(f"   - action_noise: {_fmt_noise(getattr(model, 'action_noise', None))}  # SB3 default None")

    base.run_training(model, env, run_dir)


if __name__ == "__main__":
    main()
