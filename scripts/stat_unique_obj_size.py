# 统计test_loh_comprehensive_10k.txt所有唯一对象的size字段之和
unique_obj_sizes = {}
with open('test_loh_comprehensive_10k.txt') as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) < 3:
            continue
        obj_id = int(parts[1])    # 第二列为ID
        size = int(parts[2])      # 第三列为size
        if obj_id not in unique_obj_sizes:
            unique_obj_sizes[obj_id] = size
print(f"Unique object count: {len(unique_obj_sizes)}")
print(f"Sum of unique object sizes: {sum(unique_obj_sizes.values())} bytes")
