#!/usr/bin/env python3
# Print actual script filename at runtime (dynamic)
import os, sys
_loh_script_name = os.path.basename(__file__) if '__file__' in globals() and __file__ else (os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else '<unknown>')
print(f"[LOH SCRIPT] { _loh_script_name }")

# 生存函数版本：S(d) = 1 - F(d)，并在高分位数处钝化为零惩罚
# 实现思路：基于 loh_actor_critic_sb3 的实现，替换回放缓冲区的惩罚缩放逻辑，
# 使用直方图近似距离分布的经验CDF F(d)。当 d ≥ q_high (如0.99分位) 时，直接返回0。
# 注意：为避免大量代码复制，本文件仅在运行时对基准实现进行轻量注入：
import os
import math
import numpy as np
import loh_actor_critic_sb3 as base
from torch.utils.tensorboard import SummaryWriter

class SurvivalReplayBuffer(base.RetrospectiveReplayBuffer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 生存函数参数
        try:
            q_raw = os.environ.get("LOH_SURVIVAL_QUANTILE", "0.99")
            self._survival_q = float(q_raw)
        except Exception:
            self._survival_q = 0.99
        try:
            bins_raw = os.environ.get("LOH_SURVIVAL_BINS", "64")
            self._hist_bins_n = max(16, int(bins_raw))
        except Exception:
            self._hist_bins_n = 64
        try:
            mincnt_raw = os.environ.get("LOH_SURVIVAL_MINCOUNT", "1000")
            self._hist_min_count = max(10, int(mincnt_raw))
        except Exception:
            self._hist_min_count = 1000

        # 直方图边界（对距离做 log1p 压缩再等间距，再映射回原距离）
        t = np.linspace(0.0, 1.0, self._hist_bins_n + 1, dtype=np.float64)
        self._hist_edges = np.expm1(t * np.log1p(self.penalty_dmax))  # shape: (bins+1,)
        self._hist_counts = np.zeros(self._hist_bins_n, dtype=np.int64)
        self._hist_total = 0
        # 备用：对数压缩的分母（冷启动回退用）
        self._log_denom = float(max(1e-12, math.log1p(self.penalty_dmax)))

        print(f"  penalty_scale=survival, bins={self._hist_bins_n}, q={self._survival_q:.3f}, min_count={self._hist_min_count}")

    def _update_hist(self, d: float):
        try:
            d = float(d)
        except Exception:
            d = 0.0
        if d < 0:
            d = 0.0
        if d > self.penalty_dmax:
            d = float(self.penalty_dmax)
        # 找到所属bin
        idx = int(np.searchsorted(self._hist_edges, d, side='right') - 1)
        if idx < 0:
            idx = 0
        if idx >= self._hist_bins_n:
            idx = self._hist_bins_n - 1
        self._hist_counts[idx] += 1
        self._hist_total += 1

    def _cdf_from_hist(self, d: float) -> float:
        if self._hist_total <= 0:
            return 0.0
        try:
            d = float(d)
        except Exception:
            d = 0.0
        if d <= 0:
            return 0.0
        idx = int(np.searchsorted(self._hist_edges, d, side='right') - 1)
        if idx < 0:
            return 0.0
        if idx >= self._hist_bins_n:
            return 1.0
        cum = float(np.sum(self._hist_counts[:idx+1]))
        return min(1.0, cum / float(self._hist_total))

    def _get_quantile_threshold(self) -> float:
        if self._hist_total <= 0:
            return float(self.penalty_dmax)
        target = self._survival_q * float(self._hist_total)
        cum = 0.0
        for i in range(self._hist_bins_n):
            cum += float(self._hist_counts[i])
            if cum >= target:
                # 取该bin的右边界作为阈值
                return float(self._hist_edges[i+1])
        return float(self.penalty_dmax)

    def _penalty_scale(self, distance: float) -> float:
        # 早期样本不足时，回退到对数压缩以稳定训练启动
        if self._hist_total < self._hist_min_count:
            try:
                d = float(distance)
            except Exception:
                d = 0.0
            if d <= 0.0:
                return 1.0
            # log-compressed fallback: 1 - log1p(d)/log1p(dmax)
            return max(0.0, 1.0 - (math.log1p(d) / self._log_denom))
        try:
            d = float(distance)
        except Exception:
            d = 0.0
        if d <= 0:
            return 1.0
        q_th = self._get_quantile_threshold()
        if d >= q_th:
            return 0.0  # 高分位数钝化为零惩罚
        Fd = self._cdf_from_hist(d)
        Sd = 1.0 - Fd
        if Sd < 0.0:
            return 0.0
        return Sd

    def retrospective_correct_reward(self, state_version, eviction_to_access, obj_size):
        # 先调用父类，完成数据登记
        ok = super().retrospective_correct_reward(state_version, eviction_to_access, obj_size)
        # 无论是否成功登记，只要拿到距离就更新分布统计，以尽快收敛经验CDF
        try:
            self._update_hist(eviction_to_access)
        except Exception:
            pass
        return ok

class SurvivalTrainingCallback(base.LOHTrainingCallback):
    """在父回调基础上，追加距离分布的分位数/直方图统计到 TensorBoard"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tb_writer = None  # 独立的TensorBoard writer（用于直方图raw写入）

    def _ensure_tb_writer(self):
        if self._tb_writer is not None:
            return self._tb_writer
        # 尝试复用 SB3 的 logger 目录
        log_dir = None
        try:
            if hasattr(self, 'logger') and getattr(self.logger, 'dir', None):
                log_dir = self.logger.dir  # e.g., runs/<ts>/tensorboard/SAC_xxx
        except Exception:
            log_dir = None
        # 兜底：使用 RUN_TIMESTAMP 构造目录
        if not log_dir:
            ts = os.environ.get("RUN_TIMESTAMP", "default")
            log_dir = os.path.join("./runs", ts, "tensorboard")
        # 将 survival 指标写到子目录，避免与 SB3 默认事件文件冲突
        survival_dir = os.path.join(log_dir, "survival")
        os.makedirs(survival_dir, exist_ok=True)
        self._tb_writer = SummaryWriter(log_dir=survival_dir)
        try:
            print(f"[TB] Survival hist/quantiles writer initialized at: {survival_dir}")
        except Exception:
            pass
        return self._tb_writer

    def _on_step(self) -> bool:
        cont = super()._on_step()
        # 继承父类的每100步记录频率
        if hasattr(self, 'model') and self.model is not None and self.step_count % 100 == 0:
            try:
                rb = getattr(self.model, 'replay_buffer', None)
                if rb is None:
                    return cont
                # 仅当使用 SurvivalReplayBuffer 时才记录
                if not isinstance(rb, SurvivalReplayBuffer):
                    return cont

                total = int(rb._hist_total)
                self.logger.record("loh/dist_total_samples", float(total))
                if total <= 0:
                    return cont

                # 计算几个分位点（用经验CDF）
                def _quantile(p: float) -> float:
                    target = max(0.0, min(1.0, p)) * float(rb._hist_total)
                    cum = 0.0
                    for i in range(rb._hist_bins_n):
                        cum += float(rb._hist_counts[i])
                        if cum >= target:
                            return float(rb._hist_edges[i+1])
                    return float(rb._hist_edges[-1])

                q50 = _quantile(0.50)
                q90 = _quantile(0.90)
                q95 = _quantile(0.95)
                q99 = _quantile(0.99)
                qth = float(rb._get_quantile_threshold())

                # 记录到 TB（SB3 logger：scalar）
                self.logger.record("loh/dist_q50", float(q50))
                self.logger.record("loh/dist_q90", float(q90))
                self.logger.record("loh/dist_q95", float(q95))
                self.logger.record("loh/dist_q99", float(q99))
                self.logger.record("loh/dist_q_high_threshold", float(qth))

                # 可选：记录前 8 个bin的占比，帮助观察头部密度（SB3 logger：scalar）
                bins_to_log = min(8, rb._hist_bins_n)
                denom = float(rb._hist_total)
                for i in range(bins_to_log):
                    frac = float(rb._hist_counts[i]) / denom if denom > 0 else 0.0
                    self.logger.record(f"loh/dist_bin_{i}_frac", frac)

                # 另外：写入真正的直方图（TensorBoard Histogram）
                try:
                    writer = self._ensure_tb_writer()
                    # 计算直方图原始统计（使用每个bin的中点近似求和与平方和）
                    edges = np.asarray(rb._hist_edges, dtype=np.float64)
                    counts = np.asarray(rb._hist_counts, dtype=np.int64)
                    # TB raw 需要 bucket_limits（每个bin的上边界）与 bucket_counts
                    bucket_limits = edges[1:].astype(np.float64)
                    bucket_counts = counts.astype(np.int64)

                    # 近似统计量
                    mids = (edges[:-1] + edges[1:]) / 2.0
                    total_n = float(counts.sum())
                    h_sum = float((counts * mids).sum()) if total_n > 0 else 0.0
                    h_sumsq = float((counts * (mids ** 2)).sum()) if total_n > 0 else 0.0
                    h_min = float(edges[0]) if total_n > 0 else 0.0
                    h_max = float(edges[-1]) if total_n > 0 else 0.0

                    # 写入 histogram_raw（在 TB 的 Histograms 面板可见）
                    writer.add_histogram_raw(
                        tag="loh/dist_histogram",
                        min=h_min,
                        max=h_max,
                        num=int(total_n),
                        sum=h_sum,
                        sum_squares=h_sumsq,
                        bucket_limits=bucket_limits.tolist(),
                        bucket_counts=bucket_counts.tolist(),
                        global_step=int(self.num_timesteps),
                    )
                    # 也把关键分位点以 scalar 形式再写一份，便于 Scalars 面板查看
                    writer.add_scalar("loh/dist_q50", float(q50), global_step=int(self.num_timesteps))
                    writer.add_scalar("loh/dist_q90", float(q90), global_step=int(self.num_timesteps))
                    writer.add_scalar("loh/dist_q95", float(q95), global_step=int(self.num_timesteps))
                    writer.add_scalar("loh/dist_q99", float(q99), global_step=int(self.num_timesteps))
                    writer.add_scalar("loh/dist_q_high_threshold", float(qth), global_step=int(self.num_timesteps))
                    writer.flush()
                except Exception:
                    # 写入失败不影响训练
                    pass

                # 立刻 dump 一次（SB3 logger），保持与父类相同的时序
                self.logger.dump(step=self.num_timesteps)
            except Exception:
                # 诊断不应影响训练
                pass
        return cont


if __name__ == "__main__":
    # 运行前注入：让基准 main 使用 Survival 版回放与回调
    base.RetrospectiveReplayBuffer = SurvivalReplayBuffer
    base.LOHTrainingCallback = SurvivalTrainingCallback
    # Apply env-only seed if provided (LOH_RL_SEED > SEED)
    try:
        loh_seed_raw = os.environ.get("LOH_RL_SEED")
        seed = None
        if loh_seed_raw is not None and loh_seed_raw != "":
            seed = int(loh_seed_raw)
        else:
            seed_raw = os.environ.get("SEED")
            if seed_raw is not None and seed_raw != "":
                seed = int(seed_raw)
        if seed is not None:
            os.environ['PYTHONHASHSEED'] = str(seed)
            import random as _random
            _random.seed(seed)
            import numpy as _np
            _np.random.seed(seed)
            try:
                import torch as _torch
                _torch.manual_seed(seed)
                if _torch.cuda.is_available():
                    _torch.cuda.manual_seed_all(seed)
            except Exception:
                pass
            print(f"[seed] Applied LOH_RL_SEED={seed} to random/numpy/torch")
    except Exception:
        pass

    base.main()
