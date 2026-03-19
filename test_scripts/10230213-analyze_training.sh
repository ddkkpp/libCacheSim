#!/bin/bash
# 快速分析LOH RL训练日志的脚本

if [ $# -lt 2 ]; then
    echo "Usage: $0 <python_log> <cachesim_log>"
    echo "Example: $0 logs/ac_sb3_1023_143000.log logs/cachesim_sb3_1023_143000.log"
    exit 1
fi

PYTHON_LOG="$1"
CACHESIM_LOG="$2"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}    LOH RL Training Analysis Report${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo

# 1. 采样统计
echo -e "${YELLOW}[1] 采样机制检查${NC}"
SAMPLE_DEBUG_COUNT=$(grep -c "SAMPLE DEBUG" "$PYTHON_LOG" 2>/dev/null | head -1 | tr -d '\n' || echo "0")
if [ "$SAMPLE_DEBUG_COUNT" -gt 0 ] 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} 采样调试信息: $SAMPLE_DEBUG_COUNT 条"

    # 检查是否有unsafe zone警告
    UNSAFE_COUNT=$(grep -c "WARNING: Sampled from unsafe zone" "$PYTHON_LOG" 2>/dev/null | head -1 | tr -d '\n' || echo "0")
    if [ "$UNSAFE_COUNT" -gt 0 ] 2>/dev/null; then
        echo -e "  ${RED}✗${NC} 检测到 $UNSAFE_COUNT 次不安全采样！"
    else
        echo -e "  ${GREEN}✓${NC} 无不安全采样"
    fi

    # 显示最后一次采样信息
    echo -e "\n  最后一次采样状态:"
    grep "SAMPLE DEBUG" "$PYTHON_LOG" | tail -1 | sed 's/^/    /'
    grep -A 7 "SAMPLE DEBUG" "$PYTHON_LOG" | tail -7 | sed 's/^/    /'
else
    echo -e "  ${RED}✗${NC} 未找到采样调试信息（可能LOH_DEBUG未启用）"
fi
echo

# 2. 惩罚修正统计
echo -e "${YELLOW}[2] 惩罚修正统计${NC}"
CORRECTION_COUNT=$(grep -c "RETROSPECTIVE.*reward corrected" "$PYTHON_LOG" 2>/dev/null | head -1 | tr -d '\n' || echo "0")
if [ "$CORRECTION_COUNT" -gt 0 ] 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} 奖励修正次数: $CORRECTION_COUNT"

    # 提取Correction stats
    LAST_STATS=$(grep "Correction stats:" "$PYTHON_LOG" | tail -1)
    if [ -n "$LAST_STATS" ]; then
        echo -e "  ${GREEN}✓${NC} $LAST_STATS"
    fi

    # 显示几个修正样例
    echo -e "\n  修正样例 (最后3次):"
    grep -B 1 -A 4 "RETROSPECTIVE.*reward corrected" "$PYTHON_LOG" | tail -18 | sed 's/^/    /'
else
    echo -e "  ${RED}✗${NC} 未检测到惩罚修正！"
    echo -e "     可能原因："
    echo -e "     1. Ghost cache miss未发生（缓存太大或测试时间短）"
    echo -e "     2. 惩罚队列问题"
    echo -e "     3. 版本号映射失败"
fi
echo

# 3. Ghost cache miss检查
echo -e "${YELLOW}[3] Ghost Cache Miss 统计${NC}"
GHOST_MISS_COUNT=$(grep -c "Ghost cache miss" "$CACHESIM_LOG" 2>/dev/null | head -1 | tr -d '\n' || echo "0")
PENALTY_ENQUEUE_COUNT=$(grep -c "enqueue_penalty" "$CACHESIM_LOG" 2>/dev/null | head -1 | tr -d '\n' || echo "0")

echo -e "  Ghost cache miss次数: $GHOST_MISS_COUNT"
echo -e "  惩罚入队次数: $PENALTY_ENQUEUE_COUNT"

if [ "$GHOST_MISS_COUNT" -eq 0 ] 2>/dev/null; then
    echo -e "  ${YELLOW}⚠${NC}  未检测到Ghost cache miss"
    echo -e "     建议: 减小cache_size（如0.05）或增加测试请求数"
elif [ "$PENALTY_ENQUEUE_COUNT" -lt "$GHOST_MISS_COUNT" ] 2>/dev/null; then
    echo -e "  ${YELLOW}⚠${NC}  惩罚入队少于miss次数（可能队列溢出）"
else
    echo -e "  ${GREEN}✓${NC} Ghost cache工作正常"
fi
echo

# 4. 训练收敛分析
echo -e "${YELLOW}[4] 训练收敛分析${NC}"
TRAINING_COUNT=$(grep -c "rollout/ep_rew_mean" "$PYTHON_LOG" 2>/dev/null | head -1 | tr -d '\n' || echo "0")
if [ "$TRAINING_COUNT" -gt 0 ] 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} 训练更新次数: $TRAINING_COUNT"

    # 提取奖励趋势
    echo -e "\n  奖励趋势 (最后10次):"
    grep "rollout/ep_rew_mean" "$PYTHON_LOG" | tail -10 | awk '{print "    " $0}'

    # 简单判断是否收敛
    FIRST_REWARD=$(grep "rollout/ep_rew_mean" "$PYTHON_LOG" | head -1 | awk '{print $NF}')
    LAST_REWARD=$(grep "rollout/ep_rew_mean" "$PYTHON_LOG" | tail -1 | awk '{print $NF}')

    if [ -n "$FIRST_REWARD" ] && [ -n "$LAST_REWARD" ]; then
        IMPROVEMENT=$(echo "$LAST_REWARD - $FIRST_REWARD" | bc -l 2>/dev/null || echo "N/A")
        echo -e "\n  首次奖励: $FIRST_REWARD"
        echo -e "  最终奖励: $LAST_REWARD"
        echo -e "  提升幅度: $IMPROVEMENT"
    fi
else
    echo -e "  ${RED}✗${NC} 未检测到训练更新（SB3未启动训练）"
fi
echo

# 5. C++/Python通信检查
echo -e "${YELLOW}[5] C++/Python通信检查${NC}"
SEND_COUNT=$(grep -c "Sending RL request" "$CACHESIM_LOG" 2>/dev/null | head -1 | tr -d '\n' || echo "0")
RECV_COUNT=$(grep -c "Updated weights from Actor-Critic" "$CACHESIM_LOG" 2>/dev/null | head -1 | tr -d '\n' || echo "0")

echo -e "  C++ 发送性能指标: $SEND_COUNT 次"
echo -e "  C++ 接收权重更新: $RECV_COUNT 次"

DIFF=$((SEND_COUNT - RECV_COUNT)) 2>/dev/null || DIFF=0
if [ "$DIFF" -le 2 ] 2>/dev/null && [ "$DIFF" -ge -2 ] 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} 通信正常（差值: $DIFF）"
else
    echo -e "  ${YELLOW}⚠${NC}  通信可能有问题（差值: $DIFF）"
fi
echo

# 6. 错误检查
echo -e "${YELLOW}[6] 错误检查${NC}"
PYTHON_ERRORS=$(grep -c -E "(^Error|Exception|Failed|Fatal)" "$PYTHON_LOG" 2>/dev/null | head -1 | tr -d '\n' || echo "0")
C_ERRORS=$(grep -c -E "(^Error|FATAL|Segmentation)" "$CACHESIM_LOG" 2>/dev/null | head -1 | tr -d '\n' || echo "0")

if [ "$PYTHON_ERRORS" -eq 0 ] 2>/dev/null && [ "$C_ERRORS" -eq 0 ] 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} 未检测到错误"
else
    echo -e "  ${RED}✗${NC} Python错误: $PYTHON_ERRORS, C++错误: $C_ERRORS"
    if [ "$PYTHON_ERRORS" -gt 0 ] 2>/dev/null; then
        echo -e "\n  Python错误摘要:"
        grep -n -E "(^Error|Exception|Failed|Fatal)" "$PYTHON_LOG" | head -5 | sed 's/^/    /'
    fi
fi
echo

# 7. 总结与建议
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}[7] 总结与建议${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

SCORE=0
MAX_SCORE=5

# 评分（添加错误处理）
[ "${UNSAFE_COUNT:-0}" -eq 0 ] 2>/dev/null && ((SCORE++))
[ "${CORRECTION_COUNT:-0}" -gt 0 ] 2>/dev/null && ((SCORE++))
[ "${GHOST_MISS_COUNT:-0}" -gt 0 ] 2>/dev/null && ((SCORE++))
[ "${TRAINING_COUNT:-0}" -gt 10 ] 2>/dev/null && ((SCORE++))
[ "${PYTHON_ERRORS:-0}" -eq 0 ] 2>/dev/null && [ "${C_ERRORS:-0}" -eq 0 ] 2>/dev/null && ((SCORE++))

if [ "$SCORE" -eq "$MAX_SCORE" ]; then
    echo -e "${GREEN}✓ 测试完全成功！ ($SCORE/$MAX_SCORE)${NC}"
    echo
    echo "所有核心功能工作正常："
    echo "  ✓ 采样机制正确"
    echo "  ✓ 惩罚修正生效"
    echo "  ✓ Ghost cache工作"
    echo "  ✓ 训练正常进行"
    echo "  ✓ 无错误发生"
    echo
    echo "下一步建议："
    echo "  1. 运行完整测试（所有请求）"
    echo "  2. 使用 tensorboard --logdir ./runs 可视化"
    echo "  3. 对比不同参数配置的性能"
elif [ "$SCORE" -ge 3 ]; then
    echo -e "${YELLOW}⚠ 测试部分成功 ($SCORE/$MAX_SCORE)${NC}"
    echo
    echo "需要检查的问题:"
    [ "${UNSAFE_COUNT:-0}" -gt 0 ] 2>/dev/null && echo "  ✗ 采样机制有unsafe zone警告"
    [ "${CORRECTION_COUNT:-0}" -eq 0 ] 2>/dev/null && echo "  ✗ 惩罚修正未生效"
    [ "${GHOST_MISS_COUNT:-0}" -eq 0 ] 2>/dev/null && echo "  ✗ Ghost cache miss未发生"
    [ "${TRAINING_COUNT:-0}" -le 10 ] 2>/dev/null && echo "  ✗ 训练次数太少"
    [ "${PYTHON_ERRORS:-0}" -gt 0 ] 2>/dev/null || [ "${C_ERRORS:-0}" -gt 0 ] 2>/dev/null && echo "  ✗ 检测到错误"
    echo
    echo "调参建议："
    echo "  1. 检查上述问题的具体原因"
    echo "  2. 参考 20251023-TUNING_GUIDE.md 进行调整"
else
    echo -e "${RED}✗ 测试失败 ($SCORE/$MAX_SCORE)${NC}"
    echo
    echo "严重问题："
    [ "${UNSAFE_COUNT:-0}" -gt 0 ] 2>/dev/null && echo "  ✗ 采样机制有严重错误"
    [ "${CORRECTION_COUNT:-0}" -eq 0 ] 2>/dev/null && echo "  ✗ 惩罚修正完全失效"
    [ "${GHOST_MISS_COUNT:-0}" -eq 0 ] 2>/dev/null && echo "  ✗ Ghost cache未工作"
    [ "${TRAINING_COUNT:-0}" -eq 0 ] 2>/dev/null && echo "  ✗ 训练未启动"
    [ "${PYTHON_ERRORS:-0}" -gt 0 ] 2>/dev/null || [ "${C_ERRORS:-0}" -gt 0 ] 2>/dev/null && echo "  ✗ 存在错误"
    echo
    echo "紧急建议："
    echo "  1. 检查日志中的ERROR和Exception"
    echo "  2. 确认共享内存和信号量工作正常"
    echo "  3. 重新编译并测试基础功能"
fi

echo
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo "完整日志："
echo "  Python: $PYTHON_LOG"
echo "  C++:    $CACHESIM_LOG"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
