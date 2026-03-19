# 20260319 Sweeps Prefix Conflict Report (Clean)

## Summary
- Non-prefixed directories after safe rename: 62
- Conflicts with existing prefixed target: 56
- Can rename now without conflict: 6

## Can-Rename-Now
- 1063_breakthrough_compound_scale3 -> 20260319-1063_breakthrough_compound_scale3
- 1063_breakthrough_compound_scale3_v2 -> 20260319-1063_breakthrough_compound_scale3_v2
- 1063_guided_softmax_scale5 -> 20260319-1063_guided_softmax_scale5
- 1063_linear_breakthrough_ctx -> 20260319-1063_linear_breakthrough_ctx
- 1063_linear_guided_v3 -> 20260319-1063_linear_guided_v3
- 1063_softmax_ctx_bound5 -> 20260319-1063_softmax_ctx_bound5

## Conflict Handling Rule
- For 56 conflict cases, direct rename is blocked to avoid overwrite.
- Merge/reconcile is required before deleting or replacing non-prefixed directories.

## Data Sources
- tmp/20260319-maintenance_indexes/sweeps_nonprefixed_after_fix.txt
- tmp/20260319-maintenance_indexes/sweeps_prefix_rename_plan_20260319.tsv
- tmp/20260319-maintenance_indexes/sweeps_prefix_rename_exec_20260319.log
