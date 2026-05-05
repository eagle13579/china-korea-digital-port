"""
管理后台API路由
包含：登录认证、线索CRUD、状态管理、统计
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
