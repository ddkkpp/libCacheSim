#!/usr/bin/env python3
"""
LOH Actor-Critic Reinforcement Learning Model (Enhanced Version)

This script implements an Actor-Critic reinforcement learning model
that communicates with the LOH caching algorithm through shared memory.
The model learns to optimize cache eviction policies by updating the
weights used in the LOH algorithm's eviction scoring function.

Enhanced features:
- Detailed training logging with reward, loss, weights
- Terminal output of all training details
- CSV logging for analysis
- Network input/output logging
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import time
import sys
import signal
import ctypes
from ctypes import c_int, c_double, c_int64
import os
import struct
import mmap
import array
import csv
import json
from datetime import datetime
import random

# Constants - must match those in LOH.c
CONTEXT_DIM = 38  # 状态向量维度
FEATURE_DIM = 6   # 六个特征权重: recency, frequency, size, irt1, irt2, irt3
SHM_KEY = 9876

# Shared memory structure
class SharedMemoryData(ctypes.Structure):
    _fields_ = [
        ("ready_for_inference", c_int),
        ("weights_updated", c_int),
        ("terminate", c_int),
        ("state", c_double * CONTEXT_DIM),
        ("weights", c_double * FEATURE_DIM),
        ("miss_ratio", c_double),
        ("byte_miss_ratio", c_double),
        ("reward", c_double),
        ("timestamp", c_int64)
    ]

# Actor-Critic Network Models
class ActorNetwork(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(ActorNetwork, self).__init__()
        # 扩大网络容量以处理38维输入
        self.fc1 = nn.Linear(state_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, action_dim)

        # 使用更大的初始化权重，促使网络生成非零输出
        nn.init.xavier_uniform_(self.fc1.weight, gain=1.5)
        nn.init.xavier_uniform_(self.fc2.weight, gain=1.5)
        nn.init.xavier_uniform_(self.fc3.weight, gain=2.0)

        # 设置一个小的正偏置以确保有非零输出
        nn.init.constant_(self.fc3.bias, 0.5)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        # 使用softplus确保权重为正值，并增加一个小的常数确保非零
        x = F.softplus(self.fc3(x)) + 0.1
        return x

class CriticNetwork(nn.Module):
    def __init__(self, state_dim):
        super(CriticNetwork, self).__init__()
        # 扩大网络容量以处理38维输入
        self.fc1 = nn.Linear(state_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, 1)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x

class TrainingLogger:
    """Enhanced training logger for detailed analysis"""

    def __init__(self, log_dir="training_logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        # Create timestamped log files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_file = os.path.join(log_dir, f"training_log_{timestamp}.csv")
        self.json_file = os.path.join(log_dir, f"training_details_{timestamp}.json")
        self.weights_file = os.path.join(log_dir, f"weights_history_{timestamp}.csv")

        # Initialize CSV files
        self.init_csv_files()

        # Training data storage
        self.training_data = []
        self.episode_count = 0

    def init_csv_files(self):
        """Initialize CSV files with headers"""
        # Main training log
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'episode', 'timestamp', 'reward', 'actor_loss', 'critic_loss',
                'td_error', 'miss_ratio', 'byte_miss_ratio', 'value_estimate'
            ])

        # Weights history
        with open(self.weights_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'episode', 'timestamp', 'recency', 'frequency', 'size',
                'irt1', 'irt2', 'irt3'
            ])

    def log_training_step(self, episode, reward, actor_loss, critic_loss,
                         td_error, miss_ratio, byte_miss_ratio, value_estimate,
                         weights, state, action):
        """Log a training step with all details"""
        timestamp = datetime.now().isoformat()

        # Terminal output with colors
        print(f"\n{'='*60}")
        print(f"🔄 TRAINING STEP {episode}")
        print(f"⏰ Time: {timestamp}")
        print(f"💰 Reward: {reward:.4f}")
        print(f"🎭 Actor Loss: {actor_loss:.6f}")
        print(f"🎯 Critic Loss: {critic_loss:.6f}")
        print(f"📊 TD Error: {td_error:.6f}")
        print(f"❌ Miss Ratio: {miss_ratio:.4f}")
        print(f"📈 Byte Miss Ratio: {byte_miss_ratio:.4f}")
        print(f"💡 Value Estimate: {value_estimate:.4f}")

        # Print weights
        print(f"\n🎛️  Current Weights:")
        weight_names = ['recency', 'frequency', 'size', 'irt1', 'irt2', 'irt3']
        for i, (name, weight) in enumerate(zip(weight_names, weights)):
            print(f"   {name:>10}: {weight:.6f}")

        # Print state summary (first few dimensions)
        print(f"\n🔍 State Summary (first 10 dims):")
        state_subset = state[:10] if len(state) > 10 else state
        for i, val in enumerate(state_subset):
            print(f"   s[{i:2d}]: {val:.6f}")
        if len(state) > 10:
            print(f"   ... (and {len(state)-10} more dimensions)")

        print(f"{'='*60}")

        # CSV logging
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                episode, timestamp, reward, actor_loss, critic_loss,
                td_error, miss_ratio, byte_miss_ratio, value_estimate
            ])

        # Weights CSV logging
        with open(self.weights_file, 'a', newline='') as f:
            writer = csv.writer(f)
            row = [episode, timestamp] + list(weights)
            writer.writerow(row)

        # Detailed JSON logging
        step_data = {
            'episode': episode,
            'timestamp': timestamp,
            'reward': float(reward),
            'actor_loss': float(actor_loss),
            'critic_loss': float(critic_loss),
            'td_error': float(td_error),
            'miss_ratio': float(miss_ratio),
            'byte_miss_ratio': float(byte_miss_ratio),
            'value_estimate': float(value_estimate),
            'weights': {
                'recency': float(weights[0]),
                'frequency': float(weights[1]),
                'size': float(weights[2]),
                'irt1': float(weights[3]),
                'irt2': float(weights[4]),
                'irt3': float(weights[5])
            },
            'state': [float(x) for x in state],
            'action': [float(x) for x in action] if action is not None else None
        }

        self.training_data.append(step_data)

        # Save JSON periodically
        if episode % 10 == 0:
            with open(self.json_file, 'w') as f:
                json.dump(self.training_data, f, indent=2)

class LOHActorCritic:
    def __init__(self):
        self.state_dim = CONTEXT_DIM
        self.action_dim = FEATURE_DIM

        # Initialize logger
        self.logger = TrainingLogger()

        # 状态向量结构 (38维):
        # [0-1]: 全局性能指标 - 对象命中率，字节命中率
        # [2-25]: 特征表现剖析 - 每个特征在命中/未命中对象中的均值和方差 (6个特征 × 2种统计 × 2种事件)
        # [26-37]: 缓存池状态摘要 - 当前池内对象的特征均值和方差 (6个特征 × 2种统计)

        # 动作向量结构 (6维):
        # 对应六个特征的权重: recency, frequency, size, irt1, irt2, irt3

        # 设置一些初始合理的权重，这样即使在训练开始时也能有良好的性能
        # 根据经验，为LOH算法设置一些初始权重
        # LOH中的特征按顺序是：recency, frequency, size, irt1, irt2, irt3
        raw_weights = np.array([0.5, 1.0, 0.8, 0.6, 0.4, 0.3])
        self.initial_weights = raw_weights / np.sum(raw_weights)

        # Initialize networks
        self.actor = ActorNetwork(self.state_dim, self.action_dim)
        self.critic = CriticNetwork(self.state_dim)

        # Optimizers - 增加学习率以加快训练
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=0.002)  # 原来是0.0005
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=0.004)  # 原来是0.001

        # Hyperparameters
        self.gamma = 0.99  # Discount factor
        self.tau = 0.005   # Soft update parameter
        self.update_freq = 1  # 每次接收到C程序的状态就立即更新

        # Training variables
        self.last_state = None
        self.last_action = None
        self.last_value = None
        self.last_miss_ratio = None
        self.update_count = 0

        # 添加经验回放缓冲区
        self.experience_buffer = []  # 存储(state, action, reward, next_state)元组
        self.buffer_size = 100  # 经验回放缓冲区大小
        self.batch_size = 16  # 批量训练大小

        # Initialize shared memory
        self.shm = None
        self.sem = None
        self.data = None
        self.buffer = None
        print("Starting LOH Actor-Critic Enhanced")
        print("Initial state: self.shm is None, self.sem is None")
        print(f"Expected structure size: {ctypes.sizeof(SharedMemoryData)} bytes")
        self.attach_shared_memory()
        print(f"After attach_shared_memory: self.shm is {'not None' if self.shm else 'None'}")

        # 初次写入这些权重到共享内存
        if self.shm:
            print(f"Setting initial weights: {self.initial_weights}")
            self.write_weights_to_shared_memory(self.initial_weights)

        # Signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def attach_shared_memory(self):
        """Attach to shared memory file with file-based approach"""
        try:
            current_user = os.getenv('USER', 'unknown')
            print(f"Current user: {current_user}")

            # 使用文件系统的共享内存（更可靠）
            shm_filename = f"/dev/shm/loh_ac_{SHM_KEY}"
            print(f"Using shared memory file: {shm_filename}")

            # 如果文件不存在，创建一个新的
            if not os.path.exists(shm_filename):
                print(f"Creating new shared memory file: {shm_filename}")
                with open(shm_filename, 'wb') as f:
                    # 创建并初始化共享内存结构
                    data = SharedMemoryData()
                    f.write(ctypes.string_at(ctypes.addressof(data), ctypes.sizeof(data)))
                # 设置权限
                os.chmod(shm_filename, 0o666)
            else:
                print(f"Found existing shared memory file: {shm_filename}")

            # 打开文件进行读写
            self.shm_file = open(shm_filename, 'r+b')
            size = ctypes.sizeof(SharedMemoryData)
            print(f"Successfully opened shared memory file with size {size} bytes")

            # 使用mmap映射文件
            self.shm_mmap = mmap.mmap(self.shm_file.fileno(), size)
            self.shm = self.shm_mmap  # 修复：正确设置self.shm
            print("Successfully attached to shared memory file")

        except Exception as e:
            print(f"Failed to attach to shared memory: {e}")
            self.shm = None

    def read_from_shared_memory(self):
        """Read data from shared memory"""
        if self.shm is None:
            return None

        try:
            # 从内存映射文件读取数据
            self.shm.seek(0)
            raw_data = self.shm.read(ctypes.sizeof(SharedMemoryData))

            # 将字节数据转换为结构体
            data = SharedMemoryData.from_buffer_copy(raw_data)
            return data
        except Exception as e:
            print(f"Error reading from shared memory: {e}")
            return None

    def write_weights_to_shared_memory(self, weights):
        """Write weights to shared memory"""
        if self.shm is None:
            print("Shared memory not available")
            return False

        try:
            # 读取当前数据
            data = self.read_from_shared_memory()
            if data is None:
                return False

            # 更新权重
            for i in range(min(len(weights), FEATURE_DIM)):
                data.weights[i] = weights[i]

            # 标记权重已更新
            data.weights_updated = 1

            # 写回共享内存
            self.shm.seek(0)
            self.shm.write(ctypes.string_at(ctypes.addressof(data), ctypes.sizeof(data)))
            self.shm.flush()

            return True
        except Exception as e:
            print(f"Error writing to shared memory: {e}")
            return False

    def get_action(self, state):
        """Get action (weights) from actor network"""
        state_tensor = torch.FloatTensor(state).unsqueeze(0)

        with torch.no_grad():
            raw_weights = self.actor(state_tensor).squeeze().numpy()

        # 归一化权重使其和为1
        normalized_weights = raw_weights / np.sum(raw_weights)

        return normalized_weights

    def update_networks(self, state, action, reward, next_state, miss_ratio, byte_miss_ratio):
        """Update actor and critic networks using Actor-Critic algorithm"""

        # Convert to tensors
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        action_tensor = torch.FloatTensor(action).unsqueeze(0)
        reward_tensor = torch.FloatTensor([reward])

        # Get current value estimate
        current_value = self.critic(state_tensor).squeeze()

        # Calculate target value and TD error
        if next_state is not None:
            next_state_tensor = torch.FloatTensor(next_state).unsqueeze(0)
            next_value = self.critic(next_state_tensor).squeeze()
            target_value = reward_tensor + self.gamma * next_value
        else:
            target_value = reward_tensor

        td_error = target_value - current_value

        # Update critic
        critic_loss = F.mse_loss(current_value, target_value.detach())
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()

        # Update actor
        log_prob = self.compute_log_prob(state_tensor, action_tensor)
        actor_loss = -log_prob * td_error.detach()

        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        self.actor_optimizer.step()

        # Log training details
        self.update_count += 1
        self.logger.log_training_step(
            episode=self.update_count,
            reward=reward,
            actor_loss=actor_loss.item(),
            critic_loss=critic_loss.item(),
            td_error=td_error.item(),
            miss_ratio=miss_ratio,
            byte_miss_ratio=byte_miss_ratio,
            value_estimate=current_value.item(),
            weights=action,
            state=state,
            action=action
        )

        return actor_loss.item(), critic_loss.item(), td_error.item()

    def compute_log_prob(self, state, action):
        """Compute log probability of action given state (simplified for continuous case)"""
        # 对于连续动作空间，我们使用简化的方法
        # 这里我们计算预测动作与实际动作的相似性
        predicted_action = self.actor(state)

        # 使用负均方误差作为log概率的近似
        mse = F.mse_loss(predicted_action, action, reduction='mean')
        log_prob = -mse

        return log_prob

    def signal_handler(self, signum, frame):
        """Handle shutdown signal"""
        print("\nReceived shutdown signal. Cleaning up...")
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        """Clean up resources"""
        if self.shm:
            try:
                # 设置终止标志
                data = self.read_from_shared_memory()
                if data:
                    data.terminate = 1
                    self.shm.seek(0)
                    self.shm.write(ctypes.string_at(ctypes.addressof(data), ctypes.sizeof(data)))
                    self.shm.flush()

                self.shm.close()
                if hasattr(self, 'shm_file'):
                    self.shm_file.close()
            except:
                pass

    def train(self):
        """Main training loop"""
        print("Starting Actor-Critic training loop")
        print(f"Monitoring shared memory with key {SHM_KEY}")

        count = 0
        while True:
            try:
                # 读取共享内存
                data = self.read_from_shared_memory()

                if data is None:
                    time.sleep(0.1)
                    continue

                count += 1
                if count % 50 == 0:
                    print(f"Waiting for data... (count: {count})")
                    print(f"Current data: ready={bool(data.ready_for_inference)}, terminate={bool(data.terminate)}")

                # 检查终止信号
                if data.terminate:
                    print("Received termination signal")
                    break

                # 检查是否有新数据需要处理
                if data.ready_for_inference:
                    print(f"\n📥 Received data from LOH algorithm")

                    # 提取状态
                    state = np.array([data.state[i] for i in range(CONTEXT_DIM)])
                    miss_ratio = data.miss_ratio
                    byte_miss_ratio = data.byte_miss_ratio

                    print(f"📊 Current performance: Miss Ratio = {miss_ratio:.4f}, Byte Miss Ratio = {byte_miss_ratio:.4f}")

                    # 生成新的动作（权重）
                    new_weights = self.get_action(state)

                    print(f"🎛️  Generated new weights: {[f'{w:.3f}' for w in new_weights]}")

                    # 如果有之前的状态，进行训练
                    if self.last_state is not None:
                        # 计算奖励（基于miss ratio的改善）
                        if self.last_miss_ratio is not None:
                            miss_ratio_improvement = self.last_miss_ratio - miss_ratio
                            reward = miss_ratio_improvement * 100  # 放大奖励信号

                            # 添加一些正则化项鼓励权重的稳定性
                            weight_change_penalty = -0.1 * np.sum(np.abs(new_weights - self.last_action))
                            reward += weight_change_penalty
                        else:
                            reward = -miss_ratio * 100  # 初始奖励

                        print(f"💰 Calculated reward: {reward:.4f}")

                        # 更新网络
                        actor_loss, critic_loss, td_error = self.update_networks(
                            self.last_state, self.last_action, reward,
                            state, miss_ratio, byte_miss_ratio
                        )

                        print(f"📈 Network updated - Actor Loss: {actor_loss:.6f}, Critic Loss: {critic_loss:.6f}, TD Error: {td_error:.6f}")

                    # 更新共享内存中的权重
                    success = self.write_weights_to_shared_memory(new_weights)
                    if success:
                        print(f"✅ Weights written to shared memory successfully")
                    else:
                        print(f"❌ Failed to write weights to shared memory")

                    # 保存当前状态用于下次更新
                    self.last_state = state.copy()
                    self.last_action = new_weights.copy()
                    self.last_miss_ratio = miss_ratio

                    # 重置ready标志
                    data.ready_for_inference = 0
                    self.shm.seek(0)
                    self.shm.write(ctypes.string_at(ctypes.addressof(data), ctypes.sizeof(data)))
                    self.shm.flush()

                time.sleep(0.01)  # 短暂休眠以减少CPU使用

            except KeyboardInterrupt:
                print("\nTraining interrupted by user")
                break
            except Exception as e:
                print(f"Error in training loop: {e}")
                time.sleep(1)

        print("Training loop ended")
        self.cleanup()

def main():
    print("🚀 LOH Actor-Critic Enhanced Training Starting...")
    print(f"Python version: {sys.version}")

    # ------------------ Seed handling (ENV only) ------------------
    # Priority: LOH_RL_SEED > SEED. If present, apply to python random, numpy and torch.
    try:
        loh_seed_raw = os.environ.get("LOH_RL_SEED")
        seed = None
        if loh_seed_raw is not None and loh_seed_raw != "":
            seed = int(loh_seed_raw)
        else:
            seed_raw = os.environ.get("SEED")
            if seed_raw is not None and seed_raw != "":
                seed = int(seed_raw)
        if seed is not None:
            # Set PYTHONHASHSEED for reproducible hashing
            os.environ['PYTHONHASHSEED'] = str(seed)
            random.seed(seed)
            np.random.seed(seed)
            try:
                import torch as _torch
                _torch.manual_seed(seed)
                if _torch.cuda.is_available():
                    _torch.cuda.manual_seed_all(seed)
            except Exception:
                pass
            print(f"[seed] Applied LOH_RL_SEED={seed} to random/numpy/torch")
    except Exception:
        pass

    try:
        ac = LOHActorCritic()
        ac.train()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
