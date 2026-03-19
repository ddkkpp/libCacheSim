#!/usr/bin/env python3
"""
解析所有 48 组 penalty_sweep 的 Python 日志 (ac_sb3_*.log)，
分别计算每种 scale/formula/pos 组合下各阶段的值分布和 clip 比例。
"""
import os
import re
import sys
import glob
import numpy as np
from collections import defaultdict

SWEEP_DIR = "/home/dingkp/libCacheSim/tmp/penalty_sweep"
ROOT_DIR = "/home/dingkp/libCacheSim"

# 解析 [PenaltyTrace][event] 行
EVENT_RE = re.compile(
    r'\[PenaltyTrace\]\[event\]\s+'
    r'pos=(\d+)\s+type=(\w+)\s+distance=([\-\d.]+)\s+'
    r'obj_size=([\d.]+)\s+evicted_count=(\d+)\s+'
    r'evicted_bytes=([\d.]+)\s+scale=([\d.NA]+)\s+'
    r'obj_contrib=([\d.]+)\s+byte_contrib=([\d.]+)'
)
# 解析 [PenaltyTrace][final] 行
FINAL_RE = re.compile(
    r'\[PenaltyTrace\]\[final\]\s+'
    r'pos=(\d+)\s+formula=(\w+)\s+raw_penalty_count=(\d+)\s+'
    r'pos_events=(\d+)\s+neg_events=(\d+)\s+good_rate=([\d.]+)\s+'
    r'obj_penalty=([\d.]+)\s+byte_penalty=([\d.]+)\s+'
    r'penalty=([\d.]+)\s+reward_preclip=([\-\d.]+)\s+final_reward=([\-\d.]+)'
)

def get_python_log(sweep_log_path):
    """从 sweep 日志中提取对应的 Python 日志路径"""
    with open(sweep_log_path, 'r', errors='replace') as f:
        for line in f:
            m = re.search(r'Log: (ac_sb3_[^)]+)', line)
            if m:
                return os.path.join(ROOT_DIR, m.group(1))
    return None

def parse_python_log(filepath):
    """解析 Python 日志，提取 event 和 final 数据"""
    neg_scales = []
    neg_distances = []
    neg_obj_contribs = []
    pos_distances = []

    finals = []

    with open(filepath, 'r', errors='replace') as f:
        for line in f:
            if '[PenaltyTrace]' not in line:
                continue
            m = EVENT_RE.search(line)
            if m:
                if m.group(2) == 'negative':
                    neg_distances.append(float(m.group(3)))
                    s = m.group(7)
                    if s != 'NA':
                        neg_scales.append(float(s))
                    neg_obj_contribs.append(float(m.group(8)))
                elif m.group(2) == 'positive':
                    pos_distances.append(abs(float(m.group(3))))
                continue

            m = FINAL_RE.search(line)
            if m:
                finals.append({
                    'raw_penalty_count': int(m.group(3)),
                    'pos_events': int(m.group(4)),
                    'neg_events': int(m.group(5)),
                    'good_rate': float(m.group(6)),
                    'obj_penalty': float(m.group(7)),
                    'byte_penalty': float(m.group(8)),
                    'penalty': float(m.group(9)),
                    'reward_preclip': float(m.group(10)),
                    'final_reward': float(m.group(11)),
                })

    return {
        'neg_scales': neg_scales,
        'neg_distances': neg_distances,
        'neg_obj_contribs': neg_obj_contribs,
        'pos_distances': pos_distances,
        'finals': finals,
    }

def dist_stats(arr):
    if len(arr) == 0:
        return None
    a = np.array(arr)
    return {
        'n': len(a),
        'min': float(a.min()),
        'p1': float(np.percentile(a, 1)),
        'p5': float(np.percentile(a, 5)),
        'p10': float(np.percentile(a, 10)),
        'p25': float(np.percentile(a, 25)),
        'median': float(np.percentile(a, 50)),
        'p75': float(np.percentile(a, 75)),
        'p90': float(np.percentile(a, 90)),
        'p95': float(np.percentile(a, 95)),
        'p99': float(np.percentile(a, 99)),
        'max': float(a.max()),
        'mean': float(a.mean()),
        'std': float(a.std()),
    }

def clip_ratio(arr, lo=-1.0, hi=1.0):
    if len(arr) == 0:
        return 0.0, 0.0, 0.0
    a = np.array(arr)
    n = len(a)
    return float(np.sum(a < lo))/n, float(np.sum(a > hi))/n, float(np.sum((a < lo)|(a > hi)))/n

def fmt(v, decimals=6):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A"
    return f"{v:.{decimals}f}"

def load_summary():
    results = {}
    sf = os.path.join(SWEEP_DIR, "summary.csv")
    if not os.path.exists(sf):
        return results
    with open(sf, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('scale'):
                continue
            parts = line.split(',')
            if len(parts) >= 5:
                key = f"{parts[0]}_{parts[1]}_pos{parts[2]}"
                results[key] = {'mr': float(parts[3]), 'bmr': float(parts[4])}
    return results


def main():
    summary = load_summary()

    # 找到所有 48 组
    sweep_logs = sorted(glob.glob(os.path.join(SWEEP_DIR, "*.log")))
    sweep_logs = [f for f in sweep_logs if os.path.basename(f) not in
                  ('batch_run.log',)]

    all_data = {}
    total_finals = 0
    total_events = 0

    for sweep_log in sweep_logs:
        base = os.path.basename(sweep_log)
        if base.endswith('.log'):
            base = base[:-4]
        # filter out non-combo files
        if not any(base.startswith(s) for s in ('binary', 'log', 'reciprocal', 'survival')):
            continue

        python_log = get_python_log(sweep_log)
        if not python_log or not os.path.exists(python_log):
            print(f"  SKIP {base}: python log not found", file=sys.stderr)
            continue

        # Parse combo name
        parts = base.split('_')
        if parts[0] in ('binary', 'log', 'reciprocal', 'survival'):
            scale = parts[0]
            if parts[1] == 'one' and len(parts) >= 4:
                formula = 'one_minus'
                pos_str = parts[3]
            else:
                formula = parts[1]
                pos_str = parts[2]
        else:
            continue

        print(f"  处理 {base} ({python_log})...", file=sys.stderr)
        data = parse_python_log(python_log)
        n_finals = len(data['finals'])
        n_events = len(data['neg_distances']) + len(data['pos_distances'])
        total_finals += n_finals
        total_events += n_events

        mr_info = summary.get(base, {})

        all_data[base] = {
            'scale': scale,
            'formula': formula,
            'pos': pos_str,
            'data': data,
            'n_finals': n_finals,
            'n_events': n_events,
            'mr': mr_info.get('mr', float('nan')),
        }

    print(f"\n总计: {len(all_data)} 组, {total_finals} finals, {total_events} events", file=sys.stderr)

    # ====== 生成文档 ======
    lines = []
    lines.append("# Penalty Sweep 各组合分布分析（基于完整 Python 日志）\n")
    lines.append(f"数据来源: 48 组 penalty_sweep Python 日志")
    lines.append(f"总计: {total_finals:,} 个 finalization 周期, {total_events:,} 个事件\n")

    # ====== 计算管道说明 ======
    lines.append("## 一、计算管道\n")
    lines.append("```")
    lines.append("distance(d) → scale(d) → obj_contrib=(1/evicted_count)×scale → obj_penalty=Σobj_contrib")
    lines.append("                                                              → byte_penalty=Σbyte_contrib")
    lines.append("             ↓")
    lines.append("penalty = w_obj × obj_penalty + w_byte × byte_penalty")
    lines.append("             ↓")
    lines.append("reward_preclip = formula(penalty, good_rate)")
    lines.append("             ↓")
    lines.append("final_reward = clip(reward_preclip, -1, 1)")
    lines.append("```\n")

    # ====== 按 Scale 分组 ======
    lines.append("## 二、按 Scale 模式分组分析\n")

    for scale_name in ['binary', 'log', 'reciprocal', 'survival']:
        # Collect all finals for this scale
        all_scales_vals = []
        all_distances = []
        all_obj_penalties = []
        all_penalties = []
        all_good_rates = []

        for name, r in all_data.items():
            if r['scale'] == scale_name:
                all_scales_vals.extend(r['data']['neg_scales'])
                all_distances.extend(r['data']['neg_distances'])
                for f in r['data']['finals']:
                    all_obj_penalties.append(f['obj_penalty'])
                    all_penalties.append(f['penalty'])
                    all_good_rates.append(f['good_rate'])

        lines.append(f"### 2.{['binary','log','reciprocal','survival'].index(scale_name)+1} {scale_name}\n")

        if scale_name == 'binary':
            lines.append("公式: `scale(d) = 1.0` (恒定)\n")
        elif scale_name == 'log':
            lines.append("公式: `scale(d) = max(0, 1 - log1p(d)/log1p(dmax))`\n")
        elif scale_name == 'reciprocal':
            lines.append("公式: `scale(d) = 1/max(d, 1)`\n")
        elif scale_name == 'survival':
            lines.append("公式: `scale(d) = 1 - F(d)` (F=经验CDF)\n")

        # Scale values
        st = dist_stats(all_scales_vals)
        if st:
            lines.append(f"**scale(d) 分布** (n={st['n']:,}):")
            lines.append(f"| p1 | p10 | p25 | median | p75 | p90 | p99 | mean | std |")
            lines.append(f"|---:|----:|----:|-------:|----:|----:|----:|-----:|----:|")
            lines.append(f"| {fmt(st['p1'])} | {fmt(st['p10'])} | {fmt(st['p25'])} | {fmt(st['median'])} | {fmt(st['p75'])} | {fmt(st['p90'])} | {fmt(st['p99'])} | {fmt(st['mean'])} | {fmt(st['std'])} |")
            lines.append("")

        # Distance
        st = dist_stats(all_distances)
        if st:
            lines.append(f"**负样本 distance 分布** (n={st['n']:,}):")
            lines.append(f"| p1 | p10 | median | p90 | p99 | mean |")
            lines.append(f"|---:|----:|-------:|----:|----:|-----:|")
            lines.append(f"| {st['p1']:.0f} | {st['p10']:.0f} | {st['median']:.0f} | {st['p90']:.0f} | {st['p99']:.0f} | {st['mean']:.0f} |")
            lines.append("")

        # obj_penalty
        st = dist_stats(all_obj_penalties)
        if st:
            lines.append(f"**obj_penalty 分布** (n={st['n']:,}):")
            lines.append(f"| min | p10 | p25 | median | p75 | p90 | max | mean |")
            lines.append(f"|----:|----:|----:|-------:|----:|----:|----:|-----:|")
            lines.append(f"| {fmt(st['min'])} | {fmt(st['p10'])} | {fmt(st['p25'])} | {fmt(st['median'])} | {fmt(st['p75'])} | {fmt(st['p90'])} | {fmt(st['max'])} | {fmt(st['mean'])} |")
            lines.append("")

        lines.append("")

    # ====== 按 Formula 分组 ======
    lines.append("## 三、按 Formula 模式分组分析\n")

    for formula_name in ['relative', 'centered', 'one_minus', 'neg', 'net', 'net2']:
        all_penalties = []
        all_rpc = []
        all_rf = []
        all_gr = []
        all_op = []

        for name, r in all_data.items():
            if r['formula'] == formula_name:
                for f in r['data']['finals']:
                    all_op.append(f['obj_penalty'])
                    all_penalties.append(f['penalty'])
                    all_rpc.append(f['reward_preclip'])
                    all_rf.append(f['final_reward'])
                    all_gr.append(f['good_rate'])

        lines.append(f"### 3.{['relative','centered','one_minus','neg','net','net2'].index(formula_name)+1} {formula_name}\n")

        if formula_name == 'relative':
            lines.append("公式: `reward = (baseline - penalty) / baseline`\n")
        elif formula_name == 'centered':
            lines.append("公式: `reward = 1 - 2×penalty`\n")
        elif formula_name == 'one_minus':
            lines.append("公式: `reward = 1 - penalty`\n")
        elif formula_name == 'neg':
            lines.append("公式: `reward = -penalty`\n")
        elif formula_name == 'net':
            lines.append("公式: `reward = good_rate - penalty`\n")
        elif formula_name == 'net2':
            lines.append("公式: `reward = (2×good_rate - 1) - penalty`\n")

        n = len(all_rpc)
        lines.append(f"样本数: {n:,}\n")

        # Penalty
        st = dist_stats(all_penalties)
        if st:
            lines.append(f"**penalty 分布**:")
            lines.append(f"| min | p10 | median | p90 | max | mean |")
            lines.append(f"|----:|----:|-------:|----:|----:|-----:|")
            lines.append(f"| {fmt(st['min'])} | {fmt(st['p10'])} | {fmt(st['median'])} | {fmt(st['p90'])} | {fmt(st['max'])} | {fmt(st['mean'])} |")
            lines.append("")

        # good_rate
        st = dist_stats(all_gr)
        if st:
            lines.append(f"**good_rate 分布**:")
            lines.append(f"| min | p10 | median | p90 | max | mean |")
            lines.append(f"|----:|----:|-------:|----:|----:|-----:|")
            lines.append(f"| {fmt(st['min'])} | {fmt(st['p10'])} | {fmt(st['median'])} | {fmt(st['p90'])} | {fmt(st['max'])} | {fmt(st['mean'])} |")
            lines.append("")

        # reward_preclip
        st = dist_stats(all_rpc)
        if st:
            lines.append(f"**reward_preclip 分布**:")
            lines.append(f"| min | p1 | p10 | median | p90 | p99 | max | mean |")
            lines.append(f"|----:|---:|----:|-------:|----:|----:|----:|-----:|")
            lines.append(f"| {fmt(st['min'])} | {fmt(st['p1'])} | {fmt(st['p10'])} | {fmt(st['median'])} | {fmt(st['p90'])} | {fmt(st['p99'])} | {fmt(st['max'])} | {fmt(st['mean'])} |")
            lines.append("")

        # Clip ratio
        clo, chi, ctot = clip_ratio(all_rpc)
        lines.append(f"**Clip 比例**: clip_lo(< -1)={clo:.1%}, clip_hi(> 1)={chi:.1%}, total={ctot:.1%}")

        # reward_preclip 区间分布
        if all_rpc:
            rpc = np.array(all_rpc)
            bins_edges = [-float('inf'), -5, -3, -2, -1.5, -1, -0.5, 0, 0.5, 1, float('inf')]
            bin_labels = ["< -5", "[-5,-3)", "[-3,-2)", "[-2,-1.5)", "[-1.5,-1)", "[-1,-0.5)", "[-0.5,0)", "[0,0.5)", "[0.5,1)", "≥ 1"]
            hist, _ = np.histogram(rpc, bins=bins_edges)
            lines.append("")
            lines.append("**reward_preclip 区间分布**:")
            lines.append("")
            lines.append("| 区间 | 数量 | 占比 |")
            lines.append("|:-----|-----:|-----:|")
            for label, count in zip(bin_labels, hist):
                pct_val = count/n*100 if n > 0 else 0
                lines.append(f"| {label} | {count:,} | {pct_val:.1f}% |")

        lines.append("")
        lines.append("")

    # ====== 每组详细表 ======
    lines.append("## 四、每组 (scale×formula×pos) reward_preclip 分布\n")

    lines.append("| 组合 | MR | finals | penalty med | penalty p90 | good_rate med | rpc med | rpc p10 | rpc p90 | clip_lo | final_rew med |")
    lines.append("|:-----|---:|-------:|:-----------|:-----------|:-------------|:--------|:--------|:--------|:--------|:-------------|")

    for name in sorted(all_data.keys()):
        r = all_data[name]
        d = r['data']
        mr_str = f"{r['mr']:.6f}" if not np.isnan(r['mr']) else "N/A"
        nf = r['n_finals']

        if d['finals']:
            penalties = [f['penalty'] for f in d['finals']]
            grs = [f['good_rate'] for f in d['finals']]
            rpcs = [f['reward_preclip'] for f in d['finals']]
            rfs = [f['final_reward'] for f in d['finals']]

            pen_med = np.median(penalties)
            pen_p90 = np.percentile(penalties, 90)
            gr_med = np.median(grs)
            rpc_med = np.median(rpcs)
            rpc_p10 = np.percentile(rpcs, 10)
            rpc_p90 = np.percentile(rpcs, 90)
            clo, _, _ = clip_ratio(rpcs)
            rf_med = np.median(rfs)

            lines.append(
                f"| {name} | {mr_str} | {nf} | {pen_med:.4f} | {pen_p90:.4f} | {gr_med:.4f} | {rpc_med:.4f} | {rpc_p10:.4f} | {rpc_p90:.4f} | {clo:.1%} | {rf_med:.4f} |"
            )
        else:
            lines.append(f"| {name} | {mr_str} | {nf} | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |")

    lines.append("")

    # ====== Clip 比例汇总矩阵 ======
    lines.append("## 五、Clip 比例汇总矩阵 (clip_lo 百分比)\n")

    lines.append("| Scale \\ Formula | relative | centered | one_minus | neg | net | net2 |")
    lines.append("|:----------------|:---------|:---------|:----------|:----|:----|:-----|")

    for scale_name in ['binary', 'log', 'reciprocal', 'survival']:
        row = [f"| {scale_name}"]
        for formula_name in ['relative', 'centered', 'one_minus', 'neg', 'net', 'net2']:
            rpc_vals = []
            for name, r in all_data.items():
                if r['scale'] == scale_name and r['formula'] == formula_name:
                    for f in r['data']['finals']:
                        rpc_vals.append(f['reward_preclip'])
            if rpc_vals:
                clo, _, _ = clip_ratio(rpc_vals)
                row.append(f" {clo:.1%}")
            else:
                row.append(" N/A")
        row.append(" |")
        lines.append(" |".join(row))

    lines.append("")

    # ====== 关键发现 ======
    lines.append("## 六、关键发现\n")

    # Best/worst combos by MR
    combos_by_mr = [(name, r['mr']) for name, r in all_data.items() if not np.isnan(r['mr'])]
    combos_by_mr.sort(key=lambda x: x[1])

    lines.append("### TOP 5 (最低 MR):")
    for name, mr in combos_by_mr[:5]:
        r = all_data[name]
        rpcs = [f['reward_preclip'] for f in r['data']['finals']] if r['data']['finals'] else []
        clo, _, _ = clip_ratio(rpcs) if rpcs else (0, 0, 0)
        lines.append(f"- **{name}**: MR={mr:.6f}, clip_lo={clo:.1%}, finals={r['n_finals']}")
    lines.append("")

    lines.append("### BOTTOM 5 (最高 MR):")
    for name, mr in combos_by_mr[-5:]:
        r = all_data[name]
        rpcs = [f['reward_preclip'] for f in r['data']['finals']] if r['data']['finals'] else []
        clo, _, _ = clip_ratio(rpcs) if rpcs else (0, 0, 0)
        lines.append(f"- {name}: MR={mr:.6f}, clip_lo={clo:.1%}, finals={r['n_finals']}")
    lines.append("")

    output = '\n'.join(lines)
    outfile = os.path.join(SWEEP_DIR, "PENALTY_DISTRIBUTION_ANALYSIS.md")
    with open(outfile, 'w') as f:
        f.write(output)

    print(output)
    print(f"\n[Done] 已写入 {outfile}", file=sys.stderr)


if __name__ == '__main__':
    main()
