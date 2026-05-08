"""
中韩出海数智港 - 用户认证API路由
包含：用户注册、登录(JWT)、获取当前用户信息
"""
import hashlib
import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional
import jwt

from backend.database import get_db

router = APIRouter(tags=["auth"])

# ── JWT 配置 ──────────────────────────────────────────
JWT_SECRET = os.environ.get("JWT_SECRET", "ckdp-jwt-secret-2026-secret-key-32bytes")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "72"))


# ── Pydantic 模型 ──────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    email: str = Field(..., description="电子邮箱")
    display_name: Optional[str] = Field(None, max_length=100, description="显示名称")
    company: Optional[str] = Field(None, max_length=200, description="公司名称")
    phone: Optional[str] = Field(None, max_length=50, description="联系电话")


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class UserUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    company: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, description="新邮箱")


# ── 辅助函数 ──────────────────────────────────────────

def _hash_password(password: str) -> str:
    """使用 SHA-256 哈希密码（后续可升级为 bcrypt）"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _create_token(user_id: int, username: str, role: str) -> str:
    """生成 JWT token"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    """解码并验证 JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的Token")


def _require_auth(authorization: str = Header(None)) -> dict:
    """从请求头中提取并验证JWT，返回用户信息"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未授权，请先登录")
    token = authorization.replace("Bearer ", "")
    return _decode_token(token)


def _get_user_by_id(user_id: int):
    """根据ID查询用户"""
    conn = get_db()
    try:
        cursor = conn.execute(
            "SELECT id, username, email, display_name, company, phone, avatar, role, is_active, created_at "
            "FROM users WHERE id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    finally:
        conn.close()


# ── API 接口 ──────────────────────────────────────────

@router.post("/api/v1/auth/register")
async def register(req: RegisterRequest):
    """用户注册"""
    conn = get_db()
    try:
        # 检查用户名是否已存在
        cursor = conn.execute("SELECT id FROM users WHERE username = ?", (req.username,))
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="用户名已被注册")

        # 检查邮箱是否已存在
        cursor = conn.execute("SELECT id FROM users WHERE email = ?", (req.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="邮箱已被注册")

        # 创建用户
        password_hash = _hash_password(req.password)
        cursor = conn.execute(
            """INSERT INTO users (username, email, password_hash, display_name, company, phone, role)
               VALUES (?, ?, ?, ?, ?, ?, 'user')""",
            (req.username, req.email, password_hash,
             req.display_name or req.username,
             req.company, req.phone),
        )
        conn.commit()
        user_id = cursor.lastrowid

        # 自动创建会员资料
        conn.execute(
            """INSERT INTO member_profiles (user_id, company_name, contact_person, contact_email, contact_phone, membership_level)
               VALUES (?, ?, ?, ?, ?, 'basic')""",
            (user_id, req.company, req.display_name or req.username, req.email, req.phone),
        )
        conn.commit()

        # 生成 JWT
        token = _create_token(user_id, req.username, "user")

        return {
            "success": True,
            "message": "注册成功",
            "data": {
                "user_id": user_id,
                "username": req.username,
                "token": token,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")
    finally:
        conn.close()


@router.post("/api/v1/auth/login")
async def login(req: LoginRequest):
    """用户登录（支持用户名或邮箱）"""
    conn = get_db()
    try:
        # 支持用户名或邮箱登录
        cursor = conn.execute(
            "SELECT id, username, email, password_hash, display_name, company, phone, avatar, role, is_active "
            "FROM users WHERE username = ? OR email = ?",
            (req.username, req.username),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        columns = [desc[0] for desc in cursor.description]
        user = dict(zip(columns, row))

        # 验证密码
        if user["password_hash"] != _hash_password(req.password):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        # 检查账户是否激活
        if not user["is_active"]:
            raise HTTPException(status_code=403, detail="账户已被禁用，请联系管理员")

        # 生成 JWT
        token = _create_token(user["id"], user["username"], user["role"])

        return {
            "success": True,
            "message": "登录成功",
            "data": {
                "user_id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "display_name": user["display_name"],
                "role": user["role"],
                "token": token,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")
    finally:
        conn.close()


@router.get("/api/v1/auth/me")
async def get_current_user(authorization: str = Header(None)):
    """获取当前登录用户信息"""
    payload = _require_auth(authorization)
    user_id = int(payload["sub"])

    user = _get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {
        "success": True,
        "data": user,
    }


@router.put("/api/v1/auth/profile")
async def update_profile(req: UserUpdateRequest, authorization: str = Header(None)):
    """更新当前用户信息"""
    payload = _require_auth(authorization)
    user_id = int(payload["sub"])

    conn = get_db()
    try:
        # 构建动态更新字段
        updates = []
        params = []
        if req.display_name is not None:
            updates.append("display_name = ?")
            params.append(req.display_name)
        if req.company is not None:
            updates.append("company = ?")
            params.append(req.company)
        if req.phone is not None:
            updates.append("phone = ?")
            params.append(req.phone)
        if req.email is not None:
            # 检查新邮箱是否被占用
            cursor = conn.execute(
                "SELECT id FROM users WHERE email = ? AND id != ?",
                (req.email, user_id),
            )
            if cursor.fetchone():
                raise HTTPException(status_code=409, detail="该邮箱已被其他账户使用")
            updates.append("email = ?")
            params.append(req.email)

        if not updates:
            return {"success": True, "message": "没有需要更新的字段"}

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(user_id)

        conn.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        conn.commit()

        user = _get_user_by_id(user_id)
        return {"success": True, "message": "更新成功", "data": user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")
    finally:
        conn.close()
