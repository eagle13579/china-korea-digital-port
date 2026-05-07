"""
邮件通知服务
- 新线索通知销售
- 报价发送给客户
- 支付成功通知
使用 smtplib + email 标准库，SMTP配置从环境变量读取。
如果SMTP未配置，静默跳过不报错（开发模式兼容）。
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)

# SMTP配置
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)

# 销售通知邮箱（默认发送到SMTP_FROM自己）
SALES_EMAIL = os.environ.get("SALES_EMAIL", SMTP_FROM)


def is_smtp_configured() -> bool:
    """检查SMTP是否已配置"""
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASS)


def _send_email(to_email: str, subject: str, html_content: str) -> bool:
    """
    发送邮件核心函数
    如果SMTP未配置，静默跳过并返回False
    """
    if not is_smtp_configured():
        logger.debug(f"SMTP未配置，跳过邮件发送: {subject} -> {to_email}")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_FROM
        msg["To"] = to_email
        msg["Subject"] = subject

        # HTML内容
        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)

        # 连接SMTP并发送
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

        logger.info(f"邮件发送成功: {subject} -> {to_email}")
        return True
    except Exception as e:
        logger.warning(f"邮件发送失败: {subject} -> {to_email}, 错误: {e}")
        return False


def _get_base_html(content_body: str) -> str:
    """获取基础HTML模板"""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 0; }}
.container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
.header {{ background: linear-gradient(135deg, #8B5CF6, #06B6D4); color: white; padding: 30px; text-align: center; border-radius: 12px 12px 0 0; }}
.header h1 {{ margin: 0; font-size: 24px; }}
.content {{ background: white; padding: 30px; border-radius: 0 0 12px 12px; color: #333; line-height: 1.6; }}
.footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
</style></head>
<body>
<div class="container">
<div class="header"><h1>中韩出海数智港</h1><p style="opacity:0.9;margin:5px 0 0">China-Korea Digital Port</p></div>
<div class="content">{content_body}</div>
<div class="footer">© 2026 中韩出海数智港 · 沪ICP备2026007459号</div>
</div>
</body>
</html>"""


def send_new_lead_notification(lead_info: dict) -> bool:
    """
    新线索通知销售
    当有新的 contact / demo / pricing 提交时调用
    """
    source = lead_info.get("_label", lead_info.get("source", "未知来源"))
    name = lead_info.get("name", "")
    company = lead_info.get("company", "")
    email = lead_info.get("email", "")
    phone = lead_info.get("phone", "")
    message = lead_info.get("message", lead_info.get("notes", ""))

    subject = f"[新线索] {source} - {name} ({company or '未填写公司'})"

    content = f"""
    <h2 style="color:#8B5CF6;margin-top:0">🆕 新线索通知</h2>
    <table style="width:100%;border-collapse:collapse">
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666;width:80px">来源</td><td style="padding:8px;border-bottom:1px solid #eee"><strong>{source}</strong></td></tr>
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">联系人</td><td style="padding:8px;border-bottom:1px solid #eee"><strong>{name}</strong></td></tr>
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">公司</td><td style="padding:8px;border-bottom:1px solid #eee">{company or '-'}</td></tr>
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">邮箱</td><td style="padding:8px;border-bottom:1px solid #eee">{email}</td></tr>
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">电话</td><td style="padding:8px;border-bottom:1px solid #eee">{phone or '-'}</td></tr>
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">留言</td><td style="padding:8px;border-bottom:1px solid #eee">{message or '-'}</td></tr>
    </table>
    <p style="margin-top:20px"><a href="https://go-aiport.com/admin" style="display:inline-block;background:#8B5CF6;color:white;padding:10px 24px;border-radius:8px;text-decoration:none">前往后台处理 →</a></p>
    """

    return _send_email(SALES_EMAIL, subject, _get_base_html(content))


def send_quote_to_customer(customer_email: str, customer_name: str, quote_info: dict) -> bool:
    """
    报价发送给客户
    quote_info = {
        "company": 客户公司,
        "plan_name": 方案名称,
        "price": 价格,
        "quote_no": 报价编号,
        "items": [{"name": ..., "price": ...}, ...]
    }
    """
    company = quote_info.get("company", "")
    plan_name = quote_info.get("plan_name", "")
    price = quote_info.get("price", 0)
    quote_no = quote_info.get("quote_no", "")
    items = quote_info.get("items", [])

    subject = f"中韩出海数智港 - 报价单 #{quote_no}"

    items_html = ""
    for item in items:
        items_html += f"""
        <tr><td style="padding:8px;border-bottom:1px solid #eee">{item.get('name', '')}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;text-align:right">¥{float(item.get('price', 0)):,.2f}</td></tr>
        """

    content = f"""
    <h2 style="color:#8B5CF6;margin-top:0">📄 报价单</h2>
    <p>尊敬的 {customer_name} 您好，</p>
    <p>感谢您对中韩出海数智港的关注！根据您的需求，我们为您提供以下报价方案：</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0">
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">报价编号</td><td style="padding:8px;border-bottom:1px solid #eee"><strong>#{quote_no}</strong></td></tr>
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">公司</td><td style="padding:8px;border-bottom:1px solid #eee">{company or '-'}</td></tr>
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">方案</td><td style="padding:8px;border-bottom:1px solid #eee"><strong>{plan_name}</strong></td></tr>
    </table>
    <table style="width:100%;border-collapse:collapse;margin:16px 0">
        <tr><th style="padding:8px;border-bottom:2px solid #8B5CF6;text-align:left">项目</th>
            <th style="padding:8px;border-bottom:2px solid #8B5CF6;text-align:right">金额</th></tr>
        {items_html}
        <tr><td style="padding:12px 8px;border-top:2px solid #333;font-weight:bold">合计</td>
            <td style="padding:12px 8px;border-top:2px solid #333;font-weight:bold;text-align:right;font-size:18px;color:#8B5CF6">¥{price:,.2f}</td></tr>
    </table>
    <p>如您有任何疑问，请随时回复此邮件或致电我们的销售团队。期待与您的合作！</p>
    <p style="margin-top:20px">此致，<br>中韩出海数智港 团队</p>
    """

    return _send_email(customer_email, subject, _get_base_html(content))


def send_payment_success_notification(order_info: dict) -> bool:
    """
    支付成功通知客户
    order_info = {
        "user_name": 客户姓名,
        "user_email": 客户邮箱,
        "user_company": 客户公司,
        "order_no": 订单号,
        "plan_type": 套餐类型,
        "price": 金额,
        "license_key": License Key
    }
    """
    user_name = order_info.get("user_name", "")
    user_email = order_info.get("user_email", "")
    company = order_info.get("user_company", "")
    order_no = order_info.get("order_no", "")
    plan_type = order_info.get("plan_type", "")
    price = order_info.get("price", 0)
    license_key = order_info.get("license_key", "")

    subject = f"支付成功 - 中韩出海数智港 #{order_no}"

    content = f"""
    <h2 style="color:#8B5CF6;margin-top:0">✅ 支付成功确认</h2>
    <p>尊敬的 {user_name} 您好，</p>
    <p>您的订单已成功支付！以下是您的订单详情：</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0">
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">订单号</td><td style="padding:8px;border-bottom:1px solid #eee"><strong>{order_no}</strong></td></tr>
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">公司</td><td style="padding:8px;border-bottom:1px solid #eee">{company or '-'}</td></tr>
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">方案</td><td style="padding:8px;border-bottom:1px solid #eee"><strong>{plan_type}</strong></td></tr>
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">金额</td><td style="padding:8px;border-bottom:1px solid #eee"><strong style="font-size:18px;color:#8B5CF6">¥{price:,.2f}</strong></td></tr>
    </table>
    """

    if license_key:
        content += f"""
    <div style="background:#f3f0ff;border:2px dashed #8B5CF6;border-radius:12px;padding:20px;margin:20px 0;text-align:center">
        <p style="color:#666;margin:0 0 8px;font-size:14px">您的授权密钥</p>
        <p style="font-family:'Courier New',monospace;font-size:18px;font-weight:bold;color:#8B5CF6;margin:0;letter-spacing:1px">{license_key}</p>
    </div>
    <p style="font-size:14px;color:#999">请妥善保管此密钥，用于激活您的中韩出海数智港服务。</p>
    """

    content += """
    <p>立即登录平台，开启您的跨境之旅！</p>
    <p><a href="https://go-aiport.com" style="display:inline-block;background:#8B5CF6;color:white;padding:10px 24px;border-radius:8px;text-decoration:none">进入平台 →</a></p>
    <p style="margin-top:20px">如有任何问题，请随时联系我们。<br>中韩出海数智港 团队</p>
    """

    return _send_email(user_email, subject, _get_base_html(content))


def send_payment_notification_to_sales(order_info: dict) -> bool:
    """
    支付成功通知销售团队
    """
    user_name = order_info.get("user_name", "")
    user_email = order_info.get("user_email", "")
    company = order_info.get("user_company", "")
    order_no = order_info.get("order_no", "")
    plan_type = order_info.get("plan_type", "")
    price = order_info.get("price", 0)
    license_key = order_info.get("license_key", "")

    subject = f"[支付成功] {company or user_name} - {plan_type} ¥{price:,.0f}"

    content = f"""
    <h2 style="color:#8B5CF6;margin-top:0">💰 支付成功通知</h2>
    <table style="width:100%;border-collapse:collapse">
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">订单号</td><td style="padding:8px;border-bottom:1px solid #eee"><strong>{order_no}</strong></td></tr>
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">客户</td><td style="padding:8px;border-bottom:1px solid #eee"><strong>{user_name}</strong></td></tr>
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">公司</td><td style="padding:8px;border-bottom:1px solid #eee">{company or '-'}</td></tr>
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">邮箱</td><td style="padding:8px;border-bottom:1px solid #eee">{user_email}</td></tr>
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">方案</td><td style="padding:8px;border-bottom:1px solid #eee">{plan_type}</td></tr>
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">金额</td><td style="padding:8px;border-bottom:1px solid #eee"><strong style="font-size:18px;color:#8B5CF6">¥{price:,.2f}</strong></td></tr>
        <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666">License</td><td style="padding:8px;border-bottom:1px solid #eee;font-family:monospace">{license_key or '-'}</td></tr>
    </table>
    <p style="margin-top:20px"><a href="https://go-aiport.com/admin" style="display:inline-block;background:#8B5CF6;color:white;padding:10px 24px;border-radius:8px;text-decoration:none">前往后台查看 →</a></p>
    """

    return _send_email(SALES_EMAIL, subject, _get_base_html(content))
