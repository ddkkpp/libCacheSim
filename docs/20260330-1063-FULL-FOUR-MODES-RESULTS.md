# 20260330 1063 全量四模式结果

## 实验矩阵

- Trace: /mnt/serverpool/dingkp_trace/tencentBlock/v2/else/tencentBlock_1063.oracleGeneral.zst
- 请求量: 全量 (360960512 req)
- 模式: blocked/nonblocked x penalty(0/1)
- semaphore: 开启

## 结果汇总 (首轮)

| 模式 | miss ratio | byte miss ratio | throughput |
|---|---:|---:|---:|
| blocked + penalty=0 | 0.023998 | 0.025334 | 0.11 MQPS |
| blocked + penalty=1 | 0.023890 | 0.025201 | 0.10 MQPS |
| nonblocked + penalty=0 | 0.022619 | 0.023859 | 0.55 MQPS |
| nonblocked + penalty=1 | 0.022352 | 0.023609 | 0.56 MQPS |

## 效果结论

- nonblocked 相比 blocked 在 penalty=0 时更优: miss ratio 下降约 5.75%。
- nonblocked 相比 blocked 在 penalty=1 时更优: miss ratio 下降约 6.44%。
- penalty 在 blocked 下有效: miss ratio 从 0.023998 降到 0.023890 (约 0.45%)。
- penalty 在 nonblocked 下有效: miss ratio 从 0.022619 降到 0.022352 (约 1.18%)。

## penalty 相关配置 (本轮)

- 显式设置: `LOH_ENABLE_PENALTY=1` (仅用于 penalty=1 两组)
- 对照组设置: `LOH_ENABLE_PENALTY=0` (penalty=0 两组)
- 其他 `LOH_PENALTY_*` 或 `LOH_REWARD_MIX_*` 参数: 本轮未额外显式设置，使用当前代码默认值。

## 四组通用配置 (本轮)

- `LOH_PARALLEL_SAFE=1`
- `LOH_BUILD_RELEASE=1`
- `LOH_SKIP_BUILD=1`
- `LOH_SKIP_PIP_INSTALL=1`
- `LOH_ENABLE_SEMAPHORE=1`
- `LOH_DISABLE_SEMAPHORE=0`
- `CACHESIM_NUM_REQ=0` (脚本转换为 ALL requests)
- `cache_size=0.1`
- `eviction=LOH`

## 日志索引

- blocked + penalty=0: tmp/20260330-1063-full-four-modes/logs/run_blocked_pen0_sem_full.log
- blocked + penalty=1: tmp/20260330-1063-full-four-modes/logs/run_blocked_pen1_sem_full.log
- nonblocked + penalty=0: tmp/20260330-1063-full-four-modes/logs/run_nonblocked_pen0_sem_full.log
- nonblocked + penalty=1: tmp/20260330-1063-full-four-modes/logs/run_nonblocked_pen1_sem_full.log
