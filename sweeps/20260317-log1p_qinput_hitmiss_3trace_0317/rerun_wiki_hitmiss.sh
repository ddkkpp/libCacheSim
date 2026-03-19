#!/usr/bin/env bash
set -u

cd /home/dingkp/libCacheSim || exit 1

OUT_DIR=tmp/log1p_qinput_hitmiss_3trace_0317
RUN_ID="$(date +%m%d_%H%M%S)"
LOG_PATH="$OUT_DIR/wiki_log1p_qinput_log1p_hitmiss_rerun_${RUN_ID}.log"
RESULTS_CSV="$OUT_DIR/results.csv"
DOC_PATH=docs/20260317-FULL_EXPERIMENT_RESULTS.md

echo "[prebuild] rebuild release with LOH_INCLUDE_HIT_MISS_FEATURES=1" >> "$OUT_DIR/runner.log"
(
  export LOH_BUILD_RELEASE=1
  export LOH_INCLUDE_HIT_MISS_FEATURES=1
  export LOH_SKIP_BUILD=0
  bash scripts/debug.sh -r
) >> "$OUT_DIR/prebuild_wiki_rerun.log" 2>&1 || {
  echo "[prebuild] failed, see $OUT_DIR/prebuild_wiki_rerun.log"
  exit 1
}

SHM_KEY=$(printf "%s" "wiki_hitmiss_rerun_$(date +%s%N)" | cksum | awk '{print $1}')
rm -f "/dev/shm/loh_ac_${SHM_KEY}" "/dev/shm/sem.loh_ac_ready_${SHM_KEY}" "/dev/shm/sem.loh_ac_ack_${SHM_KEY}"

(
  export LOH_SHM_KEY="$SHM_KEY"
  export RUN_TIMESTAMP="${RUN_ID}_wiki_hitmiss_rerun"
  export CACHESIM_NUM_REQ=0
  export LOH_PARALLEL_SAFE=1
  export LOH_ENABLE_SEMAPHORE=1
  export LOH_SEM_TIMEOUT_S=1.0
  export LOH_WAIT_NEWSTATE_MAX_CONSEC_TIMEOUTS=1800
  export LOH_WAIT_NEWSTATE_IDLE_S=1800
  export LOH_BUILD_RELEASE=1
  export LOH_SKIP_BUILD=1
  export LOH_SKIP_PIP_INSTALL=1
  export LOH_PERF_PROFILING=0
  export LOH_DEBUG_LEVEL=0
  export LOH_ENABLE_RL=1
  export LOH_SCORE_USE_COMPOUND=1
  export LOH_SCORE_USE_IRT=0
  export LOH_RANDOM_CANDIDATES=96
  export LOH_STRUCTURED_CANDIDATES=96
  export LOH_WAIT_MODE=nonblocked
  export LOH_ASYNC_TRAIN=1
  export LOH_MISS_RATIO_WEIGHT=1.0
  export LOH_INCLUDE_WEIGHTS_IN_OBS=1
  export LOH_ADAPTIVE_BUDGET=1
  export LOH_USE_SCORE_REBALANCE=0
  export LOH_FEATURE_UNIFIED_FORMULA=0
  export LOH_FEATURE_IDENTITY=0
  export LOH_FEATURE_LOG1P=1
  export LOH_FEATURE_LOG1P_RECIPROCAL=0
  export LOH_ENABLE_FEATURE_NORMALIZATION=0
  export LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1
  export LOH_ADAPTIVE_NORM_LO_Q=0.0
  export LOH_ADAPTIVE_NORM_HI_Q=1.0
  export LOH_ADAPTIVE_NORM_WARMUP=0
  export LOH_ADAPTIVE_NORM_QUANTILE_INPUT=log1p
  export LOH_INCLUDE_HIT_MISS_FEATURES=1
  bash scripts/test_loh_rl_sb3.sh data/WikiCDN/wiki_2019t.oracleGeneral.zst 0.1
) > "$LOG_PATH" 2>&1
RC=$?

FIN=$(awk '/LOH-OMR cache size/ {mr=""; bmr=""; mqps=""; if (match($0,/miss ratio [0-9]+\.[0-9]+/)) mr=substr($0,RSTART+11,RLENGTH-11); if (match($0,/byte miss ratio [0-9]+\.[0-9]+/)) bmr=substr($0,RSTART+16,RLENGTH-16); if (match($0,/throughput [0-9]+\.[0-9]+ MQPS/)) mqps=substr($0,RSTART+11,RLENGTH-16); if (mr!="" && bmr!="" && mqps!="") last=mr","bmr","mqps;} END{if(last!="") print last;}' "$LOG_PATH")
FMR=NA
FBMR=NA
FMQPS=NA
if [ -n "$FIN" ]; then
  FMR=$(echo "$FIN" | cut -d',' -f1)
  FBMR=$(echo "$FIN" | cut -d',' -f2)
  FMQPS=$(echo "$FIN" | cut -d',' -f3)
fi

STATUS=ok
if [ "$RC" -ne 0 ]; then
  STATUS=failed
fi

echo "wiki,${STATUS},${RC},${FMR},${FBMR},${FMQPS},${LOG_PATH}" >> "$RESULTS_CSV"
python3 "$OUT_DIR/update_doc_section.py" "$RESULTS_CSV" "$DOC_PATH" >> "$OUT_DIR/doc_update.log" 2>&1

echo "[rerun-done] status=${STATUS} rc=${RC} final_mr=${FMR} log=${LOG_PATH}"
