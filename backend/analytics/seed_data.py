"""
中韩出海数智港 - 模拟种子数据生成
生成 analytic_events 表和 users/orders 表的模拟数据，
供 user_segmentation 和 retention 模块使用。
"""
import sys
import os
import json
import random
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics.event_tracker import get_db, EVENTS_TABLE, init_analytics_db


def _ensure_tables(conn, cursor):
    """确保所有需要的表存在（不依赖 database.init_db）"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            company TEXT,
            phone TEXT,
            avatar TEXT,
            role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user','vip','admin')),
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)
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


NUM_USERS = 50
EVENTS_PER_USER_MEAN = 30
EVENTS_PER_USER_STD = 15
DAYS_BACK = 60

USER_NAMES = [
    "alice", "bob", "charlie", "diana", "eve", "frank", "grace", "henry",
    "ivy", "jack", "kate", "leo", "maya", "nick", "olivia", "peter",
    "quincy", "rachel", "sam", "tina", "ulysses", "victoria", "walter",
    "xia", "yuki", "zara", "amber", "blake", "cora", "dylan",
    "ella", "felix", "gina", "hugo", "iris", "jake", "karen", "liam",
    "mona", "nathan", "ophelia", "paul", "qian", "rose", "steve",
    "tracy", "uma", "vince", "wade", "xena",
]

PAGE_URLS = [
    "/", "/pricing.html", "/order.html", "/payment.html",
    "/chat.html", "/team.html", "/privacy.html", "/terms.html",
    "/compliance-check.html", "/about.html", "/features.html",
]

EVENT_WEIGHTS = {
    "page_view": 0.55,
    "click": 0.25,
    "form_submit": 0.08,
    "download": 0.07,
    "payment_attempt": 0.05,
}


def random_date(days_back=DAYS_BACK) -> datetime:
    now = datetime.now()
    start = now - timedelta(days=days_back)
    delta_seconds = random.randint(0, days_back * 86400)
    return start + timedelta(seconds=delta_seconds)


def generate_seed_data(force: bool = False):
    """生成模拟种子数据"""
    init_analytics_db()

    conn = get_db()
    cursor = conn.cursor()
    _ensure_tables(conn, cursor)

    cursor.execute(f"SELECT COUNT(*) as cnt FROM {EVENTS_TABLE}")
    existing = cursor.fetchone()["cnt"]
    if existing > 0 and not force:
        print(f"Seed data already exists ({existing} events), use --force to regenerate.")
        conn.close()
        return

    if force:
        cursor.execute(f"DELETE FROM {EVENTS_TABLE}")
        cursor.execute("DELETE FROM orders")
        cursor.execute("DELETE FROM payments")
        cursor.execute("DELETE FROM users WHERE id > 1")
        conn.commit()

    # 1. Create users
    users = []
    for i in range(NUM_USERS):
        name = USER_NAMES[i]
        email = f"{name}@example.com"
        reg_days_ago = random.randint(1, DAYS_BACK)
        reg_date = datetime.now() - timedelta(days=reg_days_ago)
        role = random.choices(["user", "vip", "admin"], weights=[0.7, 0.25, 0.05])[0]

        cursor.execute("""
            INSERT INTO users (username, email, password_hash, display_name, company,
                               phone, role, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
        """, (
            name, email, f"hash_{name}", name.capitalize(),
            random.choice(["ACorp", "BCorp", "CCorp", "DGlobal", "ECorp"]),
            f"010-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
            role, reg_date.isoformat(),
        ))
        user_id = cursor.lastrowid
        users.append({
            "id": user_id,
            "name": name,
            "email": email,
            "role": role,
            "reg_date": reg_date,
        })

    # 2. Paid orders for ~25% of users
    paid_users = random.sample(users, int(NUM_USERS * 0.25))
    for u in paid_users:
        plan = random.choice(["depth", "annual", "source"])
        price_map = {"depth": 9800, "annual": 28800, "source": 58800}
        order_date = u["reg_date"] + timedelta(days=random.randint(0, 14))
        cursor.execute("""
            INSERT INTO orders (order_no, user_company, user_name, user_phone,
                                user_email, plan_type, price, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'paid', ?)
        """, (
            f"ORD{random.randint(100000, 999999)}",
            random.choice(["ACorp", "BCorp", "CCorp"]),
            u["name"].capitalize(),
            f"010-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
            u["email"],
            plan, price_map[plan],
            order_date.isoformat(),
        ))
        order_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO payments (order_id, method, amount, status, confirmed_at)
            VALUES (?, ?, ?, 'confirmed', ?)
        """, (
            order_id,
            random.choice(["alipay", "wechat", "transfer"]),
            price_map[plan],
            (order_date + timedelta(hours=1)).isoformat(),
        ))

    paid_emails = {u["email"] for u in paid_users}

    # 3. Generate behavioral events
    total_events = 0
    for u in users:
        if random.random() < 0.15:
            num_events = random.randint(0, 3)
        elif random.random() < 0.20:
            num_events = random.randint(5, 15)
        else:
            num_events = max(1, int(random.gauss(EVENTS_PER_USER_MEAN, EVENTS_PER_USER_STD)))

        is_paid = u["email"] in paid_emails

        for _ in range(num_events):
            event_type = random.choices(
                list(EVENT_WEIGHTS.keys()),
                weights=list(EVENT_WEIGHTS.values()),
            )[0]
            if is_paid and random.random() < 0.3:
                event_type = "payment_attempt"
            event_time = u["reg_date"] + timedelta(
                seconds=random.randint(0, max(1, int((datetime.now() - u["reg_date"]).total_seconds())))
            )
            page_url = random.choice(PAGE_URLS)
            if event_type == "payment_attempt":
                page_url = "/payment.html"
            event_data = {
                "source": random.choice(["organic", "direct", "referral", "social"]),
                "is_paid_user": is_paid,
            }
            if event_type == "form_submit":
                event_data["form_type"] = random.choice(["contact", "demo", "pricing"])
            elif event_type == "download":
                event_data["file"] = random.choice(["brochure.pdf", "guide.pdf", "whitepaper.pdf"])
            cursor.execute(f"""
                INSERT INTO {EVENTS_TABLE}
                    (user_id, event_type, event_data, page_url, session_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(u["id"]),
                event_type,
                json.dumps(event_data, ensure_ascii=False),
                page_url,
                f"session_{u['id']}_{random.randint(1,10)}",
                event_time.isoformat(),
            ))
            total_events += 1

    conn.commit()
    conn.close()

    print(f"Seed data generated!")
    print(f"  Users: {len(users)} total ({len(paid_users)} paid)")
    print(f"  Events: {total_events}")
    print(f"  Timespan: {DAYS_BACK} days")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate seed analytics data")
    parser.add_argument("--force", "-f", action="store_true", help="Force regenerate")
    args = parser.parse_args()
    generate_seed_data(force=args.force)
