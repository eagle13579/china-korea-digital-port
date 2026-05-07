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
    if 'paid_at' not in cols:
        cursor.execute("ALTER TABLE orders ADD COLUMN paid_at TIMESTAMP")
    if 'customer_name' not in cols:
        # user_name already covers this; adding alias column for compatibility
        pass

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

    # 合规自检表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compliance_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            answers TEXT NOT NULL,
            company_name TEXT,
            contact_name TEXT,
            email TEXT NOT NULL,
            phone TEXT,
            language TEXT DEFAULT 'zh-CN',
            score INTEGER,
            score_detail TEXT,
            report_generated INTEGER DEFAULT 0,
            report_downloaded INTEGER DEFAULT 0,
            status TEXT DEFAULT 'completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 合规线索表（销售线索，跟 admin 的 leads 同步）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compliance_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            email TEXT NOT NULL,
            company_name TEXT,
            contact_name TEXT,
            phone TEXT,
            language TEXT DEFAULT 'zh-CN',
            score INTEGER NOT NULL,
            score_detail TEXT,
            priority TEXT DEFAULT 'normal',
            status TEXT DEFAULT 'new',
            source TEXT DEFAULT '合规自检',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (check_id) REFERENCES compliance_checks(id)
        )
    """)

    # 报价表（销售漏斗用）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_no TEXT UNIQUE,
            lead_table TEXT NOT NULL,
            lead_id INTEGER NOT NULL,
            lead_name TEXT,
            lead_company TEXT,
            lead_email TEXT,
            plan_name TEXT NOT NULL,
            plan_price REAL NOT NULL DEFAULT 0,
            status TEXT DEFAULT 'draft' CHECK(status IN ('draft','sent','accepted','rejected')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)

    # 为线索表添加 stage 字段（销售漏斗阶段）
    for tbl in ["contacts", "demo_requests", "pricing_inquiries"]:
        cursor.execute(f"PRAGMA table_info({tbl})")
        cols = [r[1] for r in cursor.fetchall()]
        if "stage" not in cols:
            cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN stage TEXT DEFAULT 'new_lead'")
        if "stage_changed_at" not in cols:
            cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN stage_changed_at TIMESTAMP")

    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成: {DB_PATH}")


if __name__ == "__main__":
    init_db()