with open("scripts/train_loh_teacher_ranker.py", "r") as f:
    code = f.read()

code = code.replace(
    'cur_rows: List[Tuple[int, np.ndarray, int]] = []',
    'cur_rows: List[Tuple[int, np.ndarray, int, str]] = []'
)
code = code.replace(
    'cur_rows.append((cand_idx, feat, is_teacher))',
    'bk_str = row.get("belady_key", "")\n            cur_rows.append((cand_idx, feat, is_teacher, bk_str))'
)
with open("scripts/train_loh_teacher_ranker.py", "w") as f:
    f.write(code)
