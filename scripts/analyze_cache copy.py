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
    从日志文件中提取权重、全局特征和请求特征
    """
    weights_list = []
    global_features_list = []
    request_features_list = []
    timestamps = []
    line_count = 0

    print(f"正在读取文件: {log_file_path}")

    # 读取日志文件
    # Open in binary and decode each line with replacement for invalid bytes so
    # that non-UTF8 payload in logs doesn't crash the parser (robust for mixed
    # encodings / occasional binary blobs written into logs).
    with open(log_file_path, 'rb') as file:
        for line_num, raw in enumerate(file):
            try:
                line = raw.decode('utf-8', errors='replace')
            except Exception:
                # Fallback to latin-1 as a last resort (1:1 byte->char mapping)
                line = raw.decode('latin-1', errors='replace')
            line_count += 1
            if line_num % 10000 == 0 and line_num > 0:
                print(f"已处理 {line_num} 行...")

            # 提取权重
            weights_match = re.search(r'New weights:\s*\[([0-9.,\s-]+)\]', line)
            if weights_match:
                weights_str = weights_match.group(1)
                try:
                    weights = [float(x.strip()) for x in weights_str.split(',')]
                    weights_list.append(weights)
                    timestamps.append(line_num)
                except ValueError as e:
                    continue

            # 提取全局特征
            global_match = re.search(r'\[global_features\]:\s*\[([0-9.,\s-]+)\]', line)
            if global_match:
                global_str = global_match.group(1)
                try:
                    global_features = [float(x.strip()) for x in global_str.split(',')]
                    global_features_list.append(global_features)
                except ValueError as e:
                    continue

            # 提取请求特征
            request_match = re.search(r'\[request_features\]:\s*\[([0-9.,\s-]+)\]', line)
            if request_match:
                request_str = request_match.group(1)
                try:
                    request_features = [float(x.strip()) for x in request_str.split(',')]
                    request_features_list.append(request_features)
                except ValueError as e:
                    continue

    print(f"文件读取完成，共处理 {line_count} 行")
    return weights_list, global_features_list, request_features_list, timestamps

def save_to_csv(weights_list, global_features_list, request_features_list, timestamps, output_dir):
    """
    将数据保存到CSV文件
    """
    print("保存数据到CSV文件...")

    # 预先初始化路径变量，避免在某类数据缺失时引用未定义变量导致 UnboundLocalError
    weights_path = None
    global_path = None
    request_path = None

    # 保存权重数据
    if weights_list:
        weights_df = pd.DataFrame(weights_list)
        weights_df.columns = [f'Weight_{i+1}' for i in range(len(weights_list[0]))]
        weights_df.insert(0, 'Line_Number', timestamps[:len(weights_list)])
        weights_path = os.path.join(output_dir, 'weights_data.csv')
        weights_df.to_csv(weights_path, index=False)
        print(f"权重数据已保存: {weights_path} ({len(weights_list)} 行)")

    # 保存全局特征数据
    if global_features_list:
        global_df = pd.DataFrame(global_features_list)
        global_df.columns = [f'Global_Feature_{i+1}' for i in range(len(global_features_list[0]))]
        if len(global_features_list) <= len(timestamps):
            global_df.insert(0, 'Line_Number', timestamps[:len(global_features_list)])
        else:
            global_df.insert(0, 'Line_Number', list(range(len(global_features_list))))
        global_path = os.path.join(output_dir, 'global_features_data.csv')
        global_df.to_csv(global_path, index=False)
        print(f"全局特征数据已保存: {global_path} ({len(global_features_list)} 行)")

    # 保存请求特征数据
    if request_features_list:
        request_df = pd.DataFrame(request_features_list)
        request_df.columns = [f'Request_Feature_{i+1}' for i in range(len(request_features_list[0]))]
        if len(request_features_list) <= len(timestamps):
            request_df.insert(0, 'Line_Number', timestamps[:len(request_features_list)])
        else:
            request_df.insert(0, 'Line_Number', list(range(len(request_features_list))))
        request_path = os.path.join(output_dir, 'request_features_data.csv')
        request_df.to_csv(request_path, index=False)
        print(f"请求特征数据已保存: {request_path} ({len(request_features_list)} 行)")

    # 保存统计信息
    stats_data = []
    if weights_list:
        weights_array = np.array(weights_list)
        for i in range(weights_array.shape[1]):
            stats_data.append({
                'Feature_Type': 'Weights',
                'Index': f'Weight_{i+1}',
                'Count': len(weights_list),
                'Mean': weights_array[:, i].mean(),
                'Std': weights_array[:, i].std(),
                'Min': weights_array[:, i].min(),
                'Max': weights_array[:, i].max()
            })

    if global_features_list:
        global_array = np.array(global_features_list)
        for i in range(global_array.shape[1]):
            stats_data.append({
                'Feature_Type': 'Global_Features',
                'Index': f'Global_{i+1}',
                'Count': len(global_features_list),
                'Mean': global_array[:, i].mean(),
                'Std': global_array[:, i].std(),
                'Min': global_array[:, i].min(),
                'Max': global_array[:, i].max()
            })

    if request_features_list:
        request_array = np.array(request_features_list)
        for i in range(request_array.shape[1]):
            stats_data.append({
                'Feature_Type': 'Request_Features',
                'Index': f'Request_{i+1}',
                'Count': len(request_features_list),
                'Mean': request_array[:, i].mean(),
                'Std': request_array[:, i].std(),
                'Min': request_array[:, i].min(),
                'Max': request_array[:, i].max()
            })

    stats_df = pd.DataFrame(stats_data)
    stats_path = os.path.join(output_dir, 'statistics.csv')
    stats_df.to_csv(stats_path, index=False)
    print(f"统计信息已保存: {stats_path}")

    # 返回路径（若某类数据不存在则对应为 None）
    return [weights_path, global_path, request_path, stats_path]

def plot_large_dataset_segmented(values, title, color, output_path, dpi=100, max_points=50000):
    """
    分段绘制大型数据集，避免路径限制
    """
    total_points = len(values)

    if total_points <= max_points:
        # 如果数据点不多，直接绘制
        plt.figure(figsize=(14, 7))
        plt.plot(values, linewidth=0.8, color=color, alpha=0.8)
        plt.title(f'{title} (共 {total_points} 个数据点)', fontsize=14, fontweight='bold')
        plt.xlabel('Sample Index', fontsize=12)
        plt.ylabel('Value', fontsize=12)
        plt.grid(True, alpha=0.3)

        # 添加统计信息
        stats_text = f'总数据点: {total_points}\n均值: {values.mean():.6f}\n标准差: {values.std():.6f}\n最小值: {values.min():.6f}\n最大值: {values.max():.6f}'
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.9), fontsize=9)

        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()
        return 1
    else:
        # 数据点太多，分段绘制
        num_segments = (total_points + max_points - 1) // max_points
        segments_created = 0

        for segment in range(num_segments):
            start_idx = segment * max_points
            end_idx = min((segment + 1) * max_points, total_points)
            segment_values = values[start_idx:end_idx]

            plt.figure(figsize=(14, 7))
            plt.plot(segment_values, linewidth=0.8, color=color, alpha=0.8)

            segment_title = f'{title} (分段 {segment+1}/{num_segments}, 点 {start_idx}-{end_idx-1})'
            plt.title(segment_title, fontsize=14, fontweight='bold')
            plt.xlabel(f'Sample Index (段内)', fontsize=12)
            plt.ylabel('Value', fontsize=12)
            plt.grid(True, alpha=0.3)

            # 添加统计信息（当前段）
            stats_text = f'本段数据点: {len(segment_values)}\n段内均值: {segment_values.mean():.6f}\n段内标准差: {segment_values.std():.6f}'
            plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.9), fontsize=9)

            # 修改输出文件名以包含段信息
            base_name = os.path.splitext(output_path)[0]
            extension = os.path.splitext(output_path)[1]
            segment_output_path = f"{base_name}_segment_{segment+1}{extension}"

            plt.savefig(segment_output_path, dpi=dpi, bbox_inches='tight')
            plt.close()
            segments_created += 1

            print(f"  生成分段 {segment+1}/{num_segments} ({len(segment_values)} 个点)")

        # 创建总体统计信息文件
        overall_stats_path = f"{os.path.splitext(output_path)[0]}_overall_stats.txt"
        with open(overall_stats_path, 'w') as f:
            f.write(f"总体统计信息 - {title}\n")
            f.write("=" * 50 + "\n")
            f.write(f"总数据点数: {total_points}\n")
            f.write(f"分段数量: {num_segments}\n")
            f.write(f"每段最大点数: {max_points}\n")
            f.write(f"总体均值: {values.mean():.6f}\n")
            f.write(f"总体标准差: {values.std():.6f}\n")
            f.write(f"总体最小值: {values.min():.6f}\n")
            f.write(f"总体最大值: {values.max():.6f}\n")

        return segments_created

def plot_individual_features(weights_list, global_features_list, request_features_list, output_dir, dpi, max_points):
    """
    为每个特征单独绘制图表，处理大量数据点
    """
    print("为每个特征单独生成图表（处理大量数据点）...")

    individual_dir = os.path.join(output_dir, 'individual_plots')
    ensure_output_dir(individual_dir)

    total_plots = 0

    # 1. 绘制每个权重单独图表（6个权重）
    if weights_list:
        weights_array = np.array(weights_list)
        num_weights = weights_array.shape[1]

        for i in range(num_weights):
            weight_values = weights_array[:, i]
            output_path = os.path.join(individual_dir, f'weight_{i+1}.png')

            print(f"生成权重图 {i+1}/{num_weights} ({len(weight_values)} 个点)...")
            segments = plot_large_dataset_segmented(
                weight_values,
                f'Weight {i+1}',
                'blue',
                output_path,
                dpi,
                max_points
            )
            total_plots += segments

    # 2. 绘制每个全局特征单独图表（2个全局特征）
    if global_features_list:
        global_array = np.array(global_features_list)
        num_global_features = global_array.shape[1]

        for i in range(num_global_features):
            feature_values = global_array[:, i]
            output_path = os.path.join(individual_dir, f'global_feature_{i+1}.png')

            print(f"生成全局特征图 {i+1}/{num_global_features} ({len(feature_values)} 个点)...")
            segments = plot_large_dataset_segmented(
                feature_values,
                f'Global Feature {i+1}',
                'green',
                output_path,
                dpi,
                max_points
            )
            total_plots += segments

    # 3. 绘制每个请求特征单独图表（18个请求特征）
    if request_features_list:
        request_array = np.array(request_features_list)
        num_request_features = request_array.shape[1]

        for i in range(num_request_features):
            feature_values = request_array[:, i]
            output_path = os.path.join(individual_dir, f'request_feature_{i+1}.png')

            if (i + 1) % 5 == 0 or i + 1 == num_request_features:
                print(f"生成请求特征图 {i+1}/{num_request_features} ({len(feature_values)} 个点)...")

            segments = plot_large_dataset_segmented(
                feature_values,
                f'Request Feature {i+1}',
                'red',
                output_path,
                dpi,
                max_points
            )
            total_plots += segments

    print(f"总共生成 {total_plots} 张图表（包含分段）")
    return total_plots

def main():
    """主函数"""
    args = parse_arguments()

    # 检查文件是否存在
    if not os.path.exists(args.file_path):
        print(f"错误: 文件不存在: {args.file_path}")
        sys.exit(1)

    # 确保输出目录存在
    ensure_output_dir(args.output_dir)

    print("=" * 60)
    print("缓存特征数据提取与可视化工具")
    print("=" * 60)
    print(f"输入文件: {args.file_path}")
    print(f"输出目录: {args.output_dir}")
    print(f"图表DPI: {args.dpi}")
    print(f"每图最大点数: {args.max_points} (超过将分段)")
    print("=" * 60)

    try:
        # 提取数据
        weights_list, global_features_list, request_features_list, timestamps = extract_features_from_log(args.file_path)

        # 检查是否找到数据
        if not any([weights_list, global_features_list, request_features_list]):
            print("错误: 在日志文件中未找到任何特征数据")
            print("请检查文件格式是否正确")
            sys.exit(1)

        # 保存到CSV
        data_files = save_to_csv(weights_list, global_features_list, request_features_list, timestamps, args.output_dir)

        # 为每个特征生成单独图表
        total_plots = plot_individual_features(weights_list, global_features_list, request_features_list,
                                             args.output_dir, args.dpi, args.max_points)

        # 输出总结
        print("\n" + "=" * 60)
        print("分析完成!")
        print("=" * 60)
        print(f"权重数据: {len(weights_list)} 组")
        print(f"全局特征: {len(global_features_list)} 组")
        print(f"请求特征: {len(request_features_list)} 组")
        print(f"生成图表总数: {total_plots} 张（包含分段）")
        print(f"\n输出文件:")
        print(f"- CSV数据文件: weights_data.csv, global_features_data.csv, request_features_data.csv")
        print(f"- 单独图表目录: {os.path.join(args.output_dir, 'individual_plots')}")
        print("=" * 60)

    except Exception as e:
        print(f"处理过程中出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
