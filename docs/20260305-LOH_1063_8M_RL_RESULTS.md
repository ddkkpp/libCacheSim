# LOH 1063 8M RL Test Results (2026-03-05)

## 测试配置
- **Trace**: data/TencentCBS/1063.oracleGeneral.zst
- **Cache size**: 0.1 (3GiB)
- **Requests**: 8,000,000
- **Build**: release (_build_rel, -O2 -DNDEBUG -DG_DISABLE_ASSERT)
- **Feature mode**: LOG1P (auto-detected, score=-0.3475)
- **Score mode**: COMPOUND (USE_IRT=0, USE_COMPOUND=1)
- **Candidates**: 96 regular + 64 random sampling (RSC)
- **State dims**: CONTEXT_DIM=2, STATE_DIM=2

## 关键结果
| 指标             | 值              | 历史最佳    | 差异     |
|-----------------|-----------------|------------|---------|
| Miss ratio      | **0.173779**    | 0.1748     | -0.001（改善） |
| Byte miss ratio | 0.216756        | —          | —       |
| RL throughput   | 0.01 MQPS       | —          | RL训练期间 |

## Size 非排序优化评估
- 旧版：selection sort O(k×n) 从所有桶收集最大对象
- 新版：直接从最高桶向下取对象（skip sort）  
- **结论：miss ratio 0.1738 ≤ 0.1748，优化无负面影响**

## Python 端时间分解（总 684.5s）
| 阶段                    | 耗时(s)   | 占比    |
|------------------------|----------|---------|
| SAC.train_total        | 485.07   | 71.0%   |
| rollout.phase_total    | 195.80   | 28.7%   |
| └ env.step_total       | 83.12    | 42.4% of rollout |
| └── wait_new_state     | 61.29    | 31.3% of rollout |
| └── write_weights      | 7.83     | 4.0%    |
| └── wait_ready         | 1.70     | 0.9%    |
| └── read_shm           | 1.68     | 0.9%    |
| └── softmax            | 2.60     | 1.3%    |
| └── misc               | 6.12     | 3.1%    |
| └ rollout.other (SB3)  | 112.69   | 57.6% of rollout |
| learn.overhead         | 1.93     | 0.3%    |

## C 端 profiling（1063 100K debug build, 参考）
以下来自 /tmp/loh_1063_100k_prof.txt
| 阶段              | 耗时(s)  | 占比     |
|-------------------|---------|---------|
| LOH_total         | 2.917   | 100%    |
| evict_total       | 2.848   | 97.64%  |
| calc_features     | 1.048   | 37.91%  |
| to_evict_misc     | 0.992   | 35.87%  |
| calc_score        | 0.558   | 20.17%  |
| size_collect      | 0.047   | 1.69%   |
| freq_collect      | 0.078   | 2.81%   |
| recency_collect   | 0.043   | 1.54%   |
| IRT heaps         | 0       | 0%      |

### 优化前（size_collect占40%）→ 优化后（1.69%）= 8.1×

## 独立吞吐量（release build, meta 1M，无 RL）
| 算法      | MQPS  |
|----------|-------|
| LOH 96候选 | 0.21-0.23 |
| LOH 48候选 | 0.36   |
| 3LCache   | 0.12   |
| GDSF      | 1.14   |
| LRU       | 3.60   |

## SB3 训练统计
- n_updates: 2262 (最终)
- Final weights: [0.117, 0.103, 0.376, 0.087, 0.164, 0.154, 0]
- Mean reward: ~0.8-0.9

## 日志文件
- cachesim: cachesim_sb3_0305_174034.log
- Python AC: ac_sb3_0305_174034.log
