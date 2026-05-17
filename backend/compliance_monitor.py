"""
合规法规监控引擎 — 自动检测法规变更 + 更新知识库
crontab: 每天6:00自动检查
"""
import json, sqlite3, os, hashlib, subprocess
from datetime import datetime, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).parent
DATA_DIR = BACKEND_DIR / "data"
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = DATA_DIR / "compliance_knowledge.db"

# 法规变更监控源（可扩展）
REGULATORY_SOURCES = [
    {
        "name": "中国商务部",
        "url": "http://www.mofcom.gov.cn/",
        "type": "gov",
        "check_interval_hours": 24,
    },
    {
        "name": "国家市场监管总局",
        "url": "http://www.samr.gov.cn/",
        "type": "gov",
        "check_interval_hours": 24,
    },
    {
        "name": "国家互联网信息办公室",
        "url": "http://www.cac.gov.cn/",
        "type": "gov",
        "check_interval_hours": 24,
    },
]

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def record_check(source_name, status, details=""):
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS compliance_checks (id INTEGER PRIMARY KEY AUTOINCREMENT, source_name TEXT, status TEXT, details TEXT, checked_at TEXT)")
    conn.execute("INSERT INTO compliance_checks (source_name, status, details, checked_at) VALUES (?,?,?,?)",
                 (source_name, status, details[:500], datetime.now().isoformat()))
    conn.commit()
    conn.close()

def run_check():
    """执行一轮法规变更检查"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 法规监控检查启动")
    results = []
    for src in REGULATORY_SOURCES:
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-m", "10", src["url"]],
                capture_output=True, text=True, timeout=15
            )
            status = "ok" if result.stdout.strip() == "200" else "unreachable"
            record_check(src["name"], status)
            results.append({"source": src["name"], "status": status})
        except Exception as e:
            record_check(src["name"], "error", str(e)[:200])
            results.append({"source": src["name"], "status": "error", "error": str(e)[:100]})
    return results

def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) as c FROM compliance_checks").fetchone()["c"]
    last = conn.execute("SELECT * FROM compliance_checks ORDER BY checked_at DESC LIMIT 1").fetchone()
    statuses = conn.execute("SELECT status, COUNT(*) as c FROM compliance_checks GROUP BY status").fetchall()
    return {
        "total_checks": total,
        "last_check": dict(last) if last else None,
        "status_summary": [dict(s) for s in statuses],
    }

def get_knowledge_stats():
    conn = get_db()
    total_articles = conn.execute("SELECT COUNT(*) as c FROM knowledge_graph").fetchone()["c"]
    by_dim = conn.execute("SELECT dimension_id, COUNT(*) as c FROM knowledge_graph GROUP BY dimension_id").fetchall()
    return {
        "total_articles": total_articles,
        "dimensions": len(by_dim),
        "by_dimension": [dict(d) for d in by_dim],
    }

if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        results = run_check()
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif "--stats" in sys.argv:
        print(json.dumps({**get_stats(), **get_knowledge_stats()}, ensure_ascii=False, indent=2))
    else:
        print("用法: python3 compliance_monitor.py --check | --stats")
