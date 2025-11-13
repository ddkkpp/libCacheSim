#!/usr/bin/env python3
# Print actual script filename at runtime (dynamic)
import os, sys
_loh_script_name = os.path.basename(__file__) if '__file__' in globals() and __file__ else (os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else '<unknown>')
print(f"[LOH SCRIPT] { _loh_script_name }")

# 倒数缩放变体（pen_d）：p(d) = 1 / max(d, 1)
# 最小包装：重导出基准符号，并把入口转发给基准 main（基准即采用倒数缩放）。
from loh_actor_critic_sb3 import *

if __name__ == "__main__":
    from loh_actor_critic_sb3 import main as _base_main
    _base_main()
