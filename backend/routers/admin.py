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

# 安全认证 — 必须从环境变量读取 ADMIN_USERNAME 和 ADMIN_PASSWORD
# 如果环境变量未设置，则抛出错误，强制要求配置，杜绝默认密码风险
# 生产环境必须通过 .env 或系统环境变量设置强密码！
_ADMIN_USER = os.environ.get("ADMIN_USERNAME")
_ADMIN_PASS = os.environ.get("ADMIN_PASSWORD")
if not _ADMIN_USER or not _ADMIN_PASS:
    raise RuntimeError(
        "请设置环境变量 ADMIN_USERNAME 和 ADMIN_PASSWORD！"
        "请在 .env 文件中配置管理员用户名和密码，"
        "生产环境务必使用强密码。"
    )
ADMIN_USER = _ADMIN_USER
ADMIN_PASS = _ADMIN_PASS
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

        # 发送支付成功通知
        if req.status == "paid":
            try:
                from backend.services.email_service import (
                    send_payment_success_notification,
                    send_payment_notification_to_sales,
                )
                order_with_key = dict(order)
                order_with_key["license_key"] = license_key
                send_payment_success_notification(order_with_key)
                send_payment_notification_to_sales(order_with_key)
            except ImportError:
                pass
            except Exception:
                pass

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


# ═══════════════════════════════════════════════════════
# 销售漏斗 API
# ═══════════════════════════════════════════════════════

FUNNEL_STAGES = ["new_lead", "contacting", "quoting", "closed_won"]

FUNNEL_LABELS = {
    "new_lead": ("新线索", "새 리드"),
    "contacting": ("跟进中", "연락 중"),
    "quoting": ("报价中", "견적 중"),
    "closed_won": ("已成交", "계약 완료"),
}


@router.patch("/api/v1/admin/leads/{lead_id}/stage")
async def update_lead_stage(
    lead_id: int,
    table: str = Query(...),
    stage: str = Query(...),
    authorization: str = Header(None),
):
    """更新线索的销售漏斗阶段"""
    _require_auth(authorization)

    if table not in TABLE_NAMES:
        raise HTTPException(status_code=404, detail="表不存在")
    if stage not in FUNNEL_STAGES:
        raise HTTPException(status_code=400, detail=f"阶段无效，有效值: {', '.join(FUNNEL_STAGES)}")

    conn = get_db()
    try:
        cursor = conn.execute(
            f"UPDATE {table} SET stage = ?, stage_changed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (stage, lead_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="线索不存在")
        conn.commit()
        return {"success": True, "message": f"阶段已更新为: {stage}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新阶段失败: {str(e)}")
    finally:
        conn.close()


@router.get("/api/v1/admin/funnel")
async def get_funnel(authorization: str = Header(None)):
    """获取销售漏斗各阶段数据"""
    _require_auth(authorization)

    conn = get_db()
    try:
        result = {}
        for stage in FUNNEL_STAGES:
            items = []
            for tbl in TABLE_NAMES:
                columns = TABLE_COLUMNS.get(tbl, [])
                if not columns:
                    cursor = conn.execute(f"PRAGMA table_info({tbl})")
                    columns = [row[1] for row in cursor.fetchall()]
                    TABLE_COLUMNS[tbl] = columns

                col_str = ", ".join(columns)
                cursor = conn.execute(
                    f"SELECT {col_str} FROM {tbl} WHERE stage = ? ORDER BY created_at DESC",
                    (stage,),
                )
                for row in cursor.fetchall():
                    item = dict(zip(columns, row))
                    item["_table"] = tbl
                    item["_label"] = TABLE_LABELS.get(tbl, tbl)
                    # 计算阶段停留天数
                    changed_at = item.get("stage_changed_at") or item.get("created_at")
                    if changed_at:
                        try:
                            from datetime import datetime
                            changed_dt = datetime.strptime(changed_at[:19], "%Y-%m-%d %H:%M:%S")
                            item["stage_days"] = (datetime.now() - changed_dt).days
                        except Exception:
                            item["stage_days"] = 0
                    else:
                        item["stage_days"] = 0
                    items.append(item)

            label = FUNNEL_LABELS.get(stage, (stage, stage))
            result[stage] = {
                "label_zh": label[0],
                "label_ko": label[1],
                "count": len(items),
                "items": items,
            }

        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取漏斗数据失败: {str(e)}")
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════
# 报价管理 API
# ═══════════════════════════════════════════════════════

QUOTE_PLANS = [
    {"name": "免费初评", "name_ko": "무료 초기 평가", "price": 0, "key": "free"},
    {"name": "深度方案", "name_ko": "심층 컨설팅", "price": 9800, "key": "depth"},
    {"name": "年度订阅", "name_ko": "연간 구독", "price": 58000, "key": "annual"},
]


class QuoteCreate(BaseModel):
    lead_table: str
    lead_id: int
    plan_key: str


@router.get("/api/v1/admin/quotes")
async def get_quotes(authorization: str = Header(None)):
    """获取报价列表"""
    _require_auth(authorization)

    conn = get_db()
    try:
        cursor = conn.execute("SELECT * FROM quotes ORDER BY created_at DESC")
        columns = [desc[0] for desc in cursor.description]
        quotes = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return {"success": True, "data": quotes, "total": len(quotes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取报价失败: {str(e)}")
    finally:
        conn.close()


@router.post("/api/v1/admin/quotes")
async def create_quote(req: QuoteCreate, authorization: str = Header(None)):
    """创建报价"""
    _require_auth(authorization)

    if req.lead_table not in TABLE_NAMES:
        raise HTTPException(status_code=400, detail="无效的线索表")

    plan = None
    for p in QUOTE_PLANS:
        if p["key"] == req.plan_key:
            plan = p
            break
    if not plan:
        raise HTTPException(status_code=400, detail="无效的方案")

    conn = get_db()
    try:
        # 查询线索
        columns = TABLE_COLUMNS.get(req.lead_table, [])
        if not columns:
            cursor = conn.execute(f"PRAGMA table_info({req.lead_table})")
            columns = [row[1] for row in cursor.fetchall()]
            TABLE_COLUMNS[req.lead_table] = columns

        col_str = ", ".join(columns)
        cursor = conn.execute(f"SELECT {col_str} FROM {req.lead_table} WHERE id = ?", (req.lead_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="线索不存在")

        lead = dict(zip(columns, row))

        # 生成报价编号
        cursor = conn.execute("SELECT COUNT(*) FROM quotes")
        count = cursor.fetchone()[0]
        quote_no = f"QTE{datetime.now().strftime('%Y%m%d')}{count + 1:04d}"

        cursor = conn.execute(
            """INSERT INTO quotes (quote_no, lead_table, lead_id, lead_name, lead_company, lead_email, plan_name, plan_price, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft')""",
            (quote_no, req.lead_table, req.lead_id,
             lead.get("name", ""), lead.get("company", ""),
             lead.get("email", ""), plan["name"], plan["price"]),
        )
        conn.commit()
        quote_id = cursor.lastrowid

        # 自动将线索阶段改为"报价中"
        conn.execute(
            f"UPDATE {req.lead_table} SET stage = 'quoting', stage_changed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (req.lead_id,),
        )
        conn.commit()

        # 尝试发送报价邮件
        try:
            from backend.services.email_service import send_quote_to_customer
            quote_info = {
                "company": lead.get("company", ""),
                "plan_name": plan["name"],
                "price": plan["price"],
                "quote_no": quote_no,
                "items": [
                    {"name": plan["name"], "price": plan["price"]},
                ],
            }
            send_quote_to_customer(lead.get("email", ""), lead.get("name", ""), quote_info)
        except ImportError:
            pass
        except Exception:
            pass

        return {
            "success": True,
            "data": {
                "id": quote_id,
                "quote_no": quote_no,
                "plan_name": plan["name"],
                "plan_price": plan["price"],
            },
            "message": f"报价已生成: {quote_no}",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建报价失败: {str(e)}")
    finally:
        conn.close()


class QuoteSendRequest(BaseModel):
    action: str  # "send" or "accept" or "reject"


@router.patch("/api/v1/admin/quotes/{quote_id}")
async def update_quote(
    quote_id: int,
    req: QuoteSendRequest,
    authorization: str = Header(None),
):
    """更新报价状态（发送/接受/拒绝）"""
    _require_auth(authorization)

    valid_actions = {"send": "sent", "accept": "accepted", "reject": "rejected"}
    if req.action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"无效操作: {req.action}")

    new_status = valid_actions[req.action]

    conn = get_db()
    try:
        cursor = conn.execute("SELECT * FROM quotes WHERE id = ?", (quote_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="报价不存在")

        columns = [desc[0] for desc in cursor.description]
        quote = dict(zip(columns, row))

        if req.action == "send":
            conn.execute(
                "UPDATE quotes SET status = ?, sent_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_status, quote_id),
            )

            # 发送报价邮件
            try:
                from backend.services.email_service import send_quote_to_customer
                send_quote_to_customer(
                    quote["lead_email"],
                    quote["lead_name"],
                    {
                        "company": quote["lead_company"],
                        "plan_name": quote["plan_name"],
                        "price": quote["plan_price"],
                        "quote_no": quote["quote_no"],
                        "items": [{"name": quote["plan_name"], "price": quote["plan_price"]}],
                    },
                )
            except ImportError:
                pass
            except Exception:
                pass
        else:
            conn.execute(
                "UPDATE quotes SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_status, quote_id),
            )

            # 如果接受报价，将线索阶段改为"已成交"
            if req.action == "accept":
                conn.execute(
                    f"UPDATE {quote['lead_table']} SET stage = 'closed_won', stage_changed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (quote["lead_id"],),
                )

        conn.commit()
        return {"success": True, "message": f"报价已{req.action}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新报价失败: {str(e)}")
    finally:
        conn.close()
