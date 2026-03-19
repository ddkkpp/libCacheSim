#!/usr/bin/env python3
import csv
import os
import sys
from datetime import datetime

BEGIN = "<!-- AUTO_UNIFIED_0316_BEGIN -->"
END = "<!-- AUTO_UNIFIED_0316_END -->"


def source_from_config(cfg: str) -> str:
    if cfg.startswith("new_"):
        return "unified_new_0316"
    if cfg.startswith("sec21_"):
        return "sec21_1_matrix"
    if cfg.startswith("sec23_"):
        return "sec23_unified_4x3"
    return "other"


def fmt_num(v: str) -> str:
    if not v or v == "NA":
        return "NA"
    try:
        return f"{float(v):.6f}"
    except Exception:
        return v


def build_table(rows):
    lines = []
    lines.append("| Trace | Source | Config | Obj MR | Byte MR | MQPS | Log |")
    lines.append("|---|---|---|---:|---:|---:|---|")
    for r in rows:
        trace = r.get("trace", "")
        cfg = r.get("config", "")
        src = source_from_config(cfg)
        mr = fmt_num(r.get("final_mr", "NA"))
        bmr = fmt_num(r.get("final_bmr", "NA"))
        mqps = fmt_num(r.get("final_mqps", "NA"))
        logp = r.get("log_path", "")
        log_name = os.path.basename(logp) if logp else "NA"
        lines.append(f"| {trace} | {src} | `{cfg}` | {mr} | {bmr} | {mqps} | `{log_name}` |")
    return "\n".join(lines)


def main():
    if len(sys.argv) != 3:
        print("usage: update_doc_section.py <results_csv> <doc_path>", file=sys.stderr)
        return 2

    csv_path = sys.argv[1]
    doc_path = sys.argv[2]

    if not os.path.exists(csv_path) or not os.path.exists(doc_path):
        return 0

    rows = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("status", "") == "ok":
                rows.append(r)

    # Keep insertion order by completion history in csv.
    table = build_table(rows)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    block = (
        f"{BEGIN}\n"
        f"_Auto-updated from `tmp/unified_three_cfg_0316/results.csv` at {stamp}._\n\n"
        f"{table}\n"
        f"{END}"
    )

    with open(doc_path, "r", encoding="utf-8") as f:
        doc = f.read()

    if BEGIN in doc and END in doc:
        s = doc.index(BEGIN)
        e = doc.index(END) + len(END)
        new_doc = doc[:s] + block + doc[e:]
    else:
        section = (
            "\n\n## 25. Unified 0316 Rolling Results (Auto)\n\n"
            "格式对齐 23.4：每完成一条 case 自动刷新整表。\n\n"
            + block
            + "\n"
        )
        new_doc = doc + section

    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(new_doc)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
