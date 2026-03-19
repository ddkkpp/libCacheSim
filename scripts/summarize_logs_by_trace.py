#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scan ac_sb3_*.log and cachesim_sb3_*.log pairs, group runs by (trace path, request count),
and generate a Markdown summary that lists for each group: model, key parameters, miss/hit ratio,
observation view, first N weight vectors, and notes about initial states (if unavailable).

Usage:
  python3 scripts/summarize_logs_by_trace.py --output docs/20251107-RL_CacheSim_Run_Summary_by_Trace.md --weights 5
"""
import argparse
import glob
import os
import re
import io
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple, Set, Any
import json

CONFIG_KEYS = [
    'algorithm', 'buffer_size', 'learning_rate', 'batch_size', 'tau', 'gamma',
    'learning_starts', 'train_freq', 'gradient_steps', 'policy_delay',
    'target_policy_noise', 'target_noise_clip', 'net_arch', 'activation_fn',
    'action_noise', 'shm_key', 'obs_keep', 'obs_dim', 'rl_update_interval'
]

TRACE_RE = re.compile(r"trace path:\s*([^,]+).*?,\s*(\d+)\s+threads", re.IGNORECASE)
FINAL_RE = re.compile(r"([0-9][0-9,]*)\s+req,\s+miss ratio\s+([0-9]*\.?[0-9]+),\s+byte miss ratio\s+([0-9]*\.?[0-9]+)")
TRAINING_HDR_RE = re.compile(r"(?:📋\s*)?training configuration(?:[^\n]*):", re.IGNORECASE)
INIT_STATE_RE = re.compile(r"\[INIT\]\s*Python initial state.*?:\s*raw=\[(.*?)\]")
INIT_OBS_RE = re.compile(r"\[INIT\]\s*Python initial obs_view:\s*idx=\[(.*?)\],\s*values=\[(.*?)\]")
GLOBAL_RE = re.compile(r"\[global_features\]:\s*\[(.*?)\]")
REQUEST_RE = re.compile(r"\[request_features\]:\s*\[(.*?)\]")
CACHE_RE = re.compile(r"\[cache_features\]:\s*\[(.*?)\]")

@dataclass
class RunInfo:
    timestamp: str
    cachesim_log: str
    python_log: Optional[str]
    trace_path: str
    threads: Optional[int]
    req_count: Optional[int]
    miss_ratio: Optional[float]
    byte_miss_ratio: Optional[float]
    hit_ratio: Optional[float]
    observation_view: Optional[str]
    config_lines: List[str]
    first_weights: List[str]
    init_state: Optional[str]
    init_obs_idx: Optional[str]
    init_obs_values: Optional[str]
    states: List[Dict[str, str]]  # list of {global, request, cache?}


def parse_cachesim_log(path: str) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[float], Optional[float]]:
    """高效解析 cachesim 日志：
    - 仅读取文件前若干 KB 寻找 trace / threads。
    - 从文件末尾反向读取一个窗口抓取最终 miss ratio 行。
    """
    trace_path = None
    threads = None
    req = None
    miss = None
    byte_miss = None
    try:
        # 读取开头窗口
        with open(path, 'rb') as fb:
            head_chunk = fb.read(32 * 1024)  # 32KB 够覆盖头部 trace line
        for line in head_chunk.decode(errors='ignore').splitlines():
            if trace_path is None:
                m = TRACE_RE.search(line)
                if m:
                    trace_path = m.group(1).strip()
                    try:
                        threads = int(m.group(2))
                    except Exception:
                        threads = None
                    break
        # 读取尾部窗口
        file_size = os.path.getsize(path)
        tail_size = min(128 * 1024, file_size)  # 最多 128KB
        with open(path, 'rb') as fb:
            fb.seek(file_size - tail_size)
            tail_chunk = fb.read(tail_size)
        # 反向搜索更快：
        for line in reversed(tail_chunk.decode(errors='ignore').splitlines()):
            m2 = FINAL_RE.search(line)
            if m2:
                try:
                    req = int(m2.group(1).replace(',', ''))
                except Exception:
                    req = None
                try:
                    miss = float(m2.group(2))
                except Exception:
                    miss = None
                try:
                    byte_miss = float(m2.group(3))
                except Exception:
                    byte_miss = None
                break
    except FileNotFoundError:
        pass
    return trace_path, threads, req, miss, byte_miss


def parse_python_log(path: str, weights_limit: int, states_limit: int) -> Tuple[Optional[str], List[str], List[str], Optional[str], Optional[str], Optional[str], List[Dict[str, str]]]:
    """解析 Python 日志：快速寻找观测视图、训练配置和前 N 组权重。
    为避免读取超大文件全部内容，采用增量扫描：
    - 第一阶段：逐行扫描直到找到 training header 与观测视图或达到 20000 行上限。
    - 第二阶段：继续扫描权重行（遇到足够数量后停止）。
    """
    observation_view = None
    config_lines: List[str] = []
    first_weights: List[str] = []
    header_found = False
    header_buffer: List[str] = []
    init_state: Optional[str] = None
    init_obs_idx: Optional[str] = None
    init_obs_values: Optional[str] = None
    states: List[Dict[str, str]] = []
    current: Dict[str, str] = {}
    try:
        with open(path, 'r', errors='ignore') as f:
            for idx, line in enumerate(f):
                if observation_view is None and 'Observation view:' in line:
                    observation_view = line.strip()
                if init_state is None:
                    m_s = INIT_STATE_RE.search(line)
                    if m_s:
                        init_state = m_s.group(1).strip()
                if init_obs_idx is None or init_obs_values is None:
                    m_o = INIT_OBS_RE.search(line)
                    if m_o:
                        init_obs_idx = m_o.group(1).strip()
                        init_obs_values = m_o.group(2).strip()
                # 解析状态块：[global_features]/[request_features]/[cache_features]
                if states_limit > 0:
                    mg = GLOBAL_RE.search(line)
                    if mg:
                        # 推入上一个快照（如完整或部分）
                        if current and len(states) < states_limit:
                            states.append(current)
                        # 开启新快照
                        current = {"global": mg.group(1).strip()}
                        continue
                    mr = REQUEST_RE.search(line)
                    if mr and current is not None:
                        current["request"] = mr.group(1).strip()
                        continue
                    mc = CACHE_RE.search(line)
                    if mc and current is not None:
                        current["cache"] = mc.group(1).strip()
                        continue
                if not header_found and TRAINING_HDR_RE.search(line):
                    header_found = True
                    continue  # 下一行开始收集
                elif header_found:
                    if not line.strip():
                        break  # 结束配置段
                    header_buffer.append(line.rstrip())
                if idx > 20000 and not header_found:
                    # 放弃继续寻找 header，避免超大文件拖慢
                    break
        # 文件结束后，若还有一块未推入的状态
        if states_limit > 0 and current and len(states) < states_limit:
            states.append(current)
        # 过滤关键配置行并去重（保持顺序）
        seen: Set[str] = set()
        for ln in header_buffer:
            for key in CONFIG_KEYS:
                if key in ln:
                    s = ln.strip()
                    if s not in seen:
                        config_lines.append(s)
                        seen.add(s)
                    break
        # 单独再次扫描权重行（无需重新加载全部文件，可限行数）
        with open(path, 'r', errors='ignore') as f:
            for line in f:
                if 'Python weights written' in line:
                    first_weights.append(line.strip())
                    if len(first_weights) >= weights_limit:
                        break
    except FileNotFoundError:
        pass
    return observation_view, config_lines, first_weights, init_state, init_obs_idx, init_obs_values, states


def build_summary(weights_limit: int, states_limit: int, max_logs: Optional[int] = None, progress: bool = True) -> Dict[Tuple[str, int], List[RunInfo]]:
    groups: Dict[Tuple[str, int], List[RunInfo]] = defaultdict(list)
    cs_logs = sorted(glob.glob('logs/cachesim_sb3_*.log'))
    if max_logs is not None:
        cs_logs = cs_logs[:max_logs]
    for i, cs in enumerate(cs_logs, 1):
        cs_base = os.path.basename(cs)
        ts = cs_base.replace('cachesim_sb3_', '').replace('.log', '')
        trace_path, threads, req, miss, byte_miss = parse_cachesim_log(cs)
        if not trace_path or req is None:
            continue
        ac = os.path.join(os.path.dirname(cs), f'ac_sb3_{ts}.log')
        observation_view = None
        config_lines: List[str] = []
        first_weights: List[str] = []
        init_state = None
        init_obs_idx = None
        init_obs_values = None
        if os.path.exists(ac):
            observation_view, config_lines, first_weights, init_state, init_obs_idx, init_obs_values, states = parse_python_log(ac, weights_limit, states_limit)
        hit = (1.0 - miss) if miss is not None else None
        groups[(trace_path, req)].append(
            RunInfo(
                timestamp=ts,
                cachesim_log=cs,
                python_log=ac if os.path.exists(ac) else None,
                trace_path=trace_path,
                threads=threads,
                req_count=req,
                miss_ratio=miss,
                byte_miss_ratio=byte_miss,
                hit_ratio=hit,
                observation_view=observation_view,
                config_lines=config_lines,
                first_weights=first_weights,
                init_state=init_state,
                init_obs_idx=init_obs_idx,
                init_obs_values=init_obs_values,
                states=states,
            )
        )
        if progress and i % 50 == 0:
            print(f"[progress] 已处理 {i}/{len(cs_logs)} cachesim 日志")
    return groups


def write_markdown(groups: Dict[Tuple[str, int], List[RunInfo]], output: str, weights_limit: int, states_limit: int) -> None:
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, 'w', encoding='utf-8') as out:
        out.write("# RL + CacheSim 运行汇总（按 trace + 请求数 分组）\n\n")
        out.write(f"生成时间: 自动扫描本地日志；每组展示前 {weights_limit} 组初始权重。\\n\n")
        for (trace, req) in sorted(groups.keys(), key=lambda k: (k[0], k[1])):
            runs = sorted(groups[(trace, req)], key=lambda r: r.timestamp)
            out.write(f"## Trace: {trace} | 请求数: {req}\n\n")
            # 组内初始状态一致性分析
            init_states = [r.init_state for r in runs if r.init_state]
            if init_states:
                uniq = {s for s in init_states}
                if len(uniq) == 1:
                    out.write("- 初始状态一致性: 全部相同\n\n")
                else:
                    out.write(f"- 初始状态一致性: 存在差异（{len(uniq)} 种）\n\n")
            for r in runs:
                out.write(f"### 运行 {r.timestamp}\n\n")
                out.write(f"- Cachesim 日志: `{r.cachesim_log}`\n")
                if r.python_log:
                    out.write(f"- Python 日志: `{r.python_log}`\n")
                if r.threads is not None:
                    out.write(f"- 线程数: {r.threads}\n")
                if r.miss_ratio is not None:
                    out.write(f"- Miss ratio: {r.miss_ratio:.4f} | Hit ratio: { (1.0 - r.miss_ratio):.4f}\n")
                if r.byte_miss_ratio is not None:
                    out.write(f"- Byte miss ratio: {r.byte_miss_ratio:.4f}\n")
                if r.observation_view:
                    out.write(f"- 观测视图: {r.observation_view}\n")
                if r.config_lines:
                    out.write("- 关键训练参数:\n")
                    for ln in r.config_lines:
                        out.write(f"  - {ln}\n")
                else:
                    out.write("- 关键训练参数: N/A（未在日志中找到训练配置段）\n")
                # 初始/前几个状态（从 [global_features]/[request_features]/[cache_features] 提取）
                if r.states:
                    out.write(f"- 前 {min(states_limit, len(r.states))} 个状态:\n")
                    for i, s in enumerate(r.states[:states_limit], 1):
                        gf = s.get("global")
                        rf = s.get("request")
                        cf = s.get("cache")
                        out.write(f"  - state[{i}]:\n")
                        if gf: out.write(f"    - global_features: [{gf}]\n")
                        if rf: out.write(f"    - request_features: [{rf}]\n")
                        if cf: out.write(f"    - cache_features: [{cf}]\n")
                else:
                    # 回退：若未抓到状态，尝试用 INIT 行
                    if r.init_state:
                        out.write(f"- 初始状态(raw): [{r.init_state}]\n")
                        if r.init_obs_idx is not None and r.init_obs_values is not None:
                            out.write(f"- 初始观测(obs_view): idx=[{r.init_obs_idx}], values=[{r.init_obs_values}]\n")
                    else:
                        out.write("- 初始状态: N/A\n")
                # First weights
                if r.first_weights:
                    out.write(f"- 初始前 {min(weights_limit, len(r.first_weights))} 组权重:\n")
                    for w in r.first_weights[:weights_limit]:
                        out.write(f"  - {w}\n")
                else:
                    out.write("- 初始权重: N/A（日志未捕获到 \"Python weights written\"）\n")
                out.write("\n")
    print(f"Wrote summary to {output}")


def load_cache(cache_path: str) -> Dict[str, Any]:
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"runs": {}}  # timestamp -> run dict


def save_cache(cache_path: str, cache: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def groups_from_cache(cache: Dict[str, Any]) -> Dict[Tuple[str, int], List[RunInfo]]:
    groups: Dict[Tuple[str, int], List[RunInfo]] = defaultdict(list)
    for ts, rd in cache.get("runs", {}).items():
        ri = RunInfo(
            timestamp=ts,
            cachesim_log=rd.get("cachesim_log"),
            python_log=rd.get("python_log"),
            trace_path=rd.get("trace_path"),
            threads=rd.get("threads"),
            req_count=rd.get("req_count"),
            miss_ratio=rd.get("miss_ratio"),
            byte_miss_ratio=rd.get("byte_miss_ratio"),
            hit_ratio=rd.get("hit_ratio"),
            observation_view=rd.get("observation_view"),
            config_lines=rd.get("config_lines", []),
            first_weights=rd.get("first_weights", []),
            init_state=rd.get("init_state"),
            init_obs_idx=rd.get("init_obs_idx"),
            init_obs_values=rd.get("init_obs_values"),
            states=rd.get("states", []),
        )
        groups[(ri.trace_path, ri.req_count)].append(ri)
    return groups


def merge_runs_into_cache(cache: Dict[str, Any], groups: Dict[Tuple[str, int], List[RunInfo]]) -> Dict[str, Any]:
    runs = cache.get("runs", {})
    for glist in groups.values():
        for r in glist:
            runs[r.timestamp] = {
                "cachesim_log": r.cachesim_log,
                "python_log": r.python_log,
                "trace_path": r.trace_path,
                "threads": r.threads,
                "req_count": r.req_count,
                "miss_ratio": r.miss_ratio,
                "byte_miss_ratio": r.byte_miss_ratio,
                "hit_ratio": r.hit_ratio,
                "observation_view": r.observation_view,
                "config_lines": r.config_lines,
                "first_weights": r.first_weights,
                "init_state": r.init_state,
                "init_obs_idx": r.init_obs_idx,
                "init_obs_values": r.init_obs_values,
                "states": r.states,
            }
    cache["runs"] = runs
    return cache


def main():
    parser = argparse.ArgumentParser(description='Summarize RL + CacheSim logs by trace and request count.')
    parser.add_argument('--output', default='docs/20251107-RL_CacheSim_Run_Summary_by_Trace.md', help='Output markdown file path')
    parser.add_argument('--weights', type=int, default=5, help='Number of initial weight lines to include')
    parser.add_argument('--max-logs', type=int, default=None, help='Limit number of cachesim logs processed (for quick trial).')
    parser.add_argument('--no-progress', action='store_true', help='Disable periodic progress output.')
    parser.add_argument('--states', type=int, default=3, help='Number of initial state snapshots to include from [global/request/cache]_features logs')
    parser.add_argument('--incremental', action='store_true', help='Only parse new logs and merge into cache; rebuild markdown from cache')
    parser.add_argument('--cache', default='docs/RL_CacheSim_Run_Summary.cache.json', help='Path to cache JSON for incremental mode')
    args = parser.parse_args()

    if args.incremental:
        cache = load_cache(args.cache)
        existing_ts = set(cache.get("runs", {}).keys())
        # 识别所有 cachesim 日志并过滤掉已处理的时间戳
        cs_logs = sorted(glob.glob('logs/cachesim_sb3_*.log'))
        new_cs_logs = [
            cs for cs in cs_logs
            if os.path.basename(cs).replace('cachesim_sb3_', '').replace('.log', '') not in existing_ts
        ]
        if not new_cs_logs:
            # 无新日志，直接从缓存重建文档
            groups_cached = groups_from_cache(cache)
            if not groups_cached:
                print('No logs found in cache. Nothing to do.')
                return
            write_markdown(groups_cached, args.output, args.weights, args.states)
            print(f"Wrote summary to {args.output} (from cache)")
            return
        # 针对新日志构建分组
        # 暂时复用 build_summary，但用 max_logs 限制不生效；我们将直接临时覆盖 glob 列表
        # 为简化，临时修改工作流：依然调用 build_summary 但前置筛选 new_cs_logs
        groups_new: Dict[Tuple[str, int], List[RunInfo]] = defaultdict(list)
        total = len(new_cs_logs)
        for i, cs in enumerate(new_cs_logs, 1):
            cs_base = os.path.basename(cs)
            ts = cs_base.replace('cachesim_sb3_', '').replace('.log', '')
            trace_path, threads, req, miss, byte_miss = parse_cachesim_log(cs)
            if not trace_path or req is None:
                continue
            ac = os.path.join(os.path.dirname(cs), f'ac_sb3_{ts}.log')
            observation_view = None
            config_lines: List[str] = []
            first_weights: List[str] = []
            init_state = None
            init_obs_idx = None
            init_obs_values = None
            states: List[Dict[str, str]] = []
            if os.path.exists(ac):
                observation_view, config_lines, first_weights, init_state, init_obs_idx, init_obs_values, states = parse_python_log(ac, args.weights, args.states)
            hit = (1.0 - miss) if miss is not None else None
            groups_new[(trace_path, req)].append(
                RunInfo(
                    timestamp=ts,
                    cachesim_log=cs,
                    python_log=ac if os.path.exists(ac) else None,
                    trace_path=trace_path,
                    threads=threads,
                    req_count=req,
                    miss_ratio=miss,
                    byte_miss_ratio=byte_miss,
                    hit_ratio=hit,
                    observation_view=observation_view,
                    config_lines=config_lines,
                    first_weights=first_weights,
                    init_state=init_state,
                    init_obs_idx=init_obs_idx,
                    init_obs_values=init_obs_values,
                    states=states,
                )
            )
            if not args.no_progress and i % 50 == 0:
                print(f"[incremental] 已解析新日志 {i}/{total}")

        # 合并并保存缓存
        cache = merge_runs_into_cache(cache, groups_new)
        save_cache(args.cache, cache)
        groups_all = groups_from_cache(cache)
        write_markdown(groups_all, args.output, args.weights, args.states)
        print(f"Wrote summary to {args.output} (incremental, merged {total} new runs)")
        return

    # 非增量：全量扫描
    groups = build_summary(args.weights, args.states, max_logs=args.max_logs, progress=not args.no_progress)
    if not groups:
        print('No logs found or unable to parse any groups. Ensure cachesim_sb3_*.log files exist.')
        return
    # 保存缓存供下次增量
    cache = load_cache(args.cache)
    cache = merge_runs_into_cache(cache, groups)
    save_cache(args.cache, cache)
    write_markdown(groups, args.output, args.weights, args.states)


if __name__ == '__main__':
    main()
