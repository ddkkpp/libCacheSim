#!/usr/bin/env python3
import csv
import datetime as dt
import os
import sys

BEGIN = "<!-- AUTO_HITMISS_LO00_HI100_FULL_0316_BEGIN -->"
END = "<!-- AUTO_HITMISS_LO00_HI100_FULL_0316_END -->"


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
        text = f.read()
    s = text.find(BEGIN)
    e = text.find(END)
    if s < 0 or e < 0 or e < s:
        return 2
    e += len(END)

    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        BEGIN,
        f"_Auto-updated from `{csv_path}` at {ts}._",
        "",
        "| Trace | Status | RC | Final MR | Byte MR | MQPS | Log |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for r in load_rows(csv_path):
        log_name = os.path.basename(r.get("log_path", ""))
        lines.append(
            "| {} | {} | {} | {} | {} | {} | `{}` |".format(
                r.get("trace", ""),
                r.get("status", ""),
                r.get("rc", ""),
                r.get("final_mr", "NA"),
                r.get("final_bmr", "NA"),
                r.get("final_mqps", "NA"),
                log_name,
            )
        )
    lines.append(END)

    new_text = text[:s] + "\n".join(lines) + text[e:]
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(new_text)
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
