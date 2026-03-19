#!/usr/bin/env python3
import csv
import datetime as dt
import os
import sys

BEGIN = "<!-- AUTO_1063_BOUND_W0_0316_BEGIN -->"
END = "<!-- AUTO_1063_BOUND_W0_0316_END -->"
SECTION_TITLE = "## 27.2 1063 Quantile Bound Effect (warmup=0, Auto)"
NOTE = (
    "本节说明：本轮使用 `params->current_timestamp` 作为分位更新进度计数，"
    "并显式设置 `LOH_ADAPTIVE_NORM_WARMUP=0`。"
)


def load_rows(csv_path):
    rows = []
    if not os.path.isfile(csv_path):
        return rows
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status") != "ok":
                continue
            if (row.get("final_mr") or "NA") == "NA":
                continue
            rows.append(row)
    return rows


def sort_key(row):
    cfg = row.get("config", "")
    ident = int(row.get("identity", "0"))
    return (cfg, ident)


def parse_lo_hi(cfg):
    # cfg examples: lo005_hi099, lo00_hi100, lo01_hi0995
    lo = "?"
    hi = "?"
    if "_" not in cfg:
        return lo, hi
    parts = cfg.split("_")
    if len(parts) != 2 or not parts[0].startswith("lo") or not parts[1].startswith("hi"):
        return lo, hi

    lo_digits = parts[0][2:]
    hi_digits = parts[1][2:]

    if lo_digits.isdigit():
        if len(lo_digits) <= 2:
            lo = str(int(lo_digits) / 100.0)
        else:
            lo = str(int(lo_digits) / 1000.0)

    if hi_digits.isdigit():
        if len(hi_digits) <= 3:
            hi = str(int(hi_digits) / 100.0)
        else:
            hi = str(int(hi_digits) / 1000.0)

    return lo, hi


def build_block(csv_path, rows):
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        BEGIN,
        f"_Auto-updated from `{csv_path}` at {ts}._",
        "",
        "| Raw->Out | Norm | MR24 | MR48 | MR72 | MR96 | Final MR | Byte MR | MQPS | Log |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in sorted(rows, key=sort_key):
        log_name = os.path.basename(row.get("log_path", ""))
        identity = int(row.get("identity", "0"))
        raw_to_out = "raw" if identity == 1 else "log1p"
        lo, hi = parse_lo_hi(row.get("config", ""))
        norm_desc = f"adaptive(warmup=0, q_input=out, lo={lo}, hi={hi})"
        lines.append(
            "| `{}` | `{}` | {} | {} | {} | {} | {:.6f} | {:.6f} | {:.6f} | `{}` |".format(
                raw_to_out,
                norm_desc,
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


def ensure_section(doc):
    if BEGIN in doc and END in doc:
        return doc
    appendix = (
        "\n\n"
        + SECTION_TITLE
        + "\n\n"
        + NOTE
        + "\n\n"
        + BEGIN
        + "\n"
        + "_Auto-updated from `tmp/1063_bound_effect_0316_w0_identity/results.csv`._"
        + "\n"
        + END
        + "\n"
    )
    return doc.rstrip() + appendix


def update_doc(csv_path, doc_path):
    if not os.path.isfile(doc_path):
        return 1
    with open(doc_path, "r", encoding="utf-8") as f:
        doc = f.read()

    doc = ensure_section(doc)
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
