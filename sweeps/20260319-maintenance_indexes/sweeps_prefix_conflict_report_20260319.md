]633;E;{   echo "# 20260319 Sweeps 日期前缀冲突报告"\x3b   echo\x3b   echo "生成时间: $(date '+%Y-%m-%d %H:%M:%S %z')"\x3b   echo\x3b   echo "| old_dir | proposed_prefixed_dir | target_exists | infer_rule |"\x3b   echo "| --- | --- | --- | --- |"   while IFS= read -r d\x3b do     [ -z "$d" ] && continue     date8=$(printf '%s' "$d" | grep -oE '20[0-9]{6}' | head -1 || true)\x3b     rule="name_yyyymmdd"     if [ -z "$date8" ]\x3b then\x0ammdd=$(printf '%s' "$d" | sed -nE 's/.*_((0[1-9]|1[0-2])[0-3][0-9])_.*/\\1/p' | head -1)\x3b       if [ -n "$mmdd" ]\x3b then         if [ "$mmdd" ">" "$CUR_MMDD" ]\x3b then           year=$((CUR_YEAR-1))\x3b         else           year=$CUR_YEAR\x3b         fi\x3b         date8="${year}${mmdd}"\x3b         rule="name_mmdd_infer_year"\x3b       fi\x3b     fi     if [ -z "$date8" ]\x3b then       date8=$(date -r "sweeps/$d" +%Y%m%d)\x3b       rule="mtime_fallback"\x3b     fi     new="${date8}-${d}"\x3b     if [ -e "sweeps/$new" ]\x3b then       exists="yes"\x3b     else       exists="no"\x3b     fi     printf '| %s | %s | %s | %s |\\n' "$d" "$new" "$exists" "$rule"\x3b   done < "$IN"\x3b } > "$OUT";41c0ab9c-1ae2-468d-8b5d-9e812f4dd434]633;C# 20260319 Sweeps 日期前缀冲突报告

生成时间: 2026-03-19 11:46:15 +0800

| old_dir | proposed_prefixed_dir | target_exists | infer_rule |
| --- | --- | --- | --- |
| 1063_3m_cache_ratio_20260216_cont | 20260216-1063_3m_cache_ratio_20260216_cont | yes | name_yyyymmdd |
| 1063_best_20251225_100313 | 20251225-1063_best_20251225_100313 | yes | name_yyyymmdd |
| 1063_breakthrough_compound_scale3 | 20260319-1063_breakthrough_compound_scale3 | no | mtime_fallback |
| 1063_breakthrough_compound_scale3_v2 | 20260319-1063_breakthrough_compound_scale3_v2 | no | mtime_fallback |
| 1063_cachefeat_r1_20251231_112906 | 20251231-1063_cachefeat_r1_20251231_112906 | yes | name_yyyymmdd |
| 1063_featnorm_r1_20251229_140452 | 20251229-1063_featnorm_r1_20251229_140452 | yes | name_yyyymmdd |
| 1063_guided_softmax_scale5 | 20260319-1063_guided_softmax_scale5 | no | mtime_fallback |
| 1063_kitchensink_r1_20251231_144653 | 20251231-1063_kitchensink_r1_20251231_144653 | yes | name_yyyymmdd |
| 1063_linear_breakthrough_ctx | 20260319-1063_linear_breakthrough_ctx | no | mtime_fallback |
| 1063_linear_guided_v3 | 20260319-1063_linear_guided_v3 | no | mtime_fallback |
| 1063_linear_only_20260108_115104 | 20260108-1063_linear_only_20260108_115104 | yes | name_yyyymmdd |
| 1063_mlp_vs_linear_20260107_180946 | 20260107-1063_mlp_vs_linear_20260107_180946 | yes | name_yyyymmdd |
| 1063_penalty_3m_20260206_030550 | 20260206-1063_penalty_3m_20260206_030550 | yes | name_yyyymmdd |
| 1063_quick_r1_20251225_110318 | 20251225-1063_quick_r1_20251225_110318 | yes | name_yyyymmdd |
| 1063_reward_penalty_r1_20251225_163358 | 20251225-1063_reward_penalty_r1_20251225_163358 | yes | name_yyyymmdd |
| 1063_scalegrid_noprior_20260203 | 20260203-1063_scalegrid_noprior_20260203 | yes | name_yyyymmdd |
| 1063_softmax_ctx_bound5 | 20260319-1063_softmax_ctx_bound5 | no | mtime_fallback |
| 1063_stage2_upgrade_single_seed_20260215_123602 | 20260215-1063_stage2_upgrade_single_seed_20260215_123602 | yes | name_yyyymmdd |
| 1063_stage2_upgrade_single_seed_20260215_123619 | 20260215-1063_stage2_upgrade_single_seed_20260215_123619 | yes | name_yyyymmdd |
| 1063_stage2_upgrade_single_seed_20260215_restart_debug0 | 20260215-1063_stage2_upgrade_single_seed_20260215_restart_debug0 | yes | name_yyyymmdd |
| 1063_tempgrid_noprior_20260203 | 20260203-1063_tempgrid_noprior_20260203 | yes | name_yyyymmdd |
| 1063_to032_dryrun_20260213 | 20260213-1063_to032_dryrun_20260213 | yes | name_yyyymmdd |
| 1063_to032_fixcheck_20260213 | 20260213-1063_to032_fixcheck_20260213 | yes | name_yyyymmdd |
| 1063_wide_r2_20251226_112012 | 20251226-1063_wide_r2_20251226_112012 | yes | name_yyyymmdd |
| meta_3m_1212_152109 | 20251212-meta_3m_1212_152109 | yes | name_mmdd_infer_year |
| meta_best_action_scale_r2_20251222_183925 | 20251222-meta_best_action_scale_r2_20251222_183925 | yes | name_yyyymmdd |
| meta_best_action_scale_winner_repeat5_20251222_201349 | 20251222-meta_best_action_scale_winner_repeat5_20251222_201349 | yes | name_yyyymmdd |
| meta_best_grid_winner_repeat5_20251222_102624 | 20251222-meta_best_grid_winner_repeat5_20251222_102624 | yes | name_yyyymmdd |
| meta_best_scale_fine_r2_20251223_110142 | 20251223-meta_best_scale_fine_r2_20251223_110142 | yes | name_yyyymmdd |
| meta_best_v5_idx6_repeat5_20251217_182945 | 20251217-meta_best_v5_idx6_repeat5_20251217_182945 | yes | name_yyyymmdd |
| meta_lower_omr_3m_v2_1213_135303 | 20251213-meta_lower_omr_3m_v2_1213_135303 | yes | name_mmdd_infer_year |
| meta_lower_omr_500k_1213_032629 | 20251213-meta_lower_omr_500k_1213_032629 | yes | name_mmdd_infer_year |
| meta_precision_refine_v5_1214_212442 | 20251214-meta_precision_refine_v5_1214_212442 | yes | name_mmdd_infer_year |
| meta_refine6_3m_v3_1213_214805 | 20251213-meta_refine6_3m_v3_1213_214805 | yes | name_mmdd_infer_year |
| meta_refine_user_3m_1212_160647 | 20251212-meta_refine_user_3m_1212_160647 | yes | name_mmdd_infer_year |
| meta_reward_algo_v4_1214_014136 | 20251214-meta_reward_algo_v4_1214_014136 | yes | name_mmdd_infer_year |
| meta_reward_algo_v4_20251215_145147 | 20251215-meta_reward_algo_v4_20251215_145147 | yes | name_yyyymmdd |
| meta_reward_algo_v4_fix_1214_014409 | 20251214-meta_reward_algo_v4_fix_1214_014409 | yes | name_mmdd_infer_year |
| meta_reward_algo_v4_tqc_only_fix_20251215_211951 | 20251215-meta_reward_algo_v4_tqc_only_fix_20251215_211951 | yes | name_yyyymmdd |
| meta_smoke_1212_144755 | 20251212-meta_smoke_1212_144755 | yes | name_mmdd_infer_year |
| meta_smoke_1212_150755 | 20251212-meta_smoke_1212_150755 | yes | name_mmdd_infer_year |
| meta_smoke_fix_1212_151230 | 20251212-meta_smoke_fix_1212_151230 | yes | name_mmdd_infer_year |
| meta_temp_scale_grid_r2_20251224_142147 | 20251224-meta_temp_scale_grid_r2_20251224_142147 | yes | name_yyyymmdd |
| meta_try_cachefeat_3m_1213_234146 | 20251213-meta_try_cachefeat_3m_1213_234146 | yes | name_mmdd_infer_year |
| meta_try_cachefeat_3m_fix_1214_000103 | 20251214-meta_try_cachefeat_3m_fix_1214_000103 | yes | name_mmdd_infer_year |
| meta_try_candfeat_3m_1214_005451 | 20251214-meta_try_candfeat_3m_1214_005451 | yes | name_mmdd_infer_year |
| modes2_mrw0_0130_112123 | 20260130-modes2_mrw0_0130_112123 | yes | name_mmdd_infer_year |
| modes3_batch_0130_021623 | 20260130-modes3_batch_0130_021623 | yes | name_mmdd_infer_year |
| modes_cpd_soft_sign_3m_20260206_141233 | 20260206-modes_cpd_soft_sign_3m_20260206_141233 | yes | name_yyyymmdd |
| modes_cpd_soft_sign_3m_20260206_145822 | 20260206-modes_cpd_soft_sign_3m_20260206_145822 | yes | name_yyyymmdd |
| next_1063_localgrid_nosem_3m_20260129_184141 | 20260129-next_1063_localgrid_nosem_3m_20260129_184141 | yes | name_yyyymmdd |
| next_1063_localgrid_req1_3m_20260129_184633 | 20260129-next_1063_localgrid_req1_3m_20260129_184633 | yes | name_yyyymmdd |
| next_meta_modes_3m_20260129_183751 | 20260129-next_meta_modes_3m_20260129_183751 | yes | name_yyyymmdd |
| next_meta_modes_3m_20260129_183812 | 20260129-next_meta_modes_3m_20260129_183812 | yes | name_yyyymmdd |
| next_meta_modes_nosem_3m_20260129_184111 | 20260129-next_meta_modes_nosem_3m_20260129_184111 | yes | name_yyyymmdd |
| next_meta_modes_req1_3m_20260129_184621 | 20260129-next_meta_modes_req1_3m_20260129_184621 | yes | name_yyyymmdd |
| next_wiki_bootstrap_nosem_3m_20260129_184204 | 20260129-next_wiki_bootstrap_nosem_3m_20260129_184204 | yes | name_yyyymmdd |
| next_wiki_bootstrap_req1_3m_20260129_184646 | 20260129-next_wiki_bootstrap_req1_3m_20260129_184646 | yes | name_yyyymmdd |
| rec3m_1212_133521 | 20251212-rec3m_1212_133521 | yes | name_mmdd_infer_year |
| seedfocus3m_1212_143747 | 20251212-seedfocus3m_1212_143747 | yes | name_mmdd_infer_year |
| seedfocus3m_1212_144046 | 20251212-seedfocus3m_1212_144046 | yes | name_mmdd_infer_year |
| smoke_1212_132049 | 20251212-smoke_1212_132049 | yes | name_mmdd_infer_year |
]633;E;{   echo\x3b   echo "## 统计"\x3b   echo\x3b   echo "- remaining_nonprefixed=$(wc -l < \\"$IN\\")"\x3b   echo "- conflicts_target_exists=$(awk -F'|' 'NR>2 && $0 ~ /\\| yes \\|/ {c++} END{print c+0}' \\"$OUT\\")"\x3b   echo "- can_rename_now=$(awk -F'|' 'NR>2 && $0 ~ /\\| no \\|/ {c++} END{print c+0}' \\"$OUT\\")"\x3b } >> "$OUT";41c0ab9c-1ae2-468d-8b5d-9e812f4dd434]633;C
## 统计

- remaining_nonprefixed=
- conflicts_target_exists=
- can_rename_now=
