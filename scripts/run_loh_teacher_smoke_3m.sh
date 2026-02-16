#!/bin/bash
set -euo pipefail

TRACE_FILE="${1:-data/WikiCDN/wiki_2019t.oracleGeneral.zst}"
CACHE_SIZE="${2:-0.1}"
NUM_REQ="${CACHESIM_NUM_REQ:-3000000}"
MISS_RATIO_WEIGHT="${LOH_MISS_RATIO_WEIGHT:-1.0}"

if [ ! -f "$TRACE_FILE" ]; then
  echo "[error] trace not found: $TRACE_FILE"
  exit 1
fi

TS="$(date +%m%d_%H%M%S)"
RUN_DIR="runs/teacher_smoke_${TS}"
mkdir -p "$RUN_DIR"
TEACHER_CSV="$RUN_DIR/teacher_samples.csv"
TEACHER_W="$RUN_DIR/teacher_weights.txt"
TEACHER_LOG="$RUN_DIR/teacher_collect.log"

if [[ "$TRACE_FILE" == *.csv ]]; then
  TRACE_TYPE="csv"
  TRACE_TYPE_PARAMS=(--trace-type-params "time-col=1,obj-id-col=2,obj-size-col=3,obj-id-is-num=1,has-header=false,delimiter=,")
else
  TRACE_TYPE="oracleGeneral"
  TRACE_TYPE_PARAMS=()
fi

echo "[1/4] build debug binary"
bash scripts/debug.sh -c

echo "[2/4] collect Belady teacher labels (algo=loh-teacher, num-req=$NUM_REQ)"
export LOH_ENABLE_RL=0
export LOH_TEACHER_EXPORT_PATH="$TEACHER_CSV"
export LOH_TEACHER_EXPORT_APPEND=0

CACHESIM_CMD=(
  _build_dbg/bin/cachesim
  "$TRACE_FILE"
  "$TRACE_TYPE"
  "loh-teacher"
  "$CACHE_SIZE"
  "--eviction-params=miss-ratio-weight=$MISS_RATIO_WEIGHT"
  "--num-req=$NUM_REQ"
  -v 0
)
if [ ${#TRACE_TYPE_PARAMS[@]} -ne 0 ]; then
  CACHESIM_CMD+=("${TRACE_TYPE_PARAMS[@]}")
fi

printf '  cmd:'; printf ' %q' "${CACHESIM_CMD[@]}"; echo
"${CACHESIM_CMD[@]}" >"$TEACHER_LOG" 2>&1

if [ ! -s "$TEACHER_CSV" ]; then
  echo "[error] teacher csv not generated: $TEACHER_CSV"
  echo "[hint] check log: $TEACHER_LOG"
  exit 1
fi

echo "[3/4] train imitation ranker from teacher csv"
python3 scripts/train_loh_teacher_ranker.py \
  --csv "$TEACHER_CSV" \
  --out "$TEACHER_W" \
  --epochs "${LOH_TEACHER_EPOCHS:-20}" \
  --batch-groups "${LOH_TEACHER_BATCH_GROUPS:-256}" \
  --lr "${LOH_TEACHER_LR:-0.01}" \
  --weight-decay "${LOH_TEACHER_WEIGHT_DECAY:-1e-6}" \
  --seed "${LOH_SEED:-42}"

LOH_FIXED_WEIGHTS="$(cat "$TEACHER_W")"
if [ -z "$LOH_FIXED_WEIGHTS" ]; then
  echo "[error] empty trained weights file: $TEACHER_W"
  exit 1
fi

echo "[4/4] RL smoke run with teacher-initialized weights (num-req=$NUM_REQ)"
unset LOH_TEACHER_EXPORT_PATH
unset LOH_TEACHER_EXPORT_APPEND
export LOH_ENABLE_RL=1
export LOH_EVICTION_ALGO="loh-teacher"
export LOH_FIXED_WEIGHTS
export CACHESIM_NUM_REQ="$NUM_REQ"

bash scripts/test_loh_rl_sb3.sh "$TRACE_FILE" "$CACHE_SIZE"

echo "[done] teacher smoke finished"
echo "  teacher_csv: $TEACHER_CSV"
echo "  teacher_weights: $TEACHER_W"
echo "  teacher_collect_log: $TEACHER_LOG"
