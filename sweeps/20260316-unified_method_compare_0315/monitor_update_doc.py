#!/usr/bin/env python3
import csv
import time
from pathlib import Path

ROOT = Path('/home/dingkp/libCacheSim')
DOC = ROOT / 'docs/20260317-FULL_EXPERIMENT_RESULTS.md'
CSV = ROOT / 'tmp/unified_method_compare_0315/results.csv'
LOG = ROOT / 'tmp/unified_method_compare_0315/doc_update.log'
START = '<!-- METHOD_COMPARE_TABLE_START -->'
END = '<!-- METHOD_COMPARE_TABLE_END -->'


def load_rows():
    if not CSV.exists():
        return []
    rows = []
    with CSV.open(newline='') as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def render_table(rows):
    lines = []
    lines.append('| Phase | Trace | Method | Obj MR | Byte MR | 状态 | 日志 |')
    lines.append('|---|---|---|---:|---:|---|---|')
    if not rows:
        lines.append('| - | - | - | - | - | running | - |')
        return lines

    order_trace = {'meta': 0, '1063': 1, 'wiki': 2}
    order_phase = {'no_norm': 0, 'adaptive_norm': 1}
    order_method = {'asym': 0, 'alpha_mix': 1}

    rows2 = sorted(
        rows,
        key=lambda r: (
            order_phase.get(r.get('phase', ''), 9),
            order_trace.get(r.get('trace', ''), 9),
            order_method.get(r.get('method', ''), 9),
        ),
    )

    for r in rows2:
        mr = r.get('mr', 'NA')
        bmr = r.get('bmr', 'NA')
        status = r.get('status', '')
        lines.append(
            f"| {r.get('phase','')} | {r.get('trace','')} | {r.get('method','')} | {mr} | {bmr} | {status} | `{r.get('log_path','')}` |"
        )
    return lines


def update_doc(table_lines):
    text = DOC.read_text()
    s = text.find(START)
    e = text.find(END)
    if s < 0 or e < 0 or e < s:
        raise RuntimeError('table markers not found in doc')

    pre = text[: s + len(START)]
    post = text[e:]
    new_text = pre + '\n' + '\n'.join(table_lines) + '\n' + post
    DOC.write_text(new_text)


def log(msg):
    with LOG.open('a') as f:
        f.write(msg + '\n')


def main():
    last_count = -1
    while True:
        rows = load_rows()
        count = len(rows)
        if count != last_count:
            table = render_table(rows)
            update_doc(table)
            log(f'updated rows={count}')
            last_count = count
        time.sleep(3)


if __name__ == '__main__':
    main()
