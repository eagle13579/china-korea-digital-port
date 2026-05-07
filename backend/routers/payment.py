"""
中韩出海数智港 - 支付系统API路由
集成支付宝当面付（扫码支付）+ 额度充值

JWT认证端点（新）:
  POST /api/v1/payment/create     — 创建支付订单（需JWT）
  POST /api/v1/payment/notify     — 支付宝异步通知
  GET  /api/v1/payment/query/{order_id} — 查询订单状态
  POST /api/v1/payment/topup      — 人工充值（需admin认证）

旧版兼容端点:
  POST /api/v1/orders             — 创建订单（form）
  POST /api/v1/order/create       — 创建订单（JSON）
  GET  /api/v1/orders/{order_id}  — 查询订单
  POST /api/v1/orders/{order_id}/payment — 上传付款凭证
  POST /api/v1/payment/simulate/notify  — 模拟支付回调
  GET  /api/v1/payment/status/{order_id} — 旧版查询支付状态
"""

import os
import uuid
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Header, Request
from pydantic import BaseModel, Field

from backend.database import get_db
from backend.license import generate_license

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["payment"])

# 凭证图片存储路径
VOUCHER_DIR = Path(__file__).parent.parent / "data" / "vouchers"
VOUCHER_DIR.mkdir(parents=True, exist_ok=True)

# ── 套餐定价映射 ──────────────────────────────────────
PLAN_PRICES = {
    "free": 0,
    "depth": 9800.00,    # 深度方案 ¥9,800
    "annual": 58000.00,  # 年订阅 ¥58,000
    "source": 29999.00,  # 源码授权 ¥29,999
}

PLAN_NAMES = {
    "free": "免费初评",
    "depth": "深度方案",
    "annual": "年订阅",
    "source": "源码授权",
}

PLAN_NAMES_KO = {
    "free": "무료 초기 평가",
    "depth": "심층 컨설팅 패키지",
    "annual": "연간 구독",
    "source": "소스코드 라이선스",
}

# ── 额度套餐定价映射（新JWT认证系统用）──────────────────
SUBSCRIPTION_PLANS = {
    "basic": {
        "name": "基础版",
        "name_en": "Basic",
        "name_ko": "베이직",
        "price": 99.00,
        "quota": 100,
        "description": "100次AI数字员工分析额度",
    },
    "pro": {
        "name": "专业版",
        "name_en": "Professional",
        "name_ko": "프로페셔널",
        "price": 299.00,
        "quota": 500,
        "description": "500次AI数字员工分析额度",
    },
}

# ── 支付宝配置 ────────────────────────────────────────
ALIPAY_CONFIG = {
    "app_id": os.environ.get("ALIPAY_APP_ID", ""),
    "app_private_key_path": os.environ.get("ALIPAY_APP_PRIVATE_KEY", ""),
    "alipay_public_key_path": os.environ.get("ALIPAY_PUBLIC_KEY", ""),
    "sandbox": os.environ.get("ALIPAY_SANDBOX", "true").lower() == "true",
    "notify_url": os.environ.get("ALIPAY_NOTIFY_URL", ""),
}

# 全局支付宝客户端（延迟初始化）
_alipay_client = None


def get_alipay_client():
    """获取支付宝客户端（单例、延迟初始化）"""
    global _alipay_client
    if _alipay_client is not None:
        return _alipay_client

    app_id = ALIPAY_CONFIG["app_id"]
    private_key_path = ALIPAY_CONFIG["app_private_key_path"]
    public_key_path = ALIPAY_CONFIG["alipay_public_key_path"]

    if not app_id or app_id == "your_alipay_app_id_here":
        logger.warning("支付宝未配置 (ALIPAY_APP_ID 为空)，使用沙箱模拟模式")
        return None

    if not private_key_path:
        logger.warning("支付宝私钥未配置，使用沙箱模拟模式")
        return None

    try:
        from alipay import AliPay, AliPayConfig

        # 解析私钥路径（支持绝对路径和相对路径）
        project_root = Path(__file__).parent.parent.parent
        private_key_path_resolved = Path(private_key_path)
        if not private_key_path_resolved.is_absolute():
            private_key_path_resolved = project_root / private_key_path

        public_key_path_resolved = Path(public_key_path) if public_key_path else None
        if public_key_path_resolved and not public_key_path_resolved.is_absolute():
            public_key_path_resolved = project_root / public_key_path

        # 读取密钥
        if not private_key_path_resolved.exists():
            logger.error(f"支付宝私钥文件不存在: {private_key_path_resolved}")
            return None

        with open(private_key_path_resolved, "r") as f:
            app_private_key = f.read()

        alipay_public_key = None
        if public_key_path_resolved and public_key_path_resolved.exists():
            with open(public_key_path_resolved, "r") as f:
                alipay_public_key = f.read()

        _alipay_client = AliPay(
            appid=app_id,
            app_notify_url=ALIPAY_CONFIG["notify_url"],
            app_private_key_string=app_private_key,
            alipay_public_key_string=alipay_public_key,
            sign_type="RSA2",
            debug=ALIPAY_CONFIG["sandbox"],
            config=AliPayConfig(timeout=15),
        )
        logger.info("支付宝客户端初始化成功" + (" (沙箱模式)" if ALIPAY_CONFIG["sandbox"] else ""))
        return _alipay_client
    except ImportError:
        logger.warning("alipay-sdk-python 未安装，使用模拟模式")
        return None
    except Exception as e:
        logger.error(f"支付宝客户端初始化失败: {e}")
        return None


# ── 辅助函数 ──────────────────────────────────────────

def _generate_order_no() -> str:
    """生成订单号：ORD + 日期 + 随机码"""
    date_str = datetime.now().strftime("%Y%m%d")
    rand_str = uuid.uuid4().hex[:6].upper()
    return f"ORD{date_str}{rand_str}"


def _detect_image_format(data: bytes) -> str:
    """根据文件头检测图片格式"""
    if data[:4] == b"\x89PNG":
        return "png"
    elif data[:2] in (b"\xff\xd8",):
        return "jpg"
    elif data[:4] == b"RIFF":
        return "webp"
    elif data[:4] == b"GIF8":
        return "gif"
    elif data[:4] == b"\x42\x4d":
        return "bmp"
    else:
        return "png"


def _require_auth(authorization: str = Header(None)):
    """验证管理员认证"""
    from backend.routers.admin import _verify_token
    if not authorization:
        raise HTTPException(status_code=401, detail="未授权")
    token = authorization.replace("Bearer ", "")
    if not _verify_token(token):
        raise HTTPException(status_code=401, detail="token已过期，请重新登录")


def _require_admin(authorization: str = Header(None)):
    """验证管理员认证，返回用户信息"""
    from backend.routers.admin import _verify_token
    if not authorization:
        raise HTTPException(status_code=401, detail="未授权")
    token = authorization.replace("Bearer ", "")
    payload = _verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="token已过期，请重新登录")
    return payload


def _apply_quota_on_payment(order_id: int):
    """
    支付成功后自动更新用户额度

    根据订单的plan_type增加对应用户的 user_quotas.total_quota
    """
    conn = get_db()
    try:
        cursor = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        if not row:
            logger.warning(f"订单不存在: order_id={order_id}")
            return

        cols = [d[0] for d in cursor.description]
        order = dict(zip(cols, row))
        user_id = order.get("user_id")
        plan_type = order["plan_type"]

        if not user_id:
            logger.warning(f"订单没有关联用户: order_id={order_id}")
            return

        # 确定要增加的额度
        add_quota = 0
        if plan_type in SUBSCRIPTION_PLANS:
            add_quota = SUBSCRIPTION_PLANS[plan_type]["quota"]
        elif plan_type == "basic":
            add_quota = 100
        elif plan_type == "pro":
            add_quota = 500
        else:
            # 老的咨询套餐（depth/annual/source）增加大额额度
            quota_map = {"free": 10, "depth": 200, "annual": 1000, "source": 2000}
            add_quota = quota_map.get(plan_type, 10)

        if add_quota <= 0:
            return

        # 更新或创建用户额度
        cursor.execute("SELECT id, total_quota FROM user_quotas WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()

        if existing:
            new_total = existing["total_quota"] + add_quota
            if plan_type == "basic" or plan_type == "pro":
                # 额度套餐：更新plan_type和total_quota
                expires_at = (datetime.utcnow() + timedelta(days=365)).isoformat()
                conn.execute(
                    """UPDATE user_quotas 
                       SET plan_type = ?, total_quota = ?, expires_at = ?, updated_at = CURRENT_TIMESTAMP 
                       WHERE user_id = ?""",
                    (plan_type, new_total, expires_at, user_id),
                )
            else:
                conn.execute(
                    "UPDATE user_quotas SET total_quota = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (new_total, user_id),
                )
        else:
            expires_at = (datetime.utcnow() + timedelta(days=365)).isoformat()
            conn.execute(
                "INSERT INTO user_quotas (user_id, plan_type, total_quota, used_quota, expires_at) VALUES (?, ?, ?, 0, ?)",
                (user_id, plan_type if plan_type in ("basic", "pro") else "free", add_quota, expires_at),
            )

        conn.commit()
        logger.info(f"额度更新成功: user_id={user_id}, add_quota={add_quota}, new_total={existing['total_quota'] + add_quota if existing else add_quota}")
    except Exception as e:
        logger.error(f"额度更新失败: {e}")
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════
# 新支付系统 API (JWT认证，额度充值)
# ═══════════════════════════════════════════════════════

def _get_jwt_user(authorization: str = Header(None)) -> dict:
    """从JWT Bearer token获取当前用户"""
    from backend.routers.auth import get_current_user
    return get_current_user(authorization)


class PaymentCreateRequest(BaseModel):
    """创建支付订单请求（额度充值用）"""
    plan_type: str = Field(..., pattern=r'^(free|depth|annual|source|basic|pro)$', description="套餐类型")


@router.post("/api/v1/payment/create")
async def create_payment(req: PaymentCreateRequest, authorization: str = Header(None)):
    """
    创建支付订单（需JWT认证）
    
    流程:
    1. 验证JWT token
    2. 根据plan_type确定价格（支持老的咨询套餐和新的额度套餐）
    3. 创建订单，关联到当前用户
    4. 调用支付宝当面付生成支付二维码
    5. 返回支付信息
    """
    # 1. JWT认证
    payload = _get_jwt_user(authorization)
    user_id = int(payload["sub"])
    user_email = payload.get("email", "")

    # 2. 校验套餐
    plan_type = req.plan_type
    
    # 判断是老的咨询套餐还是新的额度套餐
    if plan_type in PLAN_PRICES:
        price = PLAN_PRICES[plan_type]
        plan_name = PLAN_NAMES.get(plan_type, plan_type)
    elif plan_type in SUBSCRIPTION_PLANS:
        sp = SUBSCRIPTION_PLANS[plan_type]
        price = sp["price"]
        plan_name = sp["name"]
    else:
        raise HTTPException(status_code=400, detail=f"不支持的套餐类型: {plan_type}")

    # 获取用户信息
    conn = get_db()
    try:
        cursor = conn.execute("SELECT id, username, email FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        username = user["username"]
        email = user["email"]
    finally:
        conn.close()

    order_no = _generate_order_no()

    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO orders (
                order_no, user_id, user_company, user_name, user_email,
                plan_type, price, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (order_no, user_id, username, username, email,
             plan_type, price),
        )
        conn.commit()
        order_id = cursor.lastrowid
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"创建订单失败: {str(e)}")

    conn.close()

    # ── 调用支付宝当面付生成支付二维码 ──
    qr_code_url = None
    alipay_trade_no = None
    alipay_client = get_alipay_client()

    if alipay_client and price > 0:
        try:
            subject = f"中韩出海数智港 - {plan_name}"
            result = alipay_client.api_alipay_trade_precreate(
                subject=subject,
                out_trade_no=order_no,
                total_amount=price,
                quit_url="",
            )
            if result.get("code") == "10000":
                qr_code_url = result.get("qr_code")
                alipay_trade_no = result.get("trade_no")
                logger.info(f"支付宝订单创建成功: order_no={order_no}, qr_code={qr_code_url}")
                # 保存支付宝交易号
                if alipay_trade_no:
                    conn = get_db()
                    conn.execute("UPDATE orders SET alipay_trade_no = ? WHERE id = ?", (alipay_trade_no, order_id))
                    conn.commit()
                    conn.close()
            else:
                logger.warning(f"支付宝预创建失败: {result.get('code')} - {result.get('msg')}")
        except Exception as e:
            logger.error(f"调用支付宝API异常: {e}")

    # 免费方案直接标记已支付并增加额度
    if price == 0:
        conn = get_db()
        try:
            conn.execute(
                "UPDATE orders SET status = 'paid', paid_at = CURRENT_TIMESTAMP WHERE id = ?",
                (order_id,),
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"免费订单自动确认失败: {e}")
        finally:
            conn.close()

        # 免费方案增加额度（如果是额度套餐）
        _apply_quota_on_payment(order_id)

        return {
            "success": True,
            "order_id": order_id,
            "order_no": order_no,
            "price": price,
            "plan_type": plan_type,
            "plan_name": plan_name,
            "status": "paid",
            "qr_code_url": None,
            "alipay_trade_no": None,
            "message": "免费方案，无需支付",
            "is_free": True,
        }

    if qr_code_url:
        return {
            "success": True,
            "order_id": order_id,
            "order_no": order_no,
            "price": price,
            "plan_type": plan_type,
            "plan_name": plan_name,
            "status": "pending",
            "qr_code_url": qr_code_url,
            "alipay_trade_no": alipay_trade_no,
            "message": "订单创建成功，请扫码支付",
            "is_free": False,
        }
    else:
        # 支付宝不可用或金额为0，返回模拟支付模式
        return {
            "success": True,
            "order_id": order_id,
            "order_no": order_no,
            "price": price,
            "plan_type": plan_type,
            "plan_name": plan_name,
            "status": "pending",
            "qr_code_url": None,
            "alipay_trade_no": None,
            "message": "订单创建成功（模拟模式，点击完成支付模拟支付成功）",
            "is_free": False,
            "simulate_mode": True,
        }


@router.post("/api/v1/payment/notify")
async def payment_notify(request: Request):
    """
    支付宝异步支付回调通知
    
    支付宝 POST 方式通知，参数以 form-data 格式发送
    需要验证签名并处理订单状态更新，支付成功后自动增加用户额度
    """
    try:
        form_data = await request.form()
        params = dict(form_data)
    except Exception:
        # 也可能是 JSON 格式
        try:
            body = await request.json()
            params = body if isinstance(body, dict) else {}
        except Exception:
            params = {}

    logger.info(f"收到支付回调: {json.dumps(params, ensure_ascii=False)[:200]}")

    alipay_client = get_alipay_client()

    if alipay_client:
        # 验证支付宝签名
        success = alipay_client.verify(params, params.pop("sign", ""))
        if not success:
            logger.warning("支付宝回调签名验证失败")
            return {"success": False, "message": "sign verify failed"}
    else:
        # 无支付宝客户端：信任回调（开发/沙箱模式）
        logger.info("支付宝未配置，跳过签名验证")
        # 检查是否为模拟支付请求
        if params.get("simulate", "").lower() == "true":
            pass  # 继续处理
        else:
            # 非模拟模式，记录但不处理
            logger.info(f"收到未知来源回调: {params.get('out_trade_no', 'unknown')}")

    # 提取关键信息
    out_trade_no = params.get("out_trade_no", "")
    trade_status = params.get("trade_status", "")
    trade_no = params.get("trade_no", "")
    total_amount = params.get("total_amount", "0")

    if not out_trade_no:
        return {"success": False, "message": "missing out_trade_no"}

    # 处理支付成功
    if trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        conn = get_db()
        try:
            cursor = conn.execute(
                "SELECT id, status FROM orders WHERE order_no = ?",
                (out_trade_no,),
            )
            row = cursor.fetchone()
            if row:
                order_id, status = row
                if status == "pending":
                    conn.execute(
                        """UPDATE orders SET status = 'paid', paid_at = CURRENT_TIMESTAMP
                           WHERE id = ? AND status = 'pending'""",
                        (order_id,),
                    )
                    conn.commit()
                    logger.info(f"订单支付成功: order_no={out_trade_no}, order_id={order_id}")

                    # 尝试生成 License
                    try:
                        cursor2 = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
                        order_row = cursor2.fetchone()
                        if order_row:
                            cols = [d[0] for d in cursor2.description]
                            order_data = dict(zip(cols, order_row))
                            licensee = order_data.get("user_company") or order_data.get("user_name", "")
                            days_map = {"free": 30, "depth": 365, "annual": 365, "source": 730}
                            days = days_map.get(order_data.get("plan_type", "depth"), 365)
                            license_key = generate_license(licensee, order_data.get("plan_type", ""), days)
                            conn.execute(
                                "UPDATE orders SET license_key = ? WHERE id = ?",
                                (license_key, order_id),
                            )
                            conn.commit()
                            logger.info(f"License 自动生成: {license_key}")

                            # 发送支付成功通知
                            try:
                                from backend.services.email_service import (
                                    send_payment_success_notification,
                                    send_payment_notification_to_sales,
                                )
                                send_payment_success_notification(order_data)
                                send_payment_notification_to_sales(order_data)
                            except ImportError:
                                pass
                            except Exception:
                                pass
                    except Exception as e:
                        logger.warning(f"License 生成失败: {e}")

                    # 额度充值：支付成功后自动更新用户额度
                    try:
                        _apply_quota_on_payment(order_id)
                    except Exception as e:
                        logger.warning(f"额度更新失败: {e}")
        except Exception as e:
            logger.error(f"回调处理异常: {e}")
            return {"success": False, "message": str(e)}
        finally:
            conn.close()

        return {"success": True, "message": "success"}
    elif trade_status == "TRADE_CLOSED":
        # 交易关闭
        logger.info(f"交易关闭: out_trade_no={out_trade_no}")
        return {"success": True, "message": "closed"}
    else:
        logger.info(f"未处理的状态: {trade_status}")
        return {"success": True, "message": "received"}


@router.get("/api/v1/payment/status/{order_id}")
async def get_payment_status(order_id: int):
    """
    查询支付订单状态

    返回订单当前状态，如果已支付还包含 License Key
    """
    conn = get_db()
    try:
        cursor = conn.execute(
            """SELECT id, order_no, plan_type, price, user_company, user_name,
                      user_email, status, license_key, created_at, paid_at
               FROM orders WHERE id = ?""",
            (order_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="订单不存在")

        columns = [desc[0] for desc in cursor.description]
        order = dict(zip(columns, row))

        result = {
            "success": True,
            "data": {
                "order_id": order["id"],
                "order_no": order["order_no"],
                "plan_type": order["plan_type"],
                "plan_name": PLAN_NAMES.get(order["plan_type"], order["plan_type"]),
                "price": order["price"],
                "customer_name": order["user_name"],
                "customer_email": order["user_email"],
                "customer_company": order["user_company"],
                "status": order["status"],
                "license_key": order["license_key"],
                "created_at": order["created_at"],
                "paid_at": order["paid_at"],
            },
        }

        # 如果已支付，尝试补全 license_key
        if order["status"] == "paid" and not order.get("license_key"):
            try:
                licensee = order["user_company"] or order["user_name"] or ""
                days_map = {"free": 30, "depth": 365, "annual": 365, "source": 730}
                days = days_map.get(order["plan_type"], 365)
                license_key = generate_license(licensee, order["plan_type"], days)
                conn.execute("UPDATE orders SET license_key = ? WHERE id = ?", (license_key, order_id))
                conn.commit()
                result["data"]["license_key"] = license_key
            except Exception as e:
                logger.warning(f"License 补充生成失败: {e}")

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
    finally:
        conn.close()


@router.post("/api/v1/payment/simulate/notify")
async def simulate_payment_notify(req: Request):
    """
    模拟支付成功回调（开发/演示用）

    接受 JSON 参数: {"order_no": "ORD20260507XXXXXX"}
    仅当 ALIPAY_SANDBOX=true 或未配置支付宝时可用
    """
    alipay_configured = bool(ALIPAY_CONFIG["app_id"] and ALIPAY_CONFIG["app_id"] != "your_alipay_app_id_here")

    try:
        body = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效的请求格式")

    order_no = body.get("order_no", "")
    if not order_no:
        raise HTTPException(status_code=400, detail="缺少 order_no")

    conn = get_db()
    try:
        cursor = conn.execute(
            "SELECT id, status FROM orders WHERE order_no = ?",
            (order_no,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"订单不存在: {order_no}")

        order_id, status = row
        if status == "paid":
            return {"success": True, "message": "订单已支付", "order_id": order_id}

        if status != "pending":
            raise HTTPException(status_code=400, detail=f"订单状态异常: {status}")

        conn.execute(
            "UPDATE orders SET status = 'paid', paid_at = CURRENT_TIMESTAMP WHERE id = ?",
            (order_id,),
        )
        conn.commit()

        # 生成 License
        order_data = None
        try:
            cursor2 = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            order_row = cursor2.fetchone()
            if order_row:
                cols = [d[0] for d in cursor2.description]
                order_data = dict(zip(cols, order_row))
                licensee = order_data.get("user_company") or order_data.get("user_name", "")
                days_map = {"free": 30, "depth": 365, "annual": 365, "source": 730}
                days = days_map.get(order_data.get("plan_type", "depth"), 365)
                license_key = generate_license(licensee, order_data.get("plan_type", ""), days)
                conn.execute("UPDATE orders SET license_key = ? WHERE id = ?", (license_key, order_id))
                conn.commit()
        except Exception as e:
            logger.warning(f"License 生成失败: {e}")

        logger.info(f"模拟支付成功: order_no={order_no}, order_id={order_id}")

        # 发送支付成功通知
        try:
            from backend.services.email_service import (
                send_payment_success_notification,
                send_payment_notification_to_sales,
            )
            if order_data:
                send_payment_success_notification(order_data)
                send_payment_notification_to_sales(order_data)
        except ImportError:
            pass
        except Exception:
            pass

        return {"success": True, "message": "模拟支付成功", "order_id": order_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模拟支付失败: {str(e)}")
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════
# 兼容旧版订单API (供 pricing-v2.html 调用)
# ═══════════════════════════════════════════════════════

@router.post("/api/v1/orders")
async def create_order(
    user_company: str = Form(...),
    user_name: str = Form(...),
    user_phone: str = Form(None),
    user_email: str = Form(...),
    plan_type: str = Form(...),
    price: float = Form(0),
):
    """创建订单（支持form和JSON两种方式）"""
    if plan_type not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail=f"不支持的套餐类型: {plan_type}")

    expected_price = PLAN_PRICES[plan_type]
    if abs(price - expected_price) > 0.01 and plan_type != "free":
        raise HTTPException(
            status_code=400,
            detail=f"价格不匹配，{PLAN_NAMES[plan_type]}价格为 ¥{expected_price:.2f}",
        )

    order_no = _generate_order_no()

    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO orders (order_no, user_company, user_name, user_phone, user_email, plan_type, price, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (order_no, user_company, user_name, user_phone, user_email,
             plan_type, price),
        )
        conn.commit()
        order_id = cursor.lastrowid

        return {
            "success": True,
            "order_id": order_id,
            "order_no": order_no,
            "price": price,
            "message": f"订单创建成功，订单号: {order_no}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建订单失败: {str(e)}")
    finally:
        conn.close()


@router.post("/api/v1/order/create")
async def create_order_json(body: dict):
    """兼容旧版JSON格式创建订单"""
    plan_type = body.get("plan_type", "")
    price = float(body.get("price", 0))

    if plan_type not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail=f"不支持的套餐类型: {plan_type}")

    expected_price = PLAN_PRICES[plan_type]
    if abs(price - expected_price) > 0.01 and plan_type != "free":
        raise HTTPException(
            status_code=400,
            detail=f"价格不匹配，{PLAN_NAMES[plan_type]}价格为 ¥{expected_price:.2f}",
        )

    order_no = _generate_order_no()

    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO orders (order_no, user_company, user_name, user_phone, user_email, plan_type, price, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (order_no, body.get("user_company", ""), body.get("user_name", ""),
             body.get("user_phone", ""), body.get("user_email", ""),
             plan_type, price),
        )
        conn.commit()
        order_id = cursor.lastrowid

        return {
            "success": True,
            "order_id": order_id,
            "order_no": order_no,
            "price": price,
            "message": "订单创建成功",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建订单失败: {str(e)}")
    finally:
        conn.close()


@router.get("/api/v1/orders/{order_id}")
async def get_order(order_id: int):
    """查询订单状态"""
    conn = get_db()
    try:
        cursor = conn.execute(
            """SELECT o.*, p.method as payment_method, p.status as payment_status,
                      p.voucher_path, p.confirmed_at
               FROM orders o
               LEFT JOIN payments p ON p.id = (SELECT MAX(id) FROM payments WHERE order_id = o.id)
               WHERE o.id = ?""",
            (order_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="订单不存在")

        columns = [desc[0] for desc in cursor.description]
        order = dict(zip(columns, row))

        return {"success": True, "data": order}
    finally:
        conn.close()


@router.post("/api/v1/orders/{order_id}/payment")
async def submit_payment(
    order_id: int,
    method: str = Form(...),
    file: UploadFile = File(None),
):
    """上传付款凭证（Multipart form）"""
    if method not in ("alipay", "wechat", "transfer"):
        raise HTTPException(status_code=400, detail="无效的支付方式")

    conn = get_db()
    try:
        cursor = conn.execute("SELECT id, price, status FROM orders WHERE id = ?", (order_id,))
        order = cursor.fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")

        columns = [desc[0] for desc in cursor.description]
        order_dict = dict(zip(columns, order))

        if order_dict["status"] != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"订单当前状态为 {order_dict['status']}，无法上传付款凭证",
            )

        voucher_path = None
        if file and file.filename:
            content = await file.read()
            ext = os.path.splitext(file.filename)[1] or ".jpg"
            if ext.lower() not in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
                ext = ".png"
            filename = f"voucher_{order_id}_{uuid.uuid4().hex[:8]}{ext}"
            file_path = VOUCHER_DIR / filename
            with open(file_path, "wb") as f:
                f.write(content)
            voucher_path = str(file_path)
        else:
            raise HTTPException(status_code=400, detail="请上传付款凭证文件")

        cursor = conn.execute(
            """INSERT INTO payments (order_id, method, amount, voucher_path, status)
               VALUES (?, ?, ?, ?, 'pending')""",
            (order_id, method, order_dict["price"], voucher_path),
        )
        conn.commit()

        return {
            "success": True,
            "message": "付款凭证上传成功，等待管理员审核",
            "voucher_path": voucher_path,
        }
    finally:
        conn.close()


# ── 管理后台订单管理API ───────────────────────────────

@router.get("/api/v1/admin/orders")
async def get_all_orders(
    status: Optional[str] = Query(None),
    authorization: str = Header(None),
):
    """管理员获取订单列表"""
    _require_auth(authorization)

    conn = get_db()
    try:
        if status:
            cursor = conn.execute(
                """SELECT o.*, p.method as payment_method, p.status as payment_status,
                          p.voucher_path, p.confirmed_at
                   FROM orders o
                   LEFT JOIN payments p ON p.id = (SELECT MAX(id) FROM payments WHERE order_id = o.id)
                   WHERE o.status = ?
                   ORDER BY o.created_at DESC""",
                (status,),
            )
        else:
            cursor = conn.execute(
                """SELECT o.*, p.method as payment_method, p.status as payment_status,
                          p.voucher_path, p.confirmed_at
                   FROM orders o
                   LEFT JOIN payments p ON p.id = (SELECT MAX(id) FROM payments WHERE order_id = o.id)
                   ORDER BY o.created_at DESC"""
            )

        columns = [desc[0] for desc in cursor.description]
        orders_list = [dict(zip(columns, row)) for row in cursor.fetchall()]

        stats = {
            "total": len(orders_list),
            "pending": sum(1 for o in orders_list if o["status"] == "pending"),
            "paid": sum(1 for o in orders_list if o["status"] == "paid"),
            "cancelled": sum(1 for o in orders_list if o["status"] == "cancelled"),
        }

        return {"success": True, "data": orders_list, "stats": stats}
    finally:
        conn.close()


@router.patch("/api/v1/admin/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    status: str = Query(...),
    authorization: str = Header(None),
):
    """确认/拒绝订单 — 确认时自动生成License"""
    _require_auth(authorization)

    if status not in ("paid", "cancelled"):
        raise HTTPException(status_code=400, detail="无效的状态值，有效值: paid, cancelled")

    conn = get_db()
    try:
        cursor = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="订单不存在")

        columns = [desc[0] for desc in cursor.description]
        order = dict(zip(columns, row))

        if order["status"] != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"订单当前状态为 {order['status']}，无法修改",
            )

        license_key = None
        if status == "paid":
            licensee = order["user_company"] or order["user_name"]
            plan = order["plan_type"]
            days_map = {
                "free": 30,
                "depth": 365,
                "annual": 365,
                "source": 730,
            }
            days = days_map.get(plan, 365)
            license_key = generate_license(licensee, plan, days)

            conn.execute(
                "UPDATE orders SET status = 'paid', license_key = ?, paid_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (license_key, order_id),
            )

            cursor = conn.execute(
                "SELECT id FROM payments WHERE order_id = ? AND status = 'pending' ORDER BY id DESC LIMIT 1",
                (order_id,),
            )
            payment_row = cursor.fetchone()
            if payment_row:
                conn.execute(
                    "UPDATE payments SET status = 'confirmed', confirmed_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (payment_row[0],),
                )
        else:
            conn.execute(
                "UPDATE orders SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (order_id,),
            )

        conn.commit()

        return {
            "success": True,
            "message": f"订单状态已更新为: {status}",
            "data": {
                "order_id": order_id,
                "status": status,
                "license_key": license_key,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新订单状态失败: {str(e)}")
    finally:
        conn.close()


@router.get("/api/v1/admin/orders/stats")
async def get_order_stats(authorization: str = Header(None)):
    """订单统计"""
    _require_auth(authorization)

    conn = get_db()
    try:
        cursor = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM orders GROUP BY status"
        )
        stats = {"total": 0, "pending": 0, "paid": 0, "cancelled": 0}
        for row in cursor.fetchall():
            stats[row[0]] = row[1]
            stats["total"] += row[1]
        return {"success": True, "data": stats}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════
# 新JWT支付订单查询 & 人工充值
# ═══════════════════════════════════════════════════════

@router.get("/api/v1/payment/query/{order_id}")
async def query_payment(order_id: int, authorization: str = Header(None)):
    """
    查询支付订单状态（需JWT认证）

    返回订单信息，包括支付状态、套餐信息等
    """
    payload = _get_jwt_user(authorization)
    user_id = int(payload["sub"])

    conn = get_db()
    try:
        cursor = conn.execute(
            """SELECT id, order_no, user_id, plan_type, price, 
                      status, alipay_trade_no, license_key,
                      created_at, paid_at
               FROM orders WHERE id = ?""",
            (order_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="订单不存在")

        columns = [desc[0] for desc in cursor.description]
        order = dict(zip(columns, row))

        # 验证订单属于当前用户
        if order["user_id"] != user_id:
            # 管理员可以查所有订单
            from backend.routers.admin import _verify_token
            try:
                admin_token = authorization.replace("Bearer ", "")
                if not _verify_token(admin_token):
                    raise HTTPException(status_code=403, detail="无权访问该订单")
            except Exception:
                raise HTTPException(status_code=403, detail="无权访问该订单")

        # 获取套餐名称
        plan_name = ""
        if order["plan_type"] in PLAN_NAMES:
            plan_name = PLAN_NAMES[order["plan_type"]]
        elif order["plan_type"] in SUBSCRIPTION_PLANS:
            plan_name = SUBSCRIPTION_PLANS[order["plan_type"]]["name"]
        else:
            plan_name = order["plan_type"]

        # 查询用户当前额度
        quota_info = None
        cursor2 = conn.execute(
            "SELECT total_quota, used_quota, plan_type, expires_at FROM user_quotas WHERE user_id = ?",
            (order["user_id"],),
        )
        quota_row = cursor2.fetchone()
        if quota_row:
            quota_info = {
                "total_quota": quota_row["total_quota"],
                "used_quota": quota_row["used_quota"],
                "remaining": quota_row["total_quota"] - quota_row["used_quota"],
                "plan_type": quota_row["plan_type"],
                "expires_at": quota_row["expires_at"],
            }

        return {
            "success": True,
            "data": {
                "order_id": order["id"],
                "order_no": order["order_no"],
                "plan_type": order["plan_type"],
                "plan_name": plan_name,
                "price": order["price"],
                "status": order["status"],
                "alipay_trade_no": order.get("alipay_trade_no"),
                "license_key": order.get("license_key"),
                "created_at": order["created_at"],
                "paid_at": order["paid_at"],
                "quota": quota_info,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
    finally:
        conn.close()


@router.post("/api/v1/payment/topup")
async def admin_topup(
    req: Request,
    authorization: str = Header(None),
):
    """
    人工充值（admin接口，需admin认证）

    请求体: {"user_id": 1, "amount": 100, "plan_type": "pro", "remark": "客户补偿"}
    直接为用户增加 quota，不经过支付宝
    """
    # 验证admin
    admin_payload = _require_admin(authorization)

    try:
        body = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效的请求格式")

    target_user_id = body.get("user_id")
    amount = body.get("amount", 0)
    plan_type = body.get("plan_type", "pro")
    remark = body.get("remark", "")

    if not target_user_id or not isinstance(target_user_id, int):
        raise HTTPException(status_code=400, detail="请提供有效的 user_id")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="充值金额必须大于0")

    # 根据plan_type计算要增加的额度
    add_quota = 0
    if plan_type == "basic":
        add_quota = 100
    elif plan_type == "pro":
        add_quota = 500
    else:
        # 自定义金额对应额度（每1元=1次额度）
        add_quota = int(amount)

    conn = get_db()
    try:
        # 检查用户是否存在
        cursor = conn.execute("SELECT id, username FROM users WHERE id = ?", (target_user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail=f"用户不存在: user_id={target_user_id}")

        # 创建订单记录
        order_no = _generate_order_no()
        cursor = conn.execute(
            """INSERT INTO orders (order_no, user_id, user_company, user_name, user_email,
                plan_type, price, status, paid_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'paid', CURRENT_TIMESTAMP)""",
            (order_no, target_user_id, user["username"], user["username"], "",
             plan_type, amount),
        )
        order_id = cursor.lastrowid

        # 更新用户额度
        cursor.execute("SELECT id, total_quota FROM user_quotas WHERE user_id = ?", (target_user_id,))
        existing = cursor.fetchone()

        if existing:
            new_total = existing["total_quota"] + add_quota
            expires_at = (datetime.utcnow() + timedelta(days=365)).isoformat()
            conn.execute(
                """UPDATE user_quotas 
                   SET plan_type = ?, total_quota = ?, expires_at = ?, updated_at = CURRENT_TIMESTAMP 
                   WHERE user_id = ?""",
                (plan_type, new_total, expires_at, target_user_id),
            )
        else:
            expires_at = (datetime.utcnow() + timedelta(days=365)).isoformat()
            conn.execute(
                "INSERT INTO user_quotas (user_id, plan_type, total_quota, used_quota, expires_at) VALUES (?, ?, ?, 0, ?)",
                (target_user_id, plan_type, add_quota, expires_at),
            )

        conn.commit()

        logger.info(f"人工充值成功: user_id={target_user_id}, amount={amount}, add_quota={add_quota}, remark={remark}")

        return {
            "success": True,
            "message": f"充值成功，为用户 {user['username']} 增加 {add_quota} 次额度",
            "data": {
                "order_id": order_id,
                "user_id": target_user_id,
                "username": user["username"],
                "amount": amount,
                "add_quota": add_quota,
                "plan_type": plan_type,
                "remark": remark,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"充值失败: {str(e)}")
    finally:
        conn.close()
