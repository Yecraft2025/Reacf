# !/usr/bin/env python3
# coding: utf-8
# @Author: YES123ID
# email: YES123ID@hiyes.top


import os
import smtplib
import ssl
import json
import socket
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, formataddr
from urllib.request import urlopen
import uuid
from collections import defaultdict
import re
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# 对称解密函数
def decrypt_symmetric(key_string: str, encrypted_data_b64: str) -> str:
    """
    解密 Base64 编码的数据。
    """
    try:
        key = base64.b64decode(key_string)
        aesgcm = AESGCM(key)
        combined_data = base64.b64decode(encrypted_data_b64)
        iv = combined_data[:12]
        ciphertext = combined_data[12:]
        decrypted_payload = aesgcm.decrypt(iv, ciphertext, None)
        return decrypted_payload.decode('utf-8')
    except Exception as e:
        log_message(f"[FATAL] 传入数据错误: {e}")
        raise

# 环境变量取值，无值为空
def get_env(name, default=None):
    """辅助函数：从环境变量获取值"""
    return os.getenv(name, default)


# 日志保存路径
def get_log_path():
    """根据 ENABLE_LOG 返回日志路径，None 表示不启用日志"""
    global LOG_PATH
    if LOG_PATH is not None:
        return LOG_PATH

    mode = (get_env("ENABLE_LOG") or "").lower()

    if mode == "one":  # 一个固定文件
        os.makedirs("logs", exist_ok=True)
        LOG_PATH = os.path.join("logs", "email.log")

    elif mode == "date":  # 按日期保存
        os.makedirs("logs", exist_ok=True)
        date_str = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d")
        LOG_PATH = os.path.join("logs", f"{date_str}.log")

    elif mode == "unique":  # 独立文件
        os.makedirs("logs", exist_ok=True)
        date_str = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d_%H-%M-%S")
        unique_id = str(uuid.uuid4())[:8]
        LOG_PATH = os.path.join("logs", f"{date_str}_{unique_id}.log")

    else:
        LOG_PATH = None  # 默认不保存

    return LOG_PATH


# 写入日志
def log_message(msg: str):
    """打印并写入日志（如果启用）"""
    timestamp = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"

    print(line)  # 控制台日志

    log_path = get_log_path()
    if log_path:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


# 检查邮箱格式
def is_valid_email(email: str) -> bool:
    """
    严格验证邮箱格式是否正确
    支持 RFC 5322 常见格式，不允许奇怪字符或非法形式
    """
    if not isinstance(email, str):
        return False

    email = email.strip()
    if not email:
        return False

    # 正则表达式：严格邮箱验证
    pattern = re.compile(
        r"^(?=.{6,254}$)"  # 总长度 6-254
        r"[A-Za-z0-9._%+-]+"  # 本地部分
        r"@"
        r"(?:[A-Za-z0-9-]+\.)+"  # 域名至少一段
        r"[A-Za-z]{2,63}$"  # 顶级域名（2-63）
    )

    return bool(pattern.match(email))


# 根据邮箱推SMTP
def guess_smtp(email):
    """根据邮箱自动猜测 SMTP"""
    # # 如果环境变量里已经提供 SMTP，则优先使用
    # SMTP_SERVER = os.getenv('SMTP_SERVER')
    # SMTP_PORT = os.getenv('SMTP_PORT')
    # SMTP_SSL = os.getenv('SMTP_SSL', 'false').lower() == 'true'
    # if SMTP_SERVER and SMTP_PORT:
    #     try:
    #         return SMTP_SERVER, int(SMTP_PORT), SMTP_SSL
    #     except ValueError:
    #         # 如果 SMTP_PORT 不是有效的数字，则忽略环境变量，继续往下走
    #         pass

    domain = email.split("@")[-1].lower()

    # (server, port, use_ssl) -> True 表示 SSL, False 表示 STARTTLS
    # 常见邮箱默认映射
    SMTP_MAPPING = {
        ("gmail.com", "googlemail.com"): ("smtp.gmail.com", 587, False),
        ("qq.com",): ("smtp.qq.com", 465, True),
        ("163.com",): ("smtp.163.com", 465, True),
        ("126.com",): ("smtp.126.com", 465, True),
        ("sina.com", "sina.cn"): ("smtp.sina.com", 465, True),
        ("outlook.com", "hotmail.com", "live.com", "office365.com", "outlook.office365.com"): (
            "smtp.office365.com", 587, False),
        ("yahoo.com", "yahoo.com.cn"): ("smtp.mail.yahoo.com", 465, True),
        ("icloud.com", "me.com", "mac.com"): ("smtp.mail.me.com", 587, False),
        ("zoho.com",): ("smtp.zoho.com", 465, True),
        ("email.67123.top",): ("smtp.email.67123.top", 587, False),  # 添加自定义的映射关系
        ("mail.67123.top",): ("smtp.mail.67123.top", 587, False)
    }

    for domains, settings in SMTP_MAPPING.items():
        if domain in domains:
            return settings

    # 默认 STARTTLS 587
    return f"smtp.{domain}", 587, False


# 构建SMTP
def build_smtp(email_user, email_pass, smtp_server=None, smtp_port=None, smtp_ssl=None, email_to=None):
    params = {
        "user": None,
        "pass": None,
        "server": None,
        "port": None,
        "ssl": None,
        "to": email_to or None,
    }

    if not email_user or not email_pass:
        return params

    params["user"] = email_user
    params["pass"] = email_pass

    port_ok = smtp_port is not None and str(smtp_port).isdigit()

    ssl_ok = False
    if smtp_ssl is not None:
        if isinstance(smtp_ssl, bool):
            ssl_ok = smtp_ssl
        elif isinstance(smtp_ssl, str):
            ssl_ok = smtp_ssl.strip().lower() == "true"

    if smtp_server and port_ok:
        params["server"] = smtp_server
        params["port"] = int(smtp_port)
        params["ssl"] = ssl_ok
    else:
        guessed_server, guessed_port, guessed_ssl = guess_smtp(email_user)
        params["server"] = guessed_server
        params["port"] = guessed_port
        params["ssl"] = guessed_ssl

    return params


# HTML内容（原）
def load_template():
    """优先读取 index.html，失败则使用内置模板"""
    fallback_html = """
     <!DOCTYPE html>
     <html lang="en">
         <head>
             <meta charset="UTF-8">
             <title>YES123ID - 🔔</title>
         </head>
         <body>
             <h1>tip-YES</h1>
             <p><b>🕒:</b> time-YES</p>
             <p><b>🖥️:</b> system-YES</p>
             <p><b>🌐:</b> gip-YES / sip-YES</p>
             <hr>
             <h2>content-YES</h2>
             <hr>
         </body>
     </html>
    """
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                log_message("⚠️ index.html 文件为空，已切换到内置模板。")
                return fallback_html

            # 健壮性检查：占位符是否完整
            required_keys = ["tip-YES", "time-YES", "system-YES", "gip-YES", "sip-YES", "content-YES"]
            missing_keys = [key for key in required_keys if key not in content]

            if missing_keys:
                log_message(f"⚠️ 模板缺少替换占位符: {', '.join(missing_keys)}")
                return fallback_html

            return content
    except Exception as e:
        log_message(f"❌ 读取 HTML 模板失败: {e}")
        log_message("  ↳ 已切换到内置备用模板。")
        # 返回一个只包含最基础HTML标签的备用模板字符串
        return fallback_html


# 系统ip
def get_ip_addresses():
    sip, gip = '0.0.0.0', '0.0.0.0'
    try:
        hostname = socket.gethostname()
        sip = socket.gethostbyname(hostname)
    except Exception:
        pass
    try:
        gip = urlopen('https://api.ipify.org', timeout=5).read().decode()
    except Exception:
        pass
    return sip, gip


# 系统信息
def get_system_info():
    try:
        if hasattr(os, 'uname'):
            return f"{os.name}, {os.uname().sysname} {os.uname().release}"
        else:
            return os.name
    except Exception:
        return "unknown"


# HTML内容（替）
def build_html(title, message):
    html_body = str(TEMPLATE_CONTENT)  # 留优化空间

    now_beijing_time = datetime.utcnow() + timedelta(hours=8)
    sip, gip = get_ip_addresses()
    system_info = get_system_info()

    html_body = html_body.replace('time-YES', now_beijing_time.strftime('%Y-%m-%d %H:%M:%S'))
    html_body = html_body.replace('tip-YES', title)
    html_body = html_body.replace('gip-YES', gip)
    html_body = html_body.replace('sip-YES', sip)
    html_body = html_body.replace('system-YES', system_info)
    html_body = html_body.replace('content-YES', message)

    return html_body


# ------------------------ 邮件发送 ------------------------
# 发送邮件
def send_email_message(server, email_user, to, subject, plain_message, html_body):
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = formataddr(("📬⏰", email_user))
        msg['To'] = to
        msg['Subject'] = subject
        msg['Date'] = formatdate(localtime=True)

        msg.attach(MIMEText(plain_message, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        server.send_message(msg)
        log_message(f"[SUCCESS] 邮件发送成功: {email_user} -> {to}")
        return True

    except Exception as e:
        log_message(f"[ERROR] 单封邮件发送失败: {email_user} -> {to}. 原因: {e}")
        stats["failed-send"] += 1
        return False


# 批量发送该组邮件
def send_messages(grouped_params):
    successful_sends_by_user = defaultdict(int)

    for (user, password), emails_to_send in grouped_params.items():
        log_message(f"--- [CONNECTING] 正在为用户 '{user}' 建立 SMTP 连接... ---")

        if not emails_to_send:
            continue

        # 从该组的第一封邮件获取 SMTP 配置
        config = emails_to_send[0]
        smtp_server = config.get('server')
        smtp_port = int(config.get('port'))
        use_ssl = config.get('ssl', False)
        connection_timeout = 10

        try:
            server_connection = None
            if use_ssl:
                context = ssl.create_default_context()
                server_connection = smtplib.SMTP_SSL(smtp_server, smtp_port, context=context, timeout=connection_timeout)
            else:
                server_connection = smtplib.SMTP(smtp_server, smtp_port, timeout=connection_timeout)
                server_connection.starttls()
                # 使用建立好的连接
            with server_connection as server:
                server.login(user, password)
                log_message(f"[INFO] 用户 '{user}' 连接并登录成功。")

                # 在此连接上批量发送该用户的所有邮件
                for email_details in emails_to_send:
                    title = email_details.get('title', '')
                    message = email_details.get('message', '')
                    message_body = message
                    html_content = build_html(title, message)

                    success = send_email_message(
                        server=server,
                        email_user=user,
                        to=email_details.get('to'),
                        subject=f"📣：{title}",
                        plain_message=message_body,
                        html_body=html_content  # 传入HTML版本
                    )
                    if success:
                        successful_sends_by_user[user] += 1

        except Exception as e:
            log_message(f"[FATAL ERROR] 无法为用户 '{user}' 建立连接或登录。跳过该用户的所有邮件。原因: {e}")
            stats["failed-send"] += len(emails_to_send)
            continue

        log_message(f"--- [DISCONNECTED] 用户 '{user}' 的邮件处理完毕，连接已关闭。 ---")

    log_message("--- 所有邮件处理完毕 ---")
    stats["success"] = sum(successful_sends_by_user.values())
    return dict(successful_sends_by_user)


# 确定发信账号和 SMTP 信息
def load_and_validate_params():
    email_user_ac = get_env('EMAIL_USER')
    email_pass_ac = get_env('EMAIL_PASS')
    smtp_smtp_ac = get_env('SMTP_SERVER')
    smtp_port_ac = get_env('SMTP_PORT')
    smtp_ssl_ac = get_env('SMTP_SSL')
    email_to_ac = get_env('EMAIL_TO')
    if not is_valid_email(email_user_ac):
        email_user_ac = None
    if not is_valid_email(email_to_ac):
        email_to_ac = None
    ac_params = build_smtp(email_user_ac, email_pass_ac, smtp_smtp_ac, smtp_port_ac, smtp_ssl_ac, email_to_ac)

    cf_payload = os.getenv('MESSAGES', '[]')
    encryption_key = os.getenv('ENCRYPTION_KEY')
    if not cf_payload:
        raise ValueError("⚠️ 环境变量 MESSAGES 为空")
    if not encryption_key:
        raise ValueError("⚠️ 环境变量 ENCRYPTION_KEY 为空")
    try:
        log_message("[INFO] 正在查看传入数据...")
        decrypted_json_string = decrypt_symmetric(encryption_key, cf_payload)
        log_message("[INFO] 数据查看成功。")
        cf_data = json.loads(decrypted_json_string)
        if not isinstance(cf_data, list):
            raise ValueError("messages 不是列表")
        if len(cf_data) == 0:
            raise ValueError("⚠️ 没有传入任何消息")
    except Exception as e:
        raise ValueError(f"❌ 解析 messages 失败: {e}")

    stats["total"] = len(cf_data)
    # 存储有效信息
    valid_cf_data = []

    for item in cf_data:
        # 确保 item 是字典
        if not isinstance(item, dict):
            log_message(f"⚠️ 传入参数不是字典！")
            stats["failed-parameter"] += 1
            continue

        # 校验 title 和 message 字段(量多可优化)
        if 'title' not in item:
            item['title'] = ""
        if 'message' not in item:
            item['message'] = ""

        # 如果没有 title 和 message，去掉该字典并统计无效
        if item['title'] == "" and item['message'] == "":
            log_message(f"⚠️ 缺少必要参数 title 或者 message ！")
            stats["failed-parameter"] += 1
            continue

        # 校验 'to' 字段
        to_addr = item.get("to")

        if not to_addr or not is_valid_email(to_addr):
            mto = ac_params.get("to")
            if mto:
                item["to"] = mto
            else:
                log_message("⚠️ 无有效的收件人！")
                stats["failed-parameter"] += 1
                continue

        if is_valid_email(item.get("user")) and item.get("pass"):
            smtp_data = build_smtp(
                item.get("user"),
                item.get("pass"),
                item.get("server"),
                item.get("port"),
                item.get("ssl"),
                item["to"]
            )
        elif ac_params.get("user") and ac_params.get("pass"):
            smtp_data = {
                "user": ac_params["user"],
                "pass": ac_params["pass"],
                "server": ac_params.get("server"),
                "port": ac_params.get("port"),
                "ssl": ac_params.get("ssl"),
                "to": item["to"],  # 保留 CF 的 to
            }
        else:
            log_message(f"⚠️ 无有效的SMTP！")
            stats["failed-parameter"] += 1
            continue

        if not smtp_data or not smtp_data.get("user") or not smtp_data.get("pass"):
            log_message(f"⚠️ 没有有效的SMTP！")
            stats["failed-parameter"] += 1
            continue

        item.update(smtp_data)
        valid_cf_data.append(item)

    grouped = defaultdict(list)
    for itemsa in valid_cf_data:
        user = itemsa.get("user")
        password = itemsa.get("pass")
        if user and password:  # 使用 (user, password) 元组作为键 的(非必要)
            group_key = (user, password)
            grouped[group_key].append(itemsa)

    return dict(grouped)


# 主函数 & 统计信息
def main():
    grouped_data = load_and_validate_params()
    success_report_counts = send_messages(grouped_data) if grouped_data else stats.update({"success": 0})

    log_message("=" * 33)
    log_message("📊 发送汇总：")
    log_message(f"  总邮件数: {stats['total']}")
    log_message(f"  成功: {stats['success']}")
    if success_report_counts:
        for user, count in success_report_counts.items():
            log_message(f"    - 用户 '{user}': {count} 封")
    log_message(f"  失败: {stats['failed-parameter'] + stats['failed-send']}")
    log_message(f"    - 参数错误:{stats['failed-parameter']}")
    log_message(f"    - 发送错误:{stats['failed-send']}")
    log_message("=" * 33)


# ------------------------ 全局日志路径缓存 ------------------------
stats = {
    "total": 0,
    "success": 0,
    "failed-parameter": 0,
    "failed-send": 0
}
LOG_PATH = None
TEMPLATE_CONTENT = load_template()

# ------------------------ 程序入口 ------------------------
if __name__ == "__main__":
    log_message("")
    try:
        main()
    except Exception as e:
        log_message("⚠️ " + "=" * 33)
        log_message(f"[FATAL] 程序执行失败: {e}")
        log_message("⚠️ " + "=" * 33)
        # raise
