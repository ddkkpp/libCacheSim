with open("scripts/train_loh_teacher_ranker.py", "r") as f:
    code = f.read()

code = code.replace(
    '''        pred = int(np.argmax(logits))
        if pred == y:
            correct += 1''',
    '''        pred = int(np.argmax(logits))
        if y[pred] > 0:
            correct += 1'''
)

# stream training
code = code.replace(
    'target = torch.tensor([y], dtype=torch.long)',
    'target = torch.from_numpy(y).unsqueeze(0)'
)
code = code.replace(
    '''            pred = int(torch.argmax(logits).item())
            if pred == y:
                correct += 1''',
    '''            pred = int(torch.argmax(logits).item())
            if y[pred] > 0:
                correct += 1'''
)

with open("scripts/train_loh_teacher_ranker.py", "w") as f:
    f.write(code)
