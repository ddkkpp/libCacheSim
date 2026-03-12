#!/usr/bin/env python3
import random

def generate_comprehensive_trace(filename, num_requests=10000):
    """生成满足所有特征观察的复杂trace"""

    # 定义对象池
    small_objects = list(range(1000, 1100))    # 100个小对象 (1KB)
    medium_objects = list(range(2000, 2050))   # 50个中等对象 (512KB)
    large_objects = list(range(3000, 3020))    # 20个大对象 (5MB)
    extra_large_objects = list(range(4000, 4005))  # 5个超大对象 (50MB)

    # 对象大小映射
    size_map = {}
    for obj in small_objects:
        size_map[obj] = 1024  # 1KB
    for obj in medium_objects:
        size_map[obj] = 512 * 1024  # 512KB
    for obj in large_objects:
        size_map[obj] = 5 * 1024 * 1024  # 5MB
    for obj in extra_large_objects:
        size_map[obj] = 50 * 1024 * 1024  # 50MB

    requests = []

    # 阶段1: 初始访问 (0-2000) - 建立基础对象
    for i in range(2000):
        if i < 500:
            # 主要访问小对象
            obj_id = random.choice(small_objects[:30])
        elif i < 1000:
            # 混合访问小和中等对象
            if random.random() < 0.7:
                obj_id = random.choice(small_objects[:50])
            else:
                obj_id = random.choice(medium_objects[:20])
        elif i < 1500:
            # 加入大对象
            prob = random.random()
            if prob < 0.5:
                obj_id = random.choice(small_objects[:70])
            elif prob < 0.8:
                obj_id = random.choice(medium_objects[:30])
            else:
                obj_id = random.choice(large_objects[:10])
        else:
            # 加入超大对象
            prob = random.random()
            if prob < 0.4:
                obj_id = random.choice(small_objects)
            elif prob < 0.7:
                obj_id = random.choice(medium_objects)
            elif prob < 0.95:
                obj_id = random.choice(large_objects)
            else:
                obj_id = random.choice(extra_large_objects)

        requests.append((i, obj_id, size_map[obj_id], -1))

    # 阶段2: 热点访问模式 (2000-5000) - 建立频率差异
    hot_objects = random.sample(small_objects[:50], 10) + random.sample(medium_objects[:20], 5)
    warm_objects = random.sample(small_objects[50:], 20) + random.sample(medium_objects[20:], 10)

    for i in range(2000, 5000):
        prob = random.random()
        if prob < 0.4:  # 40% 访问热点对象
            obj_id = random.choice(hot_objects)
        elif prob < 0.7:  # 30% 访问温热对象
            obj_id = random.choice(warm_objects)
        elif prob < 0.9:  # 20% 访问其他小中对象
            if random.random() < 0.6:
                obj_id = random.choice(small_objects)
            else:
                obj_id = random.choice(medium_objects)
        else:  # 10% 访问大对象
            if random.random() < 0.8:
                obj_id = random.choice(large_objects)
            else:
                obj_id = random.choice(extra_large_objects)

        requests.append((i, obj_id, size_map[obj_id], -1))

    # 阶段3: 周期性访问模式 (5000-7000) - 建立IRT模式
    cycle_objects = hot_objects[:5]  # 选择5个对象进行周期访问

    for i in range(5000, 7000):
        if i % 50 < 10:  # 每50个请求中的前10个访问周期对象
            obj_id = cycle_objects[i % len(cycle_objects)]
        else:
            # 随机访问其他对象
            prob = random.random()
            if prob < 0.3:
                obj_id = random.choice(hot_objects)
            elif prob < 0.6:
                obj_id = random.choice(warm_objects)
            elif prob < 0.85:
                if random.random() < 0.7:
                    obj_id = random.choice(small_objects)
                else:
                    obj_id = random.choice(medium_objects)
            else:
                if random.random() < 0.7:
                    obj_id = random.choice(large_objects)
                else:
                    obj_id = random.choice(extra_large_objects)

        requests.append((i, obj_id, size_map[obj_id], -1))

    # 阶段4: 突发访问模式 (7000-8500) - 测试新近度
    burst_objects = random.sample(small_objects, 15)

    for i in range(7000, 8500):
        if i % 100 < 30:  # 每100个请求中的前30个突发访问特定对象
            obj_id = burst_objects[(i // 100) % len(burst_objects)]
        else:
            # 正常混合访问
            prob = random.random()
            if prob < 0.2:
                obj_id = random.choice(hot_objects)
            elif prob < 0.4:
                obj_id = random.choice(warm_objects)
            elif prob < 0.7:
                if random.random() < 0.6:
                    obj_id = random.choice(small_objects)
                else:
                    obj_id = random.choice(medium_objects)
            else:
                if random.random() < 0.6:
                    obj_id = random.choice(large_objects)
                else:
                    obj_id = random.choice(extra_large_objects)

        requests.append((i, obj_id, size_map[obj_id], -1))

    # 阶段5: 复杂混合模式 (8500-10000) - 全面测试
    for i in range(8500, 10000):
        prob = random.random()
        if prob < 0.15:  # 15% 访问热点
            obj_id = random.choice(hot_objects)
        elif prob < 0.25:  # 10% 访问周期对象
            obj_id = random.choice(cycle_objects)
        elif prob < 0.35:  # 10% 访问突发对象
            obj_id = random.choice(burst_objects)
        elif prob < 0.55:  # 20% 访问温热对象
            obj_id = random.choice(warm_objects)
        elif prob < 0.75:  # 20% 访问普通小中对象
            if random.random() < 0.6:
                obj_id = random.choice(small_objects)
            else:
                obj_id = random.choice(medium_objects)
        else:  # 25% 访问大对象
            if random.random() < 0.7:
                obj_id = random.choice(large_objects)
            else:
                obj_id = random.choice(extra_large_objects)

        requests.append((i, obj_id, size_map[obj_id], -1))

    # 写入文件 (格式: timestamp,obj_id,size,next_access)
    with open(filename, 'w') as f:
        for timestamp, obj_id, size, next_access in requests:
            f.write(f"{timestamp},{obj_id},{size},{next_access}\n")

    print(f"Generated {len(requests)} requests in {filename}")

    # 统计信息
    obj_counts = {}
    size_counts = {}
    for timestamp, obj_id, size, next_access in requests:
        obj_counts[obj_id] = obj_counts.get(obj_id, 0) + 1
        size_counts[size] = size_counts.get(size, 0) + 1

    print(f"Unique objects: {len(obj_counts)}")
    print(f"Most accessed objects: {sorted(obj_counts.items(), key=lambda x: x[1], reverse=True)[:10]}")
    print(f"Size distribution: {size_counts}")

if __name__ == "__main__":
    generate_comprehensive_trace("test_loh_comprehensive_10k.csv", 10000)
