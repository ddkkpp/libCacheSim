#!/usr/bin/env python3
"""
LOH Actor-Critic with Batch Training and Experience Replay
改进版本：使用批量训练和经验回放来提高学习效率
"""

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
import time
import sys
import os
import ctypes
import mmap
import random
from collections import deque
from datetime import datetime

# 配置常量
SHM_KEY = 9876
FEATURE_DIM = 6
CONTEXT_DIM = 38
STATE_DIM = CONTEXT_DIM

class SharedMemoryData(ctypes.Structure):
    _fields_ = [
        ('ready_for_inference', ctypes.c_int),
        ('weights_updated', ctypes.c_int),
        ('terminate', ctypes.c_int),
        ('miss_ratio', ctypes.c_float),
        ('byte_miss_ratio', ctypes.c_float),
        ('state', ctypes.c_float * CONTEXT_DIM),
        ('weights', ctypes.c_float * FEATURE_DIM),
    ]

class ExperienceBuffer:
    """经验回放缓冲区"""
    def __init__(self, capacity=1000):
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        """添加经验到缓冲区"""
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        """从缓冲区随机采样一个批次"""
        if len(self.buffer) < batch_size:
            return None

        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        return (
            np.array(states),
            np.array(actions),
            np.array(rewards),
            np.array(next_states),
            np.array(dones)
        )

    def __len__(self):
        return len(self.buffer)

class Actor(nn.Module):
    """Actor网络"""
    def __init__(self, state_dim, action_dim, hidden_dim=128):
        super(Actor, self).__init__()
        self.fc1 = nn.Linear(state_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, action_dim)
        self.dropout = nn.Dropout(0.1)

    def forward(self, state):
        x = F.relu(self.fc1(state))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.dropout(x)
        x = F.softmax(self.fc3(x), dim=-1)  # 使用softmax确保权重和为1
        return x

class Critic(nn.Module):
    """Critic网络"""
    def __init__(self, state_dim, hidden_dim=128):
        super(Critic, self).__init__()
        self.fc1 = nn.Linear(state_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, 1)
        self.dropout = nn.Dropout(0.1)

    def forward(self, state):
        x = F.relu(self.fc1(state))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.dropout(x)
        value = self.fc3(x)
        return value

class LOHActorCriticBatch:
    """带批量训练的LOH Actor-Critic"""

    def __init__(self):
        self.state_dim = STATE_DIM
        self.action_dim = FEATURE_DIM
        self.lr_actor = 1e-4
        self.lr_critic = 1e-3
        self.gamma = 0.95

        # 批量训练参数
        self.batch_size = 32  # 增加批量大小
        self.min_buffer_size = 64  # 最小缓冲区大小才开始训练
        self.train_freq = 5  # 每5个样本训练一次

        # 经验回放缓冲区
        self.experience_buffer = ExperienceBuffer(capacity=2000)

        # 网络初始化
        self.actor = Actor(self.state_dim, self.action_dim)
        self.critic = Critic(self.state_dim)

        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=self.lr_actor)
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=self.lr_critic)

        # 训练统计
        self.update_count = 0
        self.sample_count = 0
        self.batch_train_count = 0

        # 状态记录
        self.last_state = None
        self.last_action = None
        self.last_miss_ratio = None

        # 初始权重
        self.initial_weights = np.array([1/6] * 6, dtype=np.float32)

        # 共享内存
        self.shm = None
        self.shm_file = None
        self.shm_mmap = None

        print(f"🚀 批量训练Actor-Critic初始化完成")
        print(f"📦 批量大小: {self.batch_size}")
        print(f"🔄 训练频率: 每{self.train_freq}个样本")
        print(f"💾 缓冲区容量: {self.experience_buffer.capacity}")

        self.attach_shared_memory()

    def attach_shared_memory(self):
        """连接到共享内存"""
        try:
            shm_path = f"/dev/shm/loh_ac_{SHM_KEY}"

            if not os.path.exists(shm_path):
                print(f"Creating shared memory file: {shm_path}")
                with open(shm_path, 'wb') as f:
                    f.write(b'\x00' * ctypes.sizeof(SharedMemoryData))

            self.shm_file = open(shm_path, 'r+b')
            size = ctypes.sizeof(SharedMemoryData)
            self.shm_mmap = mmap.mmap(self.shm_file.fileno(), size)
            self.shm = self.shm_mmap

            print(f"✅ 成功连接到共享内存 ({size} bytes)")

            # 设置初始权重
            self.write_weights_to_shared_memory(self.initial_weights)

        except Exception as e:
            print(f"❌ 共享内存连接失败: {e}")
            self.shm = None

    def read_from_shared_memory(self):
        """从共享内存读取数据"""
        if self.shm is None:
            return None

        try:
            self.shm.seek(0)
            raw_data = self.shm.read(ctypes.sizeof(SharedMemoryData))
            data = SharedMemoryData.from_buffer_copy(raw_data)
            return data
        except Exception as e:
            print(f"❌ 共享内存读取错误: {e}")
            return None

    def write_weights_to_shared_memory(self, weights):
        """写权重到共享内存"""
        if self.shm is None:
            return False

        try:
            data = self.read_from_shared_memory()
            if data is None:
                return False

            for i in range(min(len(weights), FEATURE_DIM)):
                data.weights[i] = weights[i]
            data.weights_updated = 1

            self.shm.seek(0)
            self.shm.write(ctypes.string_at(ctypes.addressof(data), ctypes.sizeof(data)))
            self.shm.flush()

            return True
        except Exception as e:
            print(f"❌ 权重写入错误: {e}")
            return False

    def get_action(self, state):
        """从Actor网络获取动作"""
        state_tensor = torch.FloatTensor(state).unsqueeze(0)

        with torch.no_grad():
            weights = self.actor(state_tensor).squeeze().numpy()

        return weights

    def batch_update_networks(self):
        """批量更新网络"""
        if len(self.experience_buffer) < self.min_buffer_size:
            return None, None, None

        # 采样批次数据
        batch = self.experience_buffer.sample(self.batch_size)
        if batch is None:
            return None, None, None

        states, actions, rewards, next_states, dones = batch

        # 转换为张量
        states_tensor = torch.FloatTensor(states)
        actions_tensor = torch.FloatTensor(actions)
        rewards_tensor = torch.FloatTensor(rewards)
        next_states_tensor = torch.FloatTensor(next_states)
        dones_tensor = torch.FloatTensor(dones)

        # 计算当前值
        current_values = self.critic(states_tensor).squeeze()

        # 计算目标值
        with torch.no_grad():
            next_values = self.critic(next_states_tensor).squeeze()
            target_values = rewards_tensor + self.gamma * next_values * (1 - dones_tensor)

        # 更新Critic
        critic_loss = F.mse_loss(current_values, target_values)
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()

        # 计算TD误差
        td_errors = target_values - current_values.detach()

        # 更新Actor
        predicted_actions = self.actor(states_tensor)
        action_loss = F.mse_loss(predicted_actions, actions_tensor, reduction='none').mean(dim=1)
        actor_loss = (action_loss * td_errors).mean()

        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        self.actor_optimizer.step()

        self.batch_train_count += 1

        print(f"📈 批量训练 #{self.batch_train_count}: Actor Loss: {actor_loss.item():.6f}, Critic Loss: {critic_loss.item():.6f}")
        print(f"   🎯 平均TD误差: {td_errors.mean().item():.6f}, 批量大小: {len(states)}")

        return actor_loss.item(), critic_loss.item(), td_errors.mean().item()

    def train(self):
        """主训练循环"""
        import math
        import datetime
        log_file = open("ac_batch_output.log", "a")
        log_file.write(f"==== LOG START {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====" + "\n")
        log_file.flush()
        print(f"🎯 开始批量训练循环...")

        count = 0
        while True:
            try:
                data = self.read_from_shared_memory()
                if data is None:
                    time.sleep(0.1)
                    continue

                count += 1
                if count % 100 == 0:
                    msg = f"⏳ 等待数据... (count: {count})"
                    print(msg)
                    log_file.write(msg + "\n")
                    log_file.flush()

                if data.terminate:
                    print("🛑 收到终止信号")
                    log_file.write("🛑 收到终止信号\n")
                    log_file.flush()
                    break

                if data.ready_for_inference:
                    self.sample_count += 1
                    msg = f"\n📥 收到第{self.sample_count}个样本"
                    print(msg)
                    log_file.write(msg + "\n")
                    log_file.flush()

                    # 提取状态
                    state = np.array([data.state[i] for i in range(CONTEXT_DIM)])
                    miss_ratio = data.miss_ratio
                    byte_miss_ratio = data.byte_miss_ratio

                    msg = f"📊 性能: Miss Ratio = {miss_ratio:.4f}, Byte Miss Ratio = {byte_miss_ratio:.4f}"
                    print(msg)
                    log_file.write(msg + "\n")
                    log_file.flush()

                    # 生成新权重
                    new_weights = self.get_action(state)
                    msg = f"🎛️  新权重: {[f'{w:.3f}' for w in new_weights]}"
                    print(msg)
                    log_file.write(msg + "\n")
                    log_file.flush()

                    # 如果有历史状态，添加到经验缓冲区
                    if self.last_state is not None:
                        # 计算奖励
                        if self.last_miss_ratio is not None:
                            reward = (self.last_miss_ratio - miss_ratio) * 100
                        else:
                            reward = -miss_ratio * 100

                        # 添加经验到缓冲区
                        self.experience_buffer.push(
                            self.last_state,
                            self.last_action,
                            reward,
                            state,
                            False  # 不是终止状态
                        )

                        msg = f"💰 奖励: {reward:.4f}, 缓冲区大小: {len(self.experience_buffer)}"
                        print(msg)
                        log_file.write(msg + "\n")
                        log_file.flush()

                        # 批量训练
                        if self.sample_count % self.train_freq == 0:
                            actor_loss, critic_loss, td_error = self.batch_update_networks()
                            if actor_loss is not None:
                                msg = f"🔄 批量训练完成 (样本 #{self.sample_count})"
                                print(msg)
                                log_file.write(msg + "\n")
                                log_file.flush()
                                # 检查nan
                                if math.isnan(actor_loss) or math.isnan(critic_loss) or math.isnan(td_error):
                                    print(f"❌ 检测到nan，退出。actor_loss={actor_loss}, critic_loss={critic_loss}, td_error={td_error}")
                                    log_file.write(f"❌ 检测到nan，退出。actor_loss={actor_loss}, critic_loss={critic_loss}, td_error={td_error}\n")
                                    log_file.write(f"last_state={self.last_state}\nlast_action={self.last_action}\nreward={reward}\nstate={state}\nmiss_ratio={miss_ratio}\nbyte_miss_ratio={byte_miss_ratio}\n")
                                    log_file.flush()
                                    log_file.close()
                                    exit(1)

                    # 更新权重到共享内存
                    if self.write_weights_to_shared_memory(new_weights):
                        msg = f"✅ 权重已更新: {[f'{w:.3f}' for w in new_weights]}"
                        print(msg)
                        log_file.write(msg + "\n")
                        log_file.flush()

                    # 保存当前状态
                    self.last_state = state.copy()
                    self.last_action = new_weights.copy()
                    self.last_miss_ratio = miss_ratio

                    # 重置ready标志
                    data.ready_for_inference = 0
                    self.shm.seek(0)
                    self.shm.write(ctypes.string_at(ctypes.addressof(data), ctypes.sizeof(data)))
                    self.shm.flush()

                time.sleep(0.01)

            except KeyboardInterrupt:
                print("\n⚠️  用户中断训练")
                log_file.write("\n⚠️  用户中断训练\n")
                log_file.flush()
                log_file.close()
                break
            except Exception as e:
                print(f"❌ 训练循环错误: {e}")
                time.sleep(1)

        print(f"🏁 训练结束")
        print(f"📊 统计: {self.sample_count}个样本, {self.batch_train_count}次批量训练")
        self.cleanup()

    def cleanup(self):
        """清理资源"""
        if self.shm:
            self.shm.close()
        if self.shm_file:
            self.shm_file.close()

def main():
    print("🚀 LOH Actor-Critic 批量训练版本启动...")
    try:
        ac = LOHActorCriticBatch()
        ac.train()
    except Exception as e:
        print(f"❌ 致命错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
