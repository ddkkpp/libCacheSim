#!/bin/bash

# LOH推理服务测试脚本
# 用于测试保存的模型是否能正确进行推理

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数：打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查参数
if [ $# -eq 0 ]; then
    echo "用法: $0 <模型路径> [测试时间秒数]"
    echo ""
    echo "示例:"
    echo "  $0 runs/1016_145032/ppo_loh_final.zip 30"
    echo "  $0 runs/1016_145032/ppo_loh_interrupted.zip"
    echo ""
    echo "说明:"
    echo "  模型路径: 训练好的PPO模型文件路径"
    echo "  测试时间: 推理服务运行时间（秒），默认30秒"
    exit 1
fi

MODEL_PATH="$1"
TEST_DURATION="${2:-30}"  # 默认测试30秒

# 检查模型文件是否存在
if [ ! -f "$MODEL_PATH" ]; then
    print_error "模型文件不存在: $MODEL_PATH"
    exit 1
fi

print_info "开始LOH推理服务测试"
print_info "模型路径: $MODEL_PATH"
print_info "测试时长: ${TEST_DURATION}秒"

# 设置环境变量
export LOH_DEBUG_LEVEL=2
export LOH_POLL_SLEEP_US=200
export LOH_SEM_TIMEOUT_S=1.0

# 创建临时日志文件
TIMESTAMP=$(date +"%m%d_%H%M%S")
LOG_FILE="test_inference_${TIMESTAMP}.log"
PID_FILE="test_inference_${TIMESTAMP}.pid"

print_info "日志文件: $LOG_FILE"

# 清理函数
cleanup() {
    print_info "清理测试环境..."

    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            print_info "终止推理服务进程 (PID: $PID)"
            kill -TERM "$PID" 2>/dev/null || true
            sleep 2
            if kill -0 "$PID" 2>/dev/null; then
                print_warning "强制终止推理服务进程"
                kill -KILL "$PID" 2>/dev/null || true
            fi
        fi
        rm -f "$PID_FILE"
    fi

    # 清理共享内存
    SHM_FILE="/dev/shm/loh_ac_9876"
    if [ -f "$SHM_FILE" ]; then
        print_info "清理共享内存文件: $SHM_FILE"
        rm -f "$SHM_FILE" 2>/dev/null || true
    fi

    # 清理信号量
    print_info "清理POSIX信号量"
    rm -f /dev/shm/sem.loh_ac_ready_9876 2>/dev/null || true
    rm -f /dev/shm/sem.loh_ac_ack_9876 2>/dev/null || true

    print_info "清理完成"
}

# 设置信号处理
trap cleanup EXIT INT TERM

# 启动推理服务
print_info "启动推理服务..."
python3 scripts/loh_inference_only.py "$MODEL_PATH" > "$LOG_FILE" 2>&1 &
INFERENCE_PID=$!
echo "$INFERENCE_PID" > "$PID_FILE"

print_info "推理服务已启动 (PID: $INFERENCE_PID)"

# 等待推理服务初始化
sleep 3

# 检查推理服务是否正常启动
if ! kill -0 "$INFERENCE_PID" 2>/dev/null; then
    print_error "推理服务启动失败"
    print_error "日志内容:"
    cat "$LOG_FILE"
    exit 1
fi

print_success "推理服务启动成功"

# 创建简单的模拟C端程序来测试推理服务
print_info "创建模拟C端测试程序..."

cat > test_c_simulator.py << 'EOF'
#!/usr/bin/env python3

import ctypes
import mmap
import os
import time
import random
import sys
import errno

# POSIX 信号量绑定
libc = ctypes.CDLL("libc.so.6", use_errno=True)

SEM_FAILED = ctypes.c_void_p(-1).value

libc.sem_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
libc.sem_open.restype = ctypes.c_void_p
libc.sem_close.argtypes = [ctypes.c_void_p]
libc.sem_close.restype = ctypes.c_int
libc.sem_post.argtypes = [ctypes.c_void_p]
libc.sem_post.restype = ctypes.c_int

# 共享内存结构
class SharedMemoryData(ctypes.Structure):
    _fields_ = [
        ("ready_for_inference", ctypes.c_int),
        ("weights_updated", ctypes.c_int),
        ("terminate", ctypes.c_int),
        ("python_ready", ctypes.c_int),
        ("state", ctypes.c_double * 26),
        ("weights", ctypes.c_double * 6),
        ("miss_ratio", ctypes.c_double),
        ("byte_miss_ratio", ctypes.c_double),
        ("reward", ctypes.c_double),
        ("state_version", ctypes.c_uint64),
        ("ack_version", ctypes.c_uint64),
        ("timestamp", ctypes.c_int64),
    ]

def simulate_c_requests(duration_seconds):
    """模拟C端发送推理请求"""
    shm_path = "/dev/shm/loh_ac_9876"
    expected_size = ctypes.sizeof(SharedMemoryData)

    # 创建或连接共享内存
    if not os.path.exists(shm_path):
        with open(shm_path, 'wb') as f:
            f.write(b'\x00' * expected_size)

    # 连接信号量
    sem_ready = None
    sem_ack = None

    ready_name = b"/loh_ac_ready_9876"
    ack_name = b"/loh_ac_ack_9876"

    # 尝试打开信号量
    try:
        sem_ready = libc.sem_open(ready_name, 0, 0, 0)  # 只打开，不创建
        if sem_ready != SEM_FAILED:
            sem_ack = libc.sem_open(ack_name, 0, 0, 0)
            if sem_ack == SEM_FAILED:
                libc.sem_close(sem_ready)
                sem_ready = None
                print("[C模拟] 无法打开ack信号量，使用轮询模式")
            else:
                print("[C模拟] 信号量模式已启用")
        else:
            print("[C模拟] 无法打开ready信号量，使用轮询模式")
    except Exception as e:
        print(f"[C模拟] 信号量初始化失败: {e}，使用轮询模式")
        sem_ready = None
        sem_ack = None

    with open(shm_path, 'r+b') as shm_file:
        shm = mmap.mmap(shm_file.fileno(), expected_size)

        start_time = time.time()
        request_count = 0
        successful_responses = 0

        print(f"开始模拟C端请求，持续 {duration_seconds} 秒...")

        while time.time() - start_time < duration_seconds:
            try:
                # 生成随机状态
                data = SharedMemoryData()

                # 设置随机状态向量
                for i in range(26):
                    data.state[i] = random.uniform(-1.0, 1.0)

                data.miss_ratio = random.uniform(0.1, 0.9)
                data.byte_miss_ratio = random.uniform(0.1, 0.9)
                data.state_version = request_count + 1
                data.ready_for_inference = 1
                data.python_ready = 1
                data.timestamp = int(time.time() * 1000000)  # 微秒时间戳

                # 写入共享内存
                raw_data = ctypes.string_at(ctypes.byref(data), ctypes.sizeof(data))
                shm.seek(0)
                shm.write(raw_data)
                shm.flush()

                request_count += 1
                print(f"[C模拟] 发送请求 #{request_count} (state_version={data.state_version})")

                # 发送ready信号量（如果可用）
                if sem_ready is not None:
                    if libc.sem_post(sem_ready) == 0:
                        print(f"[C模拟] 发送ready信号量 #{request_count}")
                    else:
                        print(f"[C模拟] 发送ready信号量失败 #{request_count}")

                # 等待Python响应
                response_timeout = 2.0  # 2秒超时
                response_start = time.time()

                while time.time() - response_start < response_timeout:
                    shm.seek(0)
                    raw_response = shm.read(expected_size)
                    response_data = SharedMemoryData.from_buffer_copy(raw_response)

                    if (response_data.weights_updated == 1 and
                        response_data.ack_version == data.state_version):
                        successful_responses += 1
                        weights = [response_data.weights[i] for i in range(6)]
                        weights_str = ", ".join([f"{w:.3f}" for w in weights])
                        print(f"[C模拟] 收到响应 #{request_count}: [{weights_str}]")

                        # 清除weights_updated标志
                        response_data.weights_updated = 0
                        raw_data = ctypes.string_at(ctypes.byref(response_data), ctypes.sizeof(response_data))
                        shm.seek(0)
                        shm.write(raw_data)
                        shm.flush()
                        break

                    time.sleep(0.01)  # 10ms轮询间隔
                else:
                    print(f"[C模拟] 请求 #{request_count} 超时")

                # 请求间隔
                time.sleep(random.uniform(0.1, 0.5))  # 100-500ms间隔

            except Exception as e:
                print(f"[C模拟] 错误: {e}")
                break

        shm.close()

        # 关闭信号量
        if sem_ready is not None:
            libc.sem_close(sem_ready)
        if sem_ack is not None:
            libc.sem_close(sem_ack)

        print(f"\n[C模拟] 测试完成:")
        print(f"  发送请求: {request_count}")
        print(f"  成功响应: {successful_responses}")
        print(f"  信号量模式: {'启用' if sem_ready is not None else '禁用'}")
        print(f"  响应率: {successful_responses/request_count*100:.1f}%" if request_count > 0 else "  响应率: 0%")

if __name__ == "__main__":
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    simulate_c_requests(duration)
EOF

# 运行C端模拟器
print_info "启动C端模拟器，测试推理服务..."
python3 test_c_simulator.py "$TEST_DURATION"

# 等待一下让推理服务处理完最后的请求
sleep 2

# 检查推理服务状态
if kill -0 "$INFERENCE_PID" 2>/dev/null; then
    print_success "推理服务仍在运行"
else
    print_warning "推理服务已退出"
fi

# 显示推理服务日志的关键信息
print_info "推理服务日志摘要:"
if [ -f "$LOG_FILE" ]; then
    echo "----------------------------------------"

    # 显示启动信息
    grep -E "(LOH推理服务启动|初始化完成|模型加载成功)" "$LOG_FILE" | head -5

    echo ""

    # 显示推理统计
    grep -E "(推理.*seq|已完成.*次推理|推理服务统计)" "$LOG_FILE" | tail -10

    echo ""

    # 显示错误信息
    if grep -q "❌\|ERROR\|失败" "$LOG_FILE"; then
        print_warning "发现错误信息:"
        grep -E "❌|ERROR|失败" "$LOG_FILE" | tail -5
    else
        print_success "未发现错误信息"
    fi

    echo "----------------------------------------"
else
    print_warning "日志文件不存在: $LOG_FILE"
fi

# 清理模拟器文件
rm -f test_c_simulator.py

print_success "推理服务测试完成"
print_info "完整日志请查看: $LOG_FILE"

# 询问是否保留日志文件
echo ""
read -p "是否保留日志文件? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    rm -f "$LOG_FILE"
    print_info "日志文件已删除"
else
    print_info "日志文件已保留: $LOG_FILE"
fi
