#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
from pathlib import Path
from typing import Optional, Tuple


def _count_non_comment_lines(path: Path) -> Optional[int]:
    try:
        n = 0
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                n += 1
        return n
    except Exception:
        return None


def _to_float(x: str) -> Optional[float]:
    try:
        v = float(x)
    except Exception:
        return None
    if v != v:  # NaN
        return None
    return v


def _load_summary_rows(summary_csv: Path):
    with summary_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _pick_best(rows) -> Tuple[Optional[dict], list]:
    scored = []
    for r in rows:
        mr = _to_float(r.get("miss_ratio_mean", ""))
        if mr is None:
            continue
        scored.append((mr, r))
    scored.sort(key=lambda t: t[0])
    best = scored[0][1] if scored else None
    top5 = [r for _, r in scored[:5]]
    return best, top5


def main() -> int:
    ap = argparse.ArgumentParser(description="Append a sweep summary into 20251205-sweep_results.md")
    ap.add_argument("--sweep-dir", required=True, help="Path like sweeps/<SWEEP_ID>")
    ap.add_argument("--configs", default="", help="Optional configs file path")
    ap.add_argument("--md", default="20251205-sweep_results.md", help="Markdown file to append")
    args = ap.parse_args()

    sweep_dir = Path(args.sweep_dir)
    summary_csv = sweep_dir / "summary.csv"
    results_csv = sweep_dir / "results.csv"

    if not summary_csv.exists():
        raise SystemExit(f"summary.csv not found: {summary_csv}")
    if not results_csv.exists():
        raise SystemExit(f"results.csv not found: {results_csv}")

    rows = _load_summary_rows(summary_csv)
    best, top5 = _pick_best(rows)

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md_path = Path(args.md)

    section_title = f"## sweep {sweep_dir.name}"
    if md_path.exists():
        try:
            existing = md_path.read_text(encoding="utf-8")
            if section_title in existing:
                print(f"Skip append: already present: {section_title}")
                return 0
        except Exception:
            pass

    header = f"\n\n## sweep {sweep_dir.name}（{now}）\n\n"
    meta = [
        f"- 输出目录: `{sweep_dir}`",
        f"- results: `{results_csv}`",
        f"- summary: `{summary_csv}`",
    ]
    if args.configs:
        meta.append(f"- configs: `{args.configs}`")

        cfg_path = Path(args.configs)
        n_cfg = _count_non_comment_lines(cfg_path) if cfg_path.exists() else None
        if n_cfg is not None:
            meta.append(f"- configs（非空/非注释）条数: {n_cfg}")

    runs_txt = sweep_dir / "runs.txt"
    if runs_txt.exists():
        meta.append(f"- runs: `{runs_txt}`")

    meta.append("- 完整配置清单: 见 results.csv 的 config 列（每行一个 run）")

    body_lines = [header, "\n".join(meta), "\n"]

    if best is None:
        body_lines.append("- best: NA（summary.csv 中没有可解析的 miss_ratio_mean）\n")
    else:
        body_lines.append(
            "- best: "
            f"idx={best.get('idx')} n={best.get('n')} "
            f"OMR(mean)={best.get('miss_ratio_mean')} std={best.get('miss_ratio_std')} "
            f"BMR(mean)={best.get('byte_miss_ratio_mean')} thr(mean)={best.get('throughput_mqps_mean')}\n"
        )
        body_lines.append("\nTop-5（按 OMR mean 升序）:\n\n")
        body_lines.append("| rank | idx | n | OMR mean | OMR std | BMR mean | thr mean |\n")
        body_lines.append("| --- | --- | --- | --- | --- | --- | --- |\n")
        for i, r in enumerate(top5, start=1):
            body_lines.append(
                f"| {i} | {r.get('idx')} | {r.get('n')} | {r.get('miss_ratio_mean')} | {r.get('miss_ratio_std')} | {r.get('byte_miss_ratio_mean')} | {r.get('throughput_mqps_mean')} |\n"
            )

    md_path.parent.mkdir(parents=True, exist_ok=True)
    with md_path.open("a", encoding="utf-8") as f:
        f.write("".join(body_lines))

    print(f"Appended sweep summary to {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
