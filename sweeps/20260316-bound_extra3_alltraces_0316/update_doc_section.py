#!/usr/bin/env python3
import csv
import datetime as dt
import os
import sys

TITLE = "## 26.3 Extra3 Across Traces (Auto)"
BEGIN = "<!-- AUTO_EXTRA3_ALLTRACES_0316_BEGIN -->"
END = "<!-- AUTO_EXTRA3_ALLTRACES_0316_END -->"
NOTE = (
    "本节记录 lo/hi 三组（lo00_hi099, lo01_hi100, lo00_hi100）在 meta/wiki 的结果；"
    "并发 6，完成一条即刷新。"
)


def load_ok_rows(csv_path):
    rows = []
    if not os.path.isfile(csv_path):
        return rows
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            if row.get("status") != "ok":
                continue
            if (row.get("final_mr") or "NA") == "NA":
                continue
            rows.append(row)
    return rows


def ensure_section(doc):
    if BEGIN in doc and END in doc:
        return doc
    appendix = (
        "\n\n"
        + TITLE
        + "\n\n"
        + NOTE
        + "\n\n"
        + BEGIN
        + "\n"
        + "_Auto-updated from `tmp/bound_extra3_alltraces_0316/results.csv`._"
        + "\n"
        + END
        + "\n"
    )
    return doc.rstrip() + appendix


def build_block(csv_path, rows):
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        BEGIN,
        f"_Auto-updated from `{csv_path}` at {ts}._",
        "",
        "| Trace | Config | MR24 | MR48 | MR72 | MR96 | Final MR | Byte MR | MQPS | Log |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        log_name = os.path.basename(row.get("log_path", ""))
        lines.append(
            "| {} | `{}` | {} | {} | {} | {} | {:.6f} | {:.6f} | {:.6f} | `{}` |".format(
                row["trace"],
                row["config"],
                row.get("mr24", "NA"),
                row.get("mr48", "NA"),
                row.get("mr72", "NA"),
                row.get("mr96", "NA"),
                float(row["final_mr"]),
                float(row["final_bmr"]),
                float(row["final_mqps"]),
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
    doc = ensure_section(doc)
    block = build_block(csv_path, load_ok_rows(csv_path))
    s = doc.find(BEGIN)
    e = doc.find(END)
    if s == -1 or e == -1 or e < s:
        return 2
    e += len(END)
    new_doc = doc[:s] + block + doc[e:]
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(new_doc)
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
