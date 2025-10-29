#!/usr/bin/env python3
import psutil
import smtplib
import time
from email.mime.text import MIMEText
from email.header import Header

# ==================== 1. 修改这里的配置 ====================

# --- 邮件配置 (请根据您的邮箱服务商修改) ---
# SMTP 服务器地址，例如：
# - QQ邮箱: smtp.qq.com
# - 163邮箱: smtp.163.com
# - Gmail: smtp.gmail.com
SMTP_HOST = 'smtp.qq.com'  # <-- 修改成您的 SMTP 服务器

# SMTP 服务器端口，通常是 465 (使用SSL加密)
SMTP_PORT = 465  # <-- 通常保持 465 即可

# 您的邮箱地址 (用来发送邮件的邮箱)
SENDER_EMAIL = '2963281306@qq.com'  # <-- 修改成您的邮箱

# 您的邮箱“授权码”，而不是登录密码！
# (需要登录邮箱网页版，在“设置”->“账户”中开启SMTP服务并生成授权码)
SENDER_PASSWORD = 'phmnpnvbqafedgff'  # <-- 修改成您的邮箱授权码

# 接收告警邮件的地址
RECIPIENT_EMAIL = '2963281306@qq.com'  # <-- 修改成接收邮件的邮箱

# --- 监控配置 ---
# 内存使用率阈值 (%)
MEMORY_THRESHOLD = 90.0

# 检查间隔 (秒)
CHECK_INTERVAL = 60  # 每 60 秒检查一次

# ==================== 2. 下面的代码通常无需修改 ====================

def get_memory_usage():
    """获取当前内存使用率"""
    memory = psutil.virtual_memory()
    return memory.percent

def send_alert_email(usage):
    """发送告警邮件"""
    subject = f'内存监控提醒'
    body = (
        f'您好，\n\n'
        f'当前服务器内存使用率为 {usage:.2f}% ，已超过设定阈值 {MEMORY_THRESHOLD}% 。\n\n'
        f'请关注服务器运行状态。\n\n'
        f'-- 服务器监控通知'
    )

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = subject

    try:
        # 使用 SSL 连接 SMTP 服务器
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, [RECIPIENT_EMAIL], msg.as_string())
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 告警邮件已成功发送至 {RECIPIENT_EMAIL}")
    except smtplib.SMTPResponseException as e:
        if getattr(e, 'smtp_code', None) == -1:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 邮件已发送，但QQ邮箱服务器关闭连接时返回了异常，可忽略。")
        else:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 邮件发送失败: {e}")
    except smtplib.SMTPException as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 邮件发送失败: {e}")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 发生未知错误: {e}")

def main():
    """主监控循环"""
    print("内存监控脚本已启动...")
    print(f"监控阈值: {MEMORY_THRESHOLD}%")
    print(f"检查间隔: {CHECK_INTERVAL} 秒")

    alert_sent_recently = False # 增加一个标志位，避免短时间内重复发送

    while True:
        current_usage = get_memory_usage()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 当前内存使用率: {current_usage:.2f}%")

        if current_usage > MEMORY_THRESHOLD:
            if not alert_sent_recently:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 警告！内存使用率 ({current_usage:.2f}%) 超过阈值 ({MEMORY_THRESHOLD}%)。")
                send_alert_email(current_usage)
                alert_sent_recently = True # 标记为已发送
            else:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 内存持续过高，但告警邮件已于近期发送，本次不再重复发送。")
        else:
            # 如果内存使用率恢复正常，重置标志位
            if alert_sent_recently:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 内存使用率已恢复正常。")
                alert_sent_recently = False

        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
