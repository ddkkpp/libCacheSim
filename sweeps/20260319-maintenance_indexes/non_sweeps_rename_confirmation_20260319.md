]633;E;{   echo '# Non-Sweeps Renamed Confirmation'\x3b   echo\x3b   echo "Generated: $(date '+%F %T')"\x3b   echo\x3b   echo '| old_path | status | candidate_new_paths |'\x3b   echo '|---|---|---|'   while IFS= read -r old\x3b do     [ -z "$old" ] && continue\x3b     base=$(basename "$old")\x3b     cands=''     if [[ "$old" == docs/* ]]\x3b then\x0acands=$(find docs -maxdepth 1 -type f -name "*-$base" | sort | tr '\\n' '\x3b')\x3b     else\x0acands=$(find . -type f -name "$base" ! -path "./$old" | sort | tr '\\n' '\x3b')\x3b     fi     if [ -n "$cands" ]\x3b then       matched=$((matched+1))\x3b       echo "| $old | matched | $cands |"\x3b     else       unmatched=$((unmatched+1))\x3b       echo "| $old | unmatched |  |"\x3b     fi\x3b   done < "$LIST"   echo\x3b   echo "- matched: $matched"\x3b   echo "- unmatched: $unmatched"\x3b } > "$OUT";c33ec03e-1ac9-4c82-9493-813e46b777cd]633;C# Non-Sweeps Renamed Confirmation

Generated: 2026-03-19 02:44:10

| old_path | status | candidate_new_paths |
|---|---|---|
| data/cloudPhysicsIO.csv | unmatched |  |
| data/cloudPhysicsIO.oracleGeneral.bin | unmatched |  |
| data/cloudPhysicsIO.txt | unmatched |  |
| data/cloudPhysicsIO.vscsi | unmatched |  |
| data/twitter_cluster52.csv | unmatched |  |
| data/twitter_cluster52_10m.csv.zst | unmatched |  |
| docs/07291843-LOH_SHARED_MEMORY_FIX.md | unmatched |  |
| docs/07291843-loh_file_shm_patch.md | unmatched |  |
| docs/08081537-LOH_DEEP_ANALYSIS_FIXES.md | unmatched |  |
| docs/08081537-LOH_IMPROVEMENTS_SUMMARY.md | unmatched |  |
| docs/09021644-LOH_FIX_SUMMARY.md | unmatched |  |
| docs/09241141-LOH_Algorithm_Architecture.md | unmatched |  |
| docs/09251949-LOH_REWARD_WEIGHTS_FEATURE.md | unmatched |  |
| docs/10170043-LOH_INFERENCE_GUIDE.md | unmatched |  |
| docs/10230213-PENALTY_FIX_SUMMARY.md | unmatched |  |
| docs/10230213-PENALTY_MECHANISM_REDESIGN.md | unmatched |  |
| docs/10230213-SAC_RETROSPECTIVE_GUIDE.md | unmatched |  |
| docs/10230213-SAMPLING_EXCLUSION_STRATEGY.md | unmatched |  |
| docs/10230213-TEST_RETROSPECTIVE_PENALTY.md | unmatched |  |
| docs/10230213-TUNING_GUIDE.md | unmatched |  |
| docs/10232259-EVICTION_TIMESTAMP_IMPROVEMENT.md | unmatched |  |
| docs/10232259-PENALTY_FIXES_SUMMARY.md | unmatched |  |
| docs/10232259-TWO_COMPONENT_PENALTY_IMPLEMENTATION.md | unmatched |  |
| docs/10232259-TWO_COMPONENT_PENALTY_TEST_REPORT.md | unmatched |  |
| docs/10241746-CTRL_C_BEHAVIOR.md | unmatched |  |
| docs/10241746-LOH_GRACEFUL_SHUTDOWN.md | unmatched |  |
| docs/10272237-PENALTY_QUEUE_OPTIMIZATION.md | unmatched |  |
| docs/10282026-REWARD_IMPROVEMENT_PLAN.md | unmatched |  |
| docs/20260215_1063_to032_阶段总结与完成度.md | matched | docs/20260215-20260215_1063_to032_阶段总结与完成度.md; |
| docs/COMPREHENSIVE_EXPERIMENT_SUMMARY.md | matched | docs/20260303-COMPREHENSIVE_EXPERIMENT_SUMMARY.md; |
| docs/DOC_INDEX.md | matched | docs/20251028-DOC_INDEX.md; |
| docs/FULL_EXPERIMENT_RESULTS.md | matched | docs/20260317-FULL_EXPERIMENT_RESULTS.md; |
| docs/LOH_1063_8M_RL_RESULTS.md | matched | docs/20260305-LOH_1063_8M_RL_RESULTS.md; |
| docs/LOH_CLEANUP_SUMMARY.md | matched | docs/20251125-LOH_CLEANUP_SUMMARY.md; |
| docs/LOH_CONSTANT_WEIGHTS_BEST_3M_WIKI2019T_1063.md | matched | docs/20260131-LOH_CONSTANT_WEIGHTS_BEST_3M_WIKI2019T_1063.md; |
| docs/LOH_ENV_VARS.md | matched | docs/20251114-LOH_ENV_VARS.md; |
| docs/LOH_EXP_HISTORY.md | matched | docs/20251117-LOH_EXP_HISTORY.md; |
| docs/LOH_Framework_and_Experiments_Summary.md | matched | docs/20251117-LOH_Framework_and_Experiments_Summary.md; |
| docs/LOH_PARAM_COVERAGE_SUMMARY.md | matched | docs/20260131-LOH_PARAM_COVERAGE_SUMMARY.md; |
| docs/LOH_PENALTY_ANALYSIS.md | matched | docs/20260205-LOH_PENALTY_ANALYSIS.md; |
| docs/LOH_PENALTY_ANALYSIS_cross_date.md | matched | docs/20260205-LOH_PENALTY_ANALYSIS_cross_date.md; |
| docs/LOH_PENALTY_ANALYSIS_ignore_formula.md | matched | docs/20260205-LOH_PENALTY_ANALYSIS_ignore_formula.md; |
| docs/LOH_PENALTY_COVERAGE.md | matched | docs/20260205-LOH_PENALTY_COVERAGE.md; |
| docs/LOH_PENALTY_RUNS_0203_PLUS.md | matched | docs/20260205-LOH_PENALTY_RUNS_0203_PLUS.md; |
| docs/LOH_SCRIPTS_INTEGRATION_GUIDE.md | matched | docs/20251203-LOH_SCRIPTS_INTEGRATION_GUIDE.md; |
| docs/LOH_TESTED_CONFIGS_SUMMARY.md | matched | docs/20260129-LOH_TESTED_CONFIGS_SUMMARY.md; |
| docs/PICKLE_FIX_SUMMARY.md | matched | docs/20251029-PICKLE_FIX_SUMMARY.md; |
| docs/README.md | matched | docs/20251028-README.md; |
| docs/RL_CacheSim_Run_Summary_by_Trace.md | matched | docs/20251107-RL_CacheSim_Run_Summary_by_Trace.md; |
| docs/Scripts_and_Docs_Files_Summary.md | matched | docs/20251117-Scripts_and_Docs_Files_Summary.md; |
| docs/WHY_SACBLOCKED_WORKS.md | matched | docs/20251029-WHY_SACBLOCKED_WORKS.md; |
| docs/_generated_LOH_TESTED_CONFIGS_SUMMARY.md | matched | docs/20260129-_generated_LOH_TESTED_CONFIGS_SUMMARY.md; |
| docs/_generated_ac_reward_signal_report_0204_3m.md | matched | docs/20260205-_generated_ac_reward_signal_report_0204_3m.md; |
| docs/_generated_ac_reward_signal_report_0204_3m_pen1_final.md | matched | docs/20260206-_generated_ac_reward_signal_report_0204_3m_pen1_final.md; |
| docs/_generated_ac_reward_signal_report_0204_3m_pen1_final_with_manifest.md | matched | docs/20260206-_generated_ac_reward_signal_report_0204_3m_pen1_final_with_manifest.md; |
| docs/_generated_ac_reward_signal_report_0204_all.md | matched | docs/20260205-_generated_ac_reward_signal_report_0204_all.md; |
| docs/_generated_ac_reward_signal_report_0204_pen1_final.md | matched | docs/20260206-_generated_ac_reward_signal_report_0204_pen1_final.md; |
| docs/_generated_ac_reward_signal_report_0204_pen1_final_combined.md | matched | docs/20260206-_generated_ac_reward_signal_report_0204_pen1_final_combined.md; |
| docs/_generated_ac_reward_signal_report_0204_pen1_final_config_rich.md | matched | docs/20260206-_generated_ac_reward_signal_report_0204_pen1_final_config_rich.md; |
| docs/references.md | matched | docs/20250704-references.md; |
| docs/sweep_results.md | matched | docs/20251205-sweep_results.md; |

- matched: 33
- unmatched: 28
