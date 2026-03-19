# 20260319 Experiment Asset Index (Merged)

本文件是 20260318/20260319 资产索引与映射文档的合并版本，统一记录：
- 目录约定
- 脚本-产物-结论文档对应关系
- traceAnalyzer 产物位置
- 当前整理状态

## 1. 目录约定

- 文档：docs/YYYYMMDD-*.md
- 批量实验：sweeps/YYYYMMDD-*/
- 临时实验：tmp/YYYYMMDD-*/（当前已迁空，阶段产物统一收敛到 sweeps/）
- 运行日志：logs/ac_sb3_*.log, logs/cachesim_sb3_*.log
- 核心脚本：scripts/
- traceAnalyzer 默认产物目录：analysis/

## 2. 主要结论文档

- docs/20260317-FULL_EXPERIMENT_RESULTS.md
- docs/20260303-COMPREHENSIVE_EXPERIMENT_SUMMARY.md
- docs/20260131-LOH_CONSTANT_WEIGHTS_BEST_3M_WIKI2019T_1063.md
- docs/20251203-LOH_SCRIPTS_INTEGRATION_GUIDE.md
- docs/20260319-LOH_ENV_VARS.md
- docs/20260319-EXPERIMENTS_TO_DATE_SUMMARY.md

说明：`docs/20260319-EXPERIMENTS_TO_DATE_SUMMARY.md` 已更新为“先概括（按日期统计）再详细（逐条实验目录）”结构，当前覆盖 198 个实验目录。

## 3. 脚本-产物-结论映射

| 实验类别 | 入口脚本 | 主要产物位置 | 结论文档/索引 |
|---|---|---|---|
| 通用 RL sweep（SB3） | scripts/sweep_loh_rl_sb3.sh | sweeps/2025*/, sweeps/2026*/ | docs/20260317-FULL_EXPERIMENT_RESULTS.md |
| 1063 单/多策略升级 | scripts/run_1063_strategy_upgrade_single_seed.sh, scripts/run_1063_to_032_sprint.sh | sweeps/20260215-1063_stage2_upgrade_single_seed_*/, sweeps/20260215-1063_to032_*/ | docs/20260215-20260215_1063_to032_阶段总结与完成度.md |
| 1063 惩罚/奖励扫描 | scripts/run_1063_3mreq_penalty_sweep.sh, scripts/run_bestcfg_penalty_sweep_multitrace.sh | sweeps/20260206-1063_penalty_3m_*/, sweeps/20260211-bestcfg_penalty_3t_3m_*/ | docs/20260205-LOH_PENALTY_ANALYSIS.md |
| 多 trace 模式矩阵 | scripts/run_loh_modes2_multitrace_3m_mrw0.sh, scripts/run_loh_modes3_multitrace_3m.sh | sweeps/20260130-modes2_*/, sweeps/20260130-modes3_*/ | docs/20260303-COMPREHENSIVE_EXPERIMENT_SUMMARY.md |
| 非阻塞/异步对照 | scripts/run_nonblocked36.sh, scripts/run_async_nb_full.sh | sweeps/20260310-nonblocked36_*/, sweeps/20260310-async_nb_full*/ | docs/20260317-FULL_EXPERIMENT_RESULTS.md |
| 阶段 A/B 组合实验 | scripts/run_loh_phase_ab_experiments.sh | sweeps/20260313-phase_ab_*/, sweeps/20260314-sec20_*/ | docs/20260317-FULL_EXPERIMENT_RESULTS.md |
| trace 统计分析 | scripts/run_traceAnalyzer.sh | analysis/, sweeps/20260319-traceanalyzer/ | docs/20260319-EXPERIMENT_ASSET_INDEX.md |

## 4. traceAnalyzer 输出文件清单

traceAnalyzer 常见输出（默认落在 analysis/，文件前缀为 trace basename）：
- *.accessRtime
- *.accessVtime
- *.popularity
- *.popularityDecay_w300_req
- *.popularityDecay_w300_obj
- *.reqRate_w300
- *.reuse
- *.reuseWindow_w300_rt
- *.reuseWindow_w300_vt
- *.size
- *.sizeWindow_w300_obj
- *.sizeWindow_w300_req
- *.stat
- *.traceStat
- analysis/traceStat（聚合文本输出）

运行日志与辅助文件保持在：sweeps/20260319-traceanalyzer/

## 5. 当前整理状态（2026-03-19）

- 已完成：traceAnalyzer 产物 Output/、output/ 及根目录散落分析文件迁移到 analysis/
- 已完成：traceAnalyzer 默认输出路径切换为 analysis/
- 已完成：analysis 重复文件清理（已将 *.from_root_20260319_1 统一改回标准文件名并保留新版本内容）
- 已完成：sweeps 目录按 inferred_date 收敛完成（先重命名 6+20，再对 36 个冲突目录做重复校验后去重）
- 已完成：tmp 一级目录迁移到 sweeps（映射见 sweeps/20260319-tmp-migration-map.tsv）
- 当前状态：sweeps 一级目录已无未前缀目录；tmp 仅保留空目录供后续日志使用

## 6. 根目录分层（重要/非重要）

- 重要目录：libCacheSim/, scripts/, docs/, sweeps/, analysis/, logs/, data/
- 非重要目录：result/, results/, runs/, sb3_logs/, sb3_checkpoints/, training_logs/, tb_report/, tb_report_0203_probe/, copilot对话历史/, random/, .tmp/, _build/, _build_dbg/, _build_rel/

## 7. 维护索引

- tmp 迁移前目录体积：sweeps/20260319-maintenance_indexes/20260319-tmp-dir-sizes-before.tsv
- tmp 迁移映射：sweeps/20260319-tmp-migration-map.tsv
- tmp 体积说明文档：docs/20260319-TMP_DIR_SIZE_BEFORE_MOVE.md
- sweeps 前缀状态：sweeps/20260319-maintenance_indexes/20260319-sweeps-prefix-status.md
- sweeps 冲突报告：sweeps/20260319-maintenance_indexes/sweeps_prefix_conflict_report_clean_20260319.md
- 本轮迁移日志：sweeps/20260319-maintenance_indexes/20260319-move-and-rename.log
