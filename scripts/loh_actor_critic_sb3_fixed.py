#!/usr/bin/env python3
# Print actual script filename at runtime (dynamic)
import os, sys
_loh_script_name = os.path.basename(__file__) if '__file__' in globals() and __file__ else (os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else '<unknown>')
print(f"[LOH SCRIPT] { _loh_script_name }")

"""
LOH Actor-Critic using stable-baselines3 - 修复版本

修复了以下问题：
1. 库导入卡死问题 - 延迟导入机器学习库
2. 缩进错误问题 - 重新组织代码结构
3. 添加fallback模式 - 如果ML库导入失败，提供基本的共享内存功能
"""

# 基础库导入
import numpy as np
import ctypes
import mmap
import os
import sys
import time
from datetime import datetime

print("🔄 正在启动LOH RL Agent...")
print("🔄 导入基础库完成")

# --- 常量定义 ---
SHM_KEY = 9876
FEATURE_DIM = 6

def get_state_dim():
    """获取状态向量维度，默认为26维"""
    state_dim = os.environ.get('LOH_STATE_DIM', '26')
    return int(state_dim)

CONTEXT_DIM = get_state_dim()
STATE_DIM = CONTEXT_DIM

print(f"LOH RL Agent: Using {STATE_DIM}-dimensional state vector")

# --- 共享内存结构定义 ---
def create_shared_memory_class(state_dim):
    """动态创建与 C 端 shm_data_t 结构匹配的类"""
    class SharedMemoryData(ctypes.Structure):
        _fields_ = [
            ('ready_for_inference', ctypes.c_int),
            ('weights_updated', ctypes.c_int),
            ('terminate', ctypes.c_int),
            ('state', ctypes.c_double * state_dim),
            ('weights', ctypes.c_double * FEATURE_DIM),
            ('miss_ratio', ctypes.c_double),
            ('byte_miss_ratio', ctypes.c_double),
            ('reward', ctypes.c_double),
            ('timestamp', ctypes.c_int64),
        ]
    return SharedMemoryData

SharedMemoryData = create_shared_memory_class(CONTEXT_DIM)

# --- 延迟导入机器学习库 ---
print("🔄 正在导入机器学习库...")
try:
    import gymnasium as gym
    from gymnasium import spaces
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_checker import check_env
    from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback
    from stable_baselines3.common.monitor import Monitor
    import torch

    USE_ML = True
    print("✅ 机器学习库导入成功，将使用完整的RL训练功能")
except Exception as e:
    USE_ML = False
    print(f"⚠️ 机器学习库导入失败: {e}")
    print("⚠️ 将使用fallback模式，仅提供共享内存通信功能")

# --- 创建共享内存功能 ---
def create_shared_memory():
    """创建共享内存文件"""
    try:
        shm_path = f"/dev/shm/loh_ac_{SHM_KEY}"
        size = ctypes.sizeof(SharedMemoryData)

        if not os.path.exists(shm_path):
            print(f"🔨 创建共享内存文件: {shm_path}")
            with open(shm_path, 'wb') as f:
                f.write(b'\x00' * size)
        else:
            print(f"⏳ 共享内存文件已存在: {shm_path}")

        print(f"✅ 共享内存已准备就绪 ({size} bytes)")
        return True
    except Exception as e:
        print(f"❌ 共享内存创建失败: {e}")
        return False

# --- 如果支持ML库，定义完整的环境类 ---
if USE_ML:
    # 自定义训练监控回调
    class LOHTrainingCallback(BaseCallback):
        def __init__(self, verbose=0):
            super(LOHTrainingCallback, self).__init__(verbose)
            self.best_reward = float('-inf')
            self.best_miss_ratio = float('inf')

        def _on_rollout_end(self) -> None:
            """每次rollout结束时调用"""
            if hasattr(self.training_env.envs[0], 'total_rewards') and len(self.training_env.envs[0].total_rewards) > 0:
                recent_rewards = self.training_env.envs[0].total_rewards[-10:]
                recent_miss_ratios = self.training_env.envs[0].episode_miss_ratios[-10:]

                avg_reward = np.mean(recent_rewards)
                avg_miss_ratio = np.mean(recent_miss_ratios)

                self.logger.record("loh/avg_episode_reward", avg_reward)
                self.logger.record("loh/avg_miss_ratio", avg_miss_ratio)
                self.logger.record("loh/total_episodes", len(self.training_env.envs[0].total_rewards))

                if avg_reward > self.best_reward:
                    self.best_reward = avg_reward
                    self.logger.record("loh/best_avg_reward", self.best_reward)

                if avg_miss_ratio < self.best_miss_ratio:
                    self.best_miss_ratio = avg_miss_ratio
                    self.logger.record("loh/best_miss_ratio", self.best_miss_ratio)

                print(f"📈 Training Update - Avg Reward: {avg_reward:.4f}, Avg Miss Ratio: {avg_miss_ratio:.4f}")

            return True

    # 完整的Gymnasium环境
    class LohEnv(gym.Env):
        """遵循 Gymnasium API 的LOH环境"""
        metadata = {"render_modes": []}

        def __init__(self, shm_key=SHM_KEY):
            super(LohEnv, self).__init__()

            # 动作空间和观测空间
            self.action_space = spaces.Box(
                low=-1.0, high=1.0, shape=(FEATURE_DIM,), dtype=np.float32
            )
            self.observation_space = spaces.Box(
                low=-np.inf, high=np.inf, shape=(STATE_DIM,), dtype=np.float32
            )

            # 连接共享内存
            self.shm_key = shm_key
            self.shm = None
            self.shm_file = None
            self.shm_mmap = None
            self._attach_shared_memory()

            # 奖励函数参数
            self.reward_alpha = 1.0
            self.reward_beta = 0.0

            # 回合管理
            self.max_episode_steps = 2048
            self.current_step = 0
            self.weight_update_count = 0

            # 训练监控统计
            self.episode_count = 0
            self.total_rewards = []
            self.episode_miss_ratios = []

            # 经验记录
            self.experience_buffer = []
            self.max_buffer_size = 1000

            print("✅ LohEnv 初始化完成")

        def _attach_shared_memory(self):
            """连接到共享内存文件"""
            try:
                shm_path = f"/dev/shm/loh_ac_{self.shm_key}"
                size = ctypes.sizeof(SharedMemoryData)

                if not os.path.exists(shm_path):
                    print(f"🔨 共享内存文件不存在，Python端主动创建: {shm_path}")
                    with open(shm_path, 'wb') as f:
                        f.write(b'\x00' * size)
                else:
                    print(f"⏳ 共享内存文件已存在: {shm_path}")

                self.shm_file = open(shm_path, 'r+b')
                self.shm_mmap = mmap.mmap(self.shm_file.fileno(), size)
                self.shm = self.shm_mmap
                print(f"✅ 成功连接到共享内存 ({size} bytes)")
            except Exception as e:
                print(f"❌ 共享内存连接失败: {e}")
                raise e

        def _read_shm(self):
            """从共享内存读取数据"""
            try:
                self.shm.seek(0)
                raw_data = self.shm.read(ctypes.sizeof(SharedMemoryData))
                return SharedMemoryData.from_buffer_copy(raw_data)
            except Exception as e:
                print(f"❌ 共享内存读取错误: {e}")
                return None

        def _write_shm(self, data_struct):
            """将数据结构写入共享内存"""
            try:
                self.shm.seek(0)
                self.shm.write(data_struct)
                self.shm.flush()
                return True
            except Exception as e:
                print(f"❌ 共享内存写入错误: {e}")
                return False

        def reset(self, seed=None, options=None):
            """重置环境"""
            super().reset(seed=seed)

            self.current_step = 0
            self.weight_update_count = 0
            self.episode_count += 1

            print(f"\n🔄 Episode #{self.episode_count} Reset - Waiting for first state from C...")

            # 等待C端发送第一个有效状态
            timeout_counter = 0
            max_timeout = 60000  # 60秒超时

            initial_data = None
            while timeout_counter < max_timeout:
                data = self._read_shm()
                if data and data.ready_for_inference:
                    initial_data = data
                    break
                time.sleep(0.01)
                timeout_counter += 1

                if timeout_counter % 1000 == 0:
                    elapsed_time = timeout_counter * 0.01
                    print(f"Still waiting for first state... {elapsed_time:.1f}s elapsed")

            if timeout_counter >= max_timeout:
                raise RuntimeError("Reset timeout: C端未发送初始状态")

            # 获取初始观测状态
            initial_observation = np.array(initial_data.state, dtype=np.float32)

            # 记录初始性能指标
            initial_miss_ratio = initial_data.miss_ratio
            initial_byte_miss_ratio = initial_data.byte_miss_ratio

            # 清除历史性能指标
            if hasattr(self, '_previous_miss_ratio'):
                delattr(self, '_previous_miss_ratio')
            if hasattr(self, '_previous_byte_miss_ratio'):
                delattr(self, '_previous_byte_miss_ratio')

            print(f"✅ Episode #{self.episode_count} Reset Complete:")
            print(f"   Initial miss_ratio: {initial_miss_ratio:.4f}")
            print(f"   Initial byte_miss_ratio: {initial_byte_miss_ratio:.4f}")
            print(f"   State vector shape: {initial_observation.shape}")

            info = {
                'initial_miss_ratio': initial_miss_ratio,
                'initial_byte_miss_ratio': initial_byte_miss_ratio,
                'episode_step': self.current_step,
                'episode_count': self.episode_count,
                'state_dim': CONTEXT_DIM
            }

            return initial_observation, info

        def step(self, action):
            """执行一步操作"""
            self.current_step += 1

            # 将动作转换为权重
            action_tensor = torch.from_numpy(action)
            weights = torch.nn.functional.softmax(action_tensor, dim=-1).numpy()

            # 发送权重到C端
            data = self._read_shm()
            if data is None:
                raise RuntimeError("无法读取共享内存")

            data.weights[:] = weights
            data.weights_updated = 1
            data.ready_for_inference = 0
            self._write_shm(data)

            self.weight_update_count += 1
            print(f"[Step {self.current_step}] Sent weights: {weights}")

            # 等待C端处理并返回新状态
            timeout_counter = 0
            max_timeout = 30000

            print(f"[Step {self.current_step}] Waiting for next state from C...")
            while timeout_counter < max_timeout:
                data = self._read_shm()
                if data and data.ready_for_inference:
                    break
                time.sleep(0.01)
                timeout_counter += 1

            if timeout_counter >= max_timeout:
                raise RuntimeError(f"[Step {self.current_step}] Timeout waiting for next state from C")

            # 获取新状态和性能指标
            new_observation = np.array(data.state, dtype=np.float32)
            new_miss_ratio = data.miss_ratio
            new_byte_miss_ratio = data.byte_miss_ratio

            print(f"[Step {self.current_step}] Received new state (miss_ratio: {new_miss_ratio:.4f})")

            # 计算奖励
            obj_hit_ratio = 1.0 - new_miss_ratio
            byte_hit_ratio = 1.0 - new_byte_miss_ratio
            reward = self.reward_alpha * obj_hit_ratio + self.reward_beta * byte_hit_ratio

            if hasattr(self, '_previous_miss_ratio'):
                performance_improvement = self._previous_miss_ratio - new_miss_ratio

            print(f"[Step {self.current_step}] Calculated reward: {reward:.6f}")

            # 保存性能指标
            self._previous_miss_ratio = new_miss_ratio
            self._previous_byte_miss_ratio = new_byte_miss_ratio

            # 检查终止条件
            terminated = (data.terminate == 1)
            truncated = (self.current_step >= self.max_episode_steps)

            # 记录经验
            experience = {
                'episode': self.episode_count,
                'step': self.current_step,
                'action': action.copy(),
                'weights': weights.copy(),
                'reward': reward,
                'miss_ratio': new_miss_ratio,
                'byte_miss_ratio': new_byte_miss_ratio,
                'terminated': terminated,
                'truncated': truncated
            }

            self.experience_buffer.append(experience)
            if len(self.experience_buffer) > self.max_buffer_size:
                self.experience_buffer.pop(0)

            # 回合结束统计
            if terminated or truncated:
                episode_reward = sum([exp['reward'] for exp in self.experience_buffer if exp['episode'] == self.episode_count])
                self.total_rewards.append(episode_reward)
                self.episode_miss_ratios.append(new_miss_ratio)

                print(f"📊 Episode #{self.episode_count} Finished:")
                print(f"   Total Reward: {episode_reward:.4f}")
                print(f"   Final Miss Ratio: {new_miss_ratio:.4f}")
                print(f"   Steps: {self.current_step}")
                print(f"   Reason: {'Terminated' if terminated else 'Truncated'}")

            # 准备返回信息
            info = {
                'miss_ratio': new_miss_ratio,
                'byte_miss_ratio': new_byte_miss_ratio,
                'step': self.current_step,
                'weights_sent': weights.tolist(),
                'obj_hit_ratio': obj_hit_ratio,
                'byte_hit_ratio': byte_hit_ratio
            }

            return new_observation, reward, terminated, truncated, info

        def close(self):
            """清理资源"""
            if self.shm_mmap:
                self.shm_mmap.close()
            if self.shm_file:
                self.shm_file.close()
            print("🧹 环境已清理")

# --- 主函数 ---
def main():
    if not USE_ML:
        print("🔧 运行在fallback模式...")
        if create_shared_memory():
            print("✅ 共享内存已创建，请启动C端程序")
            print("💡 按Ctrl+C退出")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n⚠️ 用户中断")
        return

    # 使用时间戳创建运行目录
    run_timestamp = datetime.now().strftime("%m%d_%H%M%S")
    run_dir = f"./runs/{run_timestamp}"
    log_dir = f"{run_dir}/sb3_logs/"
    checkpoint_dir = f"{run_dir}/sb3_checkpoints/"
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(checkpoint_dir, exist_ok=True)

    print(f"🚀 LOH Actor-Critic (stable-baselines3 版本) 启动...")
    print(f"💾 本次运行数据将保存在: {run_dir}")

    env = None
    try:
        # 实例化环境
        env = LohEnv()

        # 使用Monitor包装
        monitor_file = f"{run_dir}/monitor.csv"
        env = Monitor(env, monitor_file)

        print("🕵️  正在检查环境...")
        check_env(env, warn=True)
        print("✅ 环境检查通过！")

        # 设置回调函数
        checkpoint_callback = CheckpointCallback(
          save_freq=4096,
          save_path=checkpoint_dir,
          name_prefix="loh_model"
        )

        training_callback = LOHTrainingCallback(verbose=1)
        callbacks = [checkpoint_callback, training_callback]

        # 实例化SAC模型
        model = PPO(
            "MlpPolicy",
            env,
            verbose=1,
            tensorboard_log=log_dir,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            learning_rate=3e-4,
            clip_range=0.2,
            ent_coef=0.01,
            vf_coef=0.5,
            max_grad_norm=0.5,
            policy_kwargs=dict(
                net_arch=[dict(pi=[256, 256], vf=[256, 256])],
                activation_fn=torch.nn.ReLU,
            ),
            gae_lambda=0.95,
            use_sde=False,
            sde_sample_freq=-1,
            target_kl=0.01,
        )

        # 开始训练
        print("🧠 开始训练模型... 按 Ctrl+C 停止。")
        print(f"📋 训练配置:")
        print(f"   - 状态维度: {CONTEXT_DIM}")
        print(f"   - 动作维度: {FEATURE_DIM}")
        print(f"   - 每回合最大步数: {env.max_episode_steps}")
        print(f"   - SAC批次大小: {model.batch_size}")
        print(f"   - SAC参数: {model.n_steps}")

        model.learn(
            total_timesteps=50000,
            callback=callbacks,
            progress_bar=True,
            tb_log_name="loh_fixed_run",
        )

        # 保存最终模型
        model.save(f"{run_dir}/sac_loh_final")
        print(f"💾 最终模型已保存为 {run_dir}/sac_loh_final.zip")

    except KeyboardInterrupt:
        print("\n⚠️  用户中断训练。")
        if 'model' in locals():
            model.save(f"{run_dir}/sac_loh_interrupted")
            print(f"💾 中断时模型已保存为 {run_dir}/sac_loh_interrupted.zip")
    except Exception as e:
        print(f"❌ 发生致命错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if 'env' in locals():
            env.close()

if __name__ == "__main__":
    print("=" * 60)
    print("LOH Actor-Critic Training with Stable-Baselines3")
    print("=" * 60)
    print()
    print("【使用说明】:")
    print("1. 确保C端LOH缓存模拟器已经启动并创建了共享内存")
    print("2. 设置环境变量 LOH_STATE_DIM 来指定状态向量维度 (26 或 38)")
    print("3. 训练过程中可以按 Ctrl+C 安全停止并保存模型")
    print("4. 训练日志保存在 ./runs/<timestamp>/ 目录下")
    print("5. 可以使用 tensorboard --logdir ./runs/<timestamp>/sb3_logs 查看训练曲线")
    print()
    print("【关键参数】:")
    print(f"- 状态维度: {CONTEXT_DIM}")
    print(f"- 动作维度: {FEATURE_DIM}")
    print(f"- 共享内存键: {SHM_KEY}")
    print()

    main()

# --- 创建共享内存 ---
def create_shared_memory():
    """创建共享内存文件"""
    try:
        shm_path = f"/dev/shm/loh_ac_{SHM_KEY}"
        size = ctypes.sizeof(SharedMemoryData)

        if not os.path.exists(shm_path):
            print(f"🔨 创建共享内存: {shm_path}")
            with open(shm_path, 'wb') as f:
                f.write(b'\x00' * size)
        else:
            print(f"✅ 共享内存已存在: {shm_path}")

        print(f"✅ 共享内存就绪 ({size} bytes)")
        return True
    except Exception as e:
        print(f"❌ 共享内存创建失败: {e}")
        return False

# 立即创建共享内存
if not create_shared_memory():
    print("❌ 无法创建共享内存，退出")
    sys.exit(1)

# --- 尝试导入ML库 ---
def try_import_ml_libs():
    """尝试导入机器学习库"""
    try:
        print("🔄 导入 Gymnasium...")
        import gymnasium as gym
        from gymnasium import spaces

        print("🔄 导入 Stable-Baselines3...")
        from stable_baselines3 import PPO
        from stable_baselines3.common.env_checker import check_env
        from stable_baselines3.common.callbacks import CheckpointCallback
        from stable_baselines3.common.monitor import Monitor

        print("🔄 导入 PyTorch...")
        import torch

        print("✅ 所有ML库导入成功")
        return True, {
            'gym': gym, 'spaces': spaces, 'PPO': PPO, 'check_env': check_env,
            'CheckpointCallback': CheckpointCallback, 'Monitor': Monitor, 'torch': torch
        }
    except Exception as e:
        print(f"❌ ML库导入失败: {e}")
        return False, None

USE_ML, ml_libs = try_import_ml_libs()

# --- 基础环境类 ---
class BaseLohEnv:
    """基础LOH环境类"""

    def __init__(self, shm_key=SHM_KEY):
        self.shm_key = shm_key
        self.shm_file = None
        self.shm_mmap = None
        self.step_count = 0
        self._attach_shared_memory()

    def _attach_shared_memory(self):
        """连接共享内存"""
        try:
            shm_path = f"/dev/shm/loh_ac_{self.shm_key}"
            size = ctypes.sizeof(SharedMemoryData)

            self.shm_file = open(shm_path, 'r+b')
            self.shm_mmap = mmap.mmap(self.shm_file.fileno(), size)
            print("✅ 共享内存连接成功")
        except Exception as e:
            print(f"❌ 共享内存连接失败: {e}")
            raise

    def _read_shm(self):
        """读取共享内存"""
        try:
            self.shm_mmap.seek(0)
            raw_data = self.shm_mmap.read(ctypes.sizeof(SharedMemoryData))
            return SharedMemoryData.from_buffer_copy(raw_data)
        except Exception as e:
            print(f"❌ 读取共享内存失败: {e}")
            return None

    def _write_shm(self, data_struct):
        """写入共享内存"""
        try:
            self.shm_mmap.seek(0)
            self.shm_mmap.write(data_struct)
            self.shm_mmap.flush()
            return True
        except Exception as e:
            print(f"❌ 写入共享内存失败: {e}")
            return False

    def wait_for_state(self, timeout_seconds=60):
        """等待C端状态"""
        print(f"⏳ 等待C端状态... (超时: {timeout_seconds}s)")

        for i in range(timeout_seconds * 10):  # 0.1s检查一次
            data = self._read_shm()
            if data and data.ready_for_inference:
                print(f"✅ 收到状态 (耗时: {i*0.1:.1f}s)")
                return data
            time.sleep(0.1)

            if i % 100 == 0 and i > 0:  # 每10秒打印一次
                print(f"⏳ 仍在等待... {i*0.1:.0f}s")

        print(f"❌ 等待超时 ({timeout_seconds}s)")
        return None

    def send_weights(self, weights):
        """发送权重"""
        data = self._read_shm()
        if data is None:
            return False

        data.weights[:] = weights
        data.weights_updated = 1
        data.ready_for_inference = 0

        if self._write_shm(data):
            self.step_count += 1
            print(f"📤 发送权重 #{self.step_count}: {weights}")
            return True
        return False

    def close(self):
        """清理资源"""
        if self.shm_mmap:
            self.shm_mmap.close()
        if self.shm_file:
            self.shm_file.close()
        print("🧹 环境已清理")

# --- ML模式 ---
if USE_ML:
    gym = ml_libs['gym']
    spaces = ml_libs['spaces']
    PPO = ml_libs['PPO']
    check_env = ml_libs['check_env']
    CheckpointCallback = ml_libs['CheckpointCallback']
    Monitor = ml_libs['Monitor']
    torch = ml_libs['torch']

    class LohEnv(BaseLohEnv, gym.Env):
        """完整的Gymnasium环境"""

        def __init__(self, shm_key=SHM_KEY):
            gym.Env.__init__(self)
            BaseLohEnv.__init__(self, shm_key)

            # 定义动作和观测空间
            self.action_space = spaces.Box(
                low=-1.0, high=1.0, shape=(FEATURE_DIM,), dtype=np.float32
            )
            self.observation_space = spaces.Box(
                low=-np.inf, high=np.inf, shape=(CONTEXT_DIM,), dtype=np.float32
            )

            # 环境参数
            self.max_episode_steps = 1024
            self.current_step = 0
            self.episode_count = 0

            print("✅ ML模式环境初始化完成")

        def reset(self, seed=None, options=None):
            """重置环境"""
            super().reset(seed=seed)
            self.current_step = 0
            self.episode_count += 1

            print(f"🔄 Episode #{self.episode_count} 开始")

            # 等待初始状态
            data = self.wait_for_state(60)
            if data is None:
                raise RuntimeError("重置超时")

            obs = np.array(data.state, dtype=np.float32)
            info = {
                'miss_ratio': data.miss_ratio,
                'episode': self.episode_count
            }

            return obs, info

        def step(self, action):
            """执行一步"""
            self.current_step += 1

            # 转换动作为权重
            weights = torch.nn.functional.softmax(torch.tensor(action), dim=-1).numpy()

            # 发送权重
            if not self.send_weights(weights):
                raise RuntimeError("权重发送失败")

            # 等待新状态
            data = self.wait_for_state(30)
            if data is None:
                raise RuntimeError("等待新状态超时")

            # 计算奖励
            obs = np.array(data.state, dtype=np.float32)
            reward = 1.0 - data.miss_ratio  # 简单的奖励函数

            terminated = (data.terminate == 1)
            truncated = (self.current_step >= self.max_episode_steps)

            info = {
                'miss_ratio': data.miss_ratio,
                'step': self.current_step
            }

            return obs, reward, terminated, truncated, info

    def run_ml_mode():
        """运行ML训练模式"""
        print("🚀 启动ML训练模式")

        # 创建运行目录
        run_timestamp = datetime.now().strftime("%m%d_%H%M%S")
        run_dir = f"./runs/{run_timestamp}"
        os.makedirs(run_dir, exist_ok=True)

        try:
            # 创建环境
            env = LohEnv()
            env = Monitor(env, f"{run_dir}/monitor.csv")

            # 创建SAC模型
            model = PPO(
                "MlpPolicy",
                env,
                verbose=1,
                n_steps=1024,
                batch_size=64,
                learning_rate=3e-4,
                tensorboard_log=f"{run_dir}/logs/"
            )

            # 开始训练
            print("🧠 开始训练...")
            model.learn(total_timesteps=10000, progress_bar=True)

            # 保存模型
            model.save(f"{run_dir}/final_model")
            print(f"💾 模型已保存: {run_dir}/final_model")

        except KeyboardInterrupt:
            print("⚠️ 用户中断")
        except Exception as e:
            print(f"❌ 训练错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if 'env' in locals():
                env.close()

else:
    # 简单模式
    def run_simple_mode():
        """运行简单测试模式"""
        print("🔧 启动简单测试模式")

        env = BaseLohEnv()

        try:
            for step in range(10):
                print(f"\n--- Step {step + 1} ---")

                # 等待状态
                data = env.wait_for_state(30)
                if data is None:
                    print("❌ 无法获取状态")
                    break

                # 生成随机权重
                weights = np.random.rand(FEATURE_DIM)
                weights = weights / weights.sum()

                # 发送权重
                if not env.send_weights(weights):
                    print("❌ 权重发送失败")
                    break

                print(f"📊 Miss Ratio: {data.miss_ratio:.4f}")

        except KeyboardInterrupt:
            print("⚠️ 用户中断")
        finally:
            env.close()

# --- 主函数 ---
def main():
    print("=" * 60)
    print("LOH Actor-Critic 训练系统")
    print("=" * 60)
    print(f"状态维度: {CONTEXT_DIM}")
    print(f"动作维度: {FEATURE_DIM}")
    print(f"模式: {'ML训练模式' if USE_ML else '简单测试模式'}")
    print()

    if USE_ML:
        run_ml_mode()
    else:
        run_simple_mode()

if __name__ == "__main__":
    main()
