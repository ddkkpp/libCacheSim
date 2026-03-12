with open("scripts/train_loh_teacher_ranker.py", "r") as f:
    code = f.read()

# Replace load_groups signature
code = code.replace(
    'def load_groups(csv_path: str, max_groups: int = 0) -> List[Tuple[np.ndarray, int]]:',
    'def load_groups(csv_path: str, max_groups: int = 0) -> List[Tuple[np.ndarray, np.ndarray]]:'
)
code = code.replace(
    'groups: List[Tuple[np.ndarray, int]] = []',
    'groups: List[Tuple[np.ndarray, np.ndarray]] = []'
)
code = code.replace(
    'cur_rows: List[Tuple[int, np.ndarray, int]] = []',
    'cur_rows: List[Tuple[int, np.ndarray, int, str]] = []'
)
code = code.replace(
    'cur_rows.append((cand_idx, feat, is_teacher))',
    'bk_str = row.get("belady_key", "")\n            cur_rows.append((cand_idx, feat, is_teacher, bk_str))'
)

# train_linear_ranker
code = code.replace(
    'groups: List[Tuple[np.ndarray, int]],',
    'groups: List[Tuple[np.ndarray, np.ndarray]],'
)
code = code.replace(
    'target = torch.tensor([y], dtype=torch.long)',
    'target = torch.from_numpy(y).unsqueeze(0)'
)
code = code.replace(
    'if pred == y:',
    'if y[pred] > 0:'
)

with open("scripts/train_loh_teacher_ranker.py", "w") as f:
    f.write(code)
