#!/usr/bin/env python3
"""
快速多 run 对比摘要：聚焦早期步数窗口内（默认 <=4000）的关键指标，输出CSV与控制台汇总。
- 指标：
  - train/actor_loss（窗口截止步的最后值）
  - reward/hit_ratio_mean（窗口截止步的最后值）
  - train/ent_coef（窗口截止步的最后值）
  - loh/ent_coef_init（若存在，取首个值）
- 组内汇总：
  - early_hit_ratio_mean_range = max(hit_mean) - min(hit_mean)
  - early_actor_loss_range = max(actor_loss) - min(actor_loss)

用法：
  python3 scripts/tb_compare_summary.py --runs-dir ./runs \
    --compare-runs 1112_102230,1112_104205,1112_104707 \
    --early-steps 4000 --out-dir tb_report/compare_summary
"""
import argparse
import os
import sys
import json
from typing import Dict, Optional

try:
    from tensorboard.backend.event_processing import event_accumulator
except Exception:
    print("ERROR: tensorboard is required (pip install tensorboard)", file=sys.stderr)
    raise

import numpy as np
import pandas as pd


def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def find_event_file(runs_dir: str, run_id: str) -> Optional[str]:
    run_dir = os.path.join(runs_dir, run_id)
    if not os.path.isdir(run_dir):
        return None
    import glob
    files = glob.glob(os.path.join(run_dir, '**', 'events*'), recursive=True)
    files = sorted(files, key=lambda p: os.path.getmtime(p))
    return files[-1] if files else None


def load_ea(event_file: str):
    ea = event_accumulator.EventAccumulator(event_file)
    ea.Reload()
    return ea


def get_last_leq_step(ea, tag: str, max_step: int):
    try:
        events = ea.Scalars(tag)
    except KeyError:
        return None
    if not events:
        return None
    # 找到 <= max_step 的最后一个值
    vals = [(e.step, e.value) for e in events if e.step <= max_step]
    if not vals:
        # 若没有<=max_step的，退化为最早值
        return float(events[0].value)
    return float(vals[-1][1])


def get_first_value(ea, tag: str):
    try:
        events = ea.Scalars(tag)
    except KeyError:
        return None
    if not events:
        return None
    return float(events[0].value)


def main():
    ap = argparse.ArgumentParser(description="Summarize early-window TB metrics across runs")
    ap.add_argument('--runs-dir', default='./runs')
    ap.add_argument('--compare-runs', required=True, help='comma-separated run IDs under runs-dir')
    ap.add_argument('--early-steps', type=int, default=4000)
    ap.add_argument('--out-dir', default='./tb_report/compare_summary')
    args = ap.parse_args()

    ensure_dir(args.out_dir)

    run_ids = [r.strip() for r in args.compare_runs.split(',') if r.strip()]
    rows = []
    for rid in run_ids:
        evf = find_event_file(args.runs_dir, rid)
        if not evf:
            print(f"WARN: no event file for run {rid}")
            continue
        ea = load_ea(evf)
        actor = get_last_leq_step(ea, 'train/actor_loss', args.early_steps)
        hit_mean = get_last_leq_step(ea, 'reward/hit_ratio_mean', args.early_steps)
        ent = get_last_leq_step(ea, 'train/ent_coef', args.early_steps)
        ent_init = get_first_value(ea, 'loh/ent_coef_init')
        # 记录差分特征模式（若存在）
        hit_delta_mode = get_last_leq_step(ea, 'obs/hit_delta_mode', args.early_steps)
        rows.append({
            'run': rid,
            'actor_loss_early': actor,
            'hit_ratio_mean_early': hit_mean,
            'ent_coef_early': ent,
            'ent_coef_init': ent_init,
            'hit_delta_mode': hit_delta_mode,
        })

    if not rows:
        print("No valid runs to summarize.")
        return

    df = pd.DataFrame(rows)
    # 组内范围
    try:
        df['actor_loss_early'] = pd.to_numeric(df['actor_loss_early'], errors='coerce')
        df['hit_ratio_mean_early'] = pd.to_numeric(df['hit_ratio_mean_early'], errors='coerce')
        al_range = float(df['actor_loss_early'].max() - df['actor_loss_early'].min())
        hr_range = float(df['hit_ratio_mean_early'].max() - df['hit_ratio_mean_early'].min())
    except Exception:
        al_range = float('nan'); hr_range = float('nan')

    csvp = os.path.join(args.out_dir, f"summary_{'_'.join(run_ids)}.csv")
    df.to_csv(csvp, index=False)
    print(f"Wrote early-window summary CSV: {csvp} ({df.shape})")

    # 控制台报告
    print("Early-window summary (<= %d steps):" % args.early_steps)
    print(df.to_string(index=False))
    print(f"Ranges: actor_loss={al_range:.6f}, hit_ratio_mean={hr_range:.6f}")
    if hr_range <= 0.005 and not np.isnan(hr_range):
        print("Note: hit_ratio_mean variation within early window is <= 0.005 (near-identical across runs).")


if __name__ == '__main__':
    main()
