"""
中韩出海数智港 - 用户留存分析模块

功能：
  - DAU / WAU / MAU 统计
  - 用户留存曲线 (D1 / D7 / D30)
  - 付费用户 vs 免费用户对比

数据源：analytic_events 表、users 表、orders 表

CLI: python3 -m backend.analytics.retention --report
"""
import sys
import argparse
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict

sys.path.insert(0, __file__[:__file__.rfind("backend") + len("backend")] if "backend" in __file__ else ".")

from .event_tracker import get_db, EVENTS_TABLE


# ========================
#  Data fetching
# ========================

def fetch_event_date_range():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT MIN(DATE(created_at)) as min_date,
               MAX(DATE(created_at)) as max_date
        FROM {EVENTS_TABLE}
    """)
    row = cursor.fetchone()
    conn.close()
    return (row["min_date"], row["max_date"]) if row else (None, None)


def fetch_dau():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT DATE(created_at) as event_date,
               COUNT(DISTINCT user_id) as dau
        FROM {EVENTS_TABLE}
        GROUP BY DATE(created_at)
        ORDER BY event_date
    """)
    result = OrderedDict()
    for r in cursor.fetchall():
        result[r["event_date"]] = r["dau"]
    conn.close()
    return result


def fetch_wau():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT DATE(created_at, 'weekday 0', '-6 days') as week_start,
               COUNT(DISTINCT user_id) as wau
        FROM {EVENTS_TABLE}
        GROUP BY week_start
        ORDER BY week_start
    """)
    result = OrderedDict()
    for r in cursor.fetchall():
        result[r["week_start"]] = r["wau"]
    conn.close()
    return result


def fetch_mau():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT DATE(created_at, 'start of month') as month_start,
               COUNT(DISTINCT user_id) as mau
        FROM {EVENTS_TABLE}
        GROUP BY month_start
        ORDER BY month_start
    """)
    result = OrderedDict()
    for r in cursor.fetchall():
        result[r["month_start"]] = r["mau"]
    conn.close()
    return result


def fetch_user_first_last():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT user_id,
               MIN(DATE(created_at)) as first_date,
               MAX(DATE(created_at)) as last_date,
               COUNT(*) as total_events
        FROM {EVENTS_TABLE}
        GROUP BY user_id
    """)
    result = {}
    for r in cursor.fetchall():
        result[r["user_id"]] = {
            "first": r["first_date"],
            "last": r["last_date"],
            "events": r["total_events"],
        }
    conn.close()
    return result


def fetch_paid_emails():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT user_email
        FROM orders
        WHERE status = 'paid'
    """)
    emails = {r["user_email"] for r in cursor.fetchall()}
    conn.close()
    return emails


def fetch_user_emails():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email FROM users")
    result = {}
    for r in cursor.fetchall():
        result[str(r["id"])] = r["email"]
    conn.close()
    return result


# ========================
#  Retention computation
# ========================

def compute_retention(first_last):
    """Compute D1/D7/D30 retention rates via cohort analysis."""
    today = datetime.now().date().isoformat()
    users_with_dates = [
        (uid, info) for uid, info in first_last.items()
        if info["first"] and info["last"]
    ]
    if not users_with_dates:
        return {}

    def _retention_for(n):
        numerator = 0
        denominator = 0
        for uid, info in users_with_dates:
            try:
                first_d = datetime.strptime(info["first"], "%Y-%m-%d").date()
                last_d = datetime.strptime(info["last"], "%Y-%m-%d").date()
            except Exception:
                continue

            target = first_d + timedelta(days=n)
            target_str = target.isoformat()
            # Only count if enough time has passed to observe retention
            if target_str > today:
                continue

            denominator += 1
            if last_d >= target:
                numerator += 1

        rate = round((numerator / denominator) * 100, 1) if denominator > 0 else 0.0
        return {"rate": rate, "num": numerator, "den": denominator}

    return {
        "d1": _retention_for(1),
        "d7": _retention_for(7),
        "d30": _retention_for(30),
    }


def compute_retention_by_group(first_last, user_emails, paid_emails):
    paid = {}
    free = {}
    for uid, info in first_last.items():
        email = user_emails.get(uid, "")
        if email in paid_emails:
            paid[uid] = info
        else:
            free[uid] = info

    return {
        "paid": compute_retention(paid),
        "free": compute_retention(free),
        "paid_count": len(paid),
        "free_count": len(free),
    }


# ========================
#  Summary helpers
# ========================

def summarize_counts(data):
    if not data:
        return {"avg": 0, "min": 0, "max": 0, "latest": 0, "count": 0}
    vals = list(data.values())
    return {
        "avg": round(sum(vals) / len(vals), 1),
        "min": min(vals),
        "max": max(vals),
        "latest": vals[-1],
        "count": len(vals),
    }


# ========================
#  Report output
# ========================

def _bar(val, max_val, width=30):
    if max_val <= 0:
        return "░" * width
    n = min(int((val / max_val) * width), width)
    return "▓" * n + "░" * (width - n)


def print_dau_wau_mau(dau, wau, mau):
    print(f"\n{'='*70}")
    print(f"  活跃用户统计 (DAU / WAU / MAU)")
    print(f"{'='*70}")

    ds = summarize_counts(dau)
    print(f"\n  [DAU - 日活跃用户]")
    print(f"    平均: {ds['avg']:>8.1f}  |  最低: {ds['min']:>4d}  |  最高: {ds['max']:>4d}")
    print(f"    最近: {ds['latest']:>4d}  |  天数: {ds['count']}")

    if dau:
        max_v = max(dau.values())
        items = list(dau.items())
        recent = items[-14:] if len(items) > 14 else items
        print(f"\n    每日趋势 (最近14天):")
        for dt_s, cnt in recent:
            print(f"    {dt_s}  {_bar(cnt, max_v)} {cnt}")

    ws = summarize_counts(wau)
    print(f"\n  [WAU - 周活跃用户]")
    print(f"    平均: {ws['avg']:>8.1f}  |  最低: {ws['min']:>4d}  |  最高: {ws['max']:>4d}")
    print(f"    最近: {ws['latest']:>4d}  |  周数: {ws['count']}")

    if wau:
        max_v = max(wau.values())
        print(f"\n    每周趋势:")
        for wk, cnt in wau.items():
            print(f"    {wk}  {_bar(cnt, max_v)} {cnt}")

    ms = summarize_counts(mau)
    print(f"\n  [MAU - 月活跃用户]")
    print(f"    平均: {ms['avg']:>8.1f}  |  最低: {ms['min']:>4d}  |  最高: {ms['max']:>4d}")
    print(f"    最近: {ms['latest']:>4d}  |  月数: {ms['count']}")

    if mau:
        max_v = max(mau.values())
        print(f"\n    每月趋势:")
        for mn, cnt in mau.items():
            print(f"    {mn}  {_bar(cnt, max_v)} {cnt}")


def print_retention(ret, title="用户留存"):
    if not ret:
        print(f"\n  [WARNING] {title}: 无足够数据")
        return
    print(f"\n  [{title}]")
    for key, label in [("d1", "D1  (次日留存)"), ("d7", "D7  (7日留存)"), ("d30", "D30 (30日留存)")]:
        if key in ret:
            r = ret[key]
            b = _bar(int(r["rate"]), 100)
            print(f"    {label}: {r['rate']:>6.1f}%  ({r['num']}/{r['den']})  {b}")


def print_paid_vs_free(bg):
    print(f"\n{'='*70}")
    print(f"  付费用户 vs 免费用户 对比")
    print(f"{'='*70}")
    print(f"\n    付费用户: {bg['paid_count']} 人")
    print(f"    免费用户: {bg['free_count']} 人")

    if bg["paid_count"] + bg["free_count"] == 0:
        print("    (无数据)")
        return

    print(f"\n    -- 付费用户留存 --")
    print_retention(bg.get("paid", {}), "付费用户留存")
    print(f"\n    -- 免费用户留存 --")
    print_retention(bg.get("free", {}), "免费用户留存")

    paid_ret = bg.get("paid", {})
    free_ret = bg.get("free", {})
    if paid_ret and free_ret:
        print(f"\n    -- 对比 --")
        for key, label in [("d1", "D1"), ("d7", "D7"), ("d30", "D30")]:
            pr = paid_ret.get(key, {}).get("rate", 0)
            fr = free_ret.get(key, {}).get("rate", 0)
            diff = pr - fr
            sign = "+" if diff > 0 else ""
            print(f"    {label}: 付费 {pr:.1f}%  vs  免费 {fr:.1f}%  ({sign}{diff:.1f}pp)")


def run_full_report():
    print(f"\n{'='*70}")
    print(f"  中韩出海数智港 - 用户留存分析")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")

    min_date, max_date = fetch_event_date_range()
    if not min_date or not max_date:
        print("\n  没有事件数据。请先运行: python3 -m backend.analytics.seed_data")
        return

    span_days = (datetime.strptime(max_date, "%Y-%m-%d") - datetime.strptime(min_date, "%Y-%m-%d")).days + 1
    print(f"\n  数据时间范围: {min_date} ~ {max_date}  ({span_days}天)")

    dau = fetch_dau()
    wau = fetch_wau()
    mau = fetch_mau()
    print_dau_wau_mau(dau, wau, mau)

    # Retention
    first_last = fetch_user_first_last()
    retention = compute_retention(first_last)

    print(f"\n{'='*70}")
    print(f"  用户留存曲线")
    print(f"{'='*70}")
    print(f"\n    有事件记录的用户: {len(first_last)} 人")
    print_retention(retention, "整体留存")

    # Paid vs Free
    paid_emails = fetch_paid_emails()
    user_emails = fetch_user_emails()
    bg = compute_retention_by_group(first_last, user_emails, paid_emails)
    print_paid_vs_free(bg)

    # Summary
    ds = summarize_counts(dau)
    ws = summarize_counts(wau)
    ms = summarize_counts(mau)
    d1 = retention.get("d1", {}).get("rate", 0)
    d7 = retention.get("d7", {}).get("rate", 0)
    d30 = retention.get("d30", {}).get("rate", 0)

    print(f"\n{'='*70}")
    print(f"  留存分析摘要")
    print(f"{'='*70}")
    print(f"\n    平均 DAU: {ds['avg']:.1f}  |  平均 WAU: {ws['avg']:.1f}  |  平均 MAU: {ms['avg']:.1f}")
    if ms["avg"] > 0:
        print(f"    DAU/MAU: {round(ds['avg']/ms['avg']*100, 1)}%  |  WAU/MAU: {round(ws['avg']/ms['avg']*100, 1)}%")
    print(f"    留存率: D1={d1:.1f}%  D7={d7:.1f}%  D30={d30:.1f}%")
    print(f"\n{'='*70}")
    print(f"  留存分析完成")
    print(f"{'='*70}")


def main():
    parser = argparse.ArgumentParser(description="中韩出海数智港 - 用户留存分析")
    parser.add_argument("--report", "-r", action="store_true", default=True, help="显示完整报告")
    args = parser.parse_args()
    if args.report:
        run_full_report()


if __name__ == "__main__":
    main()
