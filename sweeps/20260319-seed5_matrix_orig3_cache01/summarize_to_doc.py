#!/usr/bin/env python3
import argparse
import csv
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

BEGIN_MARKER = "<!-- AUTO_SEED5_MATRIX_ORIG3_CACHE01_20260319_BEGIN -->"
END_MARKER = "<!-- AUTO_SEED5_MATRIX_ORIG3_CACHE01_20260319_END -->"

SCENARIO_TITLES = {
    "S1_BASELINE": "不改变配置",
    "S2_ADAPTIVE_BUDGET": "LOH_ADAPTIVE_BUDGET=0",
    "S3_CAND_GRID": "LOH_RANDOM_CANDIDATES × LOH_STRUCTURED_CANDIDATES 网格",
    "S4_MRW_SWEEP": "LOH_MISS_RATIO_WEIGHT 阶梯 0.1",
    "S5_REWARD_PATH": "9 种 reward path",
    "S6_RL_ALGO": "RL Algo 切换",
    "S7_OBS_HITMISS": "LOH_INCLUDE_WEIGHTS_IN_OBS / LOH_INCLUDE_HIT_MISS_FEATURES 组合",
    "S8_FEATURE_MODE": "三种 feature/normalization 模式",
}

SCENARIO_ORDER = [
    "S1_BASELINE",
    "S2_ADAPTIVE_BUDGET",
    "S3_CAND_GRID",
    "S4_MRW_SWEEP",
    "S5_REWARD_PATH",
    "S6_RL_ALGO",
    "S7_OBS_HITMISS",
    "S8_FEATURE_MODE",
]

TRACE_ORDER = ["1063", "wiki", "meta"]

# 将 28.1 的默认配置结果同步注入 28.5/28.6/28.7/28.8，便于同节对照。
BASELINE_INJECT_VARIANTS = {
    "S5_REWARD_PATH": "baseline_default(no_reward_override)",
    "S6_RL_ALGO": "baseline_SAC(default_algo)",
    "S7_OBS_HITMISS": "baseline_w0_h0(W=0,H=0)",
    "S8_FEATURE_MODE": "baseline_log1p_adaptive(ID=0,LOG1P=1,ADAPT=1)",
}


def safe_float(v: str):
    try:
        return float(v)
    except Exception:
        return None


def mean_var(values):
    if not values:
        return (None, None)
    if len(values) == 1:
        return (values[0], 0.0)
    m = sum(values) / len(values)
    v = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return (m, v)


def fmt(x, nd=6):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "NA"
    return f"{x:.{nd}f}"


def bold_if_min(value, min_value):
    if value is None:
        return "NA"
    text = fmt(value)
    if min_value is None:
        return text
    if abs(value - min_value) <= 1e-12:
        return f"**{text}**"
    return text


def render(results_csv: Path) -> str:
    groups = defaultdict(list)
    failed = defaultdict(int)

    with results_csv.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            scenario = row["scenario"].strip()
            variant = row["variant"].strip()
            trace = row["trace"].strip()
            status = row["status"].strip()
            key = (scenario, variant, trace)

            if status == "ok":
                mr = safe_float(row["final_mr"])
                bmr = safe_float(row["final_bmr"])
                mqps = safe_float(row["final_mqps"])
                if mr is not None and bmr is not None and mqps is not None:
                    groups[key].append((mr, bmr, mqps))
            else:
                failed[key] += 1

    # 将 S1 默认结果拷贝到 5/6/7/8 节的“baseline 对照配置”行。
    for scenario, injected_variant in BASELINE_INJECT_VARIANTS.items():
        for trace in TRACE_ORDER:
            base_key = ("S1_BASELINE", "default", trace)
            target_key = (scenario, injected_variant, trace)
            base_vals = groups.get(base_key, [])
            if base_vals:
                groups[target_key] = list(base_vals)
            if base_key in failed:
                failed[target_key] = failed[base_key]

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    lines.append(f"_Auto-updated from `{results_csv}` at {ts}._")
    lines.append("")
    lines.append("统计口径：每组按 `trace × scenario × variant` 聚合 5 个 seed 的 `ok` 结果，表中给出均值与样本方差（var）。")
    lines.append("")

    for idx, scenario in enumerate(SCENARIO_ORDER, start=1):
        title = SCENARIO_TITLES.get(scenario, scenario)
        lines.append(f"### 28.{idx} {title}")
        lines.append("")
        lines.append("| Trace | Variant | N(ok) | MR mean | MR var | BMR mean | BMR var | MQPS mean | MQPS var | Failed |")
        lines.append("|:--|:--|---:|---:|---:|---:|---:|---:|---:|---:|")

        variant_set = sorted({v for (s, v, _t) in set(list(groups.keys()) + list(failed.keys())) if s == scenario})
        if not variant_set:
            lines.append("| (pending) | - | 0 | NA | NA | NA | NA | NA | NA | 0 |")
            lines.append("")
            continue

        for trace in TRACE_ORDER:
            per_trace_mr = []
            per_trace_bmr = []
            for variant in variant_set:
                vals = groups.get((scenario, variant, trace), [])
                mr_m, _mr_v = mean_var([x[0] for x in vals])
                bmr_m, _bmr_v = mean_var([x[1] for x in vals])
                if mr_m is not None:
                    per_trace_mr.append(mr_m)
                if bmr_m is not None:
                    per_trace_bmr.append(bmr_m)

            min_mr = min(per_trace_mr) if per_trace_mr else None
            min_bmr = min(per_trace_bmr) if per_trace_bmr else None

            for variant in variant_set:
                key = (scenario, variant, trace)
                vals = groups.get(key, [])
                mr_m, mr_v = mean_var([x[0] for x in vals])
                bmr_m, bmr_v = mean_var([x[1] for x in vals])
                mqps_m, mqps_v = mean_var([x[2] for x in vals])
                fail_n = failed.get(key, 0)
                lines.append(
                    "| {trace} | {variant} | {nok} | {mr_m} | {mr_v} | {bmr_m} | {bmr_v} | {mqps_m} | {mqps_v} | {fail_n} |".format(
                        variant=variant,
                        trace=trace,
                        nok=len(vals),
                        mr_m=bold_if_min(mr_m, min_mr),
                        mr_v=fmt(mr_v),
                        bmr_m=bold_if_min(bmr_m, min_bmr),
                        bmr_v=fmt(bmr_v),
                        mqps_m=fmt(mqps_m),
                        mqps_v=fmt(mqps_v),
                        fail_n=fail_n,
                    )
                )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def replace_block(doc_text: str, payload: str) -> str:
    b = doc_text.find(BEGIN_MARKER)
    e = doc_text.find(END_MARKER)
    if b == -1 or e == -1 or e < b:
        raise RuntimeError("document markers not found")
    b_end = b + len(BEGIN_MARKER)
    return doc_text[:b_end] + "\n" + payload + doc_text[e:]


def main():
    parser = argparse.ArgumentParser(description="Update section 27 auto block with mean/var tables.")
    parser.add_argument("--results", required=True)
    parser.add_argument("--doc", required=True)
    args = parser.parse_args()

    results = Path(args.results)
    doc = Path(args.doc)

    if not results.exists():
        raise SystemExit(f"results not found: {results}")
    if not doc.exists():
        raise SystemExit(f"doc not found: {doc}")

    payload = render(results)
    old = doc.read_text(encoding="utf-8")
    new = replace_block(old, payload)
    doc.write_text(new, encoding="utf-8")


if __name__ == "__main__":
    main()
