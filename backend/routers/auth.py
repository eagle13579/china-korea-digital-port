"""
中韩出海数智港 - 认证路由 (用户注册登录 + JWT)
"""
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field, EmailStr
from typing import Optional

from backend.database import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# ── JWT 配置 ────────────────────────────────────────────
TOKEN_SECRET = os.environ.get("TOKEN_SECRET", "fallback-secret-change-me")
TOKEN_ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24  # token 有效期24小时

# ── 默认额度配置 ────────────────────────────────────────
FREE_QUOTA_TOTAL = 10  # 新用户注册送10次


# ── 请求/响应模型 ───────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    email: str = Field(..., description="电子邮箱")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class LoginRequest(BaseModel):
    email: str = Field(..., description="电子邮箱")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class QuotaResponse(BaseModel):
    plan_type: str
    total_quota: int
    used_quota: int
    remaining: int
    expires_at: Optional[str]


class ErrorResponse(BaseModel):
    detail: str


# ── 工具函数 ────────────────────────────────────────────

def hash_password(password: str) -> str:
    """使用 sha256 哈希密码"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_token(user_id: int, email: str) -> str:
    """生成 JWT token"""
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRE_HOURS * 3600,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, TOKEN_SECRET, algorithm=TOKEN_ALGORITHM)


def decode_token(token: str) -> dict:
    """解码 JWT token，失败抛 401"""
    try:
        payload = jwt.decode(token, TOKEN_SECRET, algorithms=[TOKEN_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效 Token")


def get_current_user(authorization: str = Header(None)) -> dict:
    """从 Authorization header 提取并验证当前用户"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供 Authorization header")
    
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Authorization 格式错误，请使用 Bearer token")
    
    return decode_token(token)


def get_user_by_email(email: str):
    """通过邮箱查找用户"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, password_hash, created_at FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_user_by_id(user_id: int):
    """通过ID查找用户"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, created_at FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_user_quota(user_id: int):
    """获取用户额度信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, plan_type, total_quota, used_quota, expires_at FROM user_quotas WHERE user_id = ?",
        (user_id,),
    )
    quota = cursor.fetchone()
    conn.close()
    return quota


def create_user_quota(user_id: int, total_quota: int = FREE_QUOTA_TOTAL):
    """为新用户创建额度记录"""
    expires_at = (datetime.utcnow() + timedelta(days=365)).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO user_quotas (user_id, plan_type, total_quota, used_quota, expires_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, "free", total_quota, 0, expires_at),
    )
    conn.commit()
    conn.close()


# ── API 端点 ────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, responses={400: {"model": ErrorResponse}})
async def register(req: RegisterRequest):
    """用户注册"""
    # 检查邮箱是否已注册
    existing = get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="该邮箱已被注册")
    
    # 检查用户名是否已存在
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (req.username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="该用户名已被使用")
    
    # 创建用户
    password_hash = hash_password(req.password)
    cursor.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (req.username, req.email, password_hash),
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # 创建额度记录
    create_user_quota(user_id)
    
    # 生成 token
    token = create_token(user_id, req.email)
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user_id,
            username=req.username,
            email=req.email,
            created_at=datetime.utcnow().isoformat(),
        ),
    )


@router.post("/login", response_model=TokenResponse, responses={401: {"model": ErrorResponse}})
async def login(req: LoginRequest):
    """用户登录"""
    user = get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    
    password_hash = hash_password(req.password)
    if user["password_hash"] != password_hash:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    
    token = create_token(user["id"], user["email"])
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            created_at=user["created_at"],
        ),
    )


@router.get("/me", response_model=UserResponse, responses={401: {"model": ErrorResponse}})
async def get_me(authorization: str = Header(None)):
    """获取当前登录用户信息"""
    payload = get_current_user(authorization)
    user = get_user_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        created_at=user["created_at"],
    )


@router.get("/quota", response_model=QuotaResponse, responses={401: {"model": ErrorResponse}})
async def get_quota(authorization: str = Header(None)):
    """获取当前用户额度"""
    payload = get_current_user(authorization)
    user_id = int(payload["sub"])
    
    quota = get_user_quota(user_id)
    if not quota:
        # 如果没有额度记录，创建一个
        create_user_quota(user_id)
        quota = get_user_quota(user_id)
    
    return QuotaResponse(
        plan_type=quota["plan_type"],
        total_quota=quota["total_quota"],
        used_quota=quota["used_quota"],
        remaining=quota["total_quota"] - quota["used_quota"],
        expires_at=quota["expires_at"],
    )


@router.get("/orders")
async def get_user_orders(authorization: str = Header(None)):
    """获取当前登录用户的订单列表"""
    payload = get_current_user(authorization)
    user_id = int(payload["sub"])
    
    conn = get_db()
    try:
        cursor = conn.execute(
            """SELECT id, order_no, plan_type, price, status, created_at, paid_at
               FROM orders WHERE user_id = ?
               ORDER BY created_at DESC""",
            (user_id,),
        )
        columns = [desc[0] for desc in cursor.description]
        orders = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # 补充plan_name
        from backend.routers.payment import PLAN_NAMES, SUBSCRIPTION_PLANS
        for o in orders:
            if o["plan_type"] in PLAN_NAMES:
                o["plan_name"] = PLAN_NAMES[o["plan_type"]]
            elif o["plan_type"] in SUBSCRIPTION_PLANS:
                o["plan_name"] = SUBSCRIPTION_PLANS[o["plan_type"]]["name"]
            else:
                o["plan_name"] = o["plan_type"]
        
        return {
            "success": True,
            "data": orders,
            "total": len(orders),
        }
    finally:
        conn.close()