#!/usr/bin/env bash
# ==========================================================================
# LOH Comprehensive Batch Experiment
# Step 1: 6 configs × 3 traces (full req)
# Step 2: Structured-only with decay grid search (3M first, full for best)
# Step 3: Penalty testing (requires source edit + rebuild)
# Step 4: MISS_RATIO_WEIGHT sweep
# ==========================================================================
set -euo pipefail
cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"

RESULT_DIR="tmp/batch_$(date +%m%d_%H%M%S)"
mkdir -p "$RESULT_DIR"
SUMMARY="$RESULT_DIR/summary.csv"
echo "step,config,trace,req,mr,byte_mr,mqps,wall_time_s" > "$SUMMARY"
BATCH_LOG="$RESULT_DIR/batch.log"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$BATCH_LOG"; }

# ---------- Traces ----------
TRACES=(
  "data/TencentCBS/1063.oracleGeneral.zst"
  "data/WikiCDN/wiki_2019t.oracleGeneral.zst"
  "data/MetaCDN/meta_reag.oracleGeneral.zst"
)
TRACE_NAMES=("1063" "wiki" "meta")
TRACE_LOG1P=("1" "0" "1")
TRACE_RECIP=("0" "1" "0")

# ---------- Common env ----------
set_common_env() {
  export LOH_WAIT_MODE=nonblocked
  export LOH_ENABLE_SEMAPHORE=1
  export LOH_SCORE_USE_COMPOUND=1
  export LOH_SCORE_USE_IRT=0
  export LOH_BUILD_RELEASE=1
  export LOH_SKIP_BUILD=1
  export LOH_SKIP_PIP_INSTALL=1
  export LOH_ADAPTIVE_BUDGET=1
}

# ---------- Run one test ----------
run_one_test() {
  local step="$1" config_name="$2" trace_idx="$3" num_req="$4"
  local trace="${TRACES[$trace_idx]}"
  local tname="${TRACE_NAMES[$trace_idx]}"
  local tag="${step}_${config_name}_${tname}_$(date +%H%M%S)"

  export LOH_FEATURE_LOG1P="${TRACE_LOG1P[$trace_idx]}"
  export LOH_FEATURE_LOG1P_RECIPROCAL="${TRACE_RECIP[$trace_idx]}"

  # Handle num_req: 0 = all
  if [[ "$num_req" == "0" ]]; then
    export CACHESIM_NUM_REQ=0
  else
    export CACHESIM_NUM_REQ="$num_req"
  fi

  log "START $tag (req=$num_req, async=${LOH_ASYNC_TRAIN:-0}, struct=${LOH_STRUCTURED_CANDIDATES:-96}, rand=${LOH_RANDOM_CANDIDATES:-0}, decay=${LOH_TAIL_SAMPLE:-0}/${LOH_TAIL_SAMPLE_DECAY:-N/A}, mrw=${LOH_MISS_RATIO_WEIGHT:-1.0})"

  # Kill stale processes
  pkill -f "loh_actor_critic" 2>/dev/null || true
  pkill -f "cachesim.*LOH" 2>/dev/null || true
  rm -f /dev/shm/loh_ac_* 2>/dev/null || true
  sleep 3

  local start_ts=$(date +%s)
  # Call test_loh_rl_sb3.sh directly
  bash scripts/test_loh_rl_sb3.sh "$trace" 0.1 \
    > "$RESULT_DIR/${tag}_run.log" 2>&1 || true
  local end_ts=$(date +%s)
  local wall=$((end_ts - start_ts))

  # Extract results from cachesim log (latest)
  local cslog=$(ls -1t cachesim_sb3_*.log 2>/dev/null | head -1)
  if [[ -n "$cslog" ]]; then
    local line=$(grep "miss ratio" "$cslog" | tail -1)
    local mr=$(echo "$line" | grep -oP 'miss ratio \K[0-9.]+' | head -1)
    local bmr=$(echo "$line" | grep -oP 'byte miss ratio \K[0-9.]+')
    local mqps=$(echo "$line" | grep -oP '[0-9.]+ MQPS' | grep -oP '[0-9.]+')
    local req=$(echo "$line" | grep -oP '[0-9]+ req' | grep -oP '[0-9]+')
    echo "${step},${config_name},${tname},${req:-0},${mr:-N/A},${bmr:-N/A},${mqps:-N/A},${wall}" >> "$SUMMARY"
    log "DONE  $tag -> MR=${mr:-N/A} BMR=${bmr:-N/A} MQPS=${mqps:-N/A} (${wall}s)"
    mv "$cslog" "$RESULT_DIR/${tag}_cachesim.log" 2>/dev/null || true
    local pylog=$(ls -1t ac_sb3_*.log 2>/dev/null | head -1)
    [[ -n "$pylog" ]] && mv "$pylog" "$RESULT_DIR/${tag}_python.log" 2>/dev/null || true
  else
    echo "${step},${config_name},${tname},0,FAIL,FAIL,FAIL,${wall}" >> "$SUMMARY"
    log "FAIL  $tag (${wall}s)"
  fi

  # Post-cleanup
  pkill -f "loh_actor_critic" 2>/dev/null || true
  pkill -f "cachesim.*LOH" 2>/dev/null || true
  sleep 2
}

# ---------- Rebuild ----------
rebuild_release() {
  log "Rebuilding release binary..."
  cd "$PROJECT_ROOT/_build_rel"
  ninja -j$(nproc) 2>&1 | tail -5
  cd "$PROJECT_ROOT"
  log "Rebuild done."
}

# ==========================================================================
log "================================================================="
log "  LOH BATCH EXPERIMENT START"
log "  Results: $RESULT_DIR"
log "================================================================="

########################################
# STEP 1: 6 configs x 3 traces (full)
########################################
log ""
log "===== STEP 1: 6 configs x 3 traces (full req) ====="

configs_step1=(
  "randonly96_sync:0:0:96:0:"
  "randonly96_async:1:0:96:0:"
  "rand96_struct96_decay_sync:0:96:96:1:0.99"
  "rand96_struct96_decay_async:1:96:96:1:0.99"
  "rand96_struct96_nodecay_sync:0:96:96:0:"
  "rand96_struct96_nodecay_async:1:96:96:0:"
)
# Format: name:async:struct:rand:tailsample:decay

for cfg_str in "${configs_step1[@]}"; do
  IFS=':' read -r cname casync cstruct crand ctail cdecay <<< "$cfg_str"
  set_common_env
  export LOH_ASYNC_TRAIN="$casync"
  export LOH_STRUCTURED_CANDIDATES="$cstruct"
  export LOH_RANDOM_CANDIDATES="$crand"
  export LOH_TAIL_SAMPLE="$ctail"
  if [[ -n "$cdecay" ]]; then
    export LOH_TAIL_SAMPLE_DECAY="$cdecay"
  else
    unset LOH_TAIL_SAMPLE_DECAY 2>/dev/null || true
  fi
  for i in 0 1 2; do
    run_one_test "s1" "$cname" "$i" "0"
  done
done

log ""
log "===== STEP 1 COMPLETE ====="
log "Step 1 results:"
grep "^s1," "$SUMMARY" | tee -a "$BATCH_LOG"

########################################
# STEP 2: Decay structured-only grid search (3M first)
########################################
log ""
log "===== STEP 2: Decay structured-only grid search (3M) ====="

set_common_env
export LOH_ASYNC_TRAIN=1
export LOH_RANDOM_CANDIDATES=0

for sc in 32 64 96 128 192; do
  for decay in 0.90 0.95 0.99 0.999; do
    export LOH_STRUCTURED_CANDIDATES=$sc
    export LOH_TAIL_SAMPLE=1
    export LOH_TAIL_SAMPLE_DECAY=$decay
    cname="structonly_sc${sc}_d${decay}"
    for i in 0 1 2; do
      run_one_test "s2_3M" "$cname" "$i" "3000000"
    done
  done
done

log ""
log "===== STEP 2 (3M) COMPLETE ====="
log "Step 2 (3M) results by avg MR:"
tail -n +2 "$SUMMARY" | grep "^s2_3M," | \
  awk -F, '$5 != "N/A" && $5 != "FAIL" {
    configs[$2]+=$5; counts[$2]++
  } END {
    for(c in configs) printf "  %s avg_mr=%.6f\n", c, configs[c]/counts[c]
  }' | sort -t= -k2 -n | head -10 | tee -a "$BATCH_LOG"

# Get top 3 config names for full trace
BEST_CONFIGS=$(tail -n +2 "$SUMMARY" | grep "^s2_3M," | \
  awk -F, '$5 != "N/A" && $5 != "FAIL" {
    configs[$2]+=$5; counts[$2]++
  } END {
    for(c in configs) printf "%s %.6f\n", c, configs[c]/counts[c]
  }' | sort -k2 -n | head -3 | awk '{print $1}')

log ""
log "===== STEP 2: Full trace for top 3 configs ====="
for cfg in $BEST_CONFIGS; do
  sc=$(echo "$cfg" | grep -oP 'sc\K[0-9]+')
  decay=$(echo "$cfg" | grep -oP 'd\K[0-9.]+')
  set_common_env
  export LOH_ASYNC_TRAIN=1
  export LOH_RANDOM_CANDIDATES=0
  export LOH_STRUCTURED_CANDIDATES=$sc
  export LOH_TAIL_SAMPLE=1
  export LOH_TAIL_SAMPLE_DECAY=$decay
  for i in 0 1 2; do
    run_one_test "s2_full" "$cfg" "$i" "0"
  done
done

log ""
log "===== STEP 2 COMPLETE ====="

########################################
# STEP 3: Penalty testing (requires source rebuild)
########################################
log ""
log "===== STEP 3: Penalty testing ====="

# Enable penalty: edit source
LOH_C="$PROJECT_ROOT/libCacheSim/cache/eviction/LOH.c"
log "Enabling LOH_ENABLE_PENALTY in source..."
sed -i 's/#define LOH_ENABLE_PENALTY 0/#define LOH_ENABLE_PENALTY 1/' "$LOH_C"
rebuild_release

# Use best config from step 1 (rand96+struct96+decay+async)
set_common_env
export LOH_ASYNC_TRAIN=1
export LOH_STRUCTURED_CANDIDATES=96
export LOH_RANDOM_CANDIDATES=96
export LOH_TAIL_SAMPLE=1
export LOH_TAIL_SAMPLE_DECAY=0.99

for penalty_positive in 0 1; do
  export LOH_PENALTY_SEND_POSITIVE=$penalty_positive
  cname="penalty_pos${penalty_positive}"
  for i in 0 1 2; do
    run_one_test "s3" "$cname" "$i" "0"
  done
done

# Revert penalty
log "Reverting LOH_ENABLE_PENALTY..."
sed -i 's/#define LOH_ENABLE_PENALTY 1/#define LOH_ENABLE_PENALTY 0/' "$LOH_C"
rebuild_release
unset LOH_PENALTY_SEND_POSITIVE 2>/dev/null || true

log ""
log "===== STEP 3 COMPLETE ====="

########################################
# STEP 4: MISS_RATIO_WEIGHT sweep
########################################
log ""
log "===== STEP 4: MISS_RATIO_WEIGHT sweep ====="

set_common_env
export LOH_ASYNC_TRAIN=1
export LOH_STRUCTURED_CANDIDATES=96
export LOH_RANDOM_CANDIDATES=96
export LOH_TAIL_SAMPLE=1
export LOH_TAIL_SAMPLE_DECAY=0.99

for mrw in 0.0 0.25 0.5 0.75 1.0; do
  export LOH_MISS_RATIO_WEIGHT=$mrw
  cname="mrw_${mrw}"
  for i in 0 1 2; do
    run_one_test "s4" "$cname" "$i" "0"
  done
done
unset LOH_MISS_RATIO_WEIGHT 2>/dev/null || true

log ""
log "===== STEP 4 COMPLETE ====="

########################################
# Final summary
########################################
log ""
log "================================================================="
log "  ALL EXPERIMENTS COMPLETE - $(date)"
log "  Results: $RESULT_DIR/summary.csv"
log "================================================================="
log ""
log "Full results:"
cat "$SUMMARY" | tee -a "$BATCH_LOG"

# Generate markdown summary
{
echo "# LOH Batch Experiment Results"
echo ""
echo "## Summary Table"
echo ""
echo "| Step | Config | Trace | Requests | MR | Byte MR | MQPS | Time (s) |"
echo "|------|--------|-------|----------|----|---------|------|----------|"
tail -n +2 "$SUMMARY" | while IFS=, read -r step cfg trace req mr bmr mqps wall; do
  echo "| $step | $cfg | $trace | $req | $mr | $bmr | $mqps | $wall |"
done
} > "$RESULT_DIR/RESULTS.md"

log "Markdown summary: $RESULT_DIR/RESULTS.md"
