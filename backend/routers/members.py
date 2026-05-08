"""
中韩出海数智港 - 会员管理API路由
包含：会员信息获取/更新、订单历史查询
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel, Field
from typing import Optional
import jwt

from backend.database import get_db

router = APIRouter(tags=["members"])

# ── JWT 配置（与 auth.py 保持一致）──────────────────────
JWT_SECRET = "ckdp-jwt-secret-2026"  # 会被环境变量覆盖，保持与auth.py一致
JWT_ALGORITHM = "HS256"


# ── Pydantic 模型 ──────────────────────────────────────

class MemberProfileUpdate(BaseModel):
    """会员资料更新请求"""
    company_name: Optional[str] = Field(None, max_length=200, description="企业名称")
    company_reg_number: Optional[str] = Field(None, max_length=100, description="企业注册号")
    contact_person: Optional[str] = Field(None, max_length=100, description="联系人")
    contact_phone: Optional[str] = Field(None, max_length=50, description="联系电话")
    contact_email: Optional[str] = Field(None, description="联系邮箱")
    business_scope: Optional[str] = Field(None, max_length=500, description="经营范围")


# ── 辅助函数 ──────────────────────────────────────────


def _require_auth(authorization: str = Header(None)) -> dict:
    """从请求头中提取并验证JWT"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未授权，请先登录")
    token = authorization.replace("Bearer ", "")
    try:
        import os
        secret = os.environ.get("JWT_SECRET", "ckdp-jwt-secret-2026-secret-key-32bytes")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的Token")


# ── API 接口 ──────────────────────────────────────────

@router.get("/api/v1/members/profile")
async def get_member_profile(authorization: str = Header(None)):
    """获取当前会员的完整信息（用户信息 + 会员资料）"""
    payload = _require_auth(authorization)
    user_id = int(payload["sub"])

    conn = get_db()
    try:
        # 查询用户信息
        cursor = conn.execute(
            "SELECT id, username, email, display_name, company, phone, avatar, role, is_active, created_at "
            "FROM users WHERE id = ?",
            (user_id,),
        )
        user_row = cursor.fetchone()
        if not user_row:
            raise HTTPException(status_code=404, detail="用户不存在")

        user_columns = [desc[0] for desc in cursor.description]
        user = dict(zip(user_columns, user_row))

        # 查询会员资料
        cursor = conn.execute(
            "SELECT * FROM member_profiles WHERE user_id = ?",
            (user_id,),
        )
        profile_row = cursor.fetchone()

        profile = None
        if profile_row:
            profile_columns = [desc[0] for desc in cursor.description]
            profile = dict(zip(profile_columns, profile_row))

        # 如果没有会员资料，返回默认值
        if not profile:
            profile = {
                "user_id": user_id,
                "company_name": user.get("company", ""),
                "company_reg_number": None,
                "contact_person": user.get("display_name", ""),
                "contact_phone": user.get("phone", ""),
                "contact_email": user.get("email", ""),
                "business_scope": None,
                "membership_level": "basic",
                "points": 0,
                "total_spent": 0.0,
                "membership_expires": None,
            }

        return {
            "success": True,
            "data": {
                "user": user,
                "profile": profile,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会员信息失败: {str(e)}")
    finally:
        conn.close()


@router.put("/api/v1/members/profile")
async def update_member_profile(
    req: MemberProfileUpdate,
    authorization: str = Header(None),
):
    """更新当前会员资料"""
    payload = _require_auth(authorization)
    user_id = int(payload["sub"])

    conn = get_db()
    try:
        # 先检查会员资料是否存在，不存在则创建
        cursor = conn.execute("SELECT id FROM member_profiles WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()

        # 构建更新字段
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
            # 更新现有资料
            params.append(user_id)
            conn.execute(
                f"UPDATE member_profiles SET {', '.join(updates)} WHERE user_id = ?",
                params,
            )
        else:
            # 创建新的会员资料
            fields = [u.split(" =")[0].strip() for u in updates]
            placeholders = ["?" for _ in fields]
            all_params = params[:]
            # 确保 user_id 存在
            if "user_id" not in fields:
                fields.insert(0, "user_id")
                placeholders.insert(0, "?")
                all_params.insert(0, user_id)
            conn.execute(
                f"INSERT INTO member_profiles ({', '.join(fields)}) VALUES ({', '.join(placeholders)})",
                all_params,
            )

        conn.commit()

        return {"success": True, "message": "会员资料更新成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新会员资料失败: {str(e)}")
    finally:
        conn.close()


@router.get("/api/v1/members/orders")
async def get_member_orders(
    status: Optional[str] = Query(None, description="按状态筛选: pending/paid/cancelled"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    authorization: str = Header(None),
):
    """获取当前会员的订单历史"""
    payload = _require_auth(authorization)
    user_id = int(payload["sub"])

    conn = get_db()
    try:
        # 获取用户信息用于匹配订单（通过 user_email 关联）
        cursor = conn.execute("SELECT email, username FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            raise HTTPException(status_code=404, detail="用户不存在")

        user_email = user_row[0]
        user_name = user_row[1]

        # 构建查询 — 通过邮箱或用户名关联订单
        base_query = "SELECT * FROM orders WHERE (user_email = ? OR user_name = ?)"
        count_query = "SELECT COUNT(*) FROM orders WHERE (user_email = ? OR user_name = ?)"
        params = [user_email, user_name]

        if status:
            base_query += " AND status = ?"
            count_query += " AND status = ?"
            params.append(status)

        # 查询总数
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()[0]

        # 查询订单列表
        cursor = conn.execute(
            base_query + " ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        )
        columns = [desc[0] for desc in cursor.description]
        orders = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # 为每个订单附带付款信息
        for order in orders:
            pc = conn.execute(
                "SELECT id, method, amount, status as payment_status, voucher_path, confirmed_at "
                "FROM payments WHERE order_id = ? ORDER BY id DESC LIMIT 1",
                (order["id"],),
            )
            p_row = pc.fetchone()
            if p_row:
                p_cols = [desc[0] for desc in pc.description]
                order["payment"] = dict(zip(p_cols, p_row))
            else:
                order["payment"] = None

        return {
            "success": True,
            "data": orders,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取订单历史失败: {str(e)}")
    finally:
        conn.close()
logout
