# 画图注意事项（cache-size=0.1 / v7_3lcache-target）

## 数据源目录

- 各组 markdown：`docs/20260422-ablation-per-group-cache01/cmaes版本LOH/<group>.md`
- 汇总 markdown：同目录下的 `robustness_summary_v7_3lcache-target.md`
- 基线汇总：同目录下的 `baseline_summary_v7_3lcache-target.md`

## 画图脚本

```
generate_plots.py   # 本文件同目录，原始位于 tmp/20260423-robustness-figures/generate_plots.py
```

重新生成方式：

```bash
cd /home/丁坤鹏/libcachesim_new
PATH="$PWD/.venv/bin:$PATH" python3 \
    tmp/20260506-robustness-figures-cache01-v7-3lcache-target/generate_plots.py
```

## 四类图的数据来源规则

### rank（排名折线图，8 张）

- 直接读 `robustness_summary_v7_3lcache-target.md` 中的 8 张"排名"表（`load_rank_md_data()`）。
- **不要自己从原始值重算排名**，排名表即最终权威来源。

### dual（双轴柱状图，4 张）

- 读 `robustness_summary_v7_3lcache-target.md` 中的 8 张 `Norm Score` 表。
- **排除 `cloudphysics`**，对剩余 6 组取均值。
- 4 张图对应：绝对值 / 加权 / 相对LRU / 加权相对LRU。

### box / percentile（箱线图、累积分布图，各 12/4 张）

- 数据来自各组 markdown 中的 per-trace 表。
- **`RSD`（代表 LOH 的最佳变体）必须按 v7 策略重选**，不能直接用表4/表5的 `best_LOH`：
  - `MR`：优先 `f001_orig`，缺失时回退 `f100_ns`
  - `BMR`：`one_hit ≤ 0.72` 用 `f100_ns`，否则用 `f101_orig`，缺失时回退 `f100_ns`

## 通用规则

- **四类图均排除 `cloudphysics`**（共 6 组：alibabaBlock / metaCDN / metaKV / tencentBlock / tencentPhoto / wiki）。
- 显示名：`ThreeLCache-target` → `3L-Cache`。
- 字体：Times New Roman（需安装 `msttcorefonts` 并由脚本 `addfont` 注册）。
- 坐标轴：线性轴，刻度步长 0.2，范围窄时降为 0.1，**必须包含 1.0 刻度**。
- rank 图：折线左侧写算法名（图框内），不用图例，标记点大小 12。
- percentile 图例：压缩为单行，间距缩小。
