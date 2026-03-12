import re

with open("scripts/train_loh_teacher_ranker.py", "r") as f:
    code = f.read()

# Make changes to _finalize_group
code = re.sub(
    r'def _finalize_group\(rows: List\[Tuple\[int, np\.ndarray, int\]\]\) -> Tuple\[np\.ndarray, int\] \| None:(.*?)(?=def load_groups)',
    """def _finalize_group(rows: List[Tuple[int, np.ndarray, int, str]]) -> Tuple[np.ndarray, np.ndarray] | None:
    if not rows:
        return None
    rows_sorted = sorted(rows, key=lambda x: x[0])
    features = []
    keys = []
    fallback_label = -1
    for idx, (_, feat, is_teacher, bk_str) in enumerate(rows_sorted):
        features.append(feat)
        if bk_str:
            keys.append(np.int64(bk_str))
        if is_teacher == 1:
            fallback_label = idx

    if not features:
        return None
    x = np.stack(features, axis=0)

    if len(keys) == len(rows_sorted):
        keys_np = np.array(keys, dtype=np.int64)
        m = np.max(keys_np)
        mask = (keys_np == m)
        probs = mask.astype(np.float32) / mask.sum()
        return x, probs
    else:
        if fallback_label < 0 or fallback_label >= x.shape[0]:
            return None
        probs = np.zeros(x.shape[0], dtype=np.float32)
        probs[fallback_label] = 1.0
        return x, probs

""",
    code, flags=re.DOTALL
)

with open("scripts/train_loh_teacher_ranker.py", "w") as f:
    f.write(code)
