"""
中韩出海数智港 - 支付系统API路由
集成支付宝当面付（扫码支付）+ Stripe备用方案

API端点:
  POST /api/v1/payment/create — 创建订单，返回支付二维码/链接
  POST /api/v1/payment/notify — 支付宝支付回调通知
  GET  /api/v1/payment/status/{order_id} — 查询支付状态

还保留兼容旧版订单API:
  POST /api/v1/orders — 创建订单（form）
  POST /api/v1/order/create — 创建订单（JSON）
  GET  /api/v1/orders/{order_id} — 查询订单
  POST /api/v1/orders/{order_id}/payment — 上传付款凭证
"""

import os
import uuid
import json
import logging
from datetime import datetime
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


# ═══════════════════════════════════════════════════════
# 新支付系统 API (面向 checkout.html)
# ═══════════════════════════════════════════════════════

class PaymentCreateRequest(BaseModel):
    """创建支付订单请求"""
    plan_type: str = Field(..., pattern=r'^(free|depth|annual|source)$', description="套餐类型")
    customer_name: str = Field(..., min_length=1, max_length=100, description="联系人姓名")
    customer_email: str = Field(..., description="电子邮箱")
    customer_company: Optional[str] = Field(None, max_length=200, description="企业名称")
    customer_phone: Optional[str] = Field(None, max_length=50, description="联系电话")


@router.post("/api/v1/payment/create")
async def create_payment(req: PaymentCreateRequest):
    """
    创建支付订单，返回支付宝支付二维码链接

    流程:
    1. 校验套餐类型和价格
    2. 在数据库中创建订单记录
    3. 调用支付宝当面付 API 生成二维码
    4. 返回支付信息给前端
    """
    plan_type = req.plan_type
    if plan_type not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail=f"不支持的套餐类型: {plan_type}")

    price = PLAN_PRICES[plan_type]
    order_no = _generate_order_no()

    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO orders (
                order_no, user_company, user_name, user_phone, user_email,
                plan_type, price, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (order_no, req.customer_company or "", req.customer_name,
             req.customer_phone or "", req.customer_email,
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
            # 描述订单信息
            subject = f"中韩出海数智港 - {PLAN_NAMES.get(plan_type, plan_type)}"

            # 当面付 (Face-to-Face) 预创建订单
            # 使用 alipay.trade.precreate 接口
            result = alipay_client.api_alipay_trade_precreate(
                subject=subject,
                out_trade_no=order_no,
                total_amount=price,
                quit_url="",  # 可选：用户付款中途退出返回的URL
            )

            if result.get("code") == "10000":
                qr_code_url = result.get("qr_code")
                alipay_trade_no = result.get("trade_no")
                logger.info(f"支付宝订单创建成功: order_no={order_no}, qr_code={qr_code_url}")
            else:
                logger.warning(f"支付宝预创建失败: {result.get('code')} - {result.get('msg')} - {result.get('sub_msg')}")
                # 降级: 返回模拟二维码
        except Exception as e:
            logger.error(f"调用支付宝API异常: {e}")
            # 降级处理

    # 如果支付宝不可用或金额为0，生成模拟支付二维码
    if price == 0:
        # 免费方案：直接标记为已支付
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

        return {
            "success": True,
            "order_id": order_id,
            "order_no": order_no,
            "price": price,
            "plan_type": plan_type,
            "plan_name": PLAN_NAMES.get(plan_type, plan_type),
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
            "plan_name": PLAN_NAMES.get(plan_type, plan_type),
            "status": "pending",
            "qr_code_url": qr_code_url,
            "alipay_trade_no": alipay_trade_no,
            "message": "订单创建成功，请扫码支付",
            "is_free": False,
        }
    else:
        # 支付宝未配置，返回模拟支付模式
        return {
            "success": True,
            "order_id": order_id,
            "order_no": order_no,
            "price": price,
            "plan_type": plan_type,
            "plan_name": PLAN_NAMES.get(plan_type, plan_type),
            "status": "pending",
            "qr_code_url": None,
            "alipay_trade_no": None,
            "message": "订单创建成功（演示模式，请联系客服完成支付）",
            "is_free": False,
            "simulate_mode": True,
        }


@router.post("/api/v1/payment/notify")
async def payment_notify(request: Request):
    """
    支付宝异步支付回调通知

    支付宝 POST 方式通知，参数以 form-data 格式发送
    需要验证签名并处理订单状态更新
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

