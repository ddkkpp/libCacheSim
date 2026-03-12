import numpy as np
import time
from stable_baselines3 import PPO

# --- 配置 ---
# 【请修改】: 将此路径指向您想要测试的模型文件
# 它可以是最终模型，也可以是 sb_checkpoints/ 文件夹中的任何一个检查点
MODEL_TO_TEST = "./runs/0730_213903/ppo_loh_final.zip"

# 模拟的环境状态维度
STATE_DIM = 38
# 测试运行的次数
NUM_TEST_RUNS = 1000

def main():
    """
    加载一个已保存的SB3模型，并测试其 model.predict() 的性能。
    """
    print(f"🚀 正在加载模型: {MODEL_TO_TEST}...")
    try:
        # 加载模型。我们不需要真正的环境，所以可以传入 None
        model = PPO.load(MODEL_TO_TEST, env=None)
        print("✅ 模型加载成功。")
    except Exception as e:
        print(f"❌ 加载模型失败: {e}")
        print("请确保模型文件路径正确，并且文件存在。")
        return

    # 创建一个随机的、符合环境观测空间形状的“假”状态
    # 这足以让神经网络进行一次完整的前向传播计算
    dummy_observation = np.random.rand(STATE_DIM).astype(np.float32)

    print(f"\n🔬 准备进行 {NUM_TEST_RUNS} 次推理测试...")

    # 预热：第一次推理通常会稍慢，我们将其排除在计时之外
    _ = model.predict(dummy_observation, deterministic=True)

    start_time = time.perf_counter()

    # 在循环中执行 predict
    for _ in range(NUM_TEST_RUNS):
        # model.predict 是SB3内部调用神经网络进行推理的核心函数
        _ = model.predict(dummy_observation, deterministic=True)

    end_time = time.perf_counter()

    # 计算并打印结果
    total_time_seconds = end_time - start_time
    avg_time_ms = (total_time_seconds / NUM_TEST_RUNS) * 1000

    print("\n✅ 测试完成！")
    print("--- 性能报告 ---")
    print(f"总耗时: {total_time_seconds:.4f} 秒 ({NUM_TEST_RUNS} 次推理)")
    print(f"平均每次推理耗时: {avg_time_ms:.4f} 毫秒 (ms)")
    print("--------------------")

if __name__ == "__main__":
    main()
