"""
中韩出海数智港 - 会员管理API路由
包含：会员信息获取/更新、订单历史查询、订阅管理
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel, Field
from typing import Optional
import jwt, os, uuid

from backend.database import get_db
from backend.membership_helper import activate_membership, check_and_auto_upgrade

router = APIRouter(tags=["members"])

# ── JWT 配置（与 auth.py 保持一致）──────────────────────
JWT_SECRET = os.environ.get("JWT_SECRET", "ckdp-jwt-secret-2026-secret-key-32bytes")
JWT_ALGORITHM = "HS256"


# ── Pydantic 模型 ──────────────────────────────────────

class MemberProfileUpdate(BaseModel):
    company_name: Optional[str] = Field(None, max_length=200)
    company_reg_number: Optional[str] = Field(None, max_length=100)
    contact_person: Optional[str] = Field(None, max_length=100)
    contact_phone: Optional[str] = Field(None, max_length=50)
    contact_email: Optional[str] = Field(None)
    business_scope: Optional[str] = Field(None, max_length=500)


class SubscribeRequest(BaseModel):
    plan_type: str = Field(..., description="套餐类型: free/depth/annual/source")
    user_company: Optional[str] = Field(None, max_length=200)
    user_phone: Optional[str] = Field(None, max_length=50)


# ── 辅助函数 ──────────────────────────────────────────

def _require_auth(authorization: str = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="未授权，请先登录")
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的Token")


# ── API 接口 ──────────────────────────────────────────

@router.get("/api/v1/members/profile")
async def get_member_profile(authorization: str = Header(None)):
    payload = _require_auth(authorization)
    user_id = int(payload["sub"])
    conn = get_db()
    try:
        cursor = conn.execute(
            "SELECT id, username, email, display_name, company, phone, avatar, role, is_active, created_at "
            "FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            raise HTTPException(status_code=404, detail="用户不存在")
        user_columns = [desc[0] for desc in cursor.description]
        user = dict(zip(user_columns, user_row))

        cursor = conn.execute("SELECT * FROM member_profiles WHERE user_id = ?", (user_id,))
        profile_row = cursor.fetchone()
        profile = None
        if profile_row:
            profile_columns = [desc[0] for desc in cursor.description]
            profile = dict(zip(profile_columns, profile_row))
        if not profile:
            profile = {
                "user_id": user_id, "company_name": user.get("company", ""),
                "company_reg_number": None, "contact_person": user.get("display_name", ""),
                "contact_phone": user.get("phone", ""), "contact_email": user.get("email", ""),
                "business_scope": None, "membership_level": "basic",
                "points": 0, "total_spent": 0.0, "membership_expires": None,
            }
        return {"success": True, "data": {"user": user, "profile": profile}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会员信息失败: {str(e)}")
    finally:
        conn.close()


@router.put("/api/v1/members/profile")
async def update_member_profile(req: MemberProfileUpdate, authorization: str = Header(None)):
    payload = _require_auth(authorization)
    user_id = int(payload["sub"])
    conn = get_db()
    try:
        cursor = conn.execute("SELECT id FROM member_profiles WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()
        updates = []
        params = []
        for field in ["company_name", "company_reg_number", "contact_person",
                       "contact_phone", "contact_email", "business_scope"]:
            value = getattr(req, field, None)
            if value is not None:
                updates.append(f"{field} = ?")
                params.append(value)
        if not updates:
            return {"success": True, "message": "没有需要更新的字段"}
        if existing:
            params.append(user_id)
            conn.execute(f"UPDATE member_profiles SET {', '.join(updates)} WHERE user_id = ?", params)
        else:
            fields = [u.split(" =")[0].strip() for u in updates]
            placeholders = ["?" for _ in fields]
            all_params = params[:]
            if "user_id" not in fields:
                fields.insert(0, "user_id")
                placeholders.insert(0, "?")
                all_params.insert(0, user_id)
            conn.execute(f"INSERT INTO member_profiles ({', '.join(fields)}) VALUES ({', '.join(placeholders)})", all_params)
        conn.commit()
        return {"success": True, "message": "会员资料更新成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新会员资料失败: {str(e)}")
    finally:
        conn.close()


@router.get("/api/v1/members/orders")
async def get_member_orders(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    authorization: str = Header(None),
):
    payload = _require_auth(authorization)
    user_id = int(payload["sub"])
    conn = get_db()
    try:
        cursor = conn.execute("SELECT email, username FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            raise HTTPException(status_code=404, detail="用户不存在")
        user_email = user_row[0]
        user_name = user_row[1]
        base_query = "SELECT * FROM orders WHERE (user_email = ? OR user_name = ?)"
        count_query = "SELECT COUNT(*) FROM orders WHERE (user_email = ? OR user_name = ?)"
        params = [user_email, user_name]
        if status:
            base_query += " AND status = ?"
            count_query += " AND status = ?"
            params.append(status)
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()[0]
        cursor = conn.execute(base_query + " ORDER BY created_at DESC LIMIT ? OFFSET ?", params + [limit, offset])
        columns = [desc[0] for desc in cursor.description]
        orders = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for order in orders:
            pc = conn.execute(
                "SELECT id, method, amount, status as payment_status, voucher_path, confirmed_at "
                "FROM payments WHERE order_id = ? ORDER BY id DESC LIMIT 1", (order["id"],))
            p_row = pc.fetchone()
            if p_row:
                p_cols = [desc[0] for desc in pc.description]
                order["payment"] = dict(zip(p_cols, p_row))
            else:
                order["payment"] = None
        return {"success": True, "data": orders, "total": total, "limit": limit, "offset": offset}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取订单历史失败: {str(e)}")
    finally:
        conn.close()


# ── 会员订阅API ─────────────────────────────────────────

@router.post("/api/v1/members/subscribe")
async def member_subscribe(req: SubscribeRequest, authorization: str = Header(None)):
    """会员订阅套餐：创建订单，免费套餐自动激活会员"""
    payload = _require_auth(authorization)
    user_id = int(payload["sub"])
    plan_type = req.plan_type
    if plan_type not in ("free", "depth", "annual", "source"):
        raise HTTPException(status_code=400, detail=f"不支持的套餐类型: {plan_type}")

    from backend.routers.payment import PLAN_PRICES, PLAN_NAMES
    expected_price = PLAN_PRICES.get(plan_type, 0)
    plan_name = PLAN_NAMES.get(plan_type, plan_type)

    conn = get_db()
    try:
        cursor = conn.execute(
            "SELECT id, email, username, display_name, company, phone FROM users WHERE id = ?",
            (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            raise HTTPException(status_code=404, detail="用户不存在")
        cols = [desc[0] for desc in cursor.description]
        user = dict(zip(cols, user_row))

        user_email = user["email"]
        user_name = user["display_name"] or user["username"]
        user_company = req.user_company or user.get("company", "")
        user_phone = req.user_phone or user.get("phone", "")

        order_no = "ORD" + datetime.utcnow().strftime("%Y%m%d") + uuid.uuid4().hex[:6].upper()

        cursor = conn.execute(
            "INSERT INTO orders (order_no, user_company, user_name, user_phone, user_email, plan_type, price, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')",
            (order_no, user_company, user_name, user_phone, user_email, plan_type, expected_price))
        conn.commit()
        order_id = cursor.lastrowid

        if plan_type == "free":
            from backend.license import generate_license
            license_key = generate_license(user_company or user_name, plan_type, 30)
            conn.execute(
                "UPDATE orders SET status = 'paid', license_key = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (license_key, order_id))
            conn.commit()
            activate_membership(user_email=user_email, plan_type=plan_type, price=0, conn=conn)
            return {
                "success": True, "order_id": order_id, "order_no": order_no,
                "plan_type": plan_type, "plan_name": plan_name, "price": 0,
                "is_free": True, "license_key": license_key, "message": "免费套餐已激活",
            }

        return {
            "success": True, "order_id": order_id, "order_no": order_no,
            "plan_type": plan_type, "plan_name": plan_name, "price": expected_price,
            "is_free": False, "message": f"订单创建成功，订单号: {order_no}，请完成支付",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"订阅失败: {str(e)}")
    finally:
        conn.close()


@router.post("/api/v1/members/upgrade")
async def member_auto_upgrade(authorization: str = Header(None)):
    """检查并自动升级会员等级（基于累计消费金额）"""
    payload = _require_auth(authorization)
    user_id = int(payload["sub"])
    conn = get_db()
    try:
        upgraded_to = check_and_auto_upgrade(user_id, conn)
        if upgraded_to:
            return {"success": True, "message": f"会员等级已升级至: {upgraded_to}", "membership_level": upgraded_to}
        cursor = conn.execute(
            "SELECT membership_level, total_spent, membership_expires FROM member_profiles WHERE user_id = ?",
            (user_id,))
        row = cursor.fetchone()
        if row:
            cols = [desc[0] for desc in cursor.description]
            prof = dict(zip(cols, row))
            return {
                "success": True, "message": "当前无需升级",
                "membership_level": prof["membership_level"],
                "total_spent": prof["total_spent"],
                "membership_expires": prof.get("membership_expires"),
            }
        return {"success": True, "message": "暂无会员资料，请先订阅"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"升级检查失败: {str(e)}")
    finally:
        conn.close()


@router.get("/api/v1/members/subscription")
async def get_member_subscription(authorization: str = Header(None)):
    """获取当前会员的订阅状态：等级、消费、到期时间、下一等级"""
    payload = _require_auth(authorization)
    user_id = int(payload["sub"])
    conn = get_db()
    try:
        cursor = conn.execute(
            "SELECT membership_level, total_spent, membership_expires, points FROM member_profiles WHERE user_id = ?",
            (user_id,))
        row = cursor.fetchone()
        if not row:
            return {"success": True, "data": {
                "has_subscription": False, "membership_level": "basic", "total_spent": 0,
                "message": "请订阅套餐开启会员服务",
            }}
        cols = [desc[0] for desc in cursor.description]
        prof = dict(zip(cols, row))

        level_rank = [("basic", 0, "silver"), ("silver", 999, "gold"), ("gold", 9999, "platinum"), ("platinum", 29999, None)]
        next_info = None
        for lvl, threshold, nxt in level_rank:
            if lvl == prof["membership_level"] and nxt:
                gap = max(0, threshold - prof["total_spent"])
                next_info = {"level": nxt, "additional_spend_needed": round(gap, 2)}
                break

        cursor = conn.execute(
            "SELECT order_no, plan_type, price, status, created_at FROM orders WHERE user_email = (SELECT email FROM users WHERE id = ?) ORDER BY created_at DESC LIMIT 1",
            (user_id,))
        last_order = None
        o = cursor.fetchone()
        if o:
            ocols = [desc[0] for desc in cursor.description]
            last_order = dict(zip(ocols, o))

        return {"success": True, "data": {
            "has_subscription": True,
            "membership_level": prof["membership_level"],
            "total_spent": prof["total_spent"],
            "membership_expires": prof.get("membership_expires"),
            "points": prof.get("points", 0),
            "next_level": next_info,
            "last_order": last_order,
        }}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取订阅信息失败: {str(e)}")
    finally:
        conn.close()
