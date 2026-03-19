#!/usr/bin/env python3
"""
解析 48 组 penalty_sweep 日志中的 PenaltyTrace 数据，
计算各 scale/formula/pos 组合下的值分布和 clip 比例。
"""
import os
import re
import glob
import numpy as np
from collections import defaultdict

LOG_DIR = os.path.dirname(os.path.abspath(__file__))

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

# 解析 summary.csv 获取 MR/BMR
SUMMARY_FILE = os.path.join(LOG_DIR, "summary.csv")


def parse_log(filepath):
    """解析单个日志文件，返回 events 和 finals"""
    events = []
    finals = []
    with open(filepath, 'r', errors='replace') as f:
        for line in f:
            m = EVENT_RE.search(line)
            if m:
                events.append({
                    'pos': int(m.group(1)),
                    'type': m.group(2),
                    'distance': float(m.group(3)),
                    'obj_size': float(m.group(4)),
                    'evicted_count': int(m.group(5)),
                    'evicted_bytes': float(m.group(6)),
                    'scale': float(m.group(7)) if m.group(7) != 'NA' else None,
                    'obj_contrib': float(m.group(8)),
                    'byte_contrib': float(m.group(9)),
                })
                continue

            m = FINAL_RE.search(line)
            if m:
                finals.append({
                    'pos': int(m.group(1)),
                    'formula': m.group(2),
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
    return events, finals


def load_summary():
    """加载 summary.csv 获取每组的 MR/BMR"""
    results = {}
    if not os.path.exists(SUMMARY_FILE):
        return results
    with open(SUMMARY_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('scale'):
                continue
            parts = line.split(',')
            if len(parts) >= 5:
                key = f"{parts[0]}_{parts[1]}_pos{parts[2]}"
                results[key] = {
                    'mr': float(parts[3]),
                    'bmr': float(parts[4]),
                    'mqps': float(parts[5]) if len(parts) > 5 else 0,
                }
    return results


def pct(arr, p):
    if len(arr) == 0:
        return float('nan')
    return float(np.percentile(arr, p))


def dist_stats(arr):
    """计算分布统计"""
    if len(arr) == 0:
        return {'n': 0, 'min': float('nan'), 'p10': float('nan'),
                'median': float('nan'), 'mean': float('nan'),
                'p90': float('nan'), 'max': float('nan')}
    a = np.array(arr)
    return {
        'n': len(a),
        'min': float(a.min()),
        'p10': float(np.percentile(a, 10)),
        'median': float(np.median(a)),
        'mean': float(a.mean()),
        'p90': float(np.percentile(a, 90)),
        'max': float(a.max()),
    }


def clip_ratio(arr, lo=-1.0, hi=1.0):
    """计算 clip 到 [lo, hi] 的比例"""
    if len(arr) == 0:
        return 0.0, 0.0, 0.0
    a = np.array(arr)
    clip_lo = float(np.sum(a < lo)) / len(a)
    clip_hi = float(np.sum(a > hi)) / len(a)
    clip_total = float(np.sum((a < lo) | (a > hi))) / len(a)
    return clip_lo, clip_hi, clip_total


def main():
    summary_data = load_summary()

    log_files = sorted(glob.glob(os.path.join(LOG_DIR, "*.log")))
    log_files = [f for f in log_files if os.path.basename(f) != "batch_run.log"]

    # 收集所有组的数据
    all_results = {}

    for logf in log_files:
        name = os.path.basename(logf).replace('.log', '')
        parts = name.split('_')

        if len(parts) == 3:
            scale, formula, pos_str = parts
        elif len(parts) == 4:
            # e.g. one_minus split into one, minus
            scale = parts[0]
            formula = f"{parts[1]}_{parts[2]}"
            pos_str = parts[3]
        else:
            # Handle other complex names
            scale = parts[0]
            formula = '_'.join(parts[1:-1])
            pos_str = parts[-1]

        events, finals = parse_log(logf)

        # 提取 negative events 的 scale 值
        neg_scales = [e['scale'] for e in events if e['type'] == 'negative' and e['scale'] is not None]
        neg_distances = [e['distance'] for e in events if e['type'] == 'negative']
        neg_obj_contribs = [e['obj_contrib'] for e in events if e['type'] == 'negative']
        neg_byte_contribs = [e['byte_contrib'] for e in events if e['type'] == 'negative']
        pos_distances = [abs(e['distance']) for e in events if e['type'] == 'positive']

        # 从 finals 提取
        obj_penalties = [f['obj_penalty'] for f in finals]
        byte_penalties = [f['byte_penalty'] for f in finals]
        penalties = [f['penalty'] for f in finals]
        rewards_preclip = [f['reward_preclip'] for f in finals]
        rewards_final = [f['final_reward'] for f in finals]
        good_rates = [f['good_rate'] for f in finals]
        pos_event_counts = [f['pos_events'] for f in finals]
        neg_event_counts = [f['neg_events'] for f in finals]

        mr_info = summary_data.get(name, {})

        all_results[name] = {
            'scale': scale,
            'formula': formula,
            'pos': pos_str,
            'neg_scales': neg_scales,
            'neg_distances': neg_distances,
            'pos_distances': pos_distances,
            'neg_obj_contribs': neg_obj_contribs,
            'neg_byte_contribs': neg_byte_contribs,
            'obj_penalties': obj_penalties,
            'byte_penalties': byte_penalties,
            'penalties': penalties,
            'rewards_preclip': rewards_preclip,
            'rewards_final': rewards_final,
            'good_rates': good_rates,
            'pos_events': pos_event_counts,
            'neg_events': neg_event_counts,
            'n_events': len(events),
            'n_finals': len(finals),
            'mr': mr_info.get('mr', float('nan')),
            'bmr': mr_info.get('bmr', float('nan')),
        }

    # ====== 生成文档 ======
    lines = []
    lines.append("# Penalty Sweep 计算过程与分布分析\n")
    lines.append("## 一、计算管道总览\n")
    lines.append("```")
    lines.append("distance (d) → scale(d) → obj_contrib = (1/evicted_count) × scale")
    lines.append("                        → byte_contrib = (obj_size/evicted_bytes) × scale")
    lines.append("                  ↓")
    lines.append("obj_penalty = Σ obj_contrib  (对所有 negative events)")
    lines.append("byte_penalty = Σ byte_contrib")
    lines.append("                  ↓")
    lines.append("penalty = w_obj × obj_penalty + w_byte × byte_penalty")
    lines.append("                  ↓")
    lines.append("reward_preclip = formula(penalty, good_rate)")
    lines.append("                  ↓")
    lines.append("final_reward = clip(reward_preclip, -1, 1)")
    lines.append("```\n")

    # --- 4 种 scale 方式 ---
    lines.append("## 二、4 种 Scale 方式详解\n")

    lines.append("### 2.1 reciprocal (倒数缩放)")
    lines.append("- 公式: `scale(d) = 1 / max(d, 1)`")
    lines.append("- 特点: d 越大 → scale 越小，衰减速度快 (O(1/d))")
    lines.append("- 典型值域: d=1→1.0, d=100→0.01, d=10000→0.0001, d=300000→~3e-6")
    lines.append("")

    lines.append("### 2.2 binary (二值缩放)")
    lines.append("- 公式: `scale(d) = 1.0` (恒定)")
    lines.append("- 特点: 不区分距离远近，penalty = 错误驱逐数量比例")
    lines.append("- 典型值域: 恒为 1.0")
    lines.append("")

    lines.append("### 2.3 log (对数缩放)")
    lines.append("- 公式: `scale(d) = max(0, 1 - log1p(d)/log1p(dmax))`")
    lines.append("- 特点: 平滑衰减，速度介于 binary 和 reciprocal 之间")
    lines.append("- 典型值域 (dmax=3000000): d=1→0.95, d=100→0.69, d=10000→0.38, d=300000→0.08")
    lines.append("")

    lines.append("### 2.4 survival (生存函数)")
    lines.append("- 公式: `scale(d) = 1 - F(d)` (F 为距离的经验 CDF)")
    lines.append("- 特点: 自适应——基于实际距离分布，稀有的大距离驱逐惩罚低")
    lines.append("- 但早期样本不足时回退到 log 模式")
    lines.append("")

    # --- 6 种 formula 方式 ---
    lines.append("## 三、6 种 Formula 方式详解\n")

    lines.append("### 3.1 relative")
    lines.append("- 公式: `reward = (baseline - penalty) / baseline`")
    lines.append("- baseline 用 EMA 更新")
    lines.append("- 如果 penalty < baseline → reward > 0 (改善)")
    lines.append("- 如果 penalty > baseline → reward < 0 (恶化)")
    lines.append("")

    lines.append("### 3.2 centered")
    lines.append("- 公式: `reward = 1 - 2 × penalty`")
    lines.append("- penalty=0 → reward=1, penalty=0.5 → reward=0, penalty=1 → reward=-1")
    lines.append("- penalty>1 时 reward<-1 → clip to -1")
    lines.append("")

    lines.append("### 3.3 one_minus")
    lines.append("- 公式: `reward = 1 - penalty`")
    lines.append("- penalty=0 → reward=1, penalty=1 → reward=0, penalty>1 → reward<0")
    lines.append("- 输出偏正，对 penalty>1 的惩罚力度弱")
    lines.append("")

    lines.append("### 3.4 neg")
    lines.append("- 公式: `reward = -penalty`")
    lines.append("- penalty 越大 → reward 越负")
    lines.append("- penalty=0 → reward=0, penalty=1 → reward=-1")
    lines.append("")

    lines.append("### 3.5 net")
    lines.append("- 公式: `reward = good_scale × good_rate - pen_scale × penalty`")
    lines.append("- good_rate = pos_events / (pos_events + neg_events)")
    lines.append("- 正样本越多 → reward 提升；penalty 越大 → reward 降低")
    lines.append("")

    lines.append("### 3.6 net2")
    lines.append("- 公式: `reward = good_scale × (2×good_rate - 1) - pen_scale × penalty`")
    lines.append("- 将 good_rate 映射到 [-1, 1]，动态范围更大")
    lines.append("- good_rate<0.5 时 goodness 为负，与 penalty 叠加使 reward 更大幅度为负")
    lines.append("")

    # --- 按 scale 分组的实测分布 ---
    lines.append("## 四、各 Scale 模式下 scale(d) 的实测分布\n")

    scale_groups = defaultdict(list)
    for name, r in all_results.items():
        scale_groups[r['scale']].extend(r['neg_scales'])

    lines.append("| Scale 模式 | n | min | p10 | median | mean | p90 | max |")
    lines.append("|:-----------|--:|----:|----:|-------:|-----:|----:|----:|")
    for s in ['binary', 'log', 'reciprocal', 'survival']:
        vals = scale_groups.get(s, [])
        st = dist_stats(vals)
        lines.append(f"| {s} | {st['n']} | {st['min']:.6f} | {st['p10']:.6f} | {st['median']:.6f} | {st['mean']:.6f} | {st['p90']:.6f} | {st['max']:.6f} |")
    lines.append("")

    # --- 按 scale 分组的 distance 分布 ---
    lines.append("## 五、负样本 distance 的实测分布\n")

    dist_groups = defaultdict(list)
    for name, r in all_results.items():
        dist_groups[r['scale']].extend(r['neg_distances'])

    lines.append("| Scale 模式 | n | min | p10 | median | mean | p90 | max |")
    lines.append("|:-----------|--:|----:|----:|-------:|-----:|----:|----:|")
    for s in ['binary', 'log', 'reciprocal', 'survival']:
        vals = dist_groups.get(s, [])
        st = dist_stats(vals)
        lines.append(f"| {s} | {st['n']} | {st['min']:.0f} | {st['p10']:.0f} | {st['median']:.0f} | {st['mean']:.0f} | {st['p90']:.0f} | {st['max']:.0f} |")
    lines.append("")

    # --- 按 formula 分组的 penalty/reward 分布 ---
    lines.append("## 六、各 Formula 模式下 penalty → reward 的实测分布\n")

    for formula_name in ['relative', 'centered', 'one_minus', 'neg', 'net', 'net2']:
        lines.append(f"### 6.{['relative','centered','one_minus','neg','net','net2'].index(formula_name)+1} {formula_name}\n")

        formula_data = {
            'obj_penalty': [], 'penalty': [],
            'reward_preclip': [], 'reward_final': [],
            'good_rate': [], 'pos_events': [], 'neg_events': [],
        }
        for name, r in all_results.items():
            if r['formula'] == formula_name:
                formula_data['obj_penalty'].extend(r['obj_penalties'])
                formula_data['penalty'].extend(r['penalties'])
                formula_data['reward_preclip'].extend(r['rewards_preclip'])
                formula_data['reward_final'].extend(r['rewards_final'])
                formula_data['good_rate'].extend(r['good_rates'])
                formula_data['pos_events'].extend(r['pos_events'])
                formula_data['neg_events'].extend(r['neg_events'])

        lines.append("| 指标 | n | min | p10 | median | mean | p90 | max |")
        lines.append("|:-----|--:|----:|----:|-------:|-----:|----:|----:|")
        for metric in ['obj_penalty', 'penalty', 'reward_preclip', 'reward_final', 'good_rate']:
            st = dist_stats(formula_data[metric])
            lines.append(f"| {metric} | {st['n']} | {st['min']:.6f} | {st['p10']:.6f} | {st['median']:.6f} | {st['mean']:.6f} | {st['p90']:.6f} | {st['max']:.6f} |")

        # Clip 比例
        clo, chi, ctot = clip_ratio(formula_data['reward_preclip'])
        lines.append(f"\n**Clip 比例**: clip_lo(< -1)={clo:.1%}, clip_hi(> 1)={chi:.1%}, total={ctot:.1%}\n")

    # --- 按 scale×formula 的详细表 ---
    lines.append("## 七、每组 (scale×formula×pos) 详细数据\n")

    lines.append("| 组合 | MR | neg_events | pos_events | good_rate | obj_penalty | penalty | reward_preclip | final_reward | clip_lo | clip_hi |")
    lines.append("|:-----|---:|-----------:|-----------:|----------:|------------:|--------:|---------------:|-------------:|--------:|--------:|")

    for name in sorted(all_results.keys()):
        r = all_results[name]
        mr_str = f"{r['mr']:.6f}" if not np.isnan(r['mr']) else "N/A"

        # 使用 finals 数据（通常只有 1-2 条）
        if r['rewards_preclip']:
            clo, chi, _ = clip_ratio(r['rewards_preclip'])
            rpc = r['rewards_preclip'][-1]
            rf = r['rewards_final'][-1]
            op = r['obj_penalties'][-1] if r['obj_penalties'] else 0
            pen = r['penalties'][-1] if r['penalties'] else 0
            gr = r['good_rates'][-1] if r['good_rates'] else 0
            pe = r['pos_events'][-1] if r['pos_events'] else 0
            ne = r['neg_events'][-1] if r['neg_events'] else 0
        else:
            clo = chi = rpc = rf = op = pen = gr = pe = ne = 0

        lines.append(
            f"| {name} | {mr_str} | {ne} | {pe} | {gr:.4f} | {op:.6f} | {pen:.6f} | {rpc:.6f} | {rf:.6f} | {clo:.0%} | {chi:.0%} |"
        )

    lines.append("")

    # --- 按 scale 分组的 obj_penalty 分布 ---
    lines.append("## 八、按 Scale 分组的 obj_penalty 分布\n")

    lines.append("| Scale | n | min | p10 | median | mean | p90 | max |")
    lines.append("|:------|--:|----:|----:|-------:|-----:|----:|----:|")
    for s in ['binary', 'log', 'reciprocal', 'survival']:
        vals = []
        for name, r in all_results.items():
            if r['scale'] == s:
                vals.extend(r['obj_penalties'])
        st = dist_stats(vals)
        lines.append(f"| {s} | {st['n']} | {st['min']:.6f} | {st['p10']:.6f} | {st['median']:.6f} | {st['mean']:.6f} | {st['p90']:.6f} | {st['max']:.6f} |")
    lines.append("")

    # --- Clip 比例汇总 ---
    lines.append("## 九、Clip 比例汇总（按 scale×formula）\n")

    lines.append("| Scale | Formula | clip_lo(< -1) | clip_hi(> 1) | total_clip |")
    lines.append("|:------|:--------|:------|:-----|:------|")
    for s in ['binary', 'log', 'reciprocal', 'survival']:
        for f in ['relative', 'centered', 'one_minus', 'neg', 'net', 'net2']:
            vals = []
            for name, r in all_results.items():
                if r['scale'] == s and r['formula'] == f:
                    vals.extend(r['rewards_preclip'])
            if vals:
                clo, chi, ctot = clip_ratio(vals)
                lines.append(f"| {s} | {f} | {clo:.0%} | {chi:.0%} | {ctot:.0%} |")
            else:
                lines.append(f"| {s} | {f} | N/A | N/A | N/A |")
    lines.append("")

    # --- 关键发现 ---
    lines.append("## 十、关键发现与建议\n")

    # 找出最高和最低 clip 的组合
    clip_data = []
    for name, r in all_results.items():
        if r['rewards_preclip']:
            clo, chi, ctot = clip_ratio(r['rewards_preclip'])
            clip_data.append((name, ctot, clo, chi, r['mr']))

    if clip_data:
        clip_data.sort(key=lambda x: x[1], reverse=True)
        lines.append("### 最高 clip 比例的组合:")
        for name, ctot, clo, chi, mr in clip_data[:5]:
            lines.append(f"- {name}: total_clip={ctot:.0%} (lo={clo:.0%}, hi={chi:.0%}), MR={mr:.6f}")
        lines.append("")

        lines.append("### 最低 clip 比例的组合:")
        for name, ctot, clo, chi, mr in clip_data[-5:]:
            lines.append(f"- {name}: total_clip={ctot:.0%} (lo={clo:.0%}, hi={chi:.0%}), MR={mr:.6f}")
        lines.append("")

    output = '\n'.join(lines)

    outfile = os.path.join(LOG_DIR, "PENALTY_DISTRIBUTION_ANALYSIS.md")
    with open(outfile, 'w') as f:
        f.write(output)

    print(output)
    print(f"\n[Done] 已写入 {outfile}")


if __name__ == '__main__':
    main()
