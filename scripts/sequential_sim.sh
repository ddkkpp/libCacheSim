#!/bin/bash

# 设置算法和缓存大小参数
ALGORITHMS="LRU,LHD,GDSF,ARC,SIEVE,S3FIFO,wtinylfu,lecar,cacheus,lrb,glcache,3lcache"
CACHE_SIZES="0.001,0.1"
TRACE_FORMAT="oracleGeneral"
OUTPUT_DIR="result/sequential"

# 创建结果目录
mkdir -p "$OUTPUT_DIR"

# 记录脚本开始时间
echo "开始时间: $(date)"
echo "===================================="

# 查找所有zst文件，排除特定目录
find data -type f -name "*.zst" | grep -v "/test/" | grep -v "/MetaKV/" | grep -v "/MetaCDN/" | grep -v "/Alibaba/" | grep -v "/TencentCBS/" | sort | while read trace_file; do
    # 提取文件名用于输出
    filename=$(basename "$trace_file")
    trace_name="${filename%.*}"

    echo "处理文件: $trace_file"
    echo "开始时间: $(date)"

    # 构建命令
    cmd="./_build/bin/cachesim \"$trace_file\" $TRACE_FORMAT $ALGORITHMS $CACHE_SIZES"

    # 创建输出和错误日志文件
    output_file="$OUTPUT_DIR/${trace_name}.out"
    error_log="$OUTPUT_DIR/${trace_name}.err"

    echo "运行命令: $cmd"
    echo "输出文件: $output_file"
    echo "错误日志: $error_log"

    # 执行命令，等待其完成，同时输出到终端和文件
    eval "$cmd 2>&1 | tee \"$output_file\" | tee \"$error_log\""

    # 检查命令是否成功执行
    if [ $? -eq 0 ]; then
        echo "命令执行成功"
    else
        echo "命令执行失败，请查看错误日志: $error_log"
    fi

    echo "结束时间: $(date)"
    echo "===================================="
done

echo "所有测试完成"
echo "结束时间: $(date)"
