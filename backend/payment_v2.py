"""
中韩出海数智港 - 支付系统V2（SaaS月付版）
支付宝当面付模拟 + 微信Native Pay模拟 + 订单状态机

状态机: pending → paid → expired → refunded
       pending → expired
       paid → refunded
       paid → expired (subscription expired)

V2版本与V1共存：
  - V1: 一次性付款（凭证上传审核模式），用于深度方案、源码授权
  - V2: SaaS月付/年付模式（自动支付模拟），用于基础版/专业版/企业版

API前缀: /api/v2/payment/*
"""

import json
import os
import uuid
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Header, Request
from backend.database import get_db, DB_PATH

router = APIRouter(tags=["payment_v2"])

# ── SaaS套餐定价 ────────────────────────────────────────

SAAS_PLANS = {
    "basic": {
        "name": "基础版",
        "name_ko": "베이직",
        "monthly_price": 4900.00,
        "yearly_price": 4900.00 * 12 * 0.8,  # 年付享8折 = 47,040
        "ai_officers": 1,
        "compliance_checks": 5,
        "features": [
            "1位AI合规官",
            "5次/月合规诊断",
            "基础合规报告",
            "邮件支持",
        ],
        "features_ko": [
            "AI 규제 전문가 1명",
            "월 5회 규제 진단",
            "기본 규제 보고서",
            "이메일 지원",
        ],
    },
    "professional": {
        "name": "专业版",
        "name_ko": "프로페셔널",
        "monthly_price": 9900.00,
        "yearly_price": 9900.00 * 12 * 0.8,  # 年付享8折 = 95,040
        "ai_officers": 6,
        "compliance_checks": -1,  # -1 表示不限次数
        "features": [
            "6位AI合规官全开",
            "不限次数合规诊断",
            "完整合规报告",
            "优先技术支持",
            "实时市场情报",
        ],
        "features_ko": [
            "AI 규제 전문가 6명 전원 활성화",
            "무제한 규제 진단",
            "전체 규제 보고서",
            "우선 기술 지원",
            "실시간 시장 정보",
        ],
    },
    "enterprise": {
        "name": "企业版",
        "name_ko": "엔터프라이즈",
        "monthly_price": 29900.00,
        "yearly_price": 29900.00 * 12 * 0.8,  # 年付享8折 = 287,040
        "ai_officers": -1,  # -1 表示不限
        "compliance_checks": -1,
        "features": [
            "API接入",
            "专属知识库",
            "定制合规方案",
            "7×24小时技术支持",
            "专属客户经理",
            "季度战略复盘",
        ],
        "features_ko": [
            "API 연동",
            "전용 지식 베이스",
            "맞춤형 규제 솔루션",
            "24/7 기술 지원",
            "전담 고객 매니저",
            "분기별 전략 검토",
        ],
    },
}


# ── 辅助函数 ──────────────────────────────────────────

def _generate_order_no(prefix: str = "SAAS") -> str:
    """生成订单号：SAAS + 日期 + 随机码"""
    date_str = datetime.now().strftime("%Y%m%d")
    rand_str = uuid.uuid4().hex[:8].upper()
    return f"{prefix}{date_str}{rand_str}"


def _generate_transaction_id() -> str:
    """生成交易流水号"""
    date_str = datetime.now().strftime("%Y%m%d%H%M%S")
    rand_str = uuid.uuid4().hex[:6].upper()
    return f"TXN{date_str}{rand_str}"


def _mock_alipay_qrcode(order_no: str, amount: float, subject: str) -> str:
    """
    [模拟] 支付宝当面付二维码生成
    真实场景：调用 alipay.trade.precreate → 获取 qr_code
    模拟场景：返回一个带订单信息的二维码图片URL
    """
    qr_data = (
        f"alipay://alipay/trade/precreate?"
        f"out_trade_no={order_no}&"
        f"total_amount={amount:.2f}&"
        f"subject={subject}&"
        f"timestamp={int(time.time())}"
    )
    # 使用在线QR生成服务模拟二维码图片
    import urllib.parse
    encoded = urllib.parse.quote(qr_data)
    return f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded}&bgcolor=1677ff"


def _mock_wechat_qrcode(order_no: str, amount: float, description: str) -> str:
    """
    [模拟] 微信Native Pay二维码生成
    真实场景：调用 jsapi/unifiedorder → 获取 code_url
    模拟场景：返回一个带订单信息的二维码图片URL
    """
    qr_data = (
        f"weixin://wxpay/bizpayurl?"
        f"pr={order_no}&"
        f"total_fee={int(amount * 100)}&"
        f"description={description}&"
        f"timestamp={int(time.time())}"
    )
    import urllib.parse
    encoded = urllib.parse.quote(qr_data)
    return f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded}&bgcolor=07c160"


def _mock_verify_signature(method: str, data: dict) -> bool:
    """
    [模拟] 支付回调签名验证
    真实场景：验证支付宝/微信的异步通知签名
    模拟场景：总是返回True
    """
    return True


# ── 数据库初始化（建表） ──────────────────────────────

def init_payment_v2_tables():
    """初始化支付V2相关的数据库表"""
    conn = get_db()
    cursor = conn.cursor()

    # SaaS订阅表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saas_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_no TEXT UNIQUE NOT NULL,
            user_company TEXT NOT NULL,
            user_name TEXT NOT NULL,
            user_phone TEXT,
            user_email TEXT NOT NULL,
            plan_type TEXT NOT NULL CHECK(plan_type IN ('basic','professional','enterprise')),
            billing_cycle TEXT NOT NULL CHECK(billing_cycle IN ('monthly','yearly')),
            price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','active','expired','cancelled','refunded')),
            current_period_start TIMESTAMP,
            current_period_end TIMESTAMP,
            cancelled_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)

    # 支付交易表（V2）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_no TEXT UNIQUE NOT NULL,
            subscription_id INTEGER,
            order_no TEXT,
            amount REAL NOT NULL,
            channel TEXT NOT NULL CHECK(channel IN ('alipay','wechat','transfer')),
            channel_trade_no TEXT,
            qr_code TEXT,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','paid','failed','refunded')),
            paid_at TIMESTAMP,
            refunded_at TIMESTAMP,
            notify_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (subscription_id) REFERENCES saas_subscriptions(id)
        )
    """)

    # 迁移兼容：为已有表添加列（如果不存在）
    cursor.execute("PRAGMA table_info(saas_subscriptions)")
    cols = [r[1] for r in cursor.fetchall()]
    for col, col_type in [
        ('refund_reason', 'TEXT'),
        ('refunded_at', 'TIMESTAMP'),
    ]:
        if col not in cols:
            try:
                cursor.execute(f"ALTER TABLE saas_subscriptions ADD COLUMN {col} {col_type}")
            except Exception:
                pass

    cursor.execute("PRAGMA table_info(payment_transactions)")
    txn_cols = [r[1] for r in cursor.fetchall()]
    for col, col_type in [
        ('refund_reason', 'TEXT'),
        ('fail_reason', 'TEXT'),
    ]:
        if col not in txn_cols:
            try:
                cursor.execute(f"ALTER TABLE payment_transactions ADD COLUMN {col} {col_type}")
            except Exception:
                pass

    conn.commit()
    conn.close()


# ════════════════════════════════════════════════════════════
# API端点
# ════════════════════════════════════════════════════════════

@router.get("/api/v2/payment/plans")
async def get_saas_plans():
    """获取SaaS套餐列表"""
    return {
        "success": True,
        "data": SAAS_PLANS,
        "message": "年付享8折优惠",
    }


# ── 订阅创建 ──────────────────────────────────────────

@router.post("/api/v2/payment/subscription/create")
async def create_subscription(body: dict):
    """
    创建SaaS订阅订单

    请求体:
    {
        "user_company": "企业名称",
        "user_name": "联系人",
        "user_phone": "电话",
        "user_email": "邮箱",
        "plan_type": "basic|professional|enterprise",
        "billing_cycle": "monthly|yearly"
    }
    """
    user_company = body.get("user_company", "").strip()
    user_name = body.get("user_name", "").strip()
    user_phone = body.get("user_phone", "").strip()
    user_email = body.get("user_email", "").strip()
    plan_type = body.get("plan_type", "").strip()
    billing_cycle = body.get("billing_cycle", "monthly").strip()

    # 校验必填字段
    if not user_company:
        raise HTTPException(status_code=400, detail="企业名称不能为空")
    if not user_name:
        raise HTTPException(status_code=400, detail="联系人不能为空")
    if not user_email:
        raise HTTPException(status_code=400, detail="邮箱不能为空")

    # 校验套餐类型
    if plan_type not in SAAS_PLANS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的套餐类型: {plan_type}，支持: {', '.join(SAAS_PLANS.keys())}",
        )

    # 校验计费周期
    if billing_cycle not in ("monthly", "yearly"):
        raise HTTPException(
            status_code=400,
            detail="计费周期仅支持: monthly 或 yearly",
        )

    plan = SAAS_PLANS[plan_type]
    price = plan["yearly_price"] if billing_cycle == "yearly" else plan["monthly_price"]

    subscription_no = _generate_order_no("SUB")
    period_days = 365 if billing_cycle == "yearly" else 30
    period_start = datetime.now()
    period_end = period_start + timedelta(days=period_days)

    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO saas_subscriptions
               (subscription_no, user_company, user_name, user_phone, user_email,
                plan_type, billing_cycle, price, status,
                current_period_start, current_period_end)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
            (subscription_no, user_company, user_name, user_phone,
             user_email, plan_type, billing_cycle, price,
             period_start.isoformat(), period_end.isoformat()),
        )
        conn.commit()
        sub_id = cursor.lastrowid

        return {
            "success": True,
            "data": {
                "subscription_id": sub_id,
                "subscription_no": subscription_no,
                "plan_type": plan_type,
                "plan_name": plan["name"],
                "billing_cycle": billing_cycle,
                "price": round(price, 2),
                "price_display": f"¥{price:,.0f}",
                "status": "pending",
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "is_yearly_discount": billing_cycle == "yearly",
            },
            "message": f"订阅创建成功，订阅号: {subscription_no}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建订阅失败: {str(e)}")
    finally:
        conn.close()


# ── 支付宝当面付（模拟） ──────────────────────────────

@router.post("/api/v2/payment/alipay/precreate")
async def alipay_precreate(body: dict):
    """
    [模拟] 支付宝当面付 - 预创建支付订单

    请求体:
    {
        "subscription_id": 1,
        "return_url": "https://..."  // 支付成功后跳转地址（可选）
    }

    响应:
    {
        "success": true,
        "qr_code": "https://...",
        "out_trade_no": "SAAS20260512XXXXXXXX",
        "total_amount": "4900.00",
        "transaction_id": 1
    }
    """
    subscription_id = body.get("subscription_id")
    if not subscription_id:
        raise HTTPException(status_code=400, detail="缺少 subscription_id")

    conn = get_db()
    try:
        cursor = conn.execute(
            """SELECT id, subscription_no, plan_type, billing_cycle, price, status
               FROM saas_subscriptions WHERE id = ?""",
            (subscription_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="订阅不存在")

        columns = [desc[0] for desc in cursor.description]
        sub = dict(zip(columns, row))

        if sub["status"] not in ("pending", "expired"):
            raise HTTPException(
                status_code=400,
                detail=f"订阅状态为 {sub['status']}，不可发起支付",
            )

        # 生成交易号
        out_trade_no = _generate_order_no("ALI")
        amount = sub["price"]
        plan_name = SAAS_PLANS.get(sub["plan_type"], {}).get("name", sub["plan_type"])
        subject = f"中韩出海数智港 - {plan_name} ({sub['billing_cycle']})"

        # [模拟] 生成支付宝支付二维码
        qr_code = _mock_alipay_qrcode(out_trade_no, amount, subject)

        # 创建支付交易记录
        cursor = conn.execute(
            """INSERT INTO payment_transactions
               (transaction_no, subscription_id, order_no, amount, channel, qr_code, status)
               VALUES (?, ?, ?, ?, 'alipay', ?, 'pending')""",
            (_generate_transaction_id(), subscription_id, out_trade_no,
             amount, qr_code),
        )
        conn.commit()
        txn_id = cursor.lastrowid

        return {
            "success": True,
            "mode": "alipay",
            "qr_code": qr_code,
            "out_trade_no": out_trade_no,
            "total_amount": f"{amount:.2f}",
            "transaction_id": txn_id,
            "subscription_id": subscription_id,
            "message": "支付宝当面付二维码已生成（模拟模式）",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建支付宝支付失败: {str(e)}")
    finally:
        conn.close()


@router.post("/api/v2/payment/alipay/query")
async def alipay_query(body: dict):
    """
    [模拟] 查询支付宝交易状态（供前端轮询）

    请求体:
    {
        "out_trade_no": "ALI20260512XXXXXXXX",
        "transaction_id": 1
    }
    """
    out_trade_no = body.get("out_trade_no")
    transaction_id = body.get("transaction_id")

    conn = get_db()
    try:
        if transaction_id:
            cursor = conn.execute(
                "SELECT * FROM payment_transactions WHERE id = ?",
                (transaction_id,),
            )
        elif out_trade_no:
            cursor = conn.execute(
                "SELECT * FROM payment_transactions WHERE order_no = ?",
                (out_trade_no,),
            )
        else:
            raise HTTPException(status_code=400, detail="请提供 out_trade_no 或 transaction_id")

        row = cursor.fetchone()
        if not row:
            return {
                "success": True,
                "paid": False,
                "trade_status": "NOT_FOUND",
            }

        columns = [desc[0] for desc in cursor.description]
        txn = dict(zip(columns, row))

        return {
            "success": True,
            "mode": "db",
            "paid": txn["status"] == "paid",
            "trade_status": txn["status"],
            "transaction_id": txn["id"],
            "amount": txn["amount"],
        }
    finally:
        conn.close()


# ── 微信Native Pay（模拟） ────────────────────────────

@router.post("/api/v2/payment/wechat/native")
async def wechat_native_pay(body: dict):
    """
    [模拟] 微信Native Pay - 生成支付二维码

    请求体:
    {
        "subscription_id": 1
    }

    响应:
    {
        "success": true,
        "code_url": "weixin://...",
        "qr_code": "https://...",    // 二维码图片URL
        "out_trade_no": "WX20260512XXXXXXXX",
        "total_fee": 490000,          // 单位: 分
        "transaction_id": 1
    }
    """
    subscription_id = body.get("subscription_id")
    if not subscription_id:
        raise HTTPException(status_code=400, detail="缺少 subscription_id")

    conn = get_db()
    try:
        cursor = conn.execute(
            """SELECT id, subscription_no, plan_type, billing_cycle, price, status
               FROM saas_subscriptions WHERE id = ?""",
            (subscription_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="订阅不存在")

        columns = [desc[0] for desc in cursor.description]
        sub = dict(zip(columns, row))

        if sub["status"] not in ("pending", "expired"):
            raise HTTPException(
                status_code=400,
                detail=f"订阅状态为 {sub['status']}，不可发起支付",
            )

        out_trade_no = _generate_order_no("WX")
        amount = sub["price"]
        total_fee = int(amount * 100)  # 微信支付单位: 分
        plan_name = SAAS_PLANS.get(sub["plan_type"], {}).get("name", sub["plan_type"])
        description = f"中韩出海数智港-{plan_name}"

        # [模拟] 生成微信支付二维码
        qr_code = _mock_wechat_qrcode(out_trade_no, amount, description)
        code_url = f"weixin://wxpay/bizpayurl?pr={out_trade_no}"

        # 创建支付交易记录
        cursor = conn.execute(
            """INSERT INTO payment_transactions
               (transaction_no, subscription_id, order_no, amount, channel, qr_code, status)
               VALUES (?, ?, ?, ?, 'wechat', ?, 'pending')""",
            (_generate_transaction_id(), subscription_id, out_trade_no,
             amount, qr_code),
        )
        conn.commit()
        txn_id = cursor.lastrowid

        return {
            "success": True,
            "mode": "wechat",
            "code_url": code_url,
            "qr_code": qr_code,
            "out_trade_no": out_trade_no,
            "total_fee": total_fee,
            "total_amount": f"{amount:.2f}",
            "transaction_id": txn_id,
            "subscription_id": subscription_id,
            "message": "微信Native Pay二维码已生成（模拟模式）",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建微信支付失败: {str(e)}")
    finally:
        conn.close()


# ── 支付确认（模拟支付成功） ──────────────────────────

@router.post("/api/v2/payment/confirm")
async def confirm_payment(body: dict):
    """
    [模拟] 确认支付成功（模拟沙箱支付确认）
    真实场景下由支付宝/微信异步通知触发

    请求体:
    {
        "transaction_id": 1,
        "channel": "alipay|wechat"   // 可选，默认自动识别
    }
    """
    transaction_id = body.get("transaction_id")
    if not transaction_id:
        raise HTTPException(status_code=400, detail="缺少 transaction_id")

    conn = get_db()
    try:
        cursor = conn.execute(
            "SELECT * FROM payment_transactions WHERE id = ?",
            (transaction_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="交易记录不存在")

        columns = [desc[0] for desc in cursor.description]
        txn = dict(zip(columns, row))

        if txn["status"] == "paid":
            return {
                "success": True,
                "message": "该交易已支付成功，无需重复确认",
                "data": {"transaction_id": transaction_id, "status": "paid"},
            }

        if txn["status"] == "refunded":
            raise HTTPException(status_code=400, detail="该交易已退款，无法确认")

        # 生成渠道交易号（模拟支付宝/微信的交易流水号）
        channel_trade_no = (
            f"ALIPAY{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
            if txn["channel"] == "alipay"
            else f"WXPAY{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
        )

        # 更新交易状态为已支付
        conn.execute(
            """UPDATE payment_transactions
               SET status = 'paid', channel_trade_no = ?, paid_at = CURRENT_TIMESTAMP,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (channel_trade_no, transaction_id),
        )

        # 更新订阅状态为 active
        subscription_id = txn["subscription_id"]
        if subscription_id:
            cursor = conn.execute(
                "SELECT status FROM saas_subscriptions WHERE id = ?",
                (subscription_id,),
            )
            sub_row = cursor.fetchone()
            if sub_row and sub_row[0] in ("pending", "expired"):
                conn.execute(
                    """UPDATE saas_subscriptions
                       SET status = 'active', updated_at = CURRENT_TIMESTAMP
                       WHERE id = ?""",
                    (subscription_id,),
                )

        conn.commit()

        return {
            "success": True,
            "message": "支付确认成功",
            "data": {
                "transaction_id": transaction_id,
                "channel_trade_no": channel_trade_no,
                "status": "paid",
                "subscription_id": subscription_id,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"支付确认失败: {str(e)}")
    finally:
        conn.close()


# ── 退款 ──────────────────────────────────────────────

@router.post("/api/v2/payment/refund")
async def refund_payment(body: dict):
    """
    [模拟] 退款

    请求体:
    {
        "transaction_id": 1,        // 方式一：按交易退款
        "subscription_id": 1,       // 方式二：按订阅退款（退最近一笔交易）
        "reason": "用户申请退款"     // 退款原因（可选）
    }
    """
    transaction_id = body.get("transaction_id")
    subscription_id = body.get("subscription_id")
    reason = body.get("reason", "用户申请退款")

    if not transaction_id and not subscription_id:
        raise HTTPException(status_code=400, detail="请提供 transaction_id 或 subscription_id")

    conn = get_db()
    try:
        if transaction_id:
            cursor = conn.execute(
                "SELECT * FROM payment_transactions WHERE id = ?",
                (transaction_id,),
            )
        elif subscription_id:
            cursor = conn.execute(
                """SELECT * FROM payment_transactions
                   WHERE subscription_id = ? AND status = 'paid'
                   ORDER BY id DESC LIMIT 1""",
                (subscription_id,),
            )
        else:
            raise HTTPException(status_code=400, detail="请提供 transaction_id 或 subscription_id")

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="未找到可退款的交易记录")

        columns = [desc[0] for desc in cursor.description]
        txn = dict(zip(columns, row))

        if txn["status"] != "paid":
            raise HTTPException(
                status_code=400,
                detail=f"交易状态为 {txn['status']}，仅已支付的交易可退款",
            )

        # 更新交易状态为 refunded
        conn.execute(
            """UPDATE payment_transactions
               SET status = 'refunded', refund_reason = ?, refunded_at = CURRENT_TIMESTAMP,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (reason, txn["id"]),
        )

        # 更新订阅状态为 refunded
        sub_id = txn["subscription_id"]
        if sub_id:
            conn.execute(
                """UPDATE saas_subscriptions
                   SET status = 'refunded', refund_reason = ?, refunded_at = CURRENT_TIMESTAMP,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (reason, sub_id),
            )

        conn.commit()

        return {
            "success": True,
            "message": "退款成功",
            "data": {
                "transaction_id": txn["id"],
                "amount": txn["amount"],
                "reason": reason,
                "status": "refunded",
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"退款失败: {str(e)}")
    finally:
        conn.close()


# ── 过期处理 ──────────────────────────────────────────

@router.post("/api/v2/payment/expire")
async def expire_subscription(body: dict):
    """
    将订阅标记为已过期
    真实场景：定时任务检查 current_period_end，超过则自动过期
    模拟场景：手动触发过期

    请求体:
    {
        "subscription_id": 1
    }
    """
    subscription_id = body.get("subscription_id")
    if not subscription_id:
        raise HTTPException(status_code=400, detail="缺少 subscription_id")

    conn = get_db()
    try:
        cursor = conn.execute(
            "SELECT id, status FROM saas_subscriptions WHERE id = ?",
            (subscription_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="订阅不存在")

        if row[1] == "expired":
            return {
                "success": True,
                "message": "该订阅已过期",
                "data": {"subscription_id": subscription_id, "status": "expired"},
            }

        if row[1] == "refunded":
            raise HTTPException(status_code=400, detail="已退款的订阅不可过期")

        conn.execute(
            """UPDATE saas_subscriptions
               SET status = 'expired', updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (subscription_id,),
        )
        conn.commit()

        return {
            "success": True,
            "message": "订阅已标记为过期",
            "data": {"subscription_id": subscription_id, "status": "expired"},
        }
    finally:
        conn.close()


# ── 查询接口 ──────────────────────────────────────────

@router.get("/api/v2/payment/subscription/{subscription_id}")
async def get_subscription(subscription_id: int):
    """查询订阅详情"""
    conn = get_db()
    try:
        cursor = conn.execute(
            """SELECT s.*, GROUP_CONCAT(t.id) as transaction_ids,
                      GROUP_CONCAT(t.status) as transaction_statuses,
                      GROUP_CONCAT(t.channel) as transaction_channels
               FROM saas_subscriptions s
               LEFT JOIN payment_transactions t ON t.subscription_id = s.id
               WHERE s.id = ?
               GROUP BY s.id""",
            (subscription_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="订阅不存在")

        columns = [desc[0] for desc in cursor.description]
        sub = dict(zip(columns, row))

        # 组装交易信息
        transactions = []
        if sub.get("transaction_ids"):
            txn_ids = sub["transaction_ids"].split(",") if sub["transaction_ids"] else []
            txn_statuses = sub["transaction_statuses"].split(",") if sub["transaction_statuses"] else []
            txn_channels = sub["transaction_channels"].split(",") if sub["transaction_channels"] else []
            for i, tid in enumerate(txn_ids):
                transactions.append({
                    "id": int(tid),
                    "status": txn_statuses[i] if i < len(txn_statuses) else "unknown",
                    "channel": txn_channels[i] if i < len(txn_channels) else "unknown",
                })

        # 清理辅助字段
        for key in ["transaction_ids", "transaction_statuses", "transaction_channels"]:
            sub.pop(key, None)

        sub["transactions"] = transactions

        # 添加套餐名称
        plan = SAAS_PLANS.get(sub["plan_type"], {})
        sub["plan_name"] = plan.get("name", sub["plan_type"])
        sub["plan_name_ko"] = plan.get("name_ko", sub["plan_type"])

        return {"success": True, "data": sub}
    finally:
        conn.close()


@router.get("/api/v2/payment/transactions")
async def list_transactions(
    subscription_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """查询交易列表"""
    conn = get_db()
    try:
        query = "SELECT * FROM payment_transactions WHERE 1=1"
        params = []

        if subscription_id is not None:
            query += " AND subscription_id = ?"
            params.append(subscription_id)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        transactions = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return {"success": True, "data": transactions, "count": len(transactions)}
    finally:
        conn.close()


# ── 支付异步通知回调（模拟） ──────────────────────────

@router.post("/api/v2/payment/notify")
async def payment_notify(request: Request):
    """
    [模拟] 支付异步通知回调
    真实场景：支付宝/微信服务器会POST form数据到这里
    模拟场景：接收JSON模拟通知

    请求体 (模拟):
    {
        "transaction_id": 1,
        "channel": "alipay",
        "trade_status": "TRADE_SUCCESS",
        "out_trade_no": "ALI20260512XXXXXXXX",
        "trade_no": "2026051222001487651234"
    }
    """
    try:
        body = await request.json()
    except Exception:
        # 也支持 form 格式（模拟支付宝真实通知格式）
        try:
            form = await request.form()
            body = dict(form)
        except Exception:
            body = {}

    channel = body.get("channel", "")
    trade_status = body.get("trade_status", "TRADE_SUCCESS")
    out_trade_no = body.get("out_trade_no", "")
    trade_no = body.get("trade_no", "")

    # [模拟] 验证签名
    if not _mock_verify_signature(channel, body):
        return {"code": "FAIL", "msg": "签名验证失败"}

    if trade_status not in ("TRADE_SUCCESS", "SUCCESS"):
        return {"code": "SUCCESS", "msg": "忽略非成功状态通知"}

    conn = get_db()
    try:
        # 通过 out_trade_no 查找交易记录
        cursor = conn.execute(
            "SELECT * FROM payment_transactions WHERE order_no = ?",
            (out_trade_no,),
        )
        row = cursor.fetchone()
        if not row:
            # 尝试通过 transaction_id 查找
            txn_id = body.get("transaction_id")
            if txn_id:
                cursor = conn.execute(
                    "SELECT * FROM payment_transactions WHERE id = ?",
                    (txn_id,),
                )
                row = cursor.fetchone()

        if not row:
            print(f"[PaymentV2] 异步通知: 未找到交易记录 out_trade_no={out_trade_no}")
            return {"code": "FAIL", "msg": "交易记录不存在"}

        columns = [desc[0] for desc in cursor.description]
        txn = dict(zip(columns, row))

        if txn["status"] == "paid":
            return {"code": "SUCCESS", "msg": "重复通知"}

        # 更新交易状态
        conn.execute(
            """UPDATE payment_transactions
               SET status = 'paid', channel_trade_no = ?, paid_at = CURRENT_TIMESTAMP,
                   notify_data = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (trade_no or channel, json.dumps(body, ensure_ascii=False), txn["id"]),
        )

        # 更新订阅状态
        sub_id = txn["subscription_id"]
        if sub_id:
            cursor = conn.execute(
                "SELECT status FROM saas_subscriptions WHERE id = ?",
                (sub_id,),
            )
            sub_row = cursor.fetchone()
            if sub_row and sub_row[0] in ("pending", "expired"):
                conn.execute(
                    """UPDATE saas_subscriptions
                       SET status = 'active', updated_at = CURRENT_TIMESTAMP
                       WHERE id = ?""",
                    (sub_id,),
                )

        conn.commit()
        print(f"[PaymentV2] 异步通知成功: out_trade_no={out_trade_no}, status=paid")

        return {"code": "SUCCESS", "msg": "回调处理成功"}
    except Exception as e:
        print(f"[PaymentV2] 异步通知处理失败: {e}")
        return {"code": "FAIL", "msg": f"处理失败: {str(e)}"}
    finally:
        conn.close()
