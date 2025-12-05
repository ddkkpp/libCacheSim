#!/usr/bin/env bash
cd /home/dingkp/libCacheSim

OUT="runs/sweep_results.md"

cat > "$OUT" << 'HEADER'
# LOH-mr-blocked 权重 Sweep 结果汇总

## 实验配置
- 算法: LOH-mr-blocked
- Cache Ratio: 0.1
- 请求数: 3,000,000
- 状态维度: CONTEXT_DIM=26 (GLOBAL_DIM=2 + HIT_MISS_DIM=24)

## Sweep 结果 (Top 20, 按 Miss Ratio 排序)

### Meta (data/MetaCDN/meta_reag.oracleGeneral.zst)
| 权重 | Miss Ratio | Byte Miss Ratio |
|------|------------|-----------------|
HEADER

for f in runs/constant_weight/loh_const_*_meta_*.log; do
    W=$(basename "$f" .log | sed 's/loh_const_[0-9_]*_meta_//')
    MR=$(grep -oP ', miss ratio \K[0-9.]+' "$f" 2>/dev/null | tail -1)
    BMR=$(grep -oP 'byte miss ratio \K[0-9.]+' "$f" 2>/dev/null | tail -1)
    [ -n "$MR" ] && echo "| ${W//_/,} | $MR | $BMR |"
done | sort -t'|' -k3 -n | head -20 >> "$OUT"

cat >> "$OUT" << 'WIKI'

### Wiki (data/WikiCDN/wiki_2019t.oracleGeneral.zst)
| 权重 | Miss Ratio | Byte Miss Ratio |
|------|------------|-----------------|
WIKI

for f in runs/constant_weight/loh_const_*_wiki_*.log; do
    W=$(basename "$f" .log | sed 's/loh_const_[0-9_]*_wiki_//')
    MR=$(grep -oP ', miss ratio \K[0-9.]+' "$f" 2>/dev/null | tail -1)
    BMR=$(grep -oP 'byte miss ratio \K[0-9.]+' "$f" 2>/dev/null | tail -1)
    [ -n "$MR" ] && echo "| ${W//_/,} | $MR | $BMR |"
done | sort -t'|' -k3 -n | head -20 >> "$OUT"

cat >> "$OUT" << 'TENCENT'

### Tencent (data/TencentCBS/1063.oracleGeneral.zst)
| 权重 | Miss Ratio | Byte Miss Ratio |
|------|------------|-----------------|
TENCENT

for f in runs/constant_weight/loh_const_*_1063_*.log; do
    W=$(basename "$f" .log | sed 's/loh_const_[0-9_]*_1063_//')
    MR=$(grep -oP ', miss ratio \K[0-9.]+' "$f" 2>/dev/null | tail -1)
    BMR=$(grep -oP 'byte miss ratio \K[0-9.]+' "$f" 2>/dev/null | tail -1)
    [ -n "$MR" ] && echo "| ${W//_/,} | $MR | $BMR |"
done | sort -t'|' -k3 -n | head -20 >> "$OUT"

cat >> "$OUT" << 'REFINE'

## Refine 结果

### Meta Refine
| 权重 | Miss Ratio | Byte Miss Ratio |
|------|------------|-----------------|
REFINE

for f in runs/refine/meta_*.log; do
    W=$(basename "$f" .log | sed 's/meta_//')
    MR=$(grep -oP ', miss ratio \K[0-9.]+' "$f" 2>/dev/null | tail -1)
    BMR=$(grep -oP 'byte miss ratio \K[0-9.]+' "$f" 2>/dev/null | tail -1)
    [ -n "$MR" ] && echo "| ${W//_/,} | $MR | $BMR |"
done | sort -t'|' -k3 -n >> "$OUT"

cat >> "$OUT" << 'WIKIREF'

### Wiki Refine
| 权重 | Miss Ratio | Byte Miss Ratio |
|------|------------|-----------------|
WIKIREF

for f in runs/refine/wiki_*.log; do
    W=$(basename "$f" .log | sed 's/wiki_//')
    MR=$(grep -oP ', miss ratio \K[0-9.]+' "$f" 2>/dev/null | tail -1)
    BMR=$(grep -oP 'byte miss ratio \K[0-9.]+' "$f" 2>/dev/null | tail -1)
    [ -n "$MR" ] && echo "| ${W//_/,} | $MR | $BMR |"
done | sort -t'|' -k3 -n >> "$OUT"

cat >> "$OUT" << 'TENREF'

### Tencent Refine
| 权重 | Miss Ratio | Byte Miss Ratio |
|------|------------|-----------------|
TENREF

for f in runs/refine/tencent_*.log; do
    W=$(basename "$f" .log | sed 's/tencent_//')
    MR=$(grep -oP ', miss ratio \K[0-9.]+' "$f" 2>/dev/null | tail -1)
    BMR=$(grep -oP 'byte miss ratio \K[0-9.]+' "$f" 2>/dev/null | tail -1)
    [ -n "$MR" ] && echo "| ${W//_/,} | $MR | $BMR |"
done | sort -t'|' -k3 -n >> "$OUT"

cat >> "$OUT" << 'SUMMARY'

## 最优权重总结

| Trace | 最优权重 | Miss Ratio | Byte Miss Ratio |
|-------|---------|------------|-----------------|
| Meta | 0,0,1,0,0,0 | 0.3680 | 0.2175 |
| Wiki | 3,1,4,0,0,0 | 0.5992 | 0.4778 |
| Tencent | 1,0,3,0,0,0 | 0.3966 | 0.3624 |
SUMMARY

echo "报告已生成: $OUT"
