"""
中韩出海数智港 - 会员管理API路由
会员列表、详情、充值、暂停
admin认证（Bearer token，复用admin.py的token验证）
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel, Field
from backend.database import get_db
from backend.routers.admin import _require_auth

router = APIRouter(tags=["members"])


# ── 辅助函数 ────────────────────────────────────────────

def _generate_order_no() -> str:
    """生成订单号：TOP + 日期 + 随机码"""
    date_str = datetime.now().strftime("%Y%m%d")
    rand_str = uuid.uuid4().hex[:6].upper()
    return f"TOP{date_str}{rand_str}"


def _get_member_extra(conn, user_id: int) -> dict:
    """
    获取会员的额外统计数据：
    - order_count: 该用户的订单总数
    - total_spent: 该用户已支付订单的总金额
    - last_login: 最近登录时间（暂用created_at代替，因users表无last_login字段）
    """
    cursor = conn.execute(
        "SELECT COUNT(*) as cnt, COALESCE(SUM(CASE WHEN status='paid' THEN price ELSE 0 END), 0) as spent "
        "FROM orders WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    return {
        "order_count": row["cnt"] if row else 0,
        "total_spent": float(row["spent"]) if row else 0.0,
    }


# ── 请求/响应模型 ───────────────────────────────────────

class TopUpBody(BaseModel):
    plan_type: str = Field(..., pattern=r'^(basic|pro)$', description="套餐类型")
    amount: float = Field(..., gt=0, description="充值额度（次数）")
    remark: Optional[str] = Field(None, max_length=200, description="充值备注")


class SuspendResponse(BaseModel):
    success: bool = True
    message: str = "会员已暂停"


# ══════════════════════════════════════════════════════════
# API端点
# ══════════════════════════════════════════════════════════

@router.get("/api/v1/admin/members")
async def get_members(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    search: Optional[str] = Query(None, description="搜索关键字（用户名/邮箱模糊搜索）"),
    plan_type: Optional[str] = Query(None, description="套餐类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤（保留参数，暂未使用）"),
    authorization: str = Header(None),
):
    """
    会员列表（分页，每页20条）
    返回会员基本信息+额度信息+订单统计
    """
    _require_auth(authorization)

    conn = get_db()
    try:
        # 构建查询条件
        where_clauses = []
        params = []

        if search:
            where_clauses.append("(u.username LIKE ? OR u.email LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        if plan_type:
            where_clauses.append("q.plan_type = ?")
            params.append(plan_type)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        # 计数
        cursor = conn.execute(
            f"""SELECT COUNT(*) FROM users u
                LEFT JOIN user_quotas q ON u.id = q.user_id
                {where_sql}""",
            params,
        )
        total = cursor.fetchone()[0]

        # 查询列表（分页）
        offset = (page - 1) * page_size
        cursor = conn.execute(
            f"""SELECT u.id, u.username, u.email, u.created_at,
                       q.plan_type, q.total_quota, q.used_quota,
                       q.expires_at
                FROM users u
                LEFT JOIN user_quotas q ON u.id = q.user_id
                {where_sql}
                ORDER BY u.id DESC
                LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        )
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        members = []
        for row in rows:
            member = dict(zip(columns, row))
            member["plan_type"] = member.get("plan_type") or "free"
            member["total_quota"] = member.get("total_quota") or 0
            member["used_quota"] = member.get("used_quota") or 0
            member["remaining"] = int(member["total_quota"]) - int(member["used_quota"])
            member["last_login"] = member.get("created_at")  # 用created_at代替

            # 额外统计
            extra = _get_member_extra(conn, member["id"])
            member["order_count"] = extra["order_count"]
            member["total_spent"] = extra["total_spent"]

            members.append(member)

        return {
            "success": True,
            "data": members,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        }
    finally:
        conn.close()


@router.get("/api/v1/admin/members/{user_id}")
async def get_member_detail(
    user_id: int,
    authorization: str = Header(None),
):
    """
    会员详情
    返回用户信息+额度信息+最近10条订单记录
    """
    _require_auth(authorization)

    conn = get_db()
    try:
        # 用户基本信息
        cursor = conn.execute(
            "SELECT id, username, email, created_at, updated_at FROM users WHERE id = ?",
            (user_id,),
        )
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="会员不存在")

        cols = [desc[0] for desc in cursor.description]
        user_info = dict(zip(cols, user))

        # 额度信息
        cursor = conn.execute(
            "SELECT plan_type, total_quota, used_quota, expires_at FROM user_quotas WHERE user_id = ?",
            (user_id,),
        )
        quota_row = cursor.fetchone()
        if quota_row:
            qcols = [desc[0] for desc in cursor.description]
            quota_info = dict(zip(qcols, quota_row))
            quota_info["remaining"] = int(quota_info["total_quota"]) - int(quota_info["used_quota"])
        else:
            quota_info = {
                "plan_type": "free",
                "total_quota": 0,
                "used_quota": 0,
                "remaining": 0,
                "expires_at": None,
            }

        # 最近10条订单
        cursor = conn.execute(
            """SELECT id, order_no, plan_type, price, status, created_at, paid_at
               FROM orders WHERE user_id = ?
               ORDER BY created_at DESC LIMIT 10""",
            (user_id,),
        )
        ocols = [desc[0] for desc in cursor.description]
        orders = [dict(zip(ocols, row)) for row in cursor.fetchall()]

        # 额外统计
        extra = _get_member_extra(conn, user_id)

        return {
            "success": True,
            "data": {
                "user": user_info,
                "quota": quota_info,
                "orders": orders,
                "order_count": extra["order_count"],
                "total_spent": extra["total_spent"],
            },
        }
    finally:
        conn.close()


@router.post("/api/v1/admin/members/{user_id}/topup")
async def topup_member(
    user_id: int,
    body: TopUpBody,
    authorization: str = Header(None),
):
    """
    给指定会员充值
    - 创建一笔 paid 状态的订单记录
    - 同时更新 user_quotas.total_quota
    """
    _require_auth(authorization)

    conn = get_db()
    try:
        # 验证用户存在
        cursor = conn.execute("SELECT id, username, email FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="会员不存在")

        username = user["username"]
        email = user["email"]

        # 创建 paid 状态订单
        order_no = _generate_order_no()
        price = 0  # 管理员充值不涉及金额
        cursor.execute(
            """INSERT INTO orders (order_no, user_id, user_company, user_name, user_email,
                                   plan_type, price, status, paid_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'paid', CURRENT_TIMESTAMP)""",
            (order_no, user_id, username, username, email,
             body.plan_type, price),
        )
        order_id = cursor.lastrowid

        # 更新用户额度
        add_quota = int(body.amount)
        cursor.execute("SELECT id, total_quota FROM user_quotas WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()

        expires_at = (datetime.utcnow() + timedelta(days=365)).isoformat()
        if existing:
            new_total = existing["total_quota"] + add_quota
            cursor.execute(
                """UPDATE user_quotas
                   SET plan_type = ?, total_quota = ?, used_quota = used_quota,
                       expires_at = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = ?""",
                (body.plan_type, new_total, expires_at, user_id),
            )
        else:
            cursor.execute(
                """INSERT INTO user_quotas (user_id, plan_type, total_quota, used_quota, expires_at)
                   VALUES (?, ?, ?, 0, ?)""",
                (user_id, body.plan_type, add_quota, expires_at),
            )

        conn.commit()

        return {
            "success": True,
            "message": f"充值成功，已增加 {add_quota} 额度",
            "data": {
                "order_id": order_id,
                "order_no": order_no,
                "plan_type": body.plan_type,
                "added_quota": add_quota,
                "remark": body.remark,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"充值失败: {str(e)}")
    finally:
        conn.close()


@router.post("/api/v1/admin/members/{user_id}/suspend")
async def suspend_member(
    user_id: int,
    authorization: str = Header(None),
):
    """
    暂停会员额度
    - 将 user_quotas.total_quota 设为 0
    - 将 user_quotas.used_quota 设为 0
    """
    _require_auth(authorization)

    conn = get_db()
    try:
        # 验证用户存在
        cursor = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="会员不存在")

        # 检查是否有额度记录
        cursor = conn.execute("SELECT id FROM user_quotas WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()

        if existing:
            conn.execute(
                "UPDATE user_quotas SET total_quota = 0, used_quota = 0, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,),
            )
        else:
            expires_at = (datetime.utcnow() + timedelta(days=365)).isoformat()
            conn.execute(
                "INSERT INTO user_quotas (user_id, plan_type, total_quota, used_quota, expires_at) VALUES (?, 'free', 0, 0, ?)",
                (user_id, expires_at),
            )

        conn.commit()
        return {
            "success": True,
            "message": "会员额度已暂停（已清零）",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"暂停失败: {str(e)}")
    finally:
        conn.close()
