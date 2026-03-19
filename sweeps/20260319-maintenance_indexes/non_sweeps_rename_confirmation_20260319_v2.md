]633;E;{   echo '# Non-Sweeps Renamed Confirmation v2'\x3b   echo\x3b   echo "Generated: $(date '+%F %T')"\x3b   echo\x3b   echo '| old_path | status | rule | candidate_new_paths |'\x3b   echo '|---|---|---|---|'   while IFS= read -r old\x3b do     [ -z "$old" ] && continue\x3b     base=$(basename "$old")\x3b     stem="${base%.md}"\x3b     cands=''\x3b     rule=''     if [[ "$old" == docs/* ]]\x3b then\x0acands=$(find docs -maxdepth 1 -type f -name "*-$base" | sort | tr '\\n' '\x3b')\x3b       rule='strict-suffix'\x0aif [ -z "$cands" ]\x3b then         norm=$(echo "$stem" | sed -E 's/^[0-9]{6,8}[-_]?//')\x3b         cands=$(find docs -maxdepth 1 -type f -name "*-$norm.md" | sort | tr '\\n' '\x3b')\x3b         rule='normalized-prefix-strip'\x3b       fi\x3b     else\x0acands=$(find . -type f -name "$base" ! -path "./$old" | sort | tr '\\n' '\x3b')\x3b       rule='same-basename-anywhere'\x3b     fi     if [ -n "$cands" ]\x3b then       matched=$((matched+1))\x3b       echo "| $old | matched | $rule | $cands |"\x3b     else       unmatched=$((unmatched+1))\x3b       echo "| $old | unmatched | $rule |  |"\x3b     fi\x3b   done < "$LIST"   echo\x3b   echo "- matched: $matched"\x3b   echo "- unmatched: $unmatched"\x3b } > "$OUT";c33ec03e-1ac9-4c82-9493-813e46b777cd]633;C# Non-Sweeps Renamed Confirmation v2

Generated: 2026-03-19 02:46:10

| old_path | status | rule | candidate_new_paths |
|---|---|---|---|
| data/cloudPhysicsIO.csv | unmatched | same-basename-anywhere |  |
| data/cloudPhysicsIO.oracleGeneral.bin | unmatched | same-basename-anywhere |  |
| data/cloudPhysicsIO.txt | unmatched | same-basename-anywhere |  |
| data/cloudPhysicsIO.vscsi | unmatched | same-basename-anywhere |  |
| data/twitter_cluster52.csv | unmatched | same-basename-anywhere |  |
| data/twitter_cluster52_10m.csv.zst | unmatched | same-basename-anywhere |  |
| docs/07291843-LOH_SHARED_MEMORY_FIX.md | matched | normalized-prefix-strip | docs/07291843-LOH_SHARED_MEMORY_FIX.md;docs/20250729-LOH_SHARED_MEMORY_FIX.md; |
| docs/07291843-loh_file_shm_patch.md | matched | normalized-prefix-strip | docs/07291843-loh_file_shm_patch.md;docs/20250729-loh_file_shm_patch.md; |
| docs/08081537-LOH_DEEP_ANALYSIS_FIXES.md | matched | normalized-prefix-strip | docs/08081537-LOH_DEEP_ANALYSIS_FIXES.md;docs/20250808-LOH_DEEP_ANALYSIS_FIXES.md; |
| docs/08081537-LOH_IMPROVEMENTS_SUMMARY.md | matched | normalized-prefix-strip | docs/08081537-LOH_IMPROVEMENTS_SUMMARY.md;docs/20250807-LOH_IMPROVEMENTS_SUMMARY.md; |
| docs/09021644-LOH_FIX_SUMMARY.md | matched | normalized-prefix-strip | docs/09021644-LOH_FIX_SUMMARY.md;docs/20250902-LOH_FIX_SUMMARY.md; |
| docs/09241141-LOH_Algorithm_Architecture.md | matched | normalized-prefix-strip | docs/09241141-LOH_Algorithm_Architecture.md;docs/20250814-LOH_Algorithm_Architecture.md; |
| docs/09251949-LOH_REWARD_WEIGHTS_FEATURE.md | matched | normalized-prefix-strip | docs/09251949-LOH_REWARD_WEIGHTS_FEATURE.md;docs/20250925-LOH_REWARD_WEIGHTS_FEATURE.md; |
| docs/10170043-LOH_INFERENCE_GUIDE.md | matched | normalized-prefix-strip | docs/10170043-LOH_INFERENCE_GUIDE.md;docs/20251016-LOH_INFERENCE_GUIDE.md; |
| docs/10230213-PENALTY_FIX_SUMMARY.md | matched | normalized-prefix-strip | docs/10230213-PENALTY_FIX_SUMMARY.md;docs/20251023-PENALTY_FIX_SUMMARY.md; |
| docs/10230213-PENALTY_MECHANISM_REDESIGN.md | matched | normalized-prefix-strip | docs/10230213-PENALTY_MECHANISM_REDESIGN.md;docs/20251023-PENALTY_MECHANISM_REDESIGN.md; |
| docs/10230213-SAC_RETROSPECTIVE_GUIDE.md | matched | normalized-prefix-strip | docs/10230213-SAC_RETROSPECTIVE_GUIDE.md;docs/20251022-SAC_RETROSPECTIVE_GUIDE.md; |
| docs/10230213-SAMPLING_EXCLUSION_STRATEGY.md | matched | normalized-prefix-strip | docs/10230213-SAMPLING_EXCLUSION_STRATEGY.md;docs/20251023-SAMPLING_EXCLUSION_STRATEGY.md; |
| docs/10230213-TEST_RETROSPECTIVE_PENALTY.md | matched | normalized-prefix-strip | docs/10230213-TEST_RETROSPECTIVE_PENALTY.md;docs/20251022-TEST_RETROSPECTIVE_PENALTY.md; |
| docs/10230213-TUNING_GUIDE.md | matched | normalized-prefix-strip | docs/10230213-TUNING_GUIDE.md;docs/20251023-TUNING_GUIDE.md; |
| docs/10232259-EVICTION_TIMESTAMP_IMPROVEMENT.md | matched | normalized-prefix-strip | docs/10232259-EVICTION_TIMESTAMP_IMPROVEMENT.md;docs/20251023-EVICTION_TIMESTAMP_IMPROVEMENT.md; |
| docs/10232259-PENALTY_FIXES_SUMMARY.md | matched | normalized-prefix-strip | docs/10232259-PENALTY_FIXES_SUMMARY.md;docs/20251023-PENALTY_FIXES_SUMMARY.md; |
| docs/10232259-TWO_COMPONENT_PENALTY_IMPLEMENTATION.md | matched | normalized-prefix-strip | docs/10232259-TWO_COMPONENT_PENALTY_IMPLEMENTATION.md;docs/20251023-TWO_COMPONENT_PENALTY_IMPLEMENTATION.md; |
| docs/10232259-TWO_COMPONENT_PENALTY_TEST_REPORT.md | matched | normalized-prefix-strip | docs/10232259-TWO_COMPONENT_PENALTY_TEST_REPORT.md;docs/20251023-TWO_COMPONENT_PENALTY_TEST_REPORT.md; |
| docs/10241746-CTRL_C_BEHAVIOR.md | matched | normalized-prefix-strip | docs/10241746-CTRL_C_BEHAVIOR.md;docs/20251024-CTRL_C_BEHAVIOR.md; |
| docs/10241746-LOH_GRACEFUL_SHUTDOWN.md | matched | normalized-prefix-strip | docs/10241746-LOH_GRACEFUL_SHUTDOWN.md;docs/20251024-LOH_GRACEFUL_SHUTDOWN.md; |
| docs/10272237-PENALTY_QUEUE_OPTIMIZATION.md | matched | normalized-prefix-strip | docs/10272237-PENALTY_QUEUE_OPTIMIZATION.md;docs/20251027-PENALTY_QUEUE_OPTIMIZATION.md; |
| docs/10282026-REWARD_IMPROVEMENT_PLAN.md | matched | normalized-prefix-strip | docs/10282026-REWARD_IMPROVEMENT_PLAN.md;docs/20251028-REWARD_IMPROVEMENT_PLAN.md; |
| docs/20260215_1063_to032_阶段总结与完成度.md | matched | strict-suffix | docs/20260215-20260215_1063_to032_阶段总结与完成度.md; |
| docs/COMPREHENSIVE_EXPERIMENT_SUMMARY.md | matched | strict-suffix | docs/20260303-COMPREHENSIVE_EXPERIMENT_SUMMARY.md; |
| docs/DOC_INDEX.md | matched | strict-suffix | docs/20251028-DOC_INDEX.md; |
| docs/FULL_EXPERIMENT_RESULTS.md | matched | strict-suffix | docs/20260317-FULL_EXPERIMENT_RESULTS.md; |
| docs/LOH_1063_8M_RL_RESULTS.md | matched | strict-suffix | docs/20260305-LOH_1063_8M_RL_RESULTS.md; |
| docs/LOH_CLEANUP_SUMMARY.md | matched | strict-suffix | docs/20251125-LOH_CLEANUP_SUMMARY.md; |
| docs/LOH_CONSTANT_WEIGHTS_BEST_3M_WIKI2019T_1063.md | matched | strict-suffix | docs/20260131-LOH_CONSTANT_WEIGHTS_BEST_3M_WIKI2019T_1063.md; |
| docs/LOH_ENV_VARS.md | matched | strict-suffix | docs/20251114-LOH_ENV_VARS.md; |
| docs/LOH_EXP_HISTORY.md | matched | strict-suffix | docs/20251117-LOH_EXP_HISTORY.md; |
| docs/LOH_Framework_and_Experiments_Summary.md | matched | strict-suffix | docs/20251117-LOH_Framework_and_Experiments_Summary.md; |
| docs/LOH_PARAM_COVERAGE_SUMMARY.md | matched | strict-suffix | docs/20260131-LOH_PARAM_COVERAGE_SUMMARY.md; |
| docs/LOH_PENALTY_ANALYSIS.md | matched | strict-suffix | docs/20260205-LOH_PENALTY_ANALYSIS.md; |
| docs/LOH_PENALTY_ANALYSIS_cross_date.md | matched | strict-suffix | docs/20260205-LOH_PENALTY_ANALYSIS_cross_date.md; |
| docs/LOH_PENALTY_ANALYSIS_ignore_formula.md | matched | strict-suffix | docs/20260205-LOH_PENALTY_ANALYSIS_ignore_formula.md; |
| docs/LOH_PENALTY_COVERAGE.md | matched | strict-suffix | docs/20260205-LOH_PENALTY_COVERAGE.md; |
| docs/LOH_PENALTY_RUNS_0203_PLUS.md | matched | strict-suffix | docs/20260205-LOH_PENALTY_RUNS_0203_PLUS.md; |
| docs/LOH_SCRIPTS_INTEGRATION_GUIDE.md | matched | strict-suffix | docs/20251203-LOH_SCRIPTS_INTEGRATION_GUIDE.md; |
| docs/LOH_TESTED_CONFIGS_SUMMARY.md | matched | strict-suffix | docs/20260129-LOH_TESTED_CONFIGS_SUMMARY.md; |
| docs/PICKLE_FIX_SUMMARY.md | matched | strict-suffix | docs/20251029-PICKLE_FIX_SUMMARY.md; |
| docs/README.md | matched | strict-suffix | docs/20251028-README.md; |
| docs/RL_CacheSim_Run_Summary_by_Trace.md | matched | strict-suffix | docs/20251107-RL_CacheSim_Run_Summary_by_Trace.md; |
| docs/Scripts_and_Docs_Files_Summary.md | matched | strict-suffix | docs/20251117-Scripts_and_Docs_Files_Summary.md; |
| docs/WHY_SACBLOCKED_WORKS.md | matched | strict-suffix | docs/20251029-WHY_SACBLOCKED_WORKS.md; |
| docs/_generated_LOH_TESTED_CONFIGS_SUMMARY.md | matched | strict-suffix | docs/20260129-_generated_LOH_TESTED_CONFIGS_SUMMARY.md; |
| docs/_generated_ac_reward_signal_report_0204_3m.md | matched | strict-suffix | docs/20260205-_generated_ac_reward_signal_report_0204_3m.md; |
| docs/_generated_ac_reward_signal_report_0204_3m_pen1_final.md | matched | strict-suffix | docs/20260206-_generated_ac_reward_signal_report_0204_3m_pen1_final.md; |
| docs/_generated_ac_reward_signal_report_0204_3m_pen1_final_with_manifest.md | matched | strict-suffix | docs/20260206-_generated_ac_reward_signal_report_0204_3m_pen1_final_with_manifest.md; |
| docs/_generated_ac_reward_signal_report_0204_all.md | matched | strict-suffix | docs/20260205-_generated_ac_reward_signal_report_0204_all.md; |
| docs/_generated_ac_reward_signal_report_0204_pen1_final.md | matched | strict-suffix | docs/20260206-_generated_ac_reward_signal_report_0204_pen1_final.md; |
| docs/_generated_ac_reward_signal_report_0204_pen1_final_combined.md | matched | strict-suffix | docs/20260206-_generated_ac_reward_signal_report_0204_pen1_final_combined.md; |
| docs/_generated_ac_reward_signal_report_0204_pen1_final_config_rich.md | matched | strict-suffix | docs/20260206-_generated_ac_reward_signal_report_0204_pen1_final_config_rich.md; |
| docs/references.md | matched | strict-suffix | docs/20250704-references.md; |
| docs/sweep_results.md | matched | strict-suffix | docs/20251205-sweep_results.md; |

- matched: 55
- unmatched: 6
