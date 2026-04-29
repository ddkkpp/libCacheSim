# 20260330 多 pos 最终 reward 对账（源代码默认值）

## 1. 目的

- 按“仅改源代码默认值，不在脚本层覆盖”的要求，验证多个 pos 的 `finalize_pairwise_only` 最终值是否正确。
- 重点核对：`pair_count`、`signal` 与按事件逐项重算结果是否一致。

## 2. 前提与运行

- Python 日志：`logs/ac_sb3_0330_075811.log`
- 本次默认行为：`DEFAULT_LOH_PENALTY_REFINE_ON_LATE="0"`
- 脚本未再设置 `LOH_PENALTY_REFINE_ON_LATE` / `LOH_PAIRWISE_IMMEDIATE_FINALIZE` 默认覆盖。

## 3. 对账公式

- 单条事件项：

  $$
  term_i = \frac{kept\_life_i - evicted\_life_i}{\max(kept\_life_i + evicted\_life_i, 500)}
  $$

- 最终信号（均值）：

  $$
  signal = \frac{1}{N}\sum_{i=1}^{N} term_i
  $$

其中 $N$ 取 `finalize_pairwise_only` 打印的 `pair_count`。

## 4. 多 pos 核验结果

| pos | finalize pair_count | finalize signal | 同 pos 全量事件数 | 前 N 条均值（N=finalize pair_count） | 与 finalize 差值 | 全量均值 |
|---|---:|---:|---:|---:|---:|---:|
| 16 | 37 | 0.108413 | 97 | 0.108413 | 1.738262e-07 | 0.055515 |
| 41 | 501 | -0.267065 | 501 | -0.267065 | 2.410855e-07 | -0.267065 |
| 90 | 30 | 0.226407 | 60 | 0.226407 | 2.423691e-09 | 0.134449 |

## 5. 结论

- `finalize_pairwise_only` 的最终值计算是正确的：都与“前 N 条事件重算均值”一致（误差在浮点数量级）。
- 出现“全量均值 != finalize signal”的 pos（如 16、90）并非公式错误，而是 finalize 之后仍有晚到事件。
- 因本次默认 `refine_on_late=0`，晚到事件不会触发重算；因此最终值固定在 finalize 时刻已收到的那批事件上。

## 6. 复核命令（用于重跑对账）

```bash
py_log="logs/ac_sb3_0330_075811.log"
for pos in 16 41 90; do
  fin_line=$(rg --fixed-strings "finalize_pairwise_only pos=${pos} " "$py_log" | tail -n 1)
  fin_count=$(echo "$fin_line" | awk -F"pair_count=| signal=" '{print $2}' | awk '{print $1}')
  fin_signal=$(echo "$fin_line" | awk -F"signal=| final=" '{print $2}' | awk '{print $1}')
  rg --fixed-strings "pos=${pos} event_type=2" "$py_log" | awk -v N="$fin_count" -v POS="$pos" -v FIN="$fin_signal" '
  {
    if (match($0,/evicted_life=[0-9]+/)) {s=substr($0,RSTART,RLENGTH); sub("evicted_life=","",s); ev=s+0}
    if (match($0,/kept_life=[0-9]+/))    {s=substr($0,RSTART,RLENGTH); sub("kept_life=","",s); kp=s+0}
    den=ev+kp; if (den<500) den=500;
    term=(kp-ev)/den; cnt++; sum+=term; if (cnt<=N) sumN+=term;
  }
  END {
    mAll=(cnt?sum/cnt:0); mN=(N?sumN/N:0); d=FIN-mN; if(d<0)d=-d;
    printf("pos=%s finalize_count=%d total_events=%d finalize_signal=%.6f mean_firstN=%.6f abs_diff_firstN=%.6e mean_all=%.6f\n", POS, N, cnt, FIN+0, mN+0, d, mAll+0)
  }'
done
```
