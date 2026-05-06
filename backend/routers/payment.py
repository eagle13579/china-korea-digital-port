"""
中韩出海数智港 - 支付系统API路由（统一版）
沙箱模式：创建订单 → 上传付款凭证(Multipart) → 管理员审核确认 → License自动生成

合并自：烛龙版(payment.py) + 乘黄版(order.py)
统一API路由：/api/v1/orders/*
凭证存储：backend/data/vouchers/
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Header
from typing import Optional
from backend.database import get_db
from backend.license import generate_license

router = APIRouter(tags=["payment"])

# 凭证图片存储路径
VOUCHER_DIR = Path(__file__).parent.parent / "data" / "vouchers"
VOUCHER_DIR.mkdir(parents=True, exist_ok=True)

# ── 套餐定价映射 ──────────────────────────────────────
PLAN_PRICES = {
    "free": 0,
    "depth": 999.00,    # 深度方案 ¥999
    "annual": 9999.00,  # 年订阅 ¥9,999
    "source": 29999.00, # 源码授权 ¥29,999
}

PLAN_NAMES = {
    "free": "免费初评",
    "depth": "深度方案",
    "annual": "年订阅",
    "source": "源码授权",
}


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
        return "png"  # 默认


def _require_auth(authorization: str = Header(None)):
    """验证管理员认证"""
    from backend.routers.admin import _verify_token
    if not authorization:
        raise HTTPException(status_code=401, detail="未授权")
    token = authorization.replace("Bearer ", "")
    if not _verify_token(token):
        raise HTTPException(status_code=401, detail="token已过期，请重新登录")


# ── 订单API ───────────────────────────────────────────

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
    # 验证套餐类型
    if plan_type not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail=f"不支持的套餐类型: {plan_type}")

    # 验证价格匹配（防止篡改）
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


# 兼容JSON格式的创建订单（pricing-v2.html用）
@router.post("/api/v1/order/create")
async def create_order_json(
    body: dict,
):
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
        # 验证订单存在且为待支付状态
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

        # 保存上传的凭证文件
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

        # 创建付款记录
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
            # 确认支付 —— 自动生成License
            licensee = order["user_company"] or order["user_name"]
            plan = order["plan_type"]

            # 根据套餐类型设置授权天数
            days_map = {
                "free": 30,
                "depth": 365,
                "annual": 365,
                "source": 730,  # 源码授权2年
            }
            days = days_map.get(plan, 365)

            license_key = generate_license(licensee, plan, days)

            # 更新订单：状态 + License
            conn.execute(
                "UPDATE orders SET status = 'paid', license_key = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (license_key, order_id),
            )

            # 标记最近的付款记录为已确认
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
            # 拒绝订单
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
