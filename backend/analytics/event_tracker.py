"""
中韩出海数智港 - 用户行为事件追踪模块
纯SQLite实现，无需第三方SDK
"""
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime, date

# ── 数据库配置 ──────────────────────────────────────────
# 复用项目的 data 目录，保持数据库统一
DATA_DIR = Path(os.environ.get("DB_DIR", Path(__file__).parent.parent / "data"))
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "portal.db"

# ── 事件类型常量 ────────────────────────────────────────
VALID_EVENT_TYPES = frozenset({
    "page_view",
    "click",
    "form_submit",
    "download",
    "payment_attempt",
})

# ── 漏斗阶段页面路径映射 ────────────────────────────────
# 用于转化漏斗分析
FUNNEL_STAGES = {
    "首页": "/",
    "定价页": "/pricing.html",
    "下单页": "/order.html",
    "支付页": "/payment.html",
}

EVENTS_TABLE = "analytic_events"


def get_db() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_analytics_db():
    """初始化分析事件表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {EVENTS_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL
                CHECK(event_type IN ('page_view','click','form_submit','download','payment_attempt')),
            event_data TEXT DEFAULT '{{}}',
            page_url TEXT,
            session_id TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 索引：加速查询
    cursor.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_events_user_id
        ON {EVENTS_TABLE}(user_id)
    """)
    cursor.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_events_event_type
        ON {EVENTS_TABLE}(event_type)
    """)
    cursor.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_events_created_at
        ON {EVENTS_TABLE}(created_at)
    """)
    cursor.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_events_page_url
        ON {EVENTS_TABLE}(page_url)
    """)
    cursor.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_events_session
        ON {EVENTS_TABLE}(session_id)
    """)
    conn.commit()
    conn.close()
    print(f"✅ 分析事件表初始化完成 ({DB_PATH})")


def track_event(
    user_id: str,
    event_type: str,
    event_data: dict = None,
    page_url: str = None,
    session_id: str = None,
    ip_address: str = None,
    user_agent: str = None,
) -> int:
    """
    追踪用户行为事件

    Args:
        user_id: 用户标识（可以是IP、用户ID、匿名ID）
        event_type: 事件类型，可选值: page_view, click, form_submit, download, payment_attempt
        event_data: 事件附加数据（dict 或 None）
        page_url: 发生事件的页面URL
        session_id: 会话ID
        ip_address: 客户端IP
        user_agent: 客户端 User-Agent

    Returns:
        新插入记录的主键ID
    """
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(
            f"无效的事件类型: '{event_type}'。"
            f"有效类型: {', '.join(sorted(VALID_EVENT_TYPES))}"
        )

    if event_data is None:
        event_data = {}
    event_data_json = json.dumps(event_data, ensure_ascii=False)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        INSERT INTO {EVENTS_TABLE}
            (user_id, event_type, event_data, page_url, session_id, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, event_type, event_data_json, page_url, session_id, ip_address, user_agent))
    conn.commit()
    event_id = cursor.lastrowid
    conn.close()
    return event_id


# ── 查询辅助函数 ────────────────────────────────────────

def get_today_active_users() -> int:
    """获取今日活跃用户数（去重）"""
    conn = get_db()
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute(f"""
        SELECT COUNT(DISTINCT user_id) as cnt
        FROM {EVENTS_TABLE}
        WHERE DATE(created_at) = ?
    """, (today,))
    row = cursor.fetchone()
    conn.close()
    return row["cnt"] if row else 0


def get_today_events_count() -> int:
    """获取今日事件总数"""
    conn = get_db()
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute(f"""
        SELECT COUNT(*) as cnt
        FROM {EVENTS_TABLE}
        WHERE DATE(created_at) = ?
    """, (today,))
    row = cursor.fetchone()
    conn.close()
    return row["cnt"] if row else 0


def get_popular_pages(limit: int = 10) -> list:
    """获取热门页面排行（按 page_view 统计）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT page_url, COUNT(*) as views
        FROM {EVENTS_TABLE}
        WHERE event_type = 'page_view'
          AND page_url IS NOT NULL
        GROUP BY page_url
        ORDER BY views DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_conversion_funnel(stages: dict = None) -> list:
    """
    获取转化漏斗数据
    统计每个漏斗阶段的独立访客数

    Args:
        stages: 漏斗阶段字典 {阶段名称: page_url 或 page_url 前缀}

    Returns:
        list of dict: [{"stage": "首页", "page_url": "/", "visitors": 100}, ...]
    """
    if stages is None:
        stages = FUNNEL_STAGES

    conn = get_db()
    cursor = conn.cursor()
    results = []
    for stage_name, url_pattern in stages.items():
        cursor.execute(f"""
            SELECT COUNT(DISTINCT user_id) as visitors
            FROM {EVENTS_TABLE}
            WHERE event_type = 'page_view'
              AND page_url = ?
        """, (url_pattern,))
        row = cursor.fetchone()
        results.append({
            "stage": stage_name,
            "page_url": url_pattern,
            "visitors": row["visitors"] if row else 0,
        })
    conn.close()
    return results


def get_event_type_breakdown() -> list:
    """获取今日事件类型分布"""
    conn = get_db()
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute(f"""
        SELECT event_type, COUNT(*) as count
        FROM {EVENTS_TABLE}
        WHERE DATE(created_at) = ?
        GROUP BY event_type
        ORDER BY count DESC
    """, (today,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
