# AC Reward/Penalty Signal Combined Report

This file is created by merging:
- stats: 20260206-20260206-_generated_ac_reward_signal_report_0204_pen1_final.md
- config: 20260206-20260206-_generated_ac_reward_signal_report_0204_pen1_final_config_rich.md

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


## Notes

- Distributions/statistics come from the stats report (no log rescanning here).
- cfg/params come from the config report when available.

## penalty_scale = log

**Summary**
- immediate_reward: n=87474, mean=0.789126, bins=[0,0.25):3.00% [0.25,0.5):14.66% [0.5,0.75):20.86% [0.75,1):61.49%
- penalty_data: n=37464, zero=494 (1.32%), hist=distinct=219 top10=20:1.95% 22:1.88% 14:1.88% 19:1.87% 16:1.83% 23:1.82% 18:1.79% 21:1.77% 11:1.77% 1:1.76%
- final_reward(after clip): n=37464, mean=0.332756, min=-1, max=1, clip_sat=5.18%
- final_reward bins: [-1,-0.75):5.15% [-0.75,-0.5):1.38% [-0.5,-0.25):3.31% [-0.25,0):31.25% [0,0.25):3.77% [0.25,0.5):6.40% [0.5,0.75):14.21% [0.75,1):34.52%
- penalty(weighted) bins: [0,1e-06):1.32% [0.0001,0.001):0.13% [0.001,0.01):4.28% [0.01,0.1):59.65% [0.1,1):32.11% [1,10):2.41% [10,100):0.10%

**Files**

- **ac_sb3_0204_023003.log**
  - cfg: w_pen=0.5, dmax=400000
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=log<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.5<br>byte_penalty=0.000<br>dmax=400000<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=log_compressed
  - penalty_data: n=12487, zero=164 (1.31%), hist=distinct=195 top10=16:1.97% 20:1.95% 11:1.91% 19:1.90% 14:1.86% 1:1.83% 28:1.81% 22:1.80% 24:1.79% 15:1.79%
  - immediate_reward: n=29158, mean=0.791782, min=0.015, max=1, p50=1, p90=1, p99=1
  - immediate_reward bins: [0,0.25):2.79% [0.25,0.5):14.41% [0.5,0.75):20.97% [0.75,1):61.83%
  - reward(before clip): n=12487, mean=-0.0738361, min=-276.228, max=1, p50=0.584781, p90=0.908135, p99=1
  - final_reward(after clip): n=12487, mean=0.38579, min=-1, max=1, clip_sat=9.03%, p50=0.584781, p90=0.908135, p99=1
  - final_reward bins: [-1,-0.75):9.21% [-0.75,-0.5):2.17% [-0.5,-0.25):2.87% [-0.25,0):5.23% [0,0.25):8.24% [0.25,0.5):14.74% [0.5,0.75):26.63% [0.75,1):30.90%
  - penalty(weighted): n=12487, mean=0.183224, min=0, max=25.923, p50=0.065774, p90=0.273515, p99=2.58073
  - penalty bins: [0,1e-06):1.31% [0.0001,0.001):0.16% [0.001,0.01):4.25% [0.01,0.1):60.30% [0.1,1):31.53% [1,10):2.35% [10,100):0.10%

- **ac_sb3_0204_102923.log**
  - cfg: w_pen=0.25, formula=centered, dmax=400000
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=log<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.25<br>byte_penalty=0.000<br>dmax=400000<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_reward_formula=centered<br>penalty_scale=log_compressed
  - penalty_data: n=12483, zero=176 (1.41%), hist=distinct=192 top10=22:2.03% 20:2.02% 19:1.97% 1:1.87% 14:1.87% 16:1.83% 23:1.83% 18:1.81% 29:1.81% 11:1.77%
  - immediate_reward: n=29158, mean=0.792226, min=0.015, max=1, p50=0.98, p90=1, p99=1
  - immediate_reward bins: [0,0.25):2.82% [0.25,0.5):14.28% [0.5,0.75):20.96% [0.75,1):61.95%
  - reward(before clip): n=12483, mean=0.625416, min=-48.2467, max=1, p50=0.868106, p90=0.96848, p99=1
  - final_reward(after clip): n=12483, mean=0.742026, min=-1, max=1, clip_sat=4.09%, p50=0.868106, p90=0.96848, p99=1
  - final_reward bins: [-1,-0.75):2.97% [-0.75,-0.5):0.44% [-0.5,-0.25):0.62% [-0.25,0):0.96% [0,0.25):1.83% [0.25,0.5):4.46% [0.5,0.75):16.02% [0.75,1):72.69%
  - penalty(weighted): n=12483, mean=0.187292, min=0, max=24.6233, p50=0.0659472, p90=0.274109, p99=2.66955
  - penalty bins: [0,1e-06):1.41% [0.0001,0.001):0.11% [0.001,0.01):4.49% [0.01,0.1):59.57% [0.1,1):31.75% [1,10):2.59% [10,100):0.09%

- **ac_sb3_0204_3m_1063_p1_pen_log_neg_w1_orig1_s124.log**
  - cfg: w_pen=1.0, formula=neg, dmax=400000
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=log<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=1.0<br>byte_penalty=0.000<br>dmax=400000<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_reward_formula=neg<br>penalty_scale=log_compressed
  - penalty_data: n=12494, zero=154 (1.23%), hist=distinct=198 top10=14:1.90% 20:1.90% 23:1.89% 21:1.88% 18:1.86% 12:1.82% 22:1.82% 25:1.78% 26:1.78% 28:1.74%
  - immediate_reward: n=29158, mean=0.78337, min=0.015, max=1, p50=1, p90=1, p99=1
  - immediate_reward bins: [0,0.25):3.38% [0.25,0.5):15.28% [0.5,0.75):20.65% [0.75,1):60.69%
  - reward(before clip): n=12494, mean=-0.187936, min=-26.3366, max=-0, p50=-0.0681715, p90=-0.0169177, p99=-0
  - final_reward(after clip): n=12494, mean=-0.129157, min=-1, max=-0, clip_sat=2.43%, p50=-0.0681715, p90=-0.0169177, p99=-0
  - final_reward bins: [-1,-0.75):3.27% [-0.75,-0.5):1.54% [-0.5,-0.25):6.44% [-0.25,0):87.53% [0,0.25):1.23%
  - penalty(weighted): n=12494, mean=0.187936, min=0, max=26.3366, p50=0.0681713, p90=0.271084, p99=2.47999
  - penalty bins: [0,1e-06):1.23% [0.0001,0.001):0.12% [0.001,0.01):4.10% [0.01,0.1):59.08% [0.1,1):33.04% [1,10):2.31% [10,100):0.13%

## penalty_scale = reciprocal

**Summary**
- immediate_reward: n=145790, mean=0.790745, bins=[0,0.25):2.90% [0.25,0.5):14.42% [0.5,0.75):20.96% [0.75,1):61.72%
- penalty_data: n=62450, zero=13060 (20.91%), hist=distinct=219 top10=0:20.91% 19:1.52% 16:1.51% 15:1.51% 20:1.48% 1:1.48% 14:1.47% 21:1.45% 18:1.44% 10:1.43%
- final_reward(after clip): n=62450, mean=0.660211, min=-1, max=1, clip_sat=26.33%
- final_reward bins: [-1,-0.75):6.17% [-0.75,-0.5):1.01% [-0.5,-0.25):1.40% [-0.25,0):2.00% [0,0.25):3.24% [0.25,0.5):6.13% [0.5,0.75):13.91% [0.75,1):66.14%
- penalty(weighted) bins: [0,1e-06):22.87% [1e-06,1e-05):25.89% [1e-05,0.0001):42.71% [0.0001,0.001):7.33% [0.001,0.01):1.03% [0.01,0.1):0.17% [0.1,1):0.01%

**Files**

- **ac_sb3_0204_020116.log**
  - cfg: w_pen=0.5
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=reciprocal<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.5<br>byte_penalty=0.000<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=reciprocal
  - penalty_data: n=12479, zero=174 (1.39%), hist=distinct=189 top10=19:1.95% 15:1.92% 16:1.90% 26:1.89% 11:1.86% 13:1.84% 23:1.82% 20:1.80% 27:1.80% 24:1.78%
  - immediate_reward: n=29158, mean=0.792282, min=0.015, max=1, p50=0.975, p90=1, p99=1
  - immediate_reward bins: [0,0.25):2.80% [0.25,0.5):14.25% [0.5,0.75):21.05% [0.75,1):61.90%
  - reward(before clip): n=12479, mean=-0.482923, min=-2265.97, max=1, p50=0.816052, p90=0.979641, p99=1
  - final_reward(after clip): n=12479, mean=0.581644, min=-1, max=1, clip_sat=8.21%, p50=0.816052, p90=0.979641, p99=1
  - final_reward bins: [-1,-0.75):7.77% [-0.75,-0.5):1.19% [-0.5,-0.25):1.59% [-0.25,0):2.52% [0,0.25):3.63% [0.25,0.5):7.89% [0.5,0.75):16.94% [0.75,1):58.47%
  - penalty(weighted): n=12479, mean=0.00014096, min=0, max=0.100235, p50=1.594e-05, p90=0.000103314, p99=0.00154598
  - penalty bins: [0,1e-06):3.77% [1e-06,1e-05):32.23% [1e-05,0.0001):53.63% [0.0001,0.001):9.04% [0.001,0.01):1.11% [0.01,0.1):0.22% [0.1,1):0.01%

- **ac_sb3_0204_021319.log**
  - cfg: w_pen=0.5
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=reciprocal<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.5<br>byte_penalty=0.000<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=reciprocal
  - penalty_data: n=12490, zero=167 (1.34%), hist=distinct=191 top10=15:2.00% 14:1.99% 21:1.99% 19:1.92% 22:1.86% 17:1.84% 27:1.84% 9:1.79% 12:1.79% 16:1.79%
  - immediate_reward: n=29158, mean=0.793019, min=0.015, max=1, p50=0.985, p90=1, p99=1
  - immediate_reward bins: [0,0.25):2.77% [0.25,0.5):14.10% [0.5,0.75):21.01% [0.75,1):62.12%
  - reward(before clip): n=12490, mean=-0.296238, min=-1155.9, max=1, p50=0.790288, p90=0.971986, p99=1
  - final_reward(after clip): n=12490, mean=0.552777, min=-1, max=1, clip_sat=8.56%, p50=0.790288, p90=0.971986, p99=1
  - final_reward bins: [-1,-0.75):8.26% [-0.75,-0.5):1.31% [-0.5,-0.25):1.91% [-0.25,0):2.47% [0,0.25):4.42% [0.25,0.5):7.81% [0.5,0.75):18.39% [0.75,1):55.43%
  - penalty(weighted): n=12490, mean=0.000114307, min=0, max=0.09036, p50=1.555e-05, p90=9.9179e-05, p99=0.00140241
  - penalty bins: [0,1e-06):3.68% [1e-06,1e-05):32.61% [1e-05,0.0001):53.80% [0.0001,0.001):8.49% [0.001,0.01):1.30% [0.01,0.1):0.11%

- **ac_sb3_0204_022347.log**
  - cfg: w_pen=0.5
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=reciprocal<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.5<br>byte_penalty=0.000<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=reciprocal
  - penalty_data: n=12494, zero=172 (1.38%), hist=distinct=191 top10=16:2.07% 10:1.92% 12:1.92% 18:1.91% 25:1.90% 19:1.85% 20:1.84% 21:1.84% 15:1.82% 14:1.80%
  - immediate_reward: n=29158, mean=0.792151, min=0.015, max=1, p50=0.98, p90=1, p99=1
  - immediate_reward bins: [0,0.25):2.81% [0.25,0.5):14.32% [0.5,0.75):20.94% [0.75,1):61.94%
  - reward(before clip): n=12494, mean=-0.617868, min=-2960.78, max=1, p50=0.809924, p90=0.980375, p99=1
  - final_reward(after clip): n=12494, mean=0.582516, min=-1, max=1, clip_sat=7.78%, p50=0.809924, p90=0.980375, p99=1
  - final_reward bins: [-1,-0.75):7.28% [-0.75,-0.5):1.30% [-0.5,-0.25):1.75% [-0.25,0):2.43% [0,0.25):4.23% [0.25,0.5):7.73% [0.5,0.75):17.57% [0.75,1):57.72%
  - penalty(weighted): n=12494, mean=0.000142751, min=0, max=0.214346, p50=1.5585e-05, p90=0.00010542, p99=0.00140232
  - penalty bins: [0,1e-06):3.85% [1e-06,1e-05):32.66% [1e-05,0.0001):52.92% [0.0001,0.001):9.16% [0.001,0.01):1.26% [0.01,0.1):0.14% [0.1,1):0.02%

- **ac_sb3_0204_103522.log**
  - cfg: w_pen=1.0, formula=relative
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=reciprocal<br>LOH_REWARD_USE_PENALTY=0<br>LOH_REWARD_W_PENALTY=1.0<br>byte_penalty=0.000<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_reward_formula=relative<br>penalty_scale=reciprocal
  - penalty_data: n=12484, zero=182 (1.46%), hist=distinct=190 top10=20:1.99% 22:1.91% 18:1.90% 19:1.87% 14:1.86% 12:1.83% 13:1.83% 15:1.82% 23:1.82% 16:1.80%
  - immediate_reward: n=29158, mean=0.79229, min=0.015, max=1, p50=0.985, p90=1, p99=1
  - immediate_reward bins: [0,0.25):2.81% [0.25,0.5):14.27% [0.5,0.75):20.93% [0.75,1):61.99%
  - reward(before clip): n=12484, mean=-0.641989, min=-4313.83, max=1, p50=0.818103, p90=0.978856, p99=1
  - final_reward(after clip): n=12484, mean=0.58379, min=-1, max=1, clip_sat=8.13%, p50=0.818103, p90=0.978856, p99=1
  - final_reward bins: [-1,-0.75):7.57% [-0.75,-0.5):1.23% [-0.5,-0.25):1.78% [-0.25,0):2.60% [0,0.25):3.93% [0.25,0.5):7.22% [0.5,0.75):16.65% [0.75,1):59.03%
  - penalty(weighted): n=12484, mean=0.000156681, min=0, max=0.504439, p50=1.555e-05, p90=0.000107685, p99=0.00153823
  - penalty bins: [0,1e-06):4.05% [1e-06,1e-05):31.99% [1e-05,0.0001):53.16% [0.0001,0.001):9.34% [0.001,0.01):1.26% [0.01,0.1):0.18% [0.1,1):0.02%

- **ac_sb3_0204_3m_1063_p1_pen_w0p2_centered_s124.log**
  - cfg: w_pen=0.2, formula=centered, cutoff=100
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=reciprocal<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.2<br>byte_penalty=0.000<br>obj_penalty=1.000<br>penalty_cutoff=100<br>penalty_entry_size=32<br>penalty_reward_formula=centered<br>penalty_scale=reciprocal
  - penalty_data: n=12503, zero=12365 (98.90%), hist=distinct=6 0:98.90% 1:0.90% 2:0.15% 3:0.04% 5:0.01% 9:0.01%
  - immediate_reward: n=29158, mean=0.783985, min=0.015, max=1, p50=1, p90=1, p99=1
  - immediate_reward bins: [0,0.25):3.30% [0.25,0.5):15.14% [0.5,0.75):20.90% [0.75,1):60.66%
  - reward(before clip): n=12503, mean=0.999891, min=0.789474, max=1, p50=1, p90=1, p99=1
  - final_reward(after clip): n=12503, mean=0.999891, min=0.789474, max=1, clip_sat=98.90%, p50=1, p90=1, p99=1
  - final_reward bins: [0.75,1):100.00%
  - penalty(weighted): n=12503, mean=5.44626e-05, min=0, max=0.105263, p50=0, p90=0, p99=0.000117908
  - penalty bins: [0,1e-06):98.90% [1e-05,0.0001):0.06% [0.0001,0.001):0.62% [0.001,0.01):0.22% [0.01,0.1):0.18% [0.1,1):0.01%

## penalty_scale = survival

**Summary**
- immediate_reward: n=242998, mean=0.790232, bins=[0,0.25):2.97% [0.25,0.5):14.52% [0.5,0.75):20.76% [0.75,1):61.74%
- penalty_data: n=102744, zero=15970 (15.54%), hist=distinct=233 top10=0:15.54% 1:1.84% 18:1.61% 12:1.58% 20:1.58% 11:1.57% 22:1.57% 15:1.55% 16:1.55% 19:1.55%
- final_reward(after clip): n=102744, mean=0.404879, min=-1, max=1, clip_sat=23.86%
- final_reward bins: [-1,-0.75):10.01% [-0.75,-0.5):2.48% [-0.5,-0.25):3.56% [-0.25,0):5.63% [0,0.25):8.03% [0.25,0.5):12.66% [0.5,0.75):18.44% [0.75,1):39.19%
- penalty(weighted) bins: [0,1e-06):15.62% [1e-05,0.0001):0.00% [0.0001,0.001):0.04% [0.001,0.01):1.24% [0.01,0.1):23.30% [0.1,1):53.69% [1,10):5.57% [10,100):0.53% [100,1000):0.00%

**Files**

- **ac_sb3_0204_030758.log**
  - cfg: w_pen=0.25, dmax=400000, q=0.900, bins=64, min_count=200
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.25<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=200<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=survival<br>q=0.900
  - penalty_data: n=12489, zero=169 (1.35%), hist=distinct=194 top10=18:1.97% 16:1.95% 12:1.94% 11:1.91% 10:1.88% 20:1.86% 24:1.85% 23:1.82% 14:1.78% 21:1.76%
  - immediate_reward: n=29158, mean=0.792603, min=0.015, max=1, p50=1, p90=1, p99=1
  - immediate_reward bins: [0,0.25):2.78% [0.25,0.5):14.20% [0.5,0.75):21.10% [0.75,1):61.93%
  - reward(before clip): n=12489, mean=-0.207848, min=-109.169, max=1, p50=0.431899, p90=0.909599, p99=1
  - final_reward(after clip): n=12489, mean=0.250947, min=-1, max=1, clip_sat=12.01%, p50=0.431899, p90=0.909599, p99=1
  - final_reward bins: [-1,-0.75):12.82% [-0.75,-0.5):3.42% [-0.5,-0.25):4.62% [-0.25,0):7.81% [0,0.25):10.21% [0.25,0.5):15.81% [0.5,0.75):20.07% [0.75,1):25.25%
  - penalty(weighted): n=12489, mean=0.495789, min=0, max=75.976, p50=0.174242, p90=0.764452, p99=6.65992
  - penalty bins: [0,1e-06):1.43% [0.0001,0.001):0.05% [0.001,0.01):1.37% [0.01,0.1):26.92% [0.1,1):62.98% [1,10):6.68% [10,100):0.57%

- **ac_sb3_0204_093859.log**
  - cfg: w_pen=0.25, dmax=400000, q=0.900, bins=64, min_count=200
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.25<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=200<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=survival<br>q=0.900
  - penalty_data: n=12489, zero=169 (1.35%), hist=distinct=194 top10=18:1.97% 16:1.95% 12:1.94% 11:1.91% 10:1.88% 20:1.86% 24:1.85% 23:1.82% 14:1.78% 21:1.76%
  - immediate_reward: n=29158, mean=0.792603, min=0.015, max=1, p50=1, p90=1, p99=1
  - immediate_reward bins: [0,0.25):2.78% [0.25,0.5):14.20% [0.5,0.75):21.10% [0.75,1):61.93%
  - reward(before clip): n=12489, mean=-0.207848, min=-109.169, max=1, p50=0.431899, p90=0.909599, p99=1
  - final_reward(after clip): n=12489, mean=0.250947, min=-1, max=1, clip_sat=12.01%, p50=0.431899, p90=0.909599, p99=1
  - final_reward bins: [-1,-0.75):12.82% [-0.75,-0.5):3.42% [-0.5,-0.25):4.62% [-0.25,0):7.81% [0,0.25):10.21% [0.25,0.5):15.81% [0.5,0.75):20.07% [0.75,1):25.25%
  - penalty(weighted): n=12489, mean=0.495789, min=0, max=75.976, p50=0.174242, p90=0.764452, p99=6.65992
  - penalty bins: [0,1e-06):1.43% [0.0001,0.001):0.05% [0.001,0.01):1.37% [0.01,0.1):26.92% [0.1,1):62.98% [1,10):6.68% [10,100):0.57%

- **ac_sb3_0204_094504.log**
  - cfg: w_pen=0.25, dmax=400000, q=0.900, bins=64, min_count=200
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.25<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=200<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=survival<br>q=0.900
  - penalty_data: n=12484, zero=178 (1.43%), hist=distinct=194 top10=12:1.96% 18:1.94% 22:1.92% 11:1.90% 20:1.88% 24:1.86% 14:1.83% 19:1.83% 25:1.81% 13:1.80%
  - immediate_reward: n=29158, mean=0.792169, min=0.015, max=1, p50=0.99, p90=1, p99=1
  - immediate_reward bins: [0,0.25):2.83% [0.25,0.5):14.23% [0.5,0.75):20.99% [0.75,1):61.95%
  - reward(before clip): n=12484, mean=-0.257983, min=-215.573, max=1, p50=0.442509, p90=0.916403, p99=1
  - final_reward(after clip): n=12484, mean=0.259782, min=-1, max=1, clip_sat=12.03%, p50=0.442509, p90=0.916403, p99=1
  - final_reward bins: [-1,-0.75):12.62% [-0.75,-0.5):3.47% [-0.5,-0.25):4.71% [-0.25,0):6.86% [0,0.25):10.43% [0.25,0.5):15.85% [0.5,0.75):20.26% [0.75,1):25.79%
  - penalty(weighted): n=12484, mean=0.520497, min=0, max=60.5045, p50=0.176413, p90=0.770835, p99=7.05928
  - penalty bins: [0,1e-06):1.52% [0.0001,0.001):0.02% [0.001,0.01):1.32% [0.01,0.1):27.03% [0.1,1):62.95% [1,10):6.45% [10,100):0.70%

- **ac_sb3_0204_095110.log**
  - cfg: w_pen=0.25, dmax=400000, q=0.900, bins=64, min_count=200
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.25<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=200<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=survival<br>q=0.900
  - penalty_data: n=12488, zero=170 (1.36%), hist=distinct=189 top10=15:1.95% 17:1.89% 18:1.87% 21:1.86% 22:1.81% 19:1.79% 25:1.79% 23:1.79% 12:1.78% 11:1.75%
  - immediate_reward: n=29158, mean=0.792834, min=0.015, max=1, p50=1, p90=1, p99=1
  - immediate_reward bins: [0,0.25):2.75% [0.25,0.5):14.11% [0.5,0.75):21.06% [0.75,1):62.08%
  - reward(before clip): n=12488, mean=-0.249879, min=-209.734, max=1, p50=0.442315, p90=0.910436, p99=1
  - final_reward(after clip): n=12488, mean=0.25391, min=-1, max=1, clip_sat=12.32%, p50=0.442315, p90=0.910436, p99=1
  - final_reward bins: [-1,-0.75):13.17% [-0.75,-0.5):3.19% [-0.5,-0.25):4.70% [-0.25,0):7.03% [0,0.25):10.35% [0.25,0.5):15.70% [0.5,0.75):19.85% [0.75,1):26.01%
  - penalty(weighted): n=12488, mean=0.511698, min=0, max=90.5752, p50=0.176835, p90=0.767974, p99=6.91792
  - penalty bins: [0,1e-06):1.54% [0.0001,0.001):0.05% [0.001,0.01):1.19% [0.01,0.1):27.08% [0.1,1):63.24% [1,10):6.29% [10,100):0.61%

- **ac_sb3_0204_095921.log**
  - cfg: w_pen=0.25, cutoff=200, dmax=400000, q=0.900, bins=64, min_count=200
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.25<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=200<br>obj_penalty=1.000<br>penalty_cutoff=200<br>penalty_entry_size=32<br>penalty_scale=survival<br>q=0.900
  - penalty_data: n=2846, zero=2784 (97.82%), hist=distinct=9 0:97.82% 1:1.76% 2:0.18% 3:0.04% 4:0.07% 5:0.04% 7:0.04% 9:0.04% 10:0.04%
  - immediate_reward: n=9734, mean=0.738359, min=0, max=1, p50=1, p90=1, p99=1
  - immediate_reward bins: [0,0.25):7.11% [0.25,0.5):21.95% [0.5,0.75):14.28% [0.75,1):56.66%
  - reward(before clip): n=2846, mean=0.957855, min=-27.8043, max=1, p50=1, p90=1, p99=1
  - final_reward(after clip): n=2846, mean=0.979809, min=-1, max=1, clip_sat=98.03%, p50=1, p90=1, p99=1
  - final_reward bins: [-1,-0.75):0.39% [-0.75,-0.5):0.11% [-0.5,-0.25):0.07% [-0.25,0):0.28% [0,0.25):0.25% [0.25,0.5):0.21% [0.5,0.75):0.77% [0.75,1):97.93%
  - penalty(weighted): n=2846, mean=0.000503115, min=0, max=0.249673, p50=0, p90=0, p99=0.0121504
  - penalty bins: [0,1e-06):97.82% [0.001,0.01):1.02% [0.01,0.1):1.09% [0.1,1):0.07%

- **ac_sb3_0204_100126.log**
  - cfg: w_pen=0.15, cutoff=500, dmax=400000, q=0.900, bins=64, min_count=200
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.15<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=200<br>obj_penalty=1.000<br>penalty_cutoff=500<br>penalty_entry_size=32<br>penalty_scale=survival<br>q=0.900
  - penalty_data: n=12475, zero=11985 (96.07%), hist=distinct=11 0:96.07% 1:2.85% 2:0.58% 3:0.24% 4:0.10% 5:0.05% 6:0.05% 7:0.03% 9:0.01% 11:0.02% 13:0.01%
  - immediate_reward: n=29158, mean=0.79203, min=0.015, max=1, p50=1, p90=1, p99=1
  - immediate_reward bins: [0,0.25):2.81% [0.25,0.5):14.29% [0.5,0.75):20.92% [0.75,1):61.98%
  - reward(before clip): n=12475, mean=0.931131, min=-156.58, max=1, p50=1, p90=1, p99=1
  - final_reward(after clip): n=12475, mean=0.973369, min=-1, max=1, clip_sat=96.52%, p50=1, p90=1, p99=1
  - final_reward bins: [-1,-0.75):0.53% [-0.75,-0.5):0.08% [-0.5,-0.25):0.14% [-0.25,0):0.16% [0,0.25):0.21% [0.25,0.5):0.62% [0.5,0.75):1.08% [0.75,1):97.19%
  - penalty(weighted): n=12475, mean=0.0023414, min=0, max=3.99553, p50=0, p90=0, p99=0.0356873
  - penalty bins: [0,1e-06):96.07% [0.001,0.01):1.01% [0.01,0.1):2.57% [0.1,1):0.34% [1,10):0.02%

- **ac_sb3_0204_100753.log**
  - cfg: w_pen=0.25, dmax=400000, q=0.990, bins=64, min_count=1000
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.25<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=1000<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_scale=survival<br>q=0.990
  - penalty_data: n=12489, zero=167 (1.34%), hist=distinct=189 top10=16:2.12% 24:1.91% 22:1.89% 19:1.87% 15:1.87% 10:1.85% 20:1.83% 12:1.83% 17:1.83% 18:1.82%
  - immediate_reward: n=29158, mean=0.792273, min=0.015, max=1, p50=0.995, p90=1, p99=1
  - immediate_reward bins: [0,0.25):2.81% [0.25,0.5):14.26% [0.5,0.75):21.07% [0.75,1):61.86%
  - reward(before clip): n=12489, mean=-0.229277, min=-113.97, max=1, p50=0.43403, p90=0.907559, p99=1
  - final_reward(after clip): n=12489, mean=0.2526, min=-1, max=1, clip_sat=11.71%, p50=0.43403, p90=0.907559, p99=1
  - final_reward bins: [-1,-0.75):12.84% [-0.75,-0.5):3.30% [-0.5,-0.25):4.90% [-0.25,0):7.46% [0,0.25):10.42% [0.25,0.5):15.57% [0.5,0.75):19.95% [0.75,1):25.57%
  - penalty(weighted): n=12489, mean=0.501017, min=0, max=75.7348, p50=0.175557, p90=0.768441, p99=6.78405
  - penalty bins: [0,1e-06):1.35% [1e-05,0.0001):0.01% [0.0001,0.001):0.11% [0.001,0.01):1.23% [0.01,0.1):26.73% [0.1,1):63.42% [1,10):6.57% [10,100):0.60%

- **ac_sb3_0204_101659.log**
  - cfg: w_pen=0.25, formula=centered, dmax=400000, q=0.900, bins=64, min_count=200
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.25<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=200<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_reward_formula=centered<br>penalty_scale=survival<br>q=0.900
  - penalty_data: n=12492, zero=174 (1.39%), hist=distinct=189 top10=20:2.03% 15:1.92% 19:1.91% 14:1.89% 11:1.85% 22:1.85% 12:1.82% 21:1.82% 13:1.80% 16:1.79%
  - immediate_reward: n=29158, mean=0.792318, min=0.015, max=1, p50=1, p90=1, p99=1
  - immediate_reward bins: [0,0.25):2.84% [0.25,0.5):14.14% [0.5,0.75):21.08% [0.75,1):61.94%
  - reward(before clip): n=12492, mean=-0.0245321, min=-154.279, max=1, p50=0.648563, p90=0.92073, p99=1
  - final_reward(after clip): n=12492, mean=0.434086, min=-1, max=1, clip_sat=8.67%, p50=0.648563, p90=0.92073, p99=1
  - final_reward bins: [-1,-0.75):8.71% [-0.75,-0.5):1.75% [-0.5,-0.25):2.62% [-0.25,0):4.77% [0,0.25):7.16% [0.25,0.5):12.36% [0.5,0.75):25.21% [0.75,1):37.42%
  - penalty(weighted): n=12492, mean=0.512266, min=0, max=77.6396, p50=0.175719, p90=0.781399, p99=7.07514
  - penalty bins: [0,1e-06):1.52% [0.0001,0.001):0.02% [0.001,0.01):1.22% [0.01,0.1):27.00% [0.1,1):63.09% [1,10):6.48% [10,100):0.67%

- **ac_sb3_0204_102313.log**
  - cfg: w_pen=0.10, formula=centered, dmax=400000, q=0.900, bins=64, min_count=200
  - params: LOH_ENABLE_PENALTY=1<br>LOH_PENALTY_MODE/LOH_PENALTY_SCALE=survival<br>LOH_REWARD_USE_PENALTY=1<br>LOH_REWARD_W_PENALTY=0.10<br>bins=64<br>byte_penalty=0.000<br>dmax=400000<br>min_count=200<br>obj_penalty=1.000<br>penalty_entry_size=32<br>penalty_reward_formula=centered<br>penalty_scale=survival<br>q=0.900
  - penalty_data: n=12492, zero=174 (1.39%), hist=distinct=193 top10=14:1.96% 22:1.93% 18:1.91% 13:1.90% 20:1.86% 11:1.84% 19:1.84% 24:1.83% 12:1.78% 15:1.78%
  - immediate_reward: n=29158, mean=0.792345, min=0.015, max=1, p50=1, p90=1, p99=1
  - immediate_reward bins: [0,0.25):2.81% [0.25,0.5):14.26% [0.5,0.75):20.93% [0.75,1):62.00%
  - reward(before clip): n=12492, mean=-0.036828, min=-203.639, max=1, p50=0.650228, p90=0.921463, p99=1
  - final_reward(after clip): n=12492, mean=0.432927, min=-1, max=1, clip_sat=8.78%, p50=0.650228, p90=0.921463, p99=1
  - final_reward bins: [-1,-0.75):8.78% [-0.75,-0.5):1.78% [-0.5,-0.25):2.99% [-0.25,0):4.33% [0,0.25):7.00% [0.25,0.5):12.36% [0.5,0.75):25.04% [0.75,1):37.73%
  - penalty(weighted): n=12492, mean=0.518414, min=0, max=102.32, p50=0.174886, p90=0.791464, p99=6.95383
  - penalty bins: [0,1e-06):1.49% [0.0001,0.001):0.04% [0.001,0.01):1.30% [0.01,0.1):27.17% [0.1,1):62.71% [1,10):6.66% [10,100):0.62% [100,1000):0.01%
