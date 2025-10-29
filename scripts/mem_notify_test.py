#!/bin/bash
import smtplib
from email.mime.text import MIMEText

msg = MIMEText('测试邮件', 'plain', 'utf-8')
msg['Subject'] = '测试'
msg['From'] = '2963281306@qq.com'
msg['To'] = '2963281306@qq.com'

try:
    with smtplib.SMTP_SSL('smtp.qq.com', 465) as server:
        server.login('2963281306@qq.com', 'phmnpnvbqafedgff')
        server.sendmail('2963281306@qq.com', ['2963281306@qq.com'], msg.as_string())
    print("邮件已发送")
except smtplib.SMTPResponseException as e:
    if e.smtp_code == -1:
        print("邮件已发送，但QQ邮箱服务器关闭连接时返回了异常，可忽略。")
    else:
        print("邮件发送失败：", e)
except Exception as e:
    print("发生其他错误：", e)
