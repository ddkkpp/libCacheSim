#!/usr/bin/env python3
import csv
import datetime as dt
import os
import sys

BEGIN = "<!-- AUTO_PENALTY_NOP_0316_BEGIN -->"
END = "<!-- AUTO_PENALTY_NOP_0316_END -->"

COMPARE_BEGIN = "<!-- AUTO_PENALTY_COMPARE_0316_BEGIN -->"
COMPARE_END = "<!-- AUTO_PENALTY_COMPARE_0316_END -->"


def read_rows(csv_path):
    rows = []
    if not os.path.isfile(csv_path):
        return rows
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows


def replace_between(text, begin, end, body):
    s = text.find(begin)
    e = text.find(end)
    if s < 0 or e < 0 or e < s:
        return None
    e += len(end)
    return text[:s] + body + text[e:]


def build_20_2_block(csv_path, rows):
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        BEGIN,
        f"_Auto-updated from `{csv_path}` at {ts}._",
        "",
        "| Variant | Wait Mode | Status | MR | Byte MR | MQPS | Log |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for r in rows:
        lines.append(
            "| {} | {} | {} | {} | {} | {} | `{}` |".format(
                r.get("variant", ""),
                r.get("wait_mode", ""),
                r.get("status", ""),
                r.get("mr", "NA"),
                r.get("bmr", "NA"),
                r.get("mqps", "NA"),
                os.path.basename(r.get("log_path", "")),
            )
        )
    lines.append(END)
    return "\n".join(lines)


def build_compare_block(rows):
    by_variant = {r.get("variant"): r for r in rows if r.get("status") == "ok"}
    log1p = by_variant.get("log1p")
    blocked = by_variant.get("log1p_blocked")
    if not log1p or not blocked:
        return None

    mr_delta = float(blocked["mr"]) - float(log1p["mr"])
    bmr_delta = float(blocked["bmr"]) - float(log1p["bmr"])
    mqps_delta = float(blocked["mqps"]) - float(log1p["mqps"])

    lines = [
        COMPARE_BEGIN,
        "| 对照项 | LOG1P(nonblocked) | LOG1P+blocked | 差值(blocked-log1p) |",
        "|---|---:|---:|---:|",
        f"| MR | {float(log1p['mr']):.6f} | {float(blocked['mr']):.6f} | {mr_delta:+.6f} |",
        f"| Byte MR | {float(log1p['bmr']):.6f} | {float(blocked['bmr']):.6f} | {bmr_delta:+.6f} |",
        f"| MQPS | {float(log1p['mqps']):.2f} | {float(blocked['mqps']):.2f} | {mqps_delta:+.2f} |",
        COMPARE_END,
    ]
    return "\n".join(lines)


def update_doc(csv_path, doc_path):
    if not os.path.isfile(doc_path):
        return 1
    rows = read_rows(csv_path)
    with open(doc_path, "r", encoding="utf-8") as f:
        doc = f.read()

    block_20_2 = build_20_2_block(csv_path, rows)
    new_doc = replace_between(doc, BEGIN, END, block_20_2)
    if new_doc is None:
        return 2

    cmp_block = build_compare_block(rows)
    if cmp_block is not None:
        replaced = replace_between(new_doc, COMPARE_BEGIN, COMPARE_END, cmp_block)
        if replaced is None:
            return 3
        new_doc = replaced

    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(new_doc)
    return 0


def main():
    if len(sys.argv) != 3:
        print("usage: update_doc_section.py <results_csv> <doc_path>")
        return 2
    rc = update_doc(sys.argv[1], sys.argv[2])
    print("ok" if rc == 0 else f"err={rc}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
