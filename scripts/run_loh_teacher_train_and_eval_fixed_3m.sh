#!/bin/bash
set -euo pipefail

TRACE_FILE="${1:-data/MetaCDN/meta_reag.oracleGeneral.zst}"
CACHE_SIZE="${2:-0.1}"

NUM_REQ="${CACHESIM_NUM_REQ:-3000000}"
MISS_RATIO_WEIGHT="${LOH_MISS_RATIO_WEIGHT:-1.0}"

if [ ! -f "$TRACE_FILE" ]; then
  echo "[error] trace not found: $TRACE_FILE"
  exit 1
fi

# Optional: apply a known-good LOH config (feature toggles, penalty knobs, etc.)
# This config is applied consistently to: teacher collection + fixed-weight evaluation.
if [ -n "${LOH_CONFIG_STR:-}" ]; then
  # shellcheck disable=SC1090
  source <(python3 scripts/config_str_to_exports.py --config "${LOH_CONFIG_STR}")
elif [ -n "${LOH_CONFIG_FILE:-}" ]; then
  # shellcheck disable=SC1090
  source <(python3 scripts/config_str_to_exports.py --config-file "${LOH_CONFIG_FILE}")
fi

TS="$(date +%m%d_%H%M%S)"
RUN_DIR="runs/teacher_fixed_${TS}"
mkdir -p "$RUN_DIR"

TEACHER_CSV="$RUN_DIR/teacher_samples.csv"
TEACHER_W="$RUN_DIR/teacher_weights.txt"
TEACHER_LOG="$RUN_DIR/teacher_collect.log"
TRAIN_LOG="$RUN_DIR/teacher_train.log"
RANK_EVAL_LOG="$RUN_DIR/teacher_rank_eval.log"
EVAL_LOG="$RUN_DIR/fixed_eval.log"

echo "[1/4] build debug binary"
if [ "${LOH_SKIP_BUILD:-0}" = "1" ] && [ -x "_build_dbg/bin/cachesim" ]; then
  echo "  LOH_SKIP_BUILD=1 and binary exists, skip build"
else
  bash scripts/debug.sh -c
fi

echo "[2/4] collect Belady teacher labels (algo=loh-teacher, num-req=$NUM_REQ)"
export LOH_ENABLE_RL=0
export LOH_TEACHER_EXPORT_PATH="$TEACHER_CSV"
export LOH_TEACHER_EXPORT_APPEND=0
export LOH_TEACHER_EXPORT_MAX_ROWS="${LOH_TEACHER_EXPORT_MAX_ROWS:-800000}"
echo "  LOH_TEACHER_EXPORT_MAX_ROWS=$LOH_TEACHER_EXPORT_MAX_ROWS"

TRACE_TYPE="oracleGeneral"
if [[ "$TRACE_FILE" == *.csv ]]; then
  TRACE_TYPE="csv"
  TRACE_TYPE_PARAMS=(--trace-type-params "time-col=1,obj-id-col=2,obj-size-col=3,obj-id-is-num=1,has-header=false,delimiter=")
else
  TRACE_TYPE_PARAMS=()
fi

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
TRAIN_EXTRA_ARGS=()
if [ "${LOH_TEACHER_STREAM:-0}" = "1" ]; then
  TRAIN_EXTRA_ARGS+=(--stream)
  echo "  LOH_TEACHER_STREAM=1 (streaming training)"
fi
python3 scripts/train_loh_teacher_ranker.py \
  --csv "$TEACHER_CSV" \
  --out "$TEACHER_W" \
  --epochs "${LOH_TEACHER_EPOCHS:-20}" \
  --batch-groups "${LOH_TEACHER_BATCH_GROUPS:-256}" \
  --max-groups "${LOH_TEACHER_MAX_GROUPS:-200000}" \
  --lr "${LOH_TEACHER_LR:-0.01}" \
  --weight-decay "${LOH_TEACHER_WEIGHT_DECAY:-1e-6}" \
  --seed "${LOH_SEED:-42}" \
  "${TRAIN_EXTRA_ARGS[@]}" \
  2>&1 | tee "$TRAIN_LOG"

LOH_FIXED_WEIGHTS="$(cat "$TEACHER_W")"
if [ -z "$LOH_FIXED_WEIGHTS" ]; then
  echo "[error] empty trained weights file: $TEACHER_W"
  exit 1
fi

echo "[3.5/4] evaluate teacher-label ranking quality (Hit@K/MRR)"
RANK_CMD=(
  python3 scripts/eval_teacher_weight_ranking.py
  --csv "$TEACHER_CSV"
  --weight "teacher_trained=${LOH_FIXED_WEIGHTS}"
)
if [ -n "${LOH_COMPARE_FIXED_WEIGHTS:-}" ]; then
  RANK_CMD+=(--weight "compare_fixed=${LOH_COMPARE_FIXED_WEIGHTS}")
fi
printf '  cmd:'; printf ' %q' "${RANK_CMD[@]}"; echo
"${RANK_CMD[@]}" 2>&1 | tee "$RANK_EVAL_LOG"

echo "[4/4] evaluate fixed weights on same trace (algo=LOH, RL disabled)"
unset LOH_TEACHER_EXPORT_PATH
unset LOH_TEACHER_EXPORT_APPEND
unset LOH_TEACHER_EXPORT_MAX_ROWS
export LOH_ENABLE_RL=0
export LOH_FIXED_WEIGHTS

EVAL_CMD=(
  _build_dbg/bin/cachesim
  "$TRACE_FILE"
  "$TRACE_TYPE"
  "LOH"
  "$CACHE_SIZE"
  "--eviction-params=miss-ratio-weight=$MISS_RATIO_WEIGHT"
  "--num-req=$NUM_REQ"
  -v 1
)
if [ ${#TRACE_TYPE_PARAMS[@]} -ne 0 ]; then
  EVAL_CMD+=("${TRACE_TYPE_PARAMS[@]}")
fi

printf '  cmd:'; printf ' %q' "${EVAL_CMD[@]}"; echo
"${EVAL_CMD[@]}" >"$EVAL_LOG" 2>&1

echo "[done] teacher->fixed eval finished"
echo "  run_dir: $RUN_DIR"
echo "  teacher_csv: $TEACHER_CSV"
echo "  teacher_weights: $TEACHER_W"
echo "  teacher_collect_log: $TEACHER_LOG"
echo "  teacher_train_log: $TRAIN_LOG"
echo "  teacher_rank_eval_log: $RANK_EVAL_LOG"
echo "  fixed_eval_log: $EVAL_LOG"
