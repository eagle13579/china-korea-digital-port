"""
中韩出海数智港 - 数据库模块
SQLite连接 + 建表，WAL模式
"""
import sqlite3
import os
from pathlib import Path
from datetime import datetime

# 数据库文件存储路径 — 优先使用环境变量 DB_DIR
DATA_DIR = Path(os.environ.get("DB_DIR", Path(__file__).parent / "data"))
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "portal.db"


def get_db() -> sqlite3.Connection:
    """获取数据库连接，自动启用WAL模式"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = get_db()
    cursor = conn.cursor()

    # 联系表单表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT,
            email TEXT NOT NULL,
            phone TEXT,
            message TEXT,
            source TEXT DEFAULT 'website',
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)

    # 预约演示表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS demo_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT,
            email TEXT NOT NULL,
            phone TEXT,
            preferred_date TEXT,
            notes TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)

    # 定价咨询表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pricing_inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT,
            email TEXT NOT NULL,
            phone TEXT,
            plan_type TEXT,
            message TEXT,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)

    # 服务邀请表（数字员工邀请）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS service_inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT,
            email TEXT NOT NULL,
            phone TEXT,
            employee_id INTEGER,
            employee_name TEXT,
            message TEXT,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)

    # 订单表 — 沙箱支付模式
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT UNIQUE,
            user_company TEXT NOT NULL,
            user_name TEXT NOT NULL,
            user_phone TEXT,
            user_email TEXT NOT NULL,
            plan_type TEXT NOT NULL CHECK(plan_type IN ('free','depth','annual','source')),
            price REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','paid','cancelled')),
            license_key TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)

    # 迁移：为现有记录添加order_no（如果列为空）
    cursor.execute("PRAGMA table_info(orders)")
    cols = [r[1] for r in cursor.fetchall()]
    if 'order_no' in cols:
        cursor.execute("UPDATE orders SET order_no = 'ORD' || printf('%06d', id) WHERE order_no IS NULL")
    if 'license_key' not in cols:
        cursor.execute("ALTER TABLE orders ADD COLUMN license_key TEXT")

    # 支付表 — 三种付款方式 + 凭证上传
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            method TEXT NOT NULL CHECK(method IN ('alipay','wechat','transfer')),
            amount REAL NOT NULL,
            voucher_path TEXT,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','confirmed','rejected')),
            confirmed_at TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成: {DB_PATH}")


if __name__ == "__main__":
    init_db()