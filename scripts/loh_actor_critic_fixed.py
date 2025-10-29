#!/usr/bin/env python3
"""
LOH Actor-Critic Reinforcement Learning Model (Fixed Version)

This script implements an Actor-Critic reinforcement learning model
that communicates with the LOH caching algorithm through shared memory.
The model learns to optimize cache eviction policies by updating the
weights used in the LOH algorithm's eviction scoring function.
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

class LOHActorCritic:
    def __init__(self):
        self.state_dim = CONTEXT_DIM
        self.action_dim = FEATURE_DIM

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

    def save_model(self, path):
        """Save model to path"""
        torch.save({
            'actor_state_dict': self.actor.state_dict(),
            'critic_state_dict': self.critic.state_dict(),
            'actor_optimizer': self.actor_optimizer.state_dict(),
            'critic_optimizer': self.critic_optimizer.state_dict(),
        }, path)
        print(f"Model saved to {path}")

    def load_model(self, path):
        """Load model from path"""
        try:
            checkpoint = torch.load(path)
            self.actor.load_state_dict(checkpoint['actor_state_dict'])
            self.critic.load_state_dict(checkpoint['critic_state_dict'])
            self.actor_optimizer.load_state_dict(checkpoint['actor_optimizer'])
            self.critic_optimizer.load_state_dict(checkpoint['critic_optimizer'])
            print(f"Model loaded from {path}")
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

    def normalize_weights(self, weights):
        """Normalize weights to sum to 1"""
        weights_sum = np.sum(weights)
        if weights_sum > 0:
            return weights / weights_sum
        return weights

    def print_state_info(self, state):
        """打印38维状态向量的详细信息，帮助理解和调试"""
        print("\n=== 状态向量详细信息 ===")

        # A. 全局性能指标 (2维)
        print("A. 全局性能指标:")
        print(f"   对象命中率: {state[0]:.4f}")
        print(f"   字节命中率: {state[1]:.4f}")

        # B. 特征表现剖析 (24维)
        print("\nB. 特征表现剖析:")
        features = ["Recency", "Frequency", "Size", "IRT1", "IRT2", "IRT3"]
        offset = 2
        for i, feature in enumerate(features):
            base = offset + i * 4
            print(f"   {feature}:")
            print(f"     命中对象均值: {state[base]:.4f}")
            print(f"     命中对象方差: {state[base+1]:.4f}")
            print(f"     未命中对象均值: {state[base+2]:.4f}")
            print(f"     未命中对象方差: {state[base+3]:.4f}")

        # C. 缓存池状态摘要 (12维)
        print("\nC. 缓存池状态摘要:")
        offset = 26
        for i, feature in enumerate(features):
            base = offset + i * 2
            print(f"   {feature}:")
            print(f"     缓存中对象均值: {state[base]:.4f}")
            print(f"     缓存中对象方差: {state[base+1]:.4f}")

        print("=======================\n")

    def restore_shared_memory(self):
        """Restore shared memory connection for training using file-based approach"""
        try:
            # Re-use the attach_shared_memory method which now uses file-based approach
            if self.attach_shared_memory():
                return self.shm_file, None, self.shm_data
            else:
                return None, None, None
        except Exception as e:
            print(f"Failed to restore shared memory: {e}")
            return None, None, None

        print("Actor-Critic model initialized")

    def attach_shared_memory(self):
        """Create a shared memory segment using /dev/shm file approach"""
        try:
            # Create a unique filename in /dev/shm with current user
            import getpass
            username = getpass.getuser()
            self.shm_filename = f"/dev/shm/loh_ac_{SHM_KEY}"
            print(f"Current user: {username}")
            print(f"Using shared memory file: {self.shm_filename}")

            # Check if file exists
            if os.path.exists(self.shm_filename):
                print(f"Found existing shared memory file: {self.shm_filename}")

                # Open the file
                self.shm_file = open(self.shm_filename, "r+b")

                # Map the file to memory
                self.shm_mmap = mmap.mmap(self.shm_file.fileno(), ctypes.sizeof(SharedMemoryData))

                # Create structure from memory
                self.shm_data = SharedMemoryData.from_buffer(self.shm_mmap)
                self.data = self.shm_data  # Alias for compatibility

                print(f"Successfully opened shared memory file with size {ctypes.sizeof(SharedMemoryData)} bytes")
            else:
                print(f"Creating new shared memory file: {self.shm_filename}")

                # Create a new file
                self.shm_file = open(self.shm_filename, "wb+")

                # Initialize with zeros
                self.shm_file.write(bytes(ctypes.sizeof(SharedMemoryData)))
                self.shm_file.flush()

                # Map the file to memory
                self.shm_file.seek(0)
                self.shm_mmap = mmap.mmap(self.shm_file.fileno(), ctypes.sizeof(SharedMemoryData),
                                         access=mmap.ACCESS_WRITE)

                # Create structure from memory
                self.shm_data = SharedMemoryData.from_buffer(self.shm_mmap)
                self.data = self.shm_data  # Alias for compatibility

                # Initialize weights
                for i in range(FEATURE_DIM):
                    self.shm_data.weights[i] = 1.0 if i < 2 else 0.5

                # Set permissions
                os.chmod(self.shm_filename, 0o666)

                print(f"Successfully created shared memory file with size {ctypes.sizeof(SharedMemoryData)} bytes")

            # No semaphores needed - we'll use file locking if required
            self.buffer = bytearray(ctypes.sizeof(SharedMemoryData))
            self.shm = self.shm_mmap  # 设置shm属性以便其他代码使用

            print("Successfully attached to shared memory file")
            return True

        except Exception as e:
            print(f"Failed to create shared memory: {e}")
            import traceback
            traceback.print_exc()
            return False

    def read_shared_memory(self):
        """Read data from shared memory using file-based approach"""
        try:
            if self.shm_data is None:
                print("Error: self.shm_data is None! Attempting to re-attach...")
                if not self.attach_shared_memory():
                    print("Failed to re-attach to shared memory file")
                    return None

            # Refresh memory map to get latest data
            self.shm_mmap.seek(0)
            buffer = self.shm_mmap.read(ctypes.sizeof(SharedMemoryData))

            # Update our view of the data
            temp_data = SharedMemoryData.from_buffer_copy(buffer)

            # Convert shared memory state to numpy array
            state = np.array([temp_data.state[i] for i in range(CONTEXT_DIM)])

            return {
                'ready': bool(temp_data.ready_for_inference),
                'terminate': bool(temp_data.terminate),
                'state': state,
                'miss_ratio': temp_data.miss_ratio,
                'byte_miss_ratio': temp_data.byte_miss_ratio,
                'timestamp': temp_data.timestamp
            }
        except Exception as e:
            print(f"Error reading shared memory: {e}")
            import traceback
            traceback.print_exc()
            return None

    def write_weights_to_shared_memory(self, weights):
        """Write weights to shared memory using file-based approach"""
        try:
            if self.shm_data is None:
                return False

            # Update weights in shared memory
            for i in range(FEATURE_DIM):
                self.shm_data.weights[i] = weights[i]

            # Signal that weights have been updated
            self.shm_data.weights_updated = 1

            # Reset the ready flag
            self.shm_data.ready_for_inference = 0

            # Make sure changes are flushed to disk
            self.shm_mmap.flush()

            return True
        except Exception as e:
            print(f"Error writing to shared memory: {e}")
            import traceback
            traceback.print_exc()
            return False

    def calculate_reward(self, miss_ratio, byte_miss_ratio, prev_miss_ratio=None):
        """Calculate reward based on miss ratio improvement"""
        # Lower miss ratio is better
        if prev_miss_ratio is not None:
            # Reward improvement in miss ratio (negative value is better)
            delta = prev_miss_ratio - miss_ratio
            # Scale the reward
            reward = delta * 100.0
        else:
            # If no previous state, use the inverse of miss ratio
            reward = -miss_ratio

        # Add penalty for extreme values
        if self.last_action is not None and any(w > 10.0 for w in self.last_action):
            reward -= 0.1

        return reward

    def select_action(self, state, add_noise=False):
        """
        Use the actor network to select an action (feature weights)

        Args:
            state: The current state
            add_noise: Whether to add exploration noise to the action
        """
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        with torch.no_grad():
            action = self.actor(state_tensor).squeeze().numpy()

        # 确保没有权重为零，添加一个小的非零值
        min_weight_value = 0.2
        action = np.maximum(action, min_weight_value)

        # 设置一些权重差异，不要让所有权重都相同
        # 按特征顺序：recency, frequency, size, irt1, irt2, irt3
        action[0] = max(action[0], 0.5)  # recency权重
        action[1] = max(action[1], 0.7)  # frequency权重
        # 确保irt权重也有合理的基础值
        action[3] = max(action[3], 0.4)  # irt1权重
        action[4] = max(action[4], 0.3)  # irt2权重
        action[5] = max(action[5], 0.3)  # irt3权重

        # 在训练模式下添加一些噪声以促进探索
        if add_noise:
            import random
            noise_scale = 0.2
            noise = np.random.normal(0, noise_scale, size=self.action_dim)
            action = action + noise
            action = np.maximum(action, min_weight_value)  # 再次确保非零

        # 规范化权重，确保总和为1
        action_sum = np.sum(action)
        if action_sum > 0:
            action = action / action_sum

        return action

    def update_networks(self, state, action, reward, next_state):
        """Update actor and critic networks using experience replay"""
        # 存储经验到缓冲区
        self.experience_buffer.append((state, action, reward, next_state))

        # 限制缓冲区大小
        if len(self.experience_buffer) > self.buffer_size:
            self.experience_buffer.pop(0)

        # 如果缓冲区中的经验不足，不进行更新
        if len(self.experience_buffer) < min(10, self.batch_size):
            return {'td_error': 0, 'critic_loss': 0, 'actor_loss': 0}

        # 从经验回放缓冲区中随机抽取批次
        import random
        batch_size = min(self.batch_size, len(self.experience_buffer))
        batch = random.sample(self.experience_buffer, batch_size)

        # 准备批量数据
        states, actions, rewards, next_states = zip(*batch)

        # 转换为张量
        state_tensor = torch.FloatTensor(np.array(states))
        next_state_tensor = torch.FloatTensor(np.array(next_states))
        action_tensor = torch.FloatTensor(np.array(actions))
        reward_tensor = torch.FloatTensor(np.array(rewards)).unsqueeze(1)

        # 获取当前状态值和下一状态值
        current_values = self.critic(state_tensor)
        next_values = self.critic(next_state_tensor).detach()

        # 计算TD目标和误差
        targets = reward_tensor + self.gamma * next_values
        td_error = targets - current_values

        # 更新Critic网络
        critic_loss = F.mse_loss(current_values, targets)
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()

        # 更新Actor网络使用策略梯度
        self.actor_optimizer.zero_grad()
        # 使用优势函数（TD误差）作为权重，导向更高奖励的行为
        advantages = td_error.detach()

        # 计算策略梯度损失
        log_probs = torch.log(self.actor(state_tensor) + 1e-10)
        weighted_probs = torch.sum(log_probs * action_tensor, dim=1, keepdim=True)
        actor_loss = -torch.mean(advantages * weighted_probs)

        actor_loss.backward()
        self.actor_optimizer.step()

        return {
            'td_error': td_error.mean().item(),
            'critic_loss': critic_loss.item(),
            'actor_loss': actor_loss.item()
        }

    def run(self):
        """Main loop to monitor shared memory and update weights"""
        print("Starting Actor-Critic training loop")
        print(f"Monitoring shared memory with key {SHM_KEY}")

        # Wait counter for debugging
        wait_count = 0

        try:
            while True:
                # Read from shared memory
                data = self.read_shared_memory()
                if not data:
                    time.sleep(0.1)
                    continue

                # Print status periodically
                wait_count += 1
                if wait_count % 50 == 0:
                    print(f"Waiting for data... (count: {wait_count})")
                    print(f"Current data: ready={data['ready']}, terminate={data['terminate']}")

                if data['terminate']:
                    print("Termination signal received")
                    break

                if data['ready']:
                    current_state = data['state']
                    miss_ratio = data['miss_ratio']

                    # Select action
                    action = self.select_action(current_state)

                    # If we have previous state, update networks
                    if self.last_state is not None:
                        reward = self.calculate_reward(miss_ratio, data['byte_miss_ratio'], self.last_miss_ratio)

                        # 每次接收到C程序请求时都更新网络
                        self.update_count += 1
                        metrics = self.update_networks(self.last_state, self.last_action, reward, current_state)
                        print(f"Update {self.update_count} - Reward: {reward:.4f}, TD Error: {metrics['td_error']:.4f}, "
                              f"Miss Ratio: {miss_ratio:.4f}")

                    # Save current state
                    self.last_state = current_state
                    self.last_action = action
                    self.last_miss_ratio = miss_ratio

                    # Write weights to shared memory
                    if not self.write_weights_to_shared_memory(action):
                        print("Failed to write weights to shared memory")

                    print(f"New weights: [{', '.join([f'{w:.3f}' for w in action])}], Miss ratio: {miss_ratio:.4f}")

                # Sleep to avoid busy waiting
                time.sleep(0.01)

        except KeyboardInterrupt:
            print("Training interrupted by user")
        except Exception as e:
            print(f"Error in training loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("Cleaning up resources")
            try:
                if self.shm_mmap:
                    self.shm_mmap.close()
                if self.shm_file:
                    self.shm_file.close()
                print("Shared memory resources closed")
            except Exception as e:
                print(f"Error during cleanup: {e}")

    def signal_handler(self, sig, frame):
        """Handle termination signals"""
        print(f"Signal {sig} received, exiting...")
        try:
            if self.shm_mmap:
                self.shm_mmap.close()
            if self.shm_file:
                self.shm_file.close()
            print("Shared memory resources closed")
        except Exception as e:
            print(f"Error during cleanup: {e}")
        sys.exit(0)

    def train(self):
        """Main training loop with enhanced learning and exploration"""
        print("Starting Actor-Critic training for LOH with experience replay...")

        # Restore shared memory
        try:
            shm, shared_data_p, shared_data = self.restore_shared_memory()
            if not shm or not shared_data:
                print("Failed to restore shared memory")
                return
            print("Successfully attached to shared memory for training")
        except Exception as e:
            print(f"Failed to restore shared memory: {e}")
            return

        # Training parameters
        import random
        import csv
        import os

        # 训练参数
        step = 0
        episode = 0
        total_reward = 0
        state = np.zeros(CONTEXT_DIM)  # 初始状态
        episode_rewards = []

        # 创建日志目录和文件
        log_dir = "training_logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"loh_training_log_{int(time.time())}.csv")
        with open(log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Step', 'Reward', 'MissRatio', 'AvgReward50',
                             'ExplorationRate', 'TDError', 'CriticLoss', 'ActorLoss',
                             'Weight1', 'Weight2', 'Weight3', 'Weight4', 'Weight5', 'Weight6'])

        # 探索参数 - 随时间衰减
        exploration_start = 0.3  # 初始探索率
        exploration_end = 0.05   # 最终探索率
        exploration_decay = 0.995  # 探索率衰减因子
        exploration_rate = exploration_start

        # 训练变量初始化完成

        # 获取当前状态
        def get_state():
            """Get current state from shared memory"""
            try:
                # 刷新内存视图以获取最新数据
                self.shm_mmap.seek(0)
                buffer = self.shm_mmap.read(ctypes.sizeof(SharedMemoryData))

                # 更新我们的数据副本
                temp_data = SharedMemoryData.from_buffer_copy(buffer)

                # 转换状态向量为numpy数组
                state = np.array([temp_data.state[i] for i in range(CONTEXT_DIM)])
                return state
            except Exception as e:
                print(f"Error getting state: {e}")
                return np.zeros(CONTEXT_DIM)

        # 将权重发送给C程序
        def send_weights_to_c(weights, shared_data):
            """Send weights to C program through shared memory"""
            try:
                # 更新权重
                for i in range(FEATURE_DIM):
                    self.shm_data.weights[i] = weights[i]

                # 设置标志
                self.shm_data.weights_updated = 1
                self.shm_data.ready_for_inference = 0

                # 确保更改刷新到磁盘
                self.shm_mmap.flush()
                return True
            except Exception as e:
                print(f"Error sending weights: {e}")
                return False

        # 等待C程序返回奖励
        def wait_for_reward(shared_data):
            """Wait for C program to calculate reward"""
            max_wait = 100  # 最多等待10秒
            wait_count = 0

            while wait_count < max_wait:
                try:
                    # 刷新内存视图以获取最新数据
                    self.shm_mmap.seek(0)
                    buffer = self.shm_mmap.read(ctypes.sizeof(SharedMemoryData))

                    # 更新我们的数据副本
                    temp_data = SharedMemoryData.from_buffer_copy(buffer)

                    if temp_data.ready_for_inference == 1:
                        return temp_data.reward

                    time.sleep(0.1)
                    wait_count += 1

                except Exception as e:
                    print(f"Error waiting for reward: {e}")
                    return 0

            print("Timeout waiting for reward")
            return 0

        try:
            print("Initial state acquisition...")
            state = get_state()
            print("获取到初始状态向量")
            # 打印详细的状态信息
            self.print_state_info(state)

            # 设置初始权重
            initial_weights = self.normalize_weights(self.initial_weights)
            send_weights_to_c(initial_weights, shared_data)
            print(f"Initial weights set: {initial_weights}")

            # 主训练循环
            while True:
                # 根据当前状态选择动作，添加探索
                if random.random() < exploration_rate:
                    # 进行探索 - 生成稍微随机的权重
                    base_weights = np.array([0.5, 1.0, 0.8, 0.6, 0.4, 0.3])
                    # 先归一化基础权重
                    base_weights = base_weights / np.sum(base_weights)
                    noise = np.random.normal(0, 0.2, size=self.action_dim)
                    action = base_weights + noise
                    action = np.clip(action, 0.05, None)  # 确保权重为正
                    normalized_weights = self.normalize_weights(action)
                    print(f"Exploring with weights: {normalized_weights}")
                else:
                    # 使用策略网络 (带有少量噪声以促进探索)
                    action = self.select_action(state, add_noise=True)
                    normalized_weights = self.normalize_weights(action)

                # 通过共享内存传递权重给C程序
                send_weights_to_c(normalized_weights, shared_data)

                # 等待C程序处理并获取奖励
                reward = wait_for_reward(shared_data)
                total_reward += reward
                episode_rewards.append(reward)

                # 获取下一个状态
                next_state = get_state()

                # 更新网络 (每步都收集经验，根据update_freq决定更新频率)
                self.experience_buffer.append((state, action, reward, next_state))
                if len(self.experience_buffer) > self.buffer_size:
                    self.experience_buffer.pop(0)

                # 立即更新网络，每当C程序设置ready_for_inference时
                if len(self.experience_buffer) >= 10:
                    update_info = self.update_networks(state, action, reward, next_state)
                    print(f"Step {step} - Weights={normalized_weights}, Reward={reward:.4f}")
                    print(f"  Network update - TD Error: {update_info['td_error']:.6f}, "
                          f"Critic Loss: {update_info['critic_loss']:.6f}, "
                          f"Actor Loss: {update_info['actor_loss']:.6f}")

                    # 降低探索率
                    exploration_rate = max(exploration_end,
                                          exploration_rate * exploration_decay)

                # 更新状态
                state = next_state
                step += 1

                # 每50步打印进度
                if step % 50 == 0:
                    avg_reward = np.mean(episode_rewards[-50:]) if episode_rewards else 0
                    print(f"\n--- Training Progress ---")
                    print(f"Step: {step}, Average Reward (last 50): {avg_reward:.6f}")
                    print(f"Exploration Rate: {exploration_rate:.4f}")
                    print(f"Experience Buffer Size: {len(self.experience_buffer)}/{self.buffer_size}")

                    # 打印特征权重和其对应的含义
                    features = ["Recency", "Frequency", "Size", "IRT1", "IRT2", "IRT3"]
                    print("\n当前特征权重:")
                    for i, feature in enumerate(features):
                        print(f"  {feature}: {normalized_weights[i]:.4f}")

                    # 每100步打印一次完整状态信息
                    if step % 100 == 0:
                        self.print_state_info(next_state)

                    print(f"------------------------\n")

                    # 记录训练数据到CSV
                    with open(log_file, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([
                            step,
                            reward,
                            shared_data.miss_ratio,
                            avg_reward,
                            exploration_rate,
                            update_info['td_error'] if 'update_info' in locals() else 0,
                            update_info['critic_loss'] if 'update_info' in locals() else 0,
                            update_info['actor_loss'] if 'update_info' in locals() else 0,
                            *normalized_weights
                        ])

                # 每1000步保存一次模型快照
                if step % 1000 == 0 and step > 0:
                    self.save_model(f"loh_actor_critic_step_{step}.pth")
                    print(f"Model checkpoint saved at step {step}")

                    # 可视化奖励趋势（如果可用）
                    if episode_rewards and len(episode_rewards) > 100:
                        try:
                            import matplotlib.pyplot as plt
                            plt.figure(figsize=(10, 5))
                            window_size = 20
                            smoothed_rewards = [np.mean(episode_rewards[max(0, i-window_size):i+1])
                                              for i in range(len(episode_rewards))]
                            plt.plot(range(len(smoothed_rewards)), smoothed_rewards)
                            plt.title('Smoothed Reward Trend')
                            plt.xlabel('Step')
                            plt.ylabel('Reward (Moving Average)')
                            plt.savefig(f'reward_trend_step_{step}.png')
                            plt.close()
                            print(f"Reward trend visualization saved")
                        except ImportError:
                            print("Matplotlib not available for visualization")

        except KeyboardInterrupt:
            print("\nTraining interrupted. Saving final model...")
            self.save_model("loh_actor_critic_final.pth")

        # 清理共享内存
        try:
            if self.shm_mmap:
                self.shm_mmap.close()
            if self.shm_file:
                self.shm_file.close()
            print("Shared memory resources closed")
        except Exception as e:
            print(f"Error during cleanup: {e}")

        print("Training complete.")

if __name__ == "__main__":
    print("Starting LOH Actor-Critic")
    print("Python version:", sys.version)
    ac = LOHActorCritic()

    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='LOH Actor-Critic Model')
    parser.add_argument('--train', action='store_true', help='Run training mode')
    parser.add_argument('--load', type=str, help='Path to load model from')
    args = parser.parse_args()

    # Load model if specified
    if args.load:
        ac.load_model(args.load)

    # Run training or inference mode
    if args.train:
        ac.train()
    else:
        ac.run()
