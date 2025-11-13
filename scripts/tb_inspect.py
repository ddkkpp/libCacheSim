#!/usr/bin/env python3
"""
工具：读取并可视化 TensorBoard run 的标量（支持 CSV 导出与 PNG 绘图），并尝试提取学习率及训练进度信息。
同时支持多 run 对比（例如对比不同温度/超参的 SAC 训练）。

用法示例：
    单 run：
        python3 scripts/tb_inspect.py --runs-dir ./runs \
            --tags rollout/ep_rew_mean,train/actor_loss,train/critic_loss,train/ent_coef,time/fps \
            --out-dir ./tb_report --total-timesteps 2000000

    多 run 对比（用子目录名标识 run，例如 1110_233455 等）：
        python3 scripts/tb_inspect.py --runs-dir ./runs \
            --compare-runs 1110_233455,1111_092603,1111_093620 \
            --tags rollout/ep_rew_mean,train/ent_coef,timer/program.total,timer/rollout.phase_total

说明：
 - 脚本会在指定 runs 根目录下选择最近修改的子目录（默认 ./runs），并尝试加载其中的 events.* 文件。
 - 自动检测以下可能的学习率 tag： 'train/learning_rate', 'learning_rate', 'lr', 'train/lr'。
 - 若无法自动推断 total_timesteps，可使用 --total-timesteps 手动传入，用于计算学习率 progress。
"""
import argparse
import os
import glob
import json
import math
import sys
from datetime import datetime
from typing import Dict, List, Optional

try:
    from tensorboard.backend.event_processing import event_accumulator
except Exception as e:
    print("ERROR: tensorboard is required (pip install tensorboard).", file=sys.stderr)
    raise

try:
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
except Exception:
    print("ERROR: matplotlib, numpy and pandas are recommended (pip install matplotlib numpy pandas).", file=sys.stderr)
    raise


DEFAULT_LR_TAGS = ['train/learning_rate', 'learning_rate', 'lr', 'train/lr']


def find_latest_run(runs_dir):
    if not os.path.isdir(runs_dir):
        raise FileNotFoundError(f"runs dir not found: {runs_dir}")
    subdirs = [os.path.join(runs_dir, d) for d in os.listdir(runs_dir) if os.path.isdir(os.path.join(runs_dir, d))]
    if not subdirs:
        # maybe events files are directly under runs_dir
        return runs_dir
    latest = max(subdirs, key=lambda p: os.path.getmtime(p))
    return latest


def find_event_files(run_path):
    # search recursively for files named 'events*'
    matches = glob.glob(os.path.join(run_path, '**', 'events*'), recursive=True)
    return sorted(matches, key=os.path.getmtime)


def find_event_file_for_run(runs_dir: str, run_id: str) -> Optional[str]:
    run_dir = os.path.join(runs_dir, run_id)
    if not os.path.isdir(run_dir):
        return None
    files = find_event_files(run_dir)
    return files[-1] if files else None


def load_event_accumulator(event_file):
    # Create EventAccumulator. Different tensorboard versions expose different
    # APIs (some lack DEFAULT_SIZE_GUIDANCE). Use a safe fallback: try to use
    # DEFAULT_SIZE_GUIDANCE if available, otherwise create without guidance.
    try:
        guidance = event_accumulator.EventAccumulator.DEFAULT_SIZE_GUIDANCE.copy()
        guidance[event_accumulator.COMPRESSED_HISTOGRAMS] = 0
        guidance[event_accumulator.IMAGES] = 0
        guidance[event_accumulator.AUDIO] = 0
        ea = event_accumulator.EventAccumulator(event_file, size_guidance=guidance)
    except Exception:
        # Fallback: construct without size_guidance (may use more memory but works)
        ea = event_accumulator.EventAccumulator(event_file)
    ea.Reload()
    return ea


def list_scalar_tags(ea):
    tags = ea.Tags().get('scalars', [])
    return tags


def get_scalar_df(ea, tag):
    try:
        events = ea.Scalars(tag)
    except KeyError:
        return None
    if not events:
        return None
    df = pd.DataFrame([{'step': e.step, 'wall_time': e.wall_time, 'value': e.value} for e in events])
    return df


def smooth(series, window):
    if window <= 1:
        return series
    return series.rolling(window=window, min_periods=1, center=False).mean()


def auto_find_lr_tag(tags):
    for t in DEFAULT_LR_TAGS:
        if t in tags:
            return t
    # fallback: try tags that contain 'lr' or 'learning_rate'
    for t in tags:
        if 'lr' in t or 'learning_rate' in t:
            return t
    return None


def try_extract_total_timesteps_from_text(ea):
    # EventAccumulator exposes 'tensors'/'text' via Tags (some loggers write text). We'll try to scan text tags.
    tags = ea.Tags()
    # 'text' tag may be under 'scalars' or 'tensors' depending on logger. Search all tags for JSON-looking text.
    cand_tags = []
    for kind in tags:
        # for each kind (e.g., 'scalars','histograms','tensors') check if contain elements
        pass
    # We'll attempt to scan all scalar tag values for JSON-like sac_config dump
    for t in list_scalar_tags(ea):
        # sample first few values as strings?
        try:
            events = ea.Scalars(t)
        except Exception:
            continue
        for ev in events[-5:]:
            # if value is numeric, skip
            try:
                float(ev.value)
                continue
            except Exception:
                s = str(ev.value)
                if 'total_timesteps' in s or 'total_timesteps' in t:
                    # try to parse numbers
                    try:
                        j = json.loads(s)
                        if isinstance(j, dict) and 'total_timesteps' in j:
                            return int(j['total_timesteps'])
                    except Exception:
                        # try to extract digits
                        import re
                        m = re.search(r'total_timesteps\D*(\d+)', s)
                        if m:
                            return int(m.group(1))
    return None


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def main():
    p = argparse.ArgumentParser(description="Inspect TensorBoard runs and plot scalar tags; try to show learning rate and progress. Supports multi-run comparison.")
    p.add_argument('--runs-dir', default='./runs', help='root runs dir (default ./runs)')
    p.add_argument('--run-path', default=None, help='explicit run subdir path, bypass auto-detect')
    p.add_argument('--compare-runs', default=None, help='comma-separated run ids under runs-dir for comparison (e.g., 1110_233455,1111_092603)')
    p.add_argument('--tags', default=None, help='comma-separated tags to export/plot; if omitted, top tags are listed')
    p.add_argument('--out-dir', default='./tb_report', help='output directory for CSVs and PNGs')
    p.add_argument('--smooth', type=int, default=1, help='smoothing window (integer)')
    p.add_argument('--total-timesteps', type=int, default=None, help='(optional) total timesteps for progress calculation')
    # Auto/tag discovery helpers (compare-mode)
    p.add_argument('--auto-mode', choices=['preferred', 'union', 'intersection'], default='preferred',
                   help='when --tags not provided in compare mode: preferred uses a curated list; union lists all tags present in any run; intersection lists only tags present in all runs')
    p.add_argument('--presence-report', action='store_true',
                   help='emit a CSV matrix of tag presence across runs (rows=tags, cols=runs)')
    p.add_argument('--list-tags', action='store_true',
                   help='save per-run tag lists (tags_<run>.txt) to out-dir')
    p.add_argument('--include', default=None,
                   help='optional comma-separated substr filters; only keep tags containing any of these substrings')
    p.add_argument('--exclude', default=None,
                   help='optional comma-separated substr filters; drop tags containing any of these substrings')
    args = p.parse_args()

    ensure_dir(args.out_dir)

    # Multi-run comparison path
    if args.compare_runs:
        run_ids = [x.strip() for x in args.compare_runs.split(',') if x.strip()]
        print(f"Comparing runs under {args.runs_dir}: {run_ids}")
        # load event accumulators per run id
        accs: Dict[str, event_accumulator.EventAccumulator] = {}
        for rid in run_ids:
            evf = find_event_file_for_run(args.runs_dir, rid)
            if not evf:
                print(f"WARN: no event file found for run {rid}")
                continue
            print(f"  [{rid}] event: {evf}")
            accs[rid] = load_event_accumulator(evf)
        if not accs:
            print("No valid runs to compare.")
            return

        # Collect available tags per run
        available_by_run = {rid: set(list_scalar_tags(accs[rid])) for rid in accs}

        # Save per-run tag lists if requested
        if args.list_tags:
            for rid, tags_set in available_by_run.items():
                path_txt = os.path.join(args.out_dir, f"tags_{rid}.txt")
                with open(path_txt, 'w', encoding='utf-8') as f:
                    for t in sorted(tags_set):
                        f.write(t + "\n")
                print(f"Wrote tag list: {path_txt} ({len(tags_set)} tags)")

        # Presence matrix report if requested
        if args.presence_report:
            all_tags = sorted(set().union(*available_by_run.values()))
            # optional filters
            include_terms = [s.strip() for s in args.include.split(',')] if args.include else None
            exclude_terms = [s.strip() for s in args.exclude.split(',')] if args.exclude else None
            def tag_allowed(tag: str) -> bool:
                ok = True
                if include_terms:
                    ok = any(term in tag for term in include_terms)
                if ok and exclude_terms:
                    if any(term in tag for term in exclude_terms):
                        ok = False
                return ok
            filt_tags = [t for t in all_tags if tag_allowed(t)]
            import pandas as pd  # local import
            mat = { 'tag': filt_tags }
            for rid in available_by_run:
                mat[rid] = [1 if t in available_by_run[rid] else 0 for t in filt_tags]
            mat['present_in'] = [sum(mat[rid][i] for rid in available_by_run) for i in range(len(filt_tags))]
            dfp = pd.DataFrame(mat)
            rid_join = "_".join(available_by_run.keys())
            csvp = os.path.join(args.out_dir, f"presence_{rid_join}.csv")
            dfp.to_csv(csvp, index=False)
            print(f"Wrote presence matrix: {csvp} ({dfp.shape})")

        # tags selection
        if not args.tags:
            mode = args.auto_mode
            union = set().union(*available_by_run.values())
            intersection = set.intersection(*available_by_run.values()) if len(available_by_run) > 1 else union
            preferred = [
                'rollout/ep_rew_mean', 'rollout/ep_len_mean',
                'train/actor_loss', 'train/critic_loss', 'train/ent_coef', 'train/learning_rate',
                'time/fps', 'time/time_elapsed',
                # project-specific popular prefixes
                'loh/reward_mean', 'loh/reward_std', 'loh/reward_min', 'loh/reward_max',
                'loh/buffer_weights_mean_norm', 'loh/avg_penalty', 'loh/penalty_baseline', 'loh/total_reward_corrections',
                # 新增：奖励组件与观测差分特征相关标签（若存在）
                'reward/component_penalty', 'reward/component_miss', 'reward/component_trend', 'reward/final_mixed_pre_clip', 'reward/final_mixed', 'reward/clip_delta',
                'obs/hit_delta_mode', 'obs/hit_delta_window', 'obs/obs_dim',
            ]

            if mode == 'preferred':
                tags = [t for t in preferred if t in union]
            elif mode == 'intersection':
                tags = sorted(list(intersection))
            else:  # union
                tags = sorted(list(union))

            # optional include/exclude filtering
            include_terms = [s.strip() for s in args.include.split(',')] if args.include else None
            exclude_terms = [s.strip() for s in args.exclude.split(',')] if args.exclude else None
            def tag_ok(tag: str) -> bool:
                ok = True
                if include_terms:
                    ok = any(term in tag for term in include_terms)
                if ok and exclude_terms:
                    if any(term in tag for term in exclude_terms):
                        ok = False
                return ok
            if include_terms or exclude_terms:
                tags = [t for t in tags if tag_ok(t)]

            print(f"Auto-selected tags ({args.auto_mode}): count={len(tags)}")
            if not tags:
                print("No tags selected; listing sample from first run. Use --tags or --include/--exclude.")
                rid0 = next(iter(available_by_run.keys()))
                print(f"Sample tags ({rid0}): {sorted(list(available_by_run[rid0]))[:60]}")
                return
        else:
            tags = [t.strip() for t in args.tags.split(',') if t.strip()]

        # Plot and CSV: per tag, overlay all runs
        summary_rows = []
        for tag in tags:
            plt.figure(figsize=(10, 4))
            safe_tag = tag.replace('/', '_').replace(' ', '_')
            merged = None
            for rid, ea in accs.items():
                df = get_scalar_df(ea, tag)
                if df is None or df.empty:
                    print(f"[{rid}] tag not found/empty: {tag}")
                    continue
                series = smooth(df['value'], args.smooth) if args.smooth and args.smooth > 1 else df['value']
                plt.plot(df['step'], series, label=rid)
                # merge for CSV
                cur = df[['step', 'value']].rename(columns={'value': rid})
                merged = cur if merged is None else merged.merge(cur, on='step', how='outer')

                # collect summary for reward-like tags
                if tag.endswith('ep_rew_mean'):
                    last_n = min(100, len(df))
                    last_mean = float(df['value'].tail(last_n).mean()) if last_n > 0 else float('nan')
                    best = float(df['value'].max())
                    step_at_best = int(df.loc[df['value'].idxmax(), 'step']) if len(df) > 0 else -1
                    summary_rows.append({
                        'run': rid, 'tag': tag, 'best': best, 'step_at_best': step_at_best, 'last100_mean': last_mean,
                    })
            if merged is not None:
                csv_path = os.path.join(args.out_dir, f"compare_{safe_tag}.csv")
                merged.sort_values('step').to_csv(csv_path, index=False)
                print(f"Wrote CSV: {csv_path} ({merged.shape})")
                plt.xlabel('step')
                plt.ylabel(tag)
                plt.title(f"{tag} (smooth={args.smooth})")
                plt.legend()
                png_path = os.path.join(args.out_dir, f"compare_{safe_tag}.png")
                plt.tight_layout(); plt.savefig(png_path); plt.close()
                print(f"Wrote PNG: {png_path}")
            else:
                plt.close()

        # Summary table for rewards if any
        if summary_rows:
            import pandas as pd
            sdf = pd.DataFrame(summary_rows)
            spath = os.path.join(args.out_dir, f"summary_rewards.csv")
            sdf.to_csv(spath, index=False)
            print("Reward summary:\n", sdf.sort_values(['tag','best'], ascending=[True, False]).to_string(index=False))
            print(f"Wrote summary: {spath}")

        print(f"Compare report saved to {args.out_dir}")
        return

    # Single run path (original behavior)
    if args.run_path:
        run_dir = args.run_path
    else:
        run_dir = find_latest_run(args.runs_dir)
    print(f"Using run dir: {run_dir}")

    event_files = find_event_files(run_dir)
    if not event_files:
        print(f"No event files found under {run_dir}")
        return
    # pick the latest event file
    event_file = event_files[-1]
    print(f"Loading event file: {event_file}")
    ea = load_event_accumulator(event_file)

    tags_available = list_scalar_tags(ea)
    print(f"Found {len(tags_available)} scalar tags. Sample: {tags_available[:40]}")

    if not args.tags:
        print("No tags specified. Listing top tags and exiting. Use --tags to export/plot specific tags.")
        return

    tags = [t.strip() for t in args.tags.split(',') if t.strip()]

    # try to detect lr tag and total steps
    lr_tag = auto_find_lr_tag(tags_available)
    if lr_tag:
        print(f"Detected learning-rate tag: {lr_tag}")
    else:
        print("No obvious learning-rate tag detected automatically.")

    inferred_total = args.total_timesteps or try_extract_total_timesteps_from_text(ea)
    if inferred_total:
        print(f"Inferred total_timesteps = {inferred_total}")

    # iterate tags and export/plot
    for tag in tags:
        df = get_scalar_df(ea, tag)
        if df is None or df.empty:
            print(f"Tag not found or empty: {tag}")
            continue
        if args.smooth and args.smooth > 1:
            df['value_smooth'] = smooth(df['value'], args.smooth)
        else:
            df['value_smooth'] = df['value']

        # export CSV
        safe_tag = tag.replace('/', '_').replace(' ', '_')
        csv_path = os.path.join(args.out_dir, f"{safe_tag}.csv")
        df.to_csv(csv_path, index=False)
        print(f"Wrote CSV: {csv_path} ({len(df)} rows)")

        # plot
        plt.figure(figsize=(10, 4))
        plt.plot(df['step'], df['value'], alpha=0.25, label='raw')
        plt.plot(df['step'], df['value_smooth'], label=f'smooth({args.smooth})')
        plt.xlabel('step')
        plt.ylabel(tag)
        plt.title(f"{tag} @ {os.path.basename(run_dir)}")
        plt.legend()
        png_path = os.path.join(args.out_dir, f"{safe_tag}.png")
        plt.tight_layout()
        plt.savefig(png_path)
        plt.close()
        print(f"Wrote PNG: {png_path}")

    # report learning rate current value and progress if possible
    if lr_tag and lr_tag in tags_available:
        lr_df = get_scalar_df(ea, lr_tag)
        if lr_df is not None and not lr_df.empty:
            cur_lr = float(lr_df['value'].iloc[-1])
            cur_step = int(lr_df['step'].iloc[-1])
            print(f"Current learning rate (tag {lr_tag}) = {cur_lr} at step {cur_step}")
            if inferred_total:
                progress = float(cur_step) / float(inferred_total)
                print(f"Learning-rate progress: {progress*100:.2f}% ({cur_step}/{inferred_total})")
            else:
                print("Total timesteps unknown: pass --total-timesteps to compute progress percentage.")
        else:
            print("Learning-rate tag found but no scalar data present.")
    else:
        print("No learning-rate tag detected or not included in --tags.")

    print(f"Report saved to {args.out_dir}")


if __name__ == '__main__':
    main()
