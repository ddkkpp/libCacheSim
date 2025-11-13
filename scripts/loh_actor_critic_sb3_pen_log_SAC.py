#!/usr/bin/env python3
# Print actual script filename at runtime (dynamic)
import os, sys
_loh_script_name = os.path.basename(__file__) if '__file__' in globals() and __file__ else (os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else '<unknown>')
print(f"[LOH SCRIPT] { _loh_script_name }")

# 对数缩放变体（log）：p(d) = max(0, 1 - log1p(d)/log1p(dmax))
# - 通过运行时注入的方式，最小化代码重复
# - dmax 默认 400000，可用环境变量 LOH_PENALTY_DMAX 覆盖
import os
import math
import loh_actor_critic_sb3 as base


class LogReplayBuffer(base.RetrospectiveReplayBuffer):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		try:
			env_dmax = os.environ.get("LOH_PENALTY_DMAX")
			penalty_dmax = int(env_dmax) if env_dmax and env_dmax.strip() != "" else 400000
		except Exception:
			penalty_dmax = 400000
		self.penalty_dmax = max(1, int(penalty_dmax))
		self._log_denom = float(max(1e-12, math.log1p(self.penalty_dmax)))
		print(f"  penalty_scale=log_compressed, dmax={self.penalty_dmax}")

	def _penalty_scale(self, distance: float) -> float:
		try:
			d = float(distance)
		except Exception:
			d = 0.0
		if d <= 0.0:
			return 1.0
		# 1 - log1p(d)/log1p(dmax)，并裁剪到 [0,1]
		return max(0.0, 1.0 - (math.log1p(d) / self._log_denom))


if __name__ == "__main__":
	# 注入对数缩放的回放缓冲区，然后调用基准 main
	base.RetrospectiveReplayBuffer = LogReplayBuffer
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
