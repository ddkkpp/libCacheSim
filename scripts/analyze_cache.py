#!/usr/bin/env python3
"""
缓存模拟日志分析工具

解析 C/Python 两端的统一格式日志，提取：
1. CONTEXT_DIM_CONFIG: 状态向量维度配置
2. STATE_*: 分类别的状态向量 (MISSRATIO, HIT_MISS, CACHE, CAND_0-5, TOPK_0-7)
3. WEIGHTS_UPDATED: 权重向量

输出：
- CSV 数据文件
- 各维度的时序图
"""

import matplotlib.pyplot as plt
import re
import numpy as np
import pandas as pd
import argparse
import sys
import os

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='从缓存模拟日志中提取特征数据并可视化')
    parser.add_argument('file_path', type=str, help='日志文件路径')
    parser.add_argument('--output-dir', '-o', type=str, default='./output',
                       help='输出文件目录 (默认: ./output)')
    parser.add_argument('--dpi', type=int, default=100,
                       help='图表DPI (默认: 100)')
    parser.add_argument('--max-points', type=int, default=50000,
                       help='每个图表最大数据点数，超过则分段绘制 (默认: 50000)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='显示详细输出')
    return parser.parse_args()

def ensure_output_dir(output_dir):
    """确保输出目录存在"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")

def extract_features_from_log(log_file_path):
    """
    从日志文件中提取所有状态向量和权重数据

    返回字典包含:
    - context_dim_config: 维度配置 {HITRATIO, HIT_MISS, CACHE, CAND, TOPK, TOTAL}
    - state_hitratio: [(seq, [values]), ...]  # obj_hit_ratio, byte_hit_ratio
    - state_hit_miss: [(seq, [values]), ...]
    - state_cache: [(seq, [values]), ...]
    - state_cand_0 ~ state_cand_5: 各组候选特征
    - state_topk_0 ~ state_topk_7: 各组TopK特征
    - weights: [(seq, [values]), ...]
    """
    result = {
        'context_dim_config': None,
        'state_hitratio': [],  # 存储 obj_hit_ratio 和 byte_hit_ratio
        'state_hit_miss': [],
        'state_cache': [],
        'weights': [],
    }

    # 初始化 CAND 和 TOPK 组
    for i in range(6):
        result[f'state_cand_{i}'] = []
    for i in range(8):
        result[f'state_topk_{i}'] = []
    for i in range(8):
        result[f'state_avgtopk_{i}'] = []

    line_count = 0
    print(f"正在读取文件: {log_file_path}")

    # 正则表达式模式
    config_pattern = re.compile(
        r'\[CONTEXT_DIM_CONFIG\]\s+(?:HITRATIO|MISSRATIO)=(\d+)\s+'
        r'HIT_MISS=(\d+)\s+CACHE=(\d+)\s+CAND=(\d+)\s+TOPK=(\d+)'
        r'(?:\s+AVGTOPK=(\d+))?(?:\s+REQUEST=(\d+))?\s+TOTAL=(\d+)'
    )
    # 同时匹配 STATE_HITRATIO 和 STATE_MISSRATIO（兼容旧日志）
    state_hitratio_pattern = re.compile(r'\[STATE_(?:HITRATIO|MISSRATIO)\]\s+\[seq\s+(\d+)\]\s+\[([0-9.,\s-]+)\]')
    state_hit_miss_pattern = re.compile(r'\[STATE_HIT_MISS\]\s+\[seq\s+(\d+)\]\s+\[([0-9.,\s-]+)\]')
    state_cache_pattern = re.compile(r'\[STATE_CACHE\]\s+\[seq\s+(\d+)\]\s+\[([0-9.,\s-]+)\]')
    state_cand_pattern = re.compile(r'\[STATE_CAND_(\d+)\]\s+\[seq\s+(\d+)\]\s+\[([0-9.,\s-]+)\]')
    state_topk_pattern = re.compile(r'\[STATE_TOPK_(\d+)\]\s+\[seq\s+(\d+)\]\s+\[([0-9.,\s-]+)\]')
    state_avgtopk_pattern = re.compile(r'\[STATE_AVGTOPK_(\d+)\]\s+\[seq\s+(\d+)\]\s+\[([0-9.,\s-]+)\]')
    weights_pattern = re.compile(r'\[WEIGHTS_UPDATED\]\s+\[seq\s+(\d+)\]\s+\[([0-9.,\s-]+)\]')

    with open(log_file_path, 'rb') as file:
        for line_num, raw in enumerate(file):
            try:
                line = raw.decode('utf-8', errors='replace')
            except Exception:
                line = raw.decode('latin-1', errors='replace')
            line_count += 1
            if line_num % 50000 == 0 and line_num > 0:
                print(f"已处理 {line_num} 行...")

            # 解析 CONTEXT_DIM_CONFIG
            config_match = config_pattern.search(line)
            if config_match and result['context_dim_config'] is None:
                avg_topk = int(config_match.group(6)) if config_match.group(6) else 0
                request_dim = int(config_match.group(7)) if config_match.group(7) else 0
                total = int(config_match.group(8))
                result['context_dim_config'] = {
                    'MISSRATIO': int(config_match.group(1)),
                    'HIT_MISS': int(config_match.group(2)),
                    'CACHE': int(config_match.group(3)),
                    'CAND': int(config_match.group(4)),
                    'TOPK': int(config_match.group(5)),
                    'AVGTOPK': avg_topk,
                    'REQUEST': request_dim,
                    'TOTAL': total,
                }
                print(f"解析到维度配置: {result['context_dim_config']}")
                continue

            # 解析 STATE_HITRATIO (兼容 STATE_MISSRATIO)
            match = state_hitratio_pattern.search(line)
            if match:
                seq = int(match.group(1))
                values = [float(x.strip()) for x in match.group(2).split(',')]
                result['state_hitratio'].append((seq, values))
                continue

            # 解析 STATE_HIT_MISS
            match = state_hit_miss_pattern.search(line)
            if match:
                seq = int(match.group(1))
                values = [float(x.strip()) for x in match.group(2).split(',')]
                result['state_hit_miss'].append((seq, values))
                continue

            # 解析 STATE_CACHE
            match = state_cache_pattern.search(line)
            if match:
                seq = int(match.group(1))
                values = [float(x.strip()) for x in match.group(2).split(',')]
                result['state_cache'].append((seq, values))
                continue

            # 解析 STATE_CAND_0 ~ STATE_CAND_5
            match = state_cand_pattern.search(line)
            if match:
                group_idx = int(match.group(1))
                seq = int(match.group(2))
                values = [float(x.strip()) for x in match.group(3).split(',')]
                if 0 <= group_idx < 6:
                    result[f'state_cand_{group_idx}'].append((seq, values))
                continue

            # 解析 STATE_TOPK_0 ~ STATE_TOPK_7
            match = state_topk_pattern.search(line)
            if match:
                group_idx = int(match.group(1))
                seq = int(match.group(2))
                values = [float(x.strip()) for x in match.group(3).split(',')]
                if 0 <= group_idx < 8:
                    result[f'state_topk_{group_idx}'].append((seq, values))
                continue

            # 解析 STATE_AVGTOPK_0 ~ STATE_AVGTOPK_7
            match = state_avgtopk_pattern.search(line)
            if match:
                group_idx = int(match.group(1))
                seq = int(match.group(2))
                values = [float(x.strip()) for x in match.group(3).split(',')]
                if 0 <= group_idx < 8:
                    result[f'state_avgtopk_{group_idx}'].append((seq, values))
                continue

            # 解析 WEIGHTS_UPDATED
            match = weights_pattern.search(line)
            if match:
                seq = int(match.group(1))
                values = [float(x.strip()) for x in match.group(2).split(',')]
                result['weights'].append((seq, values))
                continue

    print(f"文件读取完成，共处理 {line_count} 行")

    # 打印统计
    print("\n数据统计:")
    print(f"  HITRATIO 记录数: {len(result['state_hitratio'])}")
    print(f"  HIT_MISS 记录数: {len(result['state_hit_miss'])}")
    print(f"  CACHE 记录数: {len(result['state_cache'])}")
    for i in range(6):
        count = len(result[f'state_cand_{i}'])
        if count > 0:
            print(f"  CAND_{i} 记录数: {count}")
    for i in range(8):
        count = len(result[f'state_topk_{i}'])
        if count > 0:
            print(f"  TOPK_{i} 记录数: {count}")
    for i in range(8):
        count = len(result[f'state_avgtopk_{i}'])
        if count > 0:
            print(f"  AVGTOPK_{i} 记录数: {count}")
    print(f"  WEIGHTS 记录数: {len(result['weights'])}")

    return result

def save_to_csv(data, output_dir):
    """将数据保存到CSV文件"""
    print("\n保存数据到CSV文件...")
    saved_files = []

    # 保存维度配置
    if data['context_dim_config']:
        config_df = pd.DataFrame([data['context_dim_config']])
        config_path = os.path.join(output_dir, 'context_dim_config.csv')
        config_df.to_csv(config_path, index=False)
        print(f"  维度配置已保存: {config_path}")
        saved_files.append(config_path)

    # 保存各类状态数据
    state_categories = [
        ('state_hitratio', 'hitratio'),
        ('state_hit_miss', 'hit_miss'),
        ('state_cache', 'cache'),
    ]

    # 添加 CAND 和 TOPK 组
    for i in range(6):
        state_categories.append((f'state_cand_{i}', f'cand_{i}'))
    for i in range(8):
        state_categories.append((f'state_topk_{i}', f'topk_{i}'))
    for i in range(8):
        state_categories.append((f'state_avgtopk_{i}', f'avgtopk_{i}'))

    for key, name in state_categories:
        records = data[key]
        if records:
            # 确定维度
            dim = len(records[0][1]) if records else 0
            if dim > 0:
                df_data = []
                for seq, values in records:
                    row = {'seq': seq}
                    for i, v in enumerate(values):
                        row[f'dim_{i}'] = v
                    df_data.append(row)
                df = pd.DataFrame(df_data)
                csv_path = os.path.join(output_dir, f'state_{name}.csv')
                df.to_csv(csv_path, index=False)
                print(f"  {name} 数据已保存: {csv_path} ({len(records)} 行, {dim} 维)")
                saved_files.append(csv_path)

    # 保存权重数据
    if data['weights']:
        df_data = []
        for seq, values in data['weights']:
            row = {'seq': seq}
            for i, v in enumerate(values):
                row[f'weight_{i}'] = v
            df_data.append(row)
        df = pd.DataFrame(df_data)
        csv_path = os.path.join(output_dir, 'weights.csv')
        df.to_csv(csv_path, index=False)
        print(f"  权重数据已保存: {csv_path} ({len(data['weights'])} 行)")
        saved_files.append(csv_path)

    return saved_files

def plot_state_category(records, category_name, output_dir, dpi=100, max_points=50000):
    """绘制单个状态类别的各维度时序图"""
    if not records:
        return 0

    # 提取数据
    seqs = [r[0] for r in records]
    values_list = [r[1] for r in records]
    dim = len(values_list[0])

    # 转换为数组
    values_array = np.array(values_list)

    plot_count = 0
    category_dir = os.path.join(output_dir, 'plots', category_name)
    ensure_output_dir(category_dir)

    # 为每个维度绘制图
    for d in range(dim):
        dim_values = values_array[:, d]

        plt.figure(figsize=(12, 5))

        if len(dim_values) <= max_points:
            plt.plot(seqs, dim_values, linewidth=0.8, alpha=0.8)
        else:
            # 下采样
            step = len(dim_values) // max_points
            indices = list(range(0, len(dim_values), step))
            plt.plot([seqs[i] for i in indices], dim_values[indices], linewidth=0.8, alpha=0.8)

        plt.title(f'{category_name} - Dimension {d}', fontsize=12)
        plt.xlabel('Sequence Number', fontsize=10)
        plt.ylabel('Value', fontsize=10)
        plt.grid(True, alpha=0.3)

        # 添加统计信息
        stats_text = f'Count: {len(dim_values)}\nMean: {dim_values.mean():.4f}\nStd: {dim_values.std():.4f}'
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes,
                verticalalignment='top', fontsize=8,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        output_path = os.path.join(category_dir, f'dim_{d}.png')
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()
        plot_count += 1

    return plot_count

def plot_weights(records, output_dir, dpi=100):
    """绘制权重演变图"""
    if not records:
        return 0

    seqs = [r[0] for r in records]
    values_list = [r[1] for r in records]
    dim = len(values_list[0])
    values_array = np.array(values_list)

    weights_dir = os.path.join(output_dir, 'plots', 'weights')
    ensure_output_dir(weights_dir)

    # 1. 所有权重在一张图
    plt.figure(figsize=(14, 8))
    weight_names = ['recency', 'frequency', 'size', 'irt1', 'irt2', 'irt3']
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

    for d in range(min(dim, 6)):
        label = weight_names[d] if d < len(weight_names) else f'weight_{d}'
        plt.plot(seqs, values_array[:, d], label=label, linewidth=1.5, color=colors[d % len(colors)])

    plt.title('Weight Evolution Over Time', fontsize=14)
    plt.xlabel('Sequence Number', fontsize=12)
    plt.ylabel('Weight Value', fontsize=12)
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)

    output_path = os.path.join(weights_dir, 'all_weights.png')
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close()

    # 2. 每个权重单独一张图
    for d in range(dim):
        plt.figure(figsize=(12, 5))
        label = weight_names[d] if d < len(weight_names) else f'weight_{d}'
        plt.plot(seqs, values_array[:, d], linewidth=1.0, color=colors[d % len(colors)])

        plt.title(f'Weight: {label}', fontsize=12)
        plt.xlabel('Sequence Number', fontsize=10)
        plt.ylabel('Value', fontsize=10)
        plt.grid(True, alpha=0.3)

        # 统计信息
        dim_values = values_array[:, d]
        stats_text = f'Count: {len(dim_values)}\nMean: {dim_values.mean():.4f}\nStd: {dim_values.std():.4f}\nMin: {dim_values.min():.4f}\nMax: {dim_values.max():.4f}'
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes,
                verticalalignment='top', fontsize=8,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        output_path = os.path.join(weights_dir, f'weight_{d}_{label}.png')
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()

    return dim + 1

def plot_all_data(data, output_dir, dpi=100, max_points=50000):
    """绘制所有数据的图表"""
    print("\n生成图表...")
    total_plots = 0

    # 绘制各状态类别
    state_categories = [
        ('state_hitratio', 'HITRATIO'),
        ('state_hit_miss', 'HIT_MISS'),
        ('state_cache', 'CACHE'),
    ]
    for i in range(6):
        state_categories.append((f'state_cand_{i}', f'CAND_{i}'))
    for i in range(8):
        state_categories.append((f'state_topk_{i}', f'TOPK_{i}'))
    for i in range(8):
        state_categories.append((f'state_avgtopk_{i}', f'AVGTOPK_{i}'))

    for key, name in state_categories:
        records = data[key]
        if records:
            count = plot_state_category(records, name, output_dir, dpi, max_points)
            if count > 0:
                print(f"  {name}: {count} 张图")
                total_plots += count

    # 绘制权重
    if data['weights']:
        count = plot_weights(data['weights'], output_dir, dpi)
        print(f"  WEIGHTS: {count} 张图")
        total_plots += count

    return total_plots

def main():
    """主函数"""
    args = parse_arguments()

    if not os.path.exists(args.file_path):
        print(f"错误: 文件不存在: {args.file_path}")
        sys.exit(1)

    ensure_output_dir(args.output_dir)

    print("=" * 60)
    print("缓存日志分析工具 (C/Python 统一格式)")
    print("=" * 60)
    print(f"输入文件: {args.file_path}")
    print(f"输出目录: {args.output_dir}")
    print(f"图表DPI: {args.dpi}")
    print("=" * 60)

    try:
        # 提取数据
        data = extract_features_from_log(args.file_path)

        # 检查是否找到数据
        has_data = any([
            data['state_hitratio'],
            data['state_hit_miss'],
            data['state_cache'],
            data['weights'],
        ] + [data[f'state_cand_{i}'] for i in range(6)] +
            [data[f'state_topk_{i}'] for i in range(8)])

        if not has_data:
            print("\n警告: 未在日志中找到新格式的状态/权重数据")
            print("请确保日志包含以下格式的数据:")
            print("  [CONTEXT_DIM_CONFIG] HITRATIO=2 HIT_MISS=0 CACHE=0 CAND=0 TOPK=192 TOTAL=194")
            print("  [STATE_HITRATIO] [seq 1] [0.380000, 0.570735]")
            print("  [STATE_TOPK_0] [seq 1] [0.1, 0.2, ...]")
            print("  [WEIGHTS_UPDATED] [seq 1] [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]")
            sys.exit(1)

        # 保存到CSV
        save_to_csv(data, args.output_dir)

        # 绘制图表
        total_plots = plot_all_data(data, args.output_dir, args.dpi, args.max_points)

        # 输出总结
        print("\n" + "=" * 60)
        print("分析完成!")
        print("=" * 60)
        print(f"输出目录: {args.output_dir}")
        print(f"生成图表数: {total_plots}")
        print("=" * 60)

    except Exception as e:
        print(f"处理过程中出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
