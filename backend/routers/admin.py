"""
管理后台API路由
包含：登录认证、线索CRUD、状态管理、统计、订单管理
"""
import sqlite3
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional
from backend.database import get_db, DB_PATH
from backend.license import generate_license

router = APIRouter(tags=["admin"])

# 简单认证 — 从环境变量读取（Phase 2 换JWT）
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")
TOKEN_SECRET = os.environ.get("TOKEN_SECRET", "china-korea-digital-port-2026")
TOKENS = {}  # token -> expiry

TABLE_NAMES = ["contacts", "demo_requests", "pricing_inquiries"]

TABLE_LABELS = {
    "contacts": "联系咨询",
    "demo_requests": "预约演示",
    "pricing_inquiries": "定价咨询",
}

# 套餐定价映射（与 payment.py 一致）
PLAN_PRICES = {
    "free": 0,
    "depth": 999.00,
    "annual": 9999.00,
    "source": 29999.00,
}

PLAN_NAMES = {
    "free": "免费初评",
    "depth": "深度方案",
    "annual": "年订阅",
    "source": "源码授权",
}

TABLE_COLUMNS = {}


def _refresh_columns():
    """刷新所有表的列信息"""
    global TABLE_COLUMNS
    conn = get_db()
    for table in TABLE_NAMES:
        cursor = conn.execute(f"PRAGMA table_info({table})")
        TABLE_COLUMNS[table] = [row[1] for row in cursor.fetchall()]
    conn.close()


def _generate_token() -> str:
    """生成简单token"""
    raw = f"{ADMIN_USER}:{datetime.now().timestamp()}:{TOKEN_SECRET}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _verify_token(token: str) -> bool:
    """验证token"""
    if token in TOKENS:
        expiry = TOKENS[token]
        if datetime.now() < expiry:
            return True
        del TOKENS[token]
    return False


# ---------- 认证接口 ----------

class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/api/v1/admin/login")
async def admin_login(req: LoginRequest):
    """管理员登录"""
    if req.username == ADMIN_USER and req.password == ADMIN_PASS:
        token = _generate_token()
        TOKENS[token] = datetime.now() + timedelta(hours=8)
        _refresh_columns()
        return {"success": True, "token": token, "message": "登录成功"}
    raise HTTPException(status_code=401, detail="用户名或密码错误")


# ---------- 线索查询接口 ----------

def _require_auth(authorization: str = Header(None)):
    """验证请求认证"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未授权")
    token = authorization.replace("Bearer ", "")
    if not _verify_token(token):
        raise HTTPException(status_code=401, detail="token已过期，请重新登录")


@router.get("/api/v1/admin/leads")
async def get_leads(
    table: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    authorization: str = Header(None),
):
    """获取所有线索，可按表和状态筛选"""
    _require_auth(authorization)

    conn = get_db()
    results = []

    tables_to_query = [table] if table and table in TABLE_NAMES else TABLE_NAMES

    for t in tables_to_query:
        columns = TABLE_COLUMNS.get(t, [])
        if not columns:
            cursor = conn.execute(f"PRAGMA table_info({t})")
            columns = [row[1] for row in cursor.fetchall()]
            TABLE_COLUMNS[t] = columns

        # 构建查询
        col_str = ", ".join(columns)
        where_clause = ""
        params = []
        if status:
            where_clause = "WHERE status = ?"
            params = [status]

        cursor = conn.execute(
            f"SELECT {col_str} FROM {t} {where_clause} ORDER BY created_at DESC",
            params,
        )
        for row in cursor.fetchall():
            item = dict(zip(columns, row))
            item["_table"] = t
            item["_label"] = TABLE_LABELS.get(t, t)
            results.append(item)

    conn.close()
    return {"success": True, "data": results, "total": len(results)}


@router.get("/api/v1/admin/leads/{table}/{item_id}")
async def get_lead_detail(table: str, item_id: int, authorization: str = Header(None)):
    """获取单条线索详情"""
    _require_auth(authorization)

    if table not in TABLE_NAMES:
        raise HTTPException(status_code=404, detail="表不存在")

    conn = get_db()
    columns = TABLE_COLUMNS.get(table, [])
    if not columns:
        cursor = conn.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        TABLE_COLUMNS[table] = columns

    col_str = ", ".join(columns)
    cursor = conn.execute(f"SELECT {col_str} FROM {table} WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="线索不存在")

    item = dict(zip(columns, row))
    item["_table"] = table
    return {"success": True, "data": item}


# ---------- 状态管理接口 ----------

VALID_STATUSES = {
    "contacts": ["new", "contacted", "qualified", "lost"],
    "demo_requests": ["pending", "confirmed", "completed", "cancelled"],
    "pricing_inquiries": ["new", "contacted", "negotiating", "closed", "lost"],
}


@router.patch("/api/v1/admin/leads/{table}/{item_id}/status")
async def update_lead_status(
    table: str, item_id: int, status: str = Query(...),
    authorization: str = Header(None),
):
    """更新线索状态"""
    _require_auth(authorization)

    if table not in TABLE_NAMES:
        raise HTTPException(status_code=404, detail="表不存在")

    valid = VALID_STATUSES.get(table, ["new", "contacted", "closed"])
    if status not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"状态无效，有效值: {', '.join(valid)}",
        )

    conn = get_db()
    conn.execute(
        f"UPDATE {table} SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, item_id),
    )
    conn.commit()
    conn.close()

    return {"success": True, "message": f"状态已更新为: {status}"}


# ---------- 统计接口 ----------

@router.get("/api/v1/admin/stats")
async def get_stats(authorization: str = Header(None)):
    """获取线索统计"""
    _require_auth(authorization)

    conn = get_db()
    stats = {}

    for table in TABLE_NAMES:
        columns = TABLE_COLUMNS.get(table, [])
        if not columns:
            cursor = conn.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            TABLE_COLUMNS[table] = columns

        # 总数
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
        total = cursor.fetchone()[0]

        # 各状态分布
        cursor = conn.execute(
            f"SELECT status, COUNT(*) as cnt FROM {table} GROUP BY status"
        )
        status_dist = {row[0]: row[1] for row in cursor.fetchall()}

        # 今日新增
        cursor = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE date(created_at) = date('now')"
        )
        today_new = cursor.fetchone()[0]

        stats[table] = {
            "label": TABLE_LABELS.get(table, table),
            "total": total,
            "today_new": today_new,
            "status_distribution": status_dist,
        }

    # 合计统计
    cursor = conn.execute(
        "SELECT COUNT(*) FROM ("
        "SELECT id FROM contacts UNION ALL "
        "SELECT id FROM demo_requests UNION ALL "
        "SELECT id FROM pricing_inquiries"
        ")"
    )
    grand_total = cursor.fetchone()[0]

    cursor = conn.execute(
        "SELECT COUNT(*) FROM ("
        "SELECT id FROM contacts WHERE date(created_at) = date('now') UNION ALL "
        "SELECT id FROM demo_requests WHERE date(created_at) = date('now') UNION ALL "
        "SELECT id FROM pricing_inquiries WHERE date(created_at) = date('now')"
        ")"
    )
    today_total = cursor.fetchone()[0]

    conn.close()

    return {
        "success": True,
        "data": {
            "grand_total": grand_total,
            "today_total": today_total,
            "by_table": stats,
        },
    }


# ── 订单管理接口 ──────────────────────────────────────


@router.get("/api/v1/admin/orders")
async def get_orders(
    status: Optional[str] = Query(None),
    authorization: str = Header(None),
):
    """获取订单列表，可按状态筛选"""
    _require_auth(authorization)

    conn = get_db()
    try:
        if status:
            cursor = conn.execute(
                "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC",
                (status,),
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM orders ORDER BY created_at DESC"
            )

        columns = [desc[0] for desc in cursor.description]
        orders = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # 为每个订单附带付款信息
        for order in orders:
            pc = conn.execute(
                "SELECT id, method, amount, status, confirmed_at FROM payments WHERE order_id = ? ORDER BY id DESC LIMIT 1",
                (order["id"],),
            )
            p_row = pc.fetchone()
            if p_row:
                p_cols = [desc[0] for desc in pc.description]
                order["latest_payment"] = dict(zip(p_cols, p_row))
            else:
                order["latest_payment"] = None

        return {"success": True, "data": orders, "total": len(orders)}
    finally:
        conn.close()


class OrderStatusRequest(BaseModel):
    """订单状态更新请求"""
    status: str


@router.patch("/api/v1/admin/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    req: OrderStatusRequest,
    authorization: str = Header(None),
):
    """确认/拒绝订单 — 确认时自动生成License"""
    _require_auth(authorization)

    valid_statuses = ["paid", "cancelled"]
    if req.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"状态无效，有效值: {', '.join(valid_statuses)}",
        )

    conn = get_db()
    try:
        # 查询订单
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

        # 更新订单状态
        conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (req.status, order_id),
        )

        license_key = None
        if req.status == "paid":
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

            # 查找该订单最近的付款记录并标记为已确认
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

        conn.commit()

        return {
            "success": True,
            "message": f"订单状态已更新为: {req.status}",
            "data": {
                "order_id": order_id,
                "status": req.status,
                "license_key": license_key,
            },
        }
    finally:
        conn.close()
