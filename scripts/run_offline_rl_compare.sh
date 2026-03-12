#!/usr/bin/env bash
set -euo pipefail

BASE="runs/teacher_rl_singletrace_clean_$(date +%m%d_%H%M%S)"
mkdir -p "$BASE"

echo "BASE=$BASE"

run_one() {
  local name="$1"
  local csv="$2"
  local trace="$3"
  local wfile="$BASE/${name}_weights.txt"
  local tlog="$BASE/${name}_train.log"
  local elog="$BASE/${name}_eval.log"

  echo "[RUN] train $name"
  LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=0 LOH_FEATURE_LOG1P=1 LOH_USE_HEURISTIC_SIGNS=1 \
  python3 -u scripts/train_loh_teacher_ranker_rl.py \
    --csv "$csv" \
    --out "$wfile" \
    --episodes 2000 \
    --batch-groups 512 \
    --lr 0.003 \
    --weight-decay 0.0 \
    --seed 42 \
    --entropy-coef 0.01 \
    --baseline-momentum 0.95 \
    --reward-mode hard \
    --temperature 1.0 \
    --eval-interval 200 \
    --l1-lambda 1e-5 \
    --nonnegative \
    --l1-normalize \
    --eval-final-top1 \
    > "$tlog" 2>&1

  local w
  w=$(cat "$wfile")

  echo "[RUN] eval $name"
  LOH_ENABLE_RL=0 \
  LOH_FIXED_WEIGHTS="$w" \
  LOH_SCORE_USE_COMPOUND=1 \
  LOH_SCORE_USE_IRT=0 \
  LOH_FEATURE_LOG1P=1 \
  LOH_ENABLE_FEATURE_NORMALIZATION=1 \
  LOH_FEATURE_LOG1P_RECIPROCAL=0 \
  LOH_USE_HEURISTIC_SIGNS=1 \
  _build_dbg/bin/cachesim "$trace" oracleGeneral LOH 0.1 \
    --eviction-params=miss-ratio-weight=1.0 --num-req=3000000 -v 1 \
    > "$elog" 2>&1

  local top1 mr
  top1=$(grep -a '\[final\] top1=' "$tlog" | tail -n 1 || true)
  mr=$(grep -a 'miss ratio' "$elog" | tail -n 1 || true)
  echo "$name|$top1|$mr" | tee -a "$BASE/summary.txt"
}

run_one 1063 runs/teacher_fixed_0228_121210/teacher_samples.csv data/TencentCBS/1063.oracleGeneral.zst
run_one wiki runs/teacher_fixed_0220_224240/teacher_samples.csv data/WikiCDN/wiki_2019t.oracleGeneral.zst
run_one meta runs/teacher_fixed_0217_144120/teacher_samples.csv data/MetaCDN/meta_reag.oracleGeneral.zst

echo "DONE"
cat "$BASE/summary.txt"
