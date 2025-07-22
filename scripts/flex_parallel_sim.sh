#!/bin/bash

# 显示帮助信息
show_help() {
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  -t, --trace PATH       指定 trace 文件或目录路径 (必须)"
    echo "  -p, --parallel NUM     指定最大并行任务数 (默认: 4)"
    echo "  -f, --format FORMAT    指定 trace 格式 (默认: oracleGeneral)"
    echo "  -h, --help             显示此帮助信息"
    echo
    echo "示例:"
    echo "  $0 -t data/TencentPhoto -p 8"
    echo "  $0 --trace data/TencentPhoto/file.zst --parallel 2"
    exit 1
}

# 设置默认参数
TRACE_PATH=""
MAX_PARALLEL=4
TRACE_FORMAT="oracleGeneral"

# 算法和缓存大小配置
declare -a ALGORITHMS=("LRU" "LHD" "GDSF" "ARC" "SIEVE" "S3FIFO" "wtinylfu" "lecar" "cacheus" "lrb" "glcache" "3lcache")
declare -a CACHE_SIZES=("0.001" "0.1")

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -t|--trace)
            TRACE_PATH="$2"
            shift 2
            ;;
        -p|--parallel)
            MAX_PARALLEL="$2"
            shift 2
            ;;
        -f|--format)
            TRACE_FORMAT="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "未知选项: $1"
            show_help
            ;;
    esac
done

# 检查必要参数
if [[ -z "$TRACE_PATH" ]]; then
    echo "错误: 必须指定 trace 文件或目录路径"
    show_help
fi

# 检查参数值是否合法
if ! [[ "$MAX_PARALLEL" =~ ^[0-9]+$ ]] || [ "$MAX_PARALLEL" -lt 1 ]; then
    echo "错误: 并行任务数必须是正整数"
    show_help
fi

# 跟踪运行中的进程
declare -a PIDS

# 等待任意一个槽位可用
wait_for_job_slot() {
    while [[ ${#PIDS[@]} -ge $MAX_PARALLEL ]]; do
        # 检查进程状态，移除已完成的进程
        for i in "${!PIDS[@]}"; do
            if ! ps -p ${PIDS[$i]} > /dev/null; then
                unset PIDS[$i]
            fi
        done

        # 如果仍然满了，等待一秒
        if [[ ${#PIDS[@]} -ge $MAX_PARALLEL ]]; then
            sleep 1
        fi
    done
}

# 等待所有进程完成
wait_for_all_jobs() {
    for pid in "${PIDS[@]}"; do
        wait $pid
    done
    PIDS=()
}

# 处理单个trace文件
process_trace_file() {
    local trace_file="$1"

    # 提取文件名用于输出
    filename=$(basename "$trace_file")
    trace_name="${filename%.*}"

    echo "处理文件: $trace_file"

    # 对每个 trace 文件，为每种算法和缓存大小组合创建任务
    for algo in "${ALGORITHMS[@]}"; do
        # 将多个缓存大小合并为逗号分隔的字符串
        cache_sizes_str=$(IFS=,; echo "${CACHE_SIZES[*]}")

        # 等待可用槽位
        wait_for_job_slot

        # 构建命令
        cmd="./_build/bin/cachesim \"$trace_file\" $TRACE_FORMAT $algo $cache_sizes_str"

        echo "开始处理 $trace_name 算法: $algo: $(date)"
        # 执行命令，后台运行
        (
            echo "===================="
            echo "正在处理: $trace_file"
            echo "算法: $algo"
            echo "缓存大小: $cache_sizes_str"
            echo "执行命令: $cmd"
            eval "$cmd"
            echo "完成: $trace_file - $algo"
            echo "完成时间: $(date)"
            echo "===================="
        ) &

        # 保存进程ID
        PIDS+=($!)

        echo "后台任务已启动: $trace_name - $algo (PID: $!), 当前运行任务数: ${#PIDS[@]}"
    done
}

# 主程序
echo "开始并行模拟，最大并行任务数: $MAX_PARALLEL"
echo "开始时间: $(date)"
echo "Trace路径: $TRACE_PATH"
echo "Trace格式: $TRACE_FORMAT"
echo "===================================="

# 检查是文件还是目录
if [ -d "$TRACE_PATH" ]; then
    # 是目录，查找所有zst文件
    # 使用数组避免管道中的子shell问题
    declare -a trace_files
    while IFS= read -r -d '' trace_file; do
        trace_files+=("$trace_file")
    done < <(find "$TRACE_PATH" -type f -name "*.zst" | grep -v "/test/" | grep -v "/MetaKV/" | grep -v "/MetaCDN/" | grep -v "/Alibaba/" | grep -v "/TencentCBS/" | sort -z)

    # 处理所有找到的文件
    for trace_file in "${trace_files[@]}"; do
        process_trace_file "$trace_file"
    done
elif [ -f "$TRACE_PATH" ]; then
    # 是文件，直接处理
    process_trace_file "$TRACE_PATH"
else
    echo "错误: $TRACE_PATH 不存在或既不是文件也不是目录"
    exit 1
fi

# 等待所有剩余的进程完成
echo "等待剩余的任务完成..."
wait_for_all_jobs

echo "所有测试完成"
echo "结束时间: $(date)"
