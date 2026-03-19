# AC Reward/Penalty Signal Detailed Report

## Inputs

- patterns: 20260206-20260206-_generated_ac_reward_signal_report_0204_pen1_final.md
- only_penalty_final: 1
- rank_clip_sat: 0
- progress_every: 5
- header_only: 1
- max_header_lines: 4000

## File Manifest

- count: 17

- ac_sb3_0204_020116.log
- ac_sb3_0204_021319.log
- ac_sb3_0204_022347.log
- ac_sb3_0204_023003.log
- ac_sb3_0204_030758.log
- ac_sb3_0204_093859.log
- ac_sb3_0204_094504.log
- ac_sb3_0204_095110.log
- ac_sb3_0204_095921.log
- ac_sb3_0204_100126.log
- ac_sb3_0204_100753.log
- ac_sb3_0204_101659.log
- ac_sb3_0204_102313.log
- ac_sb3_0204_102923.log
- ac_sb3_0204_103522.log
- ac_sb3_0204_3m_1063_p1_pen_log_neg_w1_orig1_s124.log
- ac_sb3_0204_3m_1063_p1_pen_w0p2_centered_s124.log

files: 17 (filtered from 17)
filter: only penalty=1 and has [Reward→Final]

## penalty_scale = log

**Files**

- **ac_sb3_0204_023003.log**
  - cfg: w_pen=0.5, dmax=400000
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=log<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.5<br>byte_penalty=0.000<br>dmax=400000<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=log_compressed
- **ac_sb3_0204_102923.log**
  - cfg: w_pen=0.25, formula=centered, dmax=400000
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=log<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.25<br>byte_penalty=0.000<br>dmax=400000<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_reward_formula=centered<br>penalty_scale=log_compressed
- **ac_sb3_0204_3m_1063_p1_pen_log_neg_w1_orig1_s124.log**
  - cfg: w_pen=1.0, formula=neg, dmax=400000
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=log<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=1.0<br>byte_penalty=0.000<br>dmax=400000<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_reward_formula=neg<br>penalty_scale=log_compressed

## penalty_scale = reciprocal

**Files**

- **ac_sb3_0204_020116.log**
  - cfg: w_pen=0.5
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=reciprocal<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.5<br>byte_penalty=0.000<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=reciprocal
- **ac_sb3_0204_021319.log**
  - cfg: w_pen=0.5
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=reciprocal<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.5<br>byte_penalty=0.000<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=reciprocal
- **ac_sb3_0204_022347.log**
  - cfg: w_pen=0.5
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=reciprocal<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.5<br>byte_penalty=0.000<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=reciprocal
- **ac_sb3_0204_103522.log**
  - cfg: w_pen=1.0, formula=relative
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=reciprocal<br>LOH_REWARD_USE_PENALTY=0<br>LOH_REWARD_W_PENALTY=1.0<br>byte_penalty=0.000<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_reward_formula=relative<br>penalty_scale=reciprocal
- **ac_sb3_0204_3m_1063_p1_pen_w0p2_centered_s124.log**
  - cfg: w_pen=0.2, formula=centered, cutoff=100
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=reciprocal<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.2<br>byte_penalty=0.000<br>obj_penalty=1.000<br>penalty_cutoff=100<br>penalty_entry_size=32<br>penalty_reward_formula=centered<br>penalty_scale=reciprocal

## penalty_scale = survival

**Files**

- **ac_sb3_0204_030758.log**
  - cfg: w_pen=0.25, dmax=400000, q=0.900, bins=64, min_count=200
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.25<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=200<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=survival<br>q=0.900
- **ac_sb3_0204_093859.log**
  - cfg: w_pen=0.25, dmax=400000, q=0.900, bins=64, min_count=200
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.25<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=200<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=survival<br>q=0.900
- **ac_sb3_0204_094504.log**
  - cfg: w_pen=0.25, dmax=400000, q=0.900, bins=64, min_count=200
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.25<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=200<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=survival<br>q=0.900
- **ac_sb3_0204_095110.log**
  - cfg: w_pen=0.25, dmax=400000, q=0.900, bins=64, min_count=200
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.25<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=200<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=survival<br>q=0.900
- **ac_sb3_0204_095921.log**
  - cfg: w_pen=0.25, cutoff=200, dmax=400000, q=0.900, bins=64, min_count=200
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.25<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=200<br>obj_penalty=1.000<br>penalty_cutoff=200<br>penalty_entry_size=32<br>penalty_scale=survival<br>q=0.900
- **ac_sb3_0204_100126.log**
  - cfg: w_pen=0.15, cutoff=500, dmax=400000, q=0.900, bins=64, min_count=200
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.15<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=200<br>obj_penalty=1.000<br>penalty_cutoff=500<br>penalty_entry_size=32<br>penalty_scale=survival<br>q=0.900
- **ac_sb3_0204_100753.log**
  - cfg: w_pen=0.25, dmax=400000, q=0.990, bins=64, min_count=1000
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.25<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=1000<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=survival<br>q=0.990
- **ac_sb3_0204_101659.log**
  - cfg: w_pen=0.25, formula=centered, dmax=400000, q=0.900, bins=64, min_count=200
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.25<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=200<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_reward_formula=centered<br>penalty_scale=survival<br>q=0.900
- **ac_sb3_0204_102313.log**
  - cfg: w_pen=0.10, formula=centered, dmax=400000, q=0.900, bins=64, min_count=200
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.10<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=200<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_reward_formula=centered<br>penalty_scale=survival<br>q=0.900
