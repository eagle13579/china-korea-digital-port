"""
中韩出海数智港 - AI数字员工对话API路由

API端点:
  POST /api/chat/send    — 发送消息，返回AI回复
  GET  /api/chat/history — 获取历史记录
  POST /api/chat/clear   — 清除对话
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from backend.database import get_db
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from knowledge_graph import get_db as kg_get_db, search_articles, get_articles_by_dimension
from backend.ai_dialogue import chat_send

router = APIRouter(prefix="/api/chat", tags=["ai-dialogue"])


# ── Pydantic 模型 ──────────────────────────────────────

class ChatSendRequest(BaseModel):
    message: str


class ChatMessage(BaseModel):
    id: int
    role: str  # "user" or "assistant"
    content: str
    dimension: Optional[str] = None
    dimension_label: Optional[str] = None
    source: Optional[str] = None
    created_at: str


class ChatSendResponse(BaseModel):
    success: bool = True
    reply: str
    dimension: Optional[str] = None
    dimension_label: Optional[str] = None
    source: str
    language: str


class ChatHistoryResponse(BaseModel):
    success: bool = True
    messages: List[ChatMessage] = []
    total: int = 0


class ChatClearResponse(BaseModel):
    success: bool = True
    message: str = "对话已清除"


# ── 辅助函数 ──────────────────────────────────────────

def _init_chat_table():
    """确保 chat_history 表存在"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            dimension TEXT,
            dimension_label TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def _save_message(role: str, content: str, dimension: Optional[str] = None,
                  dimension_label: Optional[str] = None, source: Optional[str] = None):
    """保存消息到数据库"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO chat_history (role, content, dimension, dimension_label, source)
           VALUES (?, ?, ?, ?, ?)""",
        (role, content, dimension, dimension_label, source),
    )
    conn.commit()
    message_id = cursor.lastrowid
    conn.close()
    return message_id


# ── API端点 ─────────────────────────────────────────────

@router.post("/send", response_model=ChatSendResponse)
async def chat_send_endpoint(request: ChatSendRequest):
    """发送消息到AI数字员工，获取合规问答回复"""
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    user_message = request.message.strip()

    # 1. 保存用户消息
    _init_chat_table()
    _save_message("user", user_message)

    # 2. 调用AI引擎
    try:
        result = chat_send(user_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI处理失败: {str(e)}")

    # 3. 保存AI回复
    _save_message(
        role="assistant",
        content=result["reply"],
        dimension=result.get("dimension"),
        dimension_label=result.get("dimension_label"),
        source=result.get("source"),
    )

    return ChatSendResponse(
        reply=result["reply"],
        dimension=result.get("dimension"),
        dimension_label=result.get("dimension_label"),
        source=result.get("source", "mock_faq"),
        language=result.get("language", "zh"),
    )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(limit: int = 50, offset: int = 0):
    """获取对话历史记录"""
    _init_chat_table()
    conn = get_db()
    cursor = conn.cursor()

    # 查询总数
    cursor.execute("SELECT COUNT(*) FROM chat_history")
    total = cursor.fetchone()[0]

    # 查询消息列表（按时间倒序，前端正序展示）
    cursor.execute(
        """SELECT id, role, content, dimension, dimension_label, source,
                  COALESCE(created_at, '') as created_at
           FROM chat_history
           ORDER BY id DESC
           LIMIT ? OFFSET ?""",
        (limit, offset),
    )
    rows = cursor.fetchall()
    messages = []
    for row in rows:
        messages.append(ChatMessage(
            id=row["id"],
            role=row["role"],
            content=row["content"],
            dimension=row["dimension"],
            dimension_label=row["dimension_label"],
            source=row["source"],
            created_at=row["created_at"],
        ))

    # 降序排列 -> 升序排列（前端展示需要）
    messages.reverse()

    conn.close()
    return ChatHistoryResponse(messages=messages, total=total)


@router.post("/clear", response_model=ChatClearResponse)
async def clear_chat_history():
    """清除对话历史"""
    _init_chat_table()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history")
    conn.commit()
    conn.close()
    return ChatClearResponse(message="对话已清除")
