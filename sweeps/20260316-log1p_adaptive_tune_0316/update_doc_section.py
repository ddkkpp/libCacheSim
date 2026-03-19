#!/usr/bin/env python3
import csv
import datetime as dt
import os
import sys

BEGIN = "<!-- AUTO_LOG1P_TUNE_0316_BEGIN -->"
END = "<!-- AUTO_LOG1P_TUNE_0316_END -->"


def load_ok_rows(csv_path: str):
    rows = []
    if not os.path.isfile(csv_path):
        return rows
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("status") != "ok":
                continue
            if (r.get("final_mr") or "NA") == "NA":
                continue
            rows.append(r)
    return rows


def build_block(csv_path: str, rows):
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    lines.append(BEGIN)
    lines.append(f"_Auto-updated from `{csv_path}` at {ts}._")
    lines.append("")
    lines.append("| Trace | Config | Obj MR | Byte MR | MQPS | Log |")
    lines.append("|---|---|---:|---:|---:|---|")
    for r in rows:
        log_name = os.path.basename(r.get("log_path", ""))
        lines.append(
            f"| {r['trace']} | `{r['config']}` | {float(r['final_mr']):.6f} | {float(r['final_bmr']):.6f} | {float(r['final_mqps']):.6f} | `{log_name}` |"
        )
    lines.append(END)
    return "\n".join(lines)


def ensure_section(doc_text: str):
    if BEGIN in doc_text and END in doc_text:
        return doc_text
    section = []
    section.append("\n\n## 26. Log1p Adaptive Tune 0316 (Auto)\n")
    section.append("仅记录 2026-03-16 调参批次：收窄分位区间 + 增大 warmup。\n")
    section.append(BEGIN)
    section.append("_Auto-updated from `tmp/log1p_adaptive_tune_0316/results.csv`._")
    section.append(END)
    return doc_text.rstrip() + "\n" + "\n".join(section) + "\n"


def update_doc(csv_path: str, doc_path: str):
    rows = load_ok_rows(csv_path)
    if not os.path.isfile(doc_path):
        return 1

    with open(doc_path, "r", encoding="utf-8") as f:
        doc = f.read()

    doc = ensure_section(doc)
    new_block = build_block(csv_path, rows)

    start = doc.find(BEGIN)
    end = doc.find(END)
    if start == -1 or end == -1 or end < start:
        return 2
    end += len(END)

    updated = doc[:start] + new_block + doc[end:]
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(updated)
    return 0


def main():
    if len(sys.argv) != 3:
        print("usage: update_doc_section.py <results_csv> <doc_path>")
        return 2
    rc = update_doc(sys.argv[1], sys.argv[2])
    if rc == 0:
        print("ok")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
