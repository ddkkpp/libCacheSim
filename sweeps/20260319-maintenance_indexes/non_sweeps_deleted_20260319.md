]633;E;{   echo '# Non-Sweeps Deleted Files (Read-Only Audit)'\x3b   echo\x3b   echo "Generated: $(date '+%F %T')"\x3b   echo\x3b   echo '## Summary'\x3b   echo\x3b   TOTAL=$(git status --short | awk '$1=="D"{print $2}' | grep -v '^sweeps/' | wc -l)\x3b   DATA_N=$(git status --short | awk '$1=="D"{print $2}' | grep '^data/' | wc -l)\x3b   DOCS_N=$(git status --short | awk '$1=="D"{print $2}' | grep '^docs/' | wc -l)\x3b   OTH_N=$((TOTAL-DATA_N-DOCS_N))\x3b   echo "- total_non_sweeps_deleted: $TOTAL"\x3b   echo "- data_deleted: $DATA_N"\x3b   echo "- docs_deleted: $DOCS_N"\x3b   echo "- others_deleted: $OTH_N"\x3b   echo\x3b   echo '## data/'\x3b   git status --short | awk '$1=="D"{print $2}' | grep '^data/' | sort\x3b   echo\x3b   echo '## docs/'\x3b   git status --short | awk '$1=="D"{print $2}' | grep '^docs/' | sort\x3b   echo\x3b   echo '## others'\x3b   git status --short | awk '$1=="D"{print $2}' | grep -v '^sweeps/' | grep -Ev '^(data|docs)/' | sort\x3b } > "$OUT";c33ec03e-1ac9-4c82-9493-813e46b777cd]633;C# Non-Sweeps Deleted Files (Read-Only Audit)

Generated: 2026-03-19 02:36:19

## Summary

- total_non_sweeps_deleted: 61
- data_deleted: 6
- docs_deleted: 54
- others_deleted: 1

## data/
data/cloudPhysicsIO.csv
data/cloudPhysicsIO.oracleGeneral.bin
data/cloudPhysicsIO.txt
data/cloudPhysicsIO.vscsi
data/twitter_cluster52_10m.csv.zst
data/twitter_cluster52.csv

## docs/
docs/07291843-loh_file_shm_patch.md
docs/07291843-LOH_SHARED_MEMORY_FIX.md
docs/08081537-LOH_DEEP_ANALYSIS_FIXES.md
docs/08081537-LOH_IMPROVEMENTS_SUMMARY.md
docs/09021644-LOH_FIX_SUMMARY.md
docs/09241141-LOH_Algorithm_Architecture.md
docs/09251949-LOH_REWARD_WEIGHTS_FEATURE.md
docs/10170043-LOH_INFERENCE_GUIDE.md
docs/10230213-PENALTY_FIX_SUMMARY.md
docs/10230213-PENALTY_MECHANISM_REDESIGN.md
docs/10230213-SAC_RETROSPECTIVE_GUIDE.md
docs/10230213-SAMPLING_EXCLUSION_STRATEGY.md
docs/10230213-TEST_RETROSPECTIVE_PENALTY.md
docs/10230213-TUNING_GUIDE.md
docs/10232259-EVICTION_TIMESTAMP_IMPROVEMENT.md
docs/10232259-PENALTY_FIXES_SUMMARY.md
docs/10232259-TWO_COMPONENT_PENALTY_IMPLEMENTATION.md
docs/10232259-TWO_COMPONENT_PENALTY_TEST_REPORT.md
docs/10241746-CTRL_C_BEHAVIOR.md
docs/10241746-LOH_GRACEFUL_SHUTDOWN.md
docs/10272237-PENALTY_QUEUE_OPTIMIZATION.md
docs/10282026-REWARD_IMPROVEMENT_PLAN.md
docs/COMPREHENSIVE_EXPERIMENT_SUMMARY.md
docs/DOC_INDEX.md
docs/FULL_EXPERIMENT_RESULTS.md
docs/_generated_ac_reward_signal_report_0204_3m.md
docs/_generated_ac_reward_signal_report_0204_3m_pen1_final.md
docs/_generated_ac_reward_signal_report_0204_3m_pen1_final_with_manifest.md
docs/_generated_ac_reward_signal_report_0204_all.md
docs/_generated_ac_reward_signal_report_0204_pen1_final_combined.md
docs/_generated_ac_reward_signal_report_0204_pen1_final_config_rich.md
docs/_generated_ac_reward_signal_report_0204_pen1_final.md
docs/_generated_LOH_TESTED_CONFIGS_SUMMARY.md
docs/LOH_1063_8M_RL_RESULTS.md
docs/LOH_CLEANUP_SUMMARY.md
docs/LOH_CONSTANT_WEIGHTS_BEST_3M_WIKI2019T_1063.md
docs/LOH_ENV_VARS.md
docs/LOH_EXP_HISTORY.md
docs/LOH_Framework_and_Experiments_Summary.md
docs/LOH_PARAM_COVERAGE_SUMMARY.md
docs/LOH_PENALTY_ANALYSIS_cross_date.md
docs/LOH_PENALTY_ANALYSIS_ignore_formula.md
docs/LOH_PENALTY_ANALYSIS.md
docs/LOH_PENALTY_COVERAGE.md
docs/LOH_PENALTY_RUNS_0203_PLUS.md
docs/LOH_SCRIPTS_INTEGRATION_GUIDE.md
docs/LOH_TESTED_CONFIGS_SUMMARY.md
docs/PICKLE_FIX_SUMMARY.md
docs/README.md
docs/references.md
docs/RL_CacheSim_Run_Summary_by_Trace.md
docs/Scripts_and_Docs_Files_Summary.md
docs/sweep_results.md
docs/WHY_SACBLOCKED_WORKS.md

## others
"docs/20260215_1063_to032_\351\230\266\346\256\265\346\200\273\347\273\223\344\270\216\345\256\214\346\210\220\345\272\246.md"
