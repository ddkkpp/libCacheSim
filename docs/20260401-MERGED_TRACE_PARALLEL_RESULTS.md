# 1063+Meta 合并 Trace 并行测试结果（快照）

- 生成时间: 2026-04-01
- Trace: `/mnt/serverpool/dingkp_trace/1063_meta_concat.oracleGeneral.zst`
- Trace type: `oracleGeneral`
- Cache size: `0.1`
- 算法集合: `acmaes, aipop, abipop, ipop, bipop, LRU, GDSF, S3FIFO, 3LCache`
- 说明: 用户输入 `bipip` 按 `bipop` 执行
- 原始运行目录: `tmp/20260401-merge-9alg-parallel/`

| algo | family | status | miss_ratio | byte_miss_ratio | mqps | log |
|---|---|---|---:|---:|---:|---|
| acmaes | loh | ok | 0.003207 | 0.002335 | 1.77 | tmp/20260401-merge-9alg-parallel/logs/loh_acmaes.log |
| aipop | loh | ok | 0.003207 | 0.002335 | 2.11 | tmp/20260401-merge-9alg-parallel/logs/loh_aipop.log |
| abipop | loh | ok | 0.003207 | 0.002335 | 1.61 | tmp/20260401-merge-9alg-parallel/logs/loh_abipop.log |
| ipop | loh | ok | 0.003207 | 0.002335 | 1.91 | tmp/20260401-merge-9alg-parallel/logs/loh_ipop.log |
| bipop | loh | ok | 0.003207 | 0.002335 | 1.92 | tmp/20260401-merge-9alg-parallel/logs/loh_bipop.log |
| LRU | baseline | ok | 0.003207 | 0.002335 | 4.88 | tmp/20260401-merge-9alg-parallel/logs/base_LRU.log |
| S3FIFO | baseline | ok | 0.003207 | 0.002335 | 5.96 | tmp/20260401-merge-9alg-parallel/logs/base_S3FIFO.log |
| 3LCache | baseline | ok | 0.003207 | 0.002335 | 1.71 | tmp/20260401-merge-9alg-parallel/logs/base_3LCache.log |
| GDSF | baseline | ok | 0.003207 | 0.002335 | 0.70 | tmp/20260401-merge-9alg-parallel/logs/base_GDSF.log |

## 备注

- 并行主脚本已完成，完整自动汇总见: `tmp/20260401-merge-9alg-parallel/docs/20260401-merge-9alg-results.md`。

## 合并有效性核对

- `zstd -lv` 核对显示:
	- `1063.oracleGeneral.zst` 解压字节 `8663052288`，按 `24` 字节/请求换算为 `360960512` 请求。
	- `meta_reag.oracleGeneral.zst` 解压字节 `1094959344`，按 `24` 字节/请求换算为 `45623306` 请求。
	- `1063_meta_concat.oracleGeneral.zst` 解压字节 `9758011632`，按 `24` 字节/请求换算为 `406583818` 请求。
	- 且该合并文件是 `2` 个 zstd frame。
- 本次并行日志中已完成算法（例如 `LRU`、`acmaes`）都显示 `360960512 req`，与 `1063` 单 trace 请求数完全一致。
- 现象解释（对应你看到的 `working set size` 变大）:
	- `cli_reader_utils` 的 working set 估计阶段会扫描到更多内容，因此在合并文件上估计值显著增大。
	- 但后续实际仿真统计中的 `total req` 仍停在 `360960512`，说明仿真主读取路径没有完整消费到第二段请求。
- 已确认根因（不是简单“文件没拼上”）:
	- `sim.c` 会先做 `req->clock_time -= start_ts`，其中 `start_ts` 取第一条请求的时间戳。
	- 合并后第二段（meta）时间戳从很小值重新开始，减去第一段的 `start_ts` 后变为负数。
	- 在默认 `warmup=-1 sec` 下，这些负时间戳请求会落入 warmup 分支并被跳过统计，因此最终 `req` 仍是第一段的 `360960512`。
	- 这也解释了“working set 变大但最终 req 没增长”的反常组合。
- 结论:
	- 这个“cat 拼接版”文件在物理上确实包含了 `1063+meta` 两段数据。
	- 但当前 `cachesim` 实际只消费了第一个 frame（即 `1063` 段），没有完整读到第二个 frame（`meta` 段）。
