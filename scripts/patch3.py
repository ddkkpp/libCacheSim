with open("scripts/train_loh_teacher_ranker.py", "r") as f:
    code = f.read()

# fix compute_top1_groups
code = code.replace(
    'def compute_top1_groups(groups: List[Tuple[np.ndarray, int]], weights: np.ndarray) -> float:',
    'def compute_top1_groups(groups: List[Tuple[np.ndarray, np.ndarray]], weights: np.ndarray) -> float:'
)
code = code.replace(
    '''        pred = int(np.argmax(logits))
        if pred == y:
            correct += 1''',
    '''        pred = int(np.argmax(logits))
        if y[pred] > 0:
            correct += 1'''
)

with open("scripts/train_loh_teacher_ranker.py", "w") as f:
    f.write(code)
