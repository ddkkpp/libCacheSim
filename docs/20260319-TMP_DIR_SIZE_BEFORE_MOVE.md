# 20260319 tmp Directory Size Before Migration

本文件记录在将 tmp/ 一级目录整体迁移到 sweeps/ 之前的目录体积快照。

## 1. 统计来源

- 原始清单：sweeps/20260319-maintenance_indexes/20260319-tmp-dir-sizes-before.tsv
- 迁移映射：sweeps/20260319-tmp-migration-map.tsv
- 当前状态：tmp/ 已无一级子目录（目录已迁移完成）

## 2. 大目录（Top 10）

- 6.3G tmp/20260311-batch_0311_020224
- 2.6G tmp/20260312-penalty_verify
- 42M tmp/20260313-phase_ab_0312_223925
- 24M tmp/20260310-rl_wiki_nothreads1_0310_111641
- 19M tmp/20260313-adaptive_budget_orig3_0313_184729
- 12M tmp/20260318-td3_ex0_retest_full_0318
- 11M tmp/20260319-root_loose_files
- 8.8M tmp/20260310-rl_wiki_blocked_0310_113234
- 2.6M tmp/20260318-td3_ex0_lru_lfu_10m_0318
- 2.6M tmp/20260318-td3_ex0_retest_0318

## 3. 说明

- 该快照用于迁移前容量审计与后续归档追溯。
- 完整目录级别明细请直接查看 TSV 原始文件。
