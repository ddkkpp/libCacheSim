#!/usr/bin/env python3
import csv
import datetime as dt
import os
import sys

BEGIN = "<!-- AUTO_PENALTY_NOP_0316_BEGIN -->"
END = "<!-- AUTO_PENALTY_NOP_0316_END -->"


def load_rows(csv_path):
    rows = []
    if not os.path.isfile(csv_path):
        return rows
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def update_doc(csv_path, doc_path):
    if not os.path.isfile(doc_path):
        return 1
    with open(doc_path, "r", encoding="utf-8") as f:
        doc = f.read()
    s = doc.find(BEGIN)
    e = doc.find(END)
    if s < 0 or e < 0 or e < s:
        return 2
    e += len(END)

    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        BEGIN,
        f"_Auto-updated from `{csv_path}` at {ts}._",
        "",
        "| Scale | Formula | Pos | Status | MR | Byte MR | MQPS | Log |",
        "|---|---|---:|---|---:|---:|---:|---|",
    ]
    for r in load_rows(csv_path):
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} | `{}` |".format(
                r.get("scale", ""),
                r.get("formula", ""),
                r.get("pos", ""),
                r.get("status", ""),
                r.get("mr", "NA"),
                r.get("bmr", "NA"),
                r.get("mqps", "NA"),
                os.path.basename(r.get("log_path", "")),
            )
        )
    lines.append(END)

    new_doc = doc[:s] + "\n".join(lines) + doc[e:]
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
