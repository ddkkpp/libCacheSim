#!/usr/bin/env python3
import csv
import datetime as dt
import os
import sys

BEGIN = "<!-- AUTO_TRANSFORM_Q0_HITMISS1_ORIG3_CACHE01_0317_BEGIN -->"
END = "<!-- AUTO_TRANSFORM_Q0_HITMISS1_ORIG3_CACHE01_0317_END -->"


def load_rows(csv_path):
    rows = []
    if not os.path.isfile(csv_path):
        return rows
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def build_block(csv_path, rows):
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        BEGIN,
        f"_Auto-updated from `{csv_path}` at {ts}._",
        "",
        "| Trace | Raw->Out | Norm | TransformQ | HitMiss | Final MR | Byte MR | MQPS | Log |",
        "|:--|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in sorted(rows, key=lambda r: r.get("trace", "")):
        if row.get("status", "") != "ok":
            continue
        log_name = os.path.basename(row.get("log_path", ""))
        fmr = row.get("final_mr", "NA")
        fbmr = row.get("final_bmr", "NA")
        fmqps = row.get("final_mqps", "NA")
        lines.append(
            "| {} | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 1 | {} | {} | {} | `{}` |".format(
                row.get("trace", ""),
                f"{float(fmr):.6f}" if fmr not in ("", "NA") else "NA",
                f"{float(fbmr):.6f}" if fbmr not in ("", "NA") else "NA",
                f"{float(fmqps):.6f}" if fmqps not in ("", "NA") else "NA",
                log_name,
            )
        )
    lines.append(END)
    return "\n".join(lines)


def update_doc(csv_path, doc_path):
    if not os.path.isfile(doc_path):
        return 1
    with open(doc_path, "r", encoding="utf-8") as f:
        doc = f.read()

    block = build_block(csv_path, load_rows(csv_path))
    s = doc.find(BEGIN)
    e = doc.find(END)
    if s == -1 or e == -1 or e < s:
        return 2
    e += len(END)

    updated = doc[:s] + block + doc[e:]
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
