#!/usr/bin/env bash
# ============================================================
# 内存监控 watchdog — 纯记录版
#
# 功能: 每 30s 记录内存和 cachesim 状态到日志
# 主动杀进程的职责已移交给 run_retry.sh 的内存感知调度
# 本脚本仅做监控和报警记录
#
# 使用: nohup bash scripts/mem_watchdog.sh &
# 日志: tmp/mem_watchdog.log
# ============================================================
set -u

INTERVAL=30  # 检查间隔（秒）

BASEDIR="/home/丁坤鹏/libcachesim_new"
LOG="${BASEDIR}/tmp/mem_watchdog.log"
mkdir -p "$(dirname "$LOG")"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] mem_watchdog started (monitor-only, interval=${INTERVAL}s)" >> "$LOG"

while true; do
    total_kb=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
    avail_kb=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
    used_pct=$(( (total_kb - avail_kb) * 100 / total_kb ))
    avail_gb=$(awk "BEGIN {printf \"%.1f\", ${avail_kb}/1048576}")

    n_cachesim=$(pgrep -c cachesim 2>/dev/null || echo 0)

    # 仅在内存偏高(≥75%)或有 cachesim 运行时记录
    if (( used_pct >= 75 )) || (( n_cachesim > 0 )); then
        # 列出各 cachesim 进程 RSS
        cachesim_detail=""
        if (( n_cachesim > 0 )); then
            cachesim_detail=$(ps -C cachesim -o pid=,rss= --sort=-rss 2>/dev/null | head -6 | awk '{printf " pid=%s(%.1fGB)", $1, $2/1048576}')
        fi
        echo "[$(date '+%H:%M:%S')] mem=${used_pct}% avail=${avail_gb}GB cachesim=${n_cachesim}${cachesim_detail}" >> "$LOG"
    fi

    sleep "$INTERVAL"
done
