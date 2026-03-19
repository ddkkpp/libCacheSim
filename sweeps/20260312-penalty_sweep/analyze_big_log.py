#!/usr/bin/env python3
"""
解析大日志 ac_sb3_0312_185744.log (binary+net2 配置)，
计算各阶段的详细值分布和 clip 比例。
"""
import re
import sys
import numpy as np

LOG_FILE = "/home/dingkp/libCacheSim/ac_sb3_0312_185744.log"

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


def pct_str(arr, percentiles):
    """格式化百分位数"""
    return {f"p{p}": float(np.percentile(arr, p)) for p in percentiles}


def dist_stats(arr, label=""):
    """打印分布统计"""
    a = np.array(arr)
    n = len(a)
    print(f"\n{'='*60}")
    print(f"  {label}  (n={n:,})")
    print(f"{'='*60}")
    print(f"  min    = {a.min():.6f}")
    print(f"  p1     = {np.percentile(a, 1):.6f}")
    print(f"  p5     = {np.percentile(a, 5):.6f}")
    print(f"  p10    = {np.percentile(a, 10):.6f}")
    print(f"  p25    = {np.percentile(a, 25):.6f}")
    print(f"  median = {np.percentile(a, 50):.6f}")
    print(f"  p75    = {np.percentile(a, 75):.6f}")
    print(f"  p90    = {np.percentile(a, 90):.6f}")
    print(f"  p95    = {np.percentile(a, 95):.6f}")
    print(f"  p99    = {np.percentile(a, 99):.6f}")
    print(f"  max    = {a.max():.6f}")
    print(f"  mean   = {a.mean():.6f}")
    print(f"  std    = {a.std():.6f}")


def main():
    print("正在解析日志... (约62万行)")

    # 收集数据
    neg_distances = []
    neg_scales = []
    neg_obj_contribs = []
    neg_byte_contribs = []
    pos_distances = []

    final_obj_penalties = []
    final_byte_penalties = []
    final_penalties = []
    final_reward_preclips = []
    final_rewards = []
    final_good_rates = []
    final_pos_events = []
    final_neg_events = []
    final_raw_penalty_counts = []

    line_count = 0
    with open(LOG_FILE, 'r', errors='replace') as f:
        for line in f:
            line_count += 1
            if line_count % 100000 == 0:
                print(f"  处理了 {line_count:,} 行...", file=sys.stderr)

            if '[PenaltyTrace]' not in line:
                continue

            m = EVENT_RE.search(line)
            if m:
                evt_type = m.group(2)
                if evt_type == 'negative':
                    neg_distances.append(float(m.group(3)))
                    scale_str = m.group(7)
                    if scale_str != 'NA':
                        neg_scales.append(float(scale_str))
                    neg_obj_contribs.append(float(m.group(8)))
                    neg_byte_contribs.append(float(m.group(9)))
                elif evt_type == 'positive':
                    pos_distances.append(abs(float(m.group(3))))
                continue

            m = FINAL_RE.search(line)
            if m:
                final_raw_penalty_counts.append(int(m.group(3)))
                final_pos_events.append(int(m.group(4)))
                final_neg_events.append(int(m.group(5)))
                final_good_rates.append(float(m.group(6)))
                final_obj_penalties.append(float(m.group(7)))
                final_byte_penalties.append(float(m.group(8)))
                final_penalties.append(float(m.group(9)))
                final_reward_preclips.append(float(m.group(10)))
                final_rewards.append(float(m.group(11)))

    print(f"\n解析完成: {line_count:,} 行")
    print(f"  negative events: {len(neg_distances):,}")
    print(f"  positive events: {len(pos_distances):,}")
    print(f"  final records:   {len(final_rewards):,}")

    # ====== 阶段分析 ======

    print("\n" + "#"*60)
    print("# 配置: binary scale + net2 formula + pos1")
    print("# scale(d) = 1.0 (恒定)")
    print("# reward = (2*good_rate - 1) - penalty")
    print("#"*60)

    # 1. Distance 分布
    if neg_distances:
        dist_stats(neg_distances, "阶段1: 负样本 distance (驱逐后再次访问距离)")
    if pos_distances:
        dist_stats(pos_distances, "阶段1b: 正样本 distance (ghost淘汰未再访问)")

    # 2. Scale 分布
    if neg_scales:
        dist_stats(neg_scales, "阶段2: scale(d) 值 [binary模式: 恒=1.0]")

    # 3. obj_contrib 分布
    if neg_obj_contribs:
        dist_stats(neg_obj_contribs, "阶段3a: obj_contrib = (1/evicted_count) × scale")

    if neg_byte_contribs:
        dist_stats(neg_byte_contribs, "阶段3b: byte_contrib = (obj_size/evicted_bytes) × scale")

    # 4. obj_penalty 分布（按 finalization 周期汇总）
    if final_obj_penalties:
        dist_stats(final_obj_penalties, "阶段4a: obj_penalty = Σ obj_contrib (每个finalization周期)")

    if final_byte_penalties:
        dist_stats(final_byte_penalties, "阶段4b: byte_penalty = Σ byte_contrib")

    # 5. penalty 分布
    if final_penalties:
        dist_stats(final_penalties, "阶段5: penalty = w_obj × obj_penalty + w_byte × byte_penalty")

    # 6. good_rate 分布
    if final_good_rates:
        dist_stats(final_good_rates, "阶段6: good_rate = pos_events / (pos_events + neg_events)")

    # 7. reward_preclip 分布
    if final_reward_preclips:
        dist_stats(final_reward_preclips, "阶段7: reward_preclip = (2*good_rate - 1) - penalty [net2公式]")

    # 8. final_reward 分布
    if final_rewards:
        dist_stats(final_rewards, "阶段8: final_reward = clip(reward_preclip, -1, 1)")

    # ====== Clip 分析 ======
    if final_reward_preclips:
        rpc = np.array(final_reward_preclips)
        n = len(rpc)
        clip_lo = np.sum(rpc < -1.0)
        clip_hi = np.sum(rpc > 1.0)
        clip_eq_minus1 = np.sum(rpc == -1.0)
        in_range = np.sum((rpc >= -1.0) & (rpc <= 1.0))

        print(f"\n{'='*60}")
        print(f"  Clip 分析 (n={n:,})")
        print(f"{'='*60}")
        print(f"  reward_preclip < -1 (clip到-1) : {clip_lo:,} ({clip_lo/n:.1%})")
        print(f"  reward_preclip == -1           : {clip_eq_minus1:,} ({clip_eq_minus1/n:.1%})")
        print(f"  -1 ≤ reward_preclip ≤ 1        : {in_range:,} ({in_range/n:.1%})")
        print(f"  reward_preclip > 1 (clip到+1)  : {clip_hi:,} ({clip_hi/n:.1%})")

        # 按区间分布
        bins_edges = [-float('inf'), -5, -3, -2, -1.5, -1, -0.5, 0, 0.5, 1, float('inf')]
        bin_labels = ["< -5", "[-5,-3)", "[-3,-2)", "[-2,-1.5)", "[-1.5,-1)", "[-1,-0.5)", "[-0.5,0)", "[0,0.5)", "[0.5,1)", "≥ 1"]
        hist, _ = np.histogram(rpc, bins=bins_edges)
        print(f"\n  reward_preclip 区间分布:")
        for label, count in zip(bin_labels, hist):
            bar = '█' * int(count / n * 50)
            print(f"    {label:>12s} : {count:6,} ({count/n:6.1%}) {bar}")

    # ====== 关键洞察 ======
    if final_good_rates and final_penalties:
        gr = np.array(final_good_rates)
        pen = np.array(final_penalties)

        # net2: reward = (2*good_rate - 1) - penalty
        # 当 good_rate < 0.5 时, (2*gr-1) < 0 → reward 恒负
        # 当 good_rate = 0 时, reward = -1 - penalty → 恒 < -1 → 全部clip
        gr_lt_05 = np.sum(gr < 0.5)
        gr_eq_0 = np.sum(gr == 0.0)

        print(f"\n{'='*60}")
        print(f"  Net2 公式洞察")
        print(f"{'='*60}")
        print(f"  good_rate < 0.5 的周期: {gr_lt_05:,}/{len(gr):,} ({gr_lt_05/len(gr):.1%})")
        print(f"  good_rate == 0 的周期:  {gr_eq_0:,}/{len(gr):,} ({gr_eq_0/len(gr):.1%})")
        print(f"  → 当 good_rate=0: goodness=2×0-1=-1, reward=-1-penalty ≤ -1 → 必然clip!")
        print(f"  → 当 good_rate<0.5: goodness<0, reward<0-penalty ≤ 0 → 多数clip")
        print(f"")

        # 计算 goodness 项
        goodness = 2.0 * gr - 1.0
        dist_stats(goodness, "goodness = 2×good_rate - 1")

        # 需要 good_rate > (1 + penalty) / 2 才能 reward > 0
        threshold = (1.0 + pen) / 2.0
        above_threshold = np.sum(gr > threshold)
        print(f"\n  需要 good_rate > (1+penalty)/2 才能 reward > 0:")
        print(f"  满足条件的周期: {above_threshold:,}/{len(gr):,} ({above_threshold/len(gr):.1%})")

    # neg/pos events 每周期汇总
    if final_neg_events and final_pos_events:
        ne = np.array(final_neg_events)
        pe = np.array(final_pos_events)
        total = ne + pe
        dist_stats(ne, "每周期 neg_events (错误驱逐数)")
        dist_stats(pe, "每周期 pos_events (正样本数)")
        dist_stats(total, "每周期 total_events")


if __name__ == '__main__':
    main()
