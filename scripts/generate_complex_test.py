#!/usr/bin/env python3
import random

# 生成一个更复杂的测试文件，包含：
# 1. 不同大小的对象
# 2. 重复访问模式
# 3. 访问频率变化

def generate_test_data(filename, num_requests=1000):
    sizes = [128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152]
    obj_ids = list(range(1001, 1101))  # 100个不同的对象

    with open(filename, 'w') as f:
        time = 1
        for i in range(num_requests):
            # 选择对象ID，偏向于某些对象更频繁访问
            if i % 10 == 0:  # 10%的时间访问热点对象
                obj_id = random.choice(obj_ids[:10])  # 前10个对象是热点
            else:
                obj_id = random.choice(obj_ids)

            # 对象大小也有偏向性
            if obj_id <= 1010:  # 热点对象倾向于有不同的大小
                size = random.choice(sizes[5:])  # 较大的尺寸
            else:
                size = random.choice(sizes)

            f.write(f"{time},{obj_id},{size}\n")
            time += 1

if __name__ == "__main__":
    generate_test_data("complex_test.csv", 1000)
    print("Generated complex_test.csv with 1000 requests")
