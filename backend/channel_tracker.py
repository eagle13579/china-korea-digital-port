"""
中韩出海数智港 - 渠道/KOI追踪系统
PRD-009: 渠道注册、追踪、订单归因、佣金计算
"""
import random
import string
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse

from backend.database import get_db


# ── Pydantic 模型 ────────────────────────────────────

class ChannelRegister(BaseModel):
    """注册新渠道请求"""
    name: str = Field(..., min_length=1, max_length=100, description="渠道名称")
    contact: Optional[str] = Field(None, max_length=100, description="联系方式")
    type: str = Field(..., pattern=r'^(KOI|渠道|合作方)$', description="类型: KOI/渠道/合作方")
    commission_rate: float = Field(0.0, ge=0.0, le=1.0, description="佣金比例(0~1)")


class ChannelUpdate(BaseModel):
    """更新渠道信息请求"""
    name: Optional[str] = Field(None, max_length=100)
    contact: Optional[str] = Field(None, max_length=100)
    type: Optional[str] = Field(None, pattern=r'^(KOI|渠道|合作方)$')
    commission_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    status: Optional[str] = Field(None, pattern=r'^(active|inactive)$')


class CommissionCalculate(BaseModel):
    """计算佣金请求"""
    order_id: int = Field(..., description="订单ID")
    ref_code: str = Field(..., min_length=7, max_length=7, description="渠道ref_code")
    order_amount: float = Field(..., ge=0, description="订单金额")


# ── 工具函数 ─────────────────────────────────────────

def generate_ref_code() -> str:
    """生成唯一ref_code：CH-XXXX (X为大写字母+数字)"""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = "CH-" + "".join(random.choices(chars, k=4))
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM channels WHERE ref_code = ?", (code,))
        exists = cursor.fetchone()
        conn.close()
        if not exists:
            return code


def get_session_ref_code(request: Request) -> Optional[str]:
    """从请求中提取渠道ref_code（优先URL参数，其次Cookie）"""
    ref = request.query_params.get("ref")
    if ref and ref.startswith("CH-") and len(ref) == 7:
        return ref
    ref = request.cookies.get("channel_ref")
    if ref and ref.startswith("CH-") and len(ref) == 7:
        return ref
    return None


def record_tracking(ref_code: str, request: Request):
    """记录一次渠道引流访问"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        ip = request.client.host if request.client else None
        session_id = request.headers.get("x-session-id", None)
        cursor.execute(
            """INSERT INTO channel_tracking (ref_code, visitor_ip, visitor_session, page_url, ref_params)
               VALUES (?, ?, ?, ?, ?)""",
            (ref_code, ip, session_id, str(request.url.path), str(request.query_params)),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # 追踪失败不影响正常请求


# ── 渠道中间件：自动追踪 + 设置Cookie ──────────────

CHANNEL_REF_COOKIE = "channel_ref"


async def channel_tracking_middleware(request: Request, call_next):
    """在 app 中间件中使用：自动检测 ?ref=CH-XXXX 并记录追踪"""
    response = await call_next(request)
    # 检查URL中是否有ref参数
    ref = request.query_params.get("ref")
    if ref and ref.startswith("CH-") and len(ref) == 7:
        # 记录追踪
        record_tracking(ref, request)
        # 设置Cookie（30天有效）
        response.set_cookie(
            key=CHANNEL_REF_COOKIE,
            value=ref,
            max_age=30 * 24 * 3600,
            path="/",
            httponly=True,
            samesite="lax",
        )
    return response


def attribute_order(order_id: int, request: Request) -> bool:
    """订单归因：将订单与渠道关联（如果session中有ref_code）"""
    ref = get_session_ref_code(request)
    if not ref:
        return False
    conn = get_db()
    cursor = conn.cursor()
    # 检查渠道是否存在且有效
    cursor.execute("SELECT commission_rate FROM channels WHERE ref_code = ? AND status = 'active'", (ref,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    commission_rate = row["commission_rate"]
    # 检查订单金额
    cursor.execute("SELECT price FROM orders WHERE id = ?", (order_id,))
    order_row = cursor.fetchone()
    if not order_row:
        conn.close()
        return False
    order_amount = order_row["price"]
    commission_amount = order_amount * commission_rate
    # 记录订单归因（防止重复）
    cursor.execute(
        "SELECT id FROM channel_orders WHERE order_id = ? AND ref_code = ?",
        (order_id, ref),
    )
    if cursor.fetchone():
        conn.close()
        return True  # 已存在，视为成功
    cursor.execute(
        """INSERT INTO channel_orders (order_id, ref_code, commission_rate, commission_amount, order_amount)
           VALUES (?, ?, ?, ?, ?)""",
        (order_id, ref, commission_rate, commission_amount, order_amount),
    )
    conn.commit()
    conn.close()
    return True


# ── API 路由 ─────────────────────────────────────────

router = APIRouter(prefix="/api/channel", tags=["channel_tracker"])


@router.post("/register")
async def register_channel(data: ChannelRegister):
    """注册新渠道/KOI，自动生成唯一ref_code"""
    try:
        ref_code = generate_ref_code()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO channels (name, contact, type, commission_rate, ref_code, status)
               VALUES (?, ?, ?, ?, ?, 'active')""",
            (data.name, data.contact, data.type, data.commission_rate, ref_code),
        )
        conn.commit()
        channel_id = cursor.lastrowid
        conn.close()
        return {
            "success": True,
            "message": "渠道注册成功",
            "data": {
                "id": channel_id,
                "ref_code": ref_code,
                "name": data.name,
                "type": data.type,
                "commission_rate": data.commission_rate,
                "status": "active",
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")


@router.get("/list")
async def list_channels(
    status: Optional[str] = Query(None, regex=r'^(active|inactive)$'),
    type_filter: Optional[str] = Query(None, alias="type", regex=r'^(KOI|渠道|合作方)$'),
):
    """渠道列表（带引流数、转化数、佣金统计）"""
    conn = get_db()
    cursor = conn.cursor()

    where_clauses = []
    params = []
    if status:
        where_clauses.append("c.status = ?")
        params.append(status)
    if type_filter:
        where_clauses.append("c.type = ?")
        params.append(type_filter)

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    cursor.execute(f"""
        SELECT
            c.id, c.name, c.contact, c.type, c.commission_rate,
            c.ref_code, c.status, c.created_at,
            COALESCE(ct.track_count, 0) AS traffic_count,
            COALESCE(co.order_count, 0) AS conversion_count,
            COALESCE(co.total_commission, 0.0) AS total_commission,
            COALESCE(co.total_amount, 0.0) AS total_order_amount
        FROM channels c
        LEFT JOIN (
            SELECT ref_code, COUNT(*) AS track_count
            FROM channel_tracking
            GROUP BY ref_code
        ) ct ON c.ref_code = ct.ref_code
        LEFT JOIN (
            SELECT ref_code,
                   COUNT(*) AS order_count,
                   SUM(commission_amount) AS total_commission,
                   SUM(order_amount) AS total_amount
            FROM channel_orders
            GROUP BY ref_code
        ) co ON c.ref_code = co.ref_code
        {where_sql}
        ORDER BY c.created_at DESC
    """, params)
    rows = cursor.fetchall()
    conn.close()

    channels = []
    for r in rows:
        channels.append({
            "id": r["id"],
            "name": r["name"],
            "contact": r["contact"],
            "type": r["type"],
            "commission_rate": r["commission_rate"],
            "ref_code": r["ref_code"],
            "status": r["status"],
            "created_at": r["created_at"],
            "traffic_count": r["traffic_count"],
            "conversion_count": r["conversion_count"],
            "total_commission": round(r["total_commission"], 2),
            "total_order_amount": round(r["total_order_amount"], 2),
        })

    return {"success": True, "data": channels, "total": len(channels)}


@router.get("/stats")
async def channel_stats():
    """渠道数据概览"""
    conn = get_db()
    cursor = conn.cursor()

    # 总渠道数
    cursor.execute("SELECT COUNT(*) FROM channels")
    total_channels = cursor.fetchone()[0]

    # 活跃渠道数
    cursor.execute("SELECT COUNT(*) FROM channels WHERE status = 'active'")
    active_channels = cursor.fetchone()[0]

    # 总引流数
    cursor.execute("SELECT COUNT(*) FROM channel_tracking")
    total_traffic = cursor.fetchone()[0]

    # 总转化数
    cursor.execute("SELECT COUNT(*) FROM channel_orders")
    total_conversions = cursor.fetchone()[0]

    # 总佣金
    cursor.execute("SELECT COALESCE(SUM(commission_amount), 0.0) FROM channel_orders")
    total_commission = cursor.fetchone()[0]

    # 各类型分布
    cursor.execute("""
        SELECT type, COUNT(*) as cnt FROM channels GROUP BY type
    """)
    type_distribution = {r["type"]: r["cnt"] for r in cursor.fetchall()}

    # 各渠道TOP10（按引流数排序）
    cursor.execute("""
        SELECT c.name, c.ref_code, c.type,
               COALESCE(ct.track_count, 0) AS traffic_count,
               COALESCE(co.order_count, 0) AS conversion_count,
               COALESCE(co.total_commission, 0.0) AS total_commission
        FROM channels c
        LEFT JOIN (
            SELECT ref_code, COUNT(*) AS track_count
            FROM channel_tracking
            GROUP BY ref_code
        ) ct ON c.ref_code = ct.ref_code
        LEFT JOIN (
            SELECT ref_code, COUNT(*) AS order_count,
                   SUM(commission_amount) AS total_commission
            FROM channel_orders
            GROUP BY ref_code
        ) co ON c.ref_code = co.ref_code
        ORDER BY ct.track_count DESC NULLS LAST
        LIMIT 10
    """)
    top_channels = []
    for r in cursor.fetchall():
        top_channels.append({
            "name": r["name"],
            "ref_code": r["ref_code"],
            "type": r["type"],
            "traffic_count": r["traffic_count"],
            "conversion_count": r["conversion_count"],
            "total_commission": round(r["total_commission"], 2),
        })

    conn.close()

    conversion_rate = round(total_conversions / total_traffic * 100, 2) if total_traffic > 0 else 0.0

    return {
        "success": True,
        "data": {
            "total_channels": total_channels,
            "active_channels": active_channels,
            "total_traffic": total_traffic,
            "total_conversions": total_conversions,
            "conversion_rate": conversion_rate,
            "total_commission": round(total_commission, 2),
            "type_distribution": type_distribution,
            "top_channels": top_channels,
        },
    }


@router.post("/commission/calculate")
async def calculate_commission(data: CommissionCalculate):
    """计算佣金（不实际支付，仅计算和记录）"""
    conn = get_db()
    cursor = conn.cursor()

    # 验证渠道
    cursor.execute("SELECT * FROM channels WHERE ref_code = ?", (data.ref_code,))
    channel = cursor.fetchone()
    if not channel:
        conn.close()
        raise HTTPException(status_code=404, detail="渠道不存在")

    # 验证订单
    cursor.execute("SELECT * FROM orders WHERE id = ?", (data.order_id,))
    order = cursor.fetchone()
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="订单不存在")

    commission_amount = data.order_amount * channel["commission_rate"]

    # 检查是否已有记录
    cursor.execute(
        "SELECT id FROM channel_orders WHERE order_id = ? AND ref_code = ?",
        (data.order_id, data.ref_code),
    )
    existing = cursor.fetchone()

    if existing:
        conn.close()
        return {
            "success": True,
            "message": "该订单已关联此渠道，佣金已存在",
            "data": {
                "channel_name": channel["name"],
                "ref_code": data.ref_code,
                "order_id": data.order_id,
                "order_amount": data.order_amount,
                "commission_rate": channel["commission_rate"],
                "commission_amount": round(commission_amount, 2),
                "already_recorded": True,
            },
        }

    # 记录佣金
    cursor.execute(
        """INSERT INTO channel_orders (order_id, ref_code, commission_rate, commission_amount, order_amount)
           VALUES (?, ?, ?, ?, ?)""",
        (data.order_id, data.ref_code, channel["commission_rate"], commission_amount, data.order_amount),
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "佣金计算完成",
        "data": {
            "channel_name": channel["name"],
            "ref_code": data.ref_code,
            "order_id": data.order_id,
            "order_amount": data.order_amount,
            "commission_rate": channel["commission_rate"],
            "commission_amount": round(commission_amount, 2),
            "already_recorded": False,
        },
    }
