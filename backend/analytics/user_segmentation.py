"""
中韩出海数智港 - 用户分群分析模块

基于用户行为数据的多维分群：
  - 注册时间分群
  - 访问频率分群
  - 页面深度分群
  - 付费行为分群

数据源：analytic_events 表、users 表、orders 表

CLI: python3 -m backend.analytics.user_segmentation --report
"""
import sys
import json
import argparse
from datetime import datetime, timedelta, date
from collections import defaultdict

sys.path.insert(0, __file__[:__file__.rfind("backend") + len("backend")] if "backend" in __file__ else ".")

from .event_tracker import get_db, EVENTS_TABLE


# ========================
#  Data fetching
# ========================

def fetch_all_users() -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, email, role, is_active, created_at
        FROM users
        ORDER BY id
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def fetch_paid_emails() -> set:
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


def fetch_user_events() -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT user_id, event_type, page_url, DATE(created_at) as event_date,
               created_at
        FROM {EVENTS_TABLE}
        ORDER BY user_id, created_at
    """)
    rows = cursor.fetchall()
    conn.close()

    result = {}
    for r in rows:
        uid = r["user_id"]
        if uid not in result:
            result[uid] = {
                "total_events": 0,
                "page_views": 0,
                "unique_pages": set(),
                "event_types": defaultdict(int),
                "has_payment_event": False,
                "first_event": None,
                "last_event": None,
                "active_days": set(),
            }
        d = result[uid]
        d["total_events"] += 1
        if r["event_type"] == "page_view":
            d["page_views"] += 1
            if r["page_url"]:
                d["unique_pages"].add(r["page_url"])
        if r["event_type"] == "payment_attempt":
            d["has_payment_event"] = True
        d["event_types"][r["event_type"]] += 1

        ts = r["created_at"]
        if d["first_event"] is None or ts < d["first_event"]:
            d["first_event"] = ts
        if d["last_event"] is None or ts > d["last_event"]:
            d["last_event"] = ts

        if r["event_date"]:
            d["active_days"].add(r["event_date"])

    for uid in result:
        d = result[uid]
        d["unique_pages"] = len(d["unique_pages"])
        d["active_days"] = len(d["active_days"])
        d["event_types"] = dict(d["event_types"])

    return result


# ========================
#  Parsing helpers
# ========================

def _parse_dt(val):
    if val is None:
        return None
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except Exception:
            return None
    return val if isinstance(val, datetime) else None


def _check_reg_dt(dt_obj, days_min=0, days_max=None):
    if dt_obj is None:
        return False
    diff = (datetime.now() - dt_obj).days
    if diff < days_min:
        return False
    if days_max is not None and diff > days_max:
        return False
    return True


def _email_of(users, user_id):
    for u in users:
        if str(u["id"]) == str(user_id):
            return u.get("email", "")
    return ""


# ========================
#  Segmentation logic
# ========================

def segment_by_registration(users, user_events, paid_emails):
    """Segment by registration time. Condition receives user dict."""
    segments = {
        "新用户 (注册<=7天)": lambda u: _check_reg_dt(_parse_dt(u.get("created_at")), days_max=7),
        "近期用户 (8-30天)": lambda u: _check_reg_dt(_parse_dt(u.get("created_at")), days_min=8, days_max=30),
        "中期用户 (31-90天)": lambda u: _check_reg_dt(_parse_dt(u.get("created_at")), days_min=31, days_max=90),
        "老用户 (>90天)": lambda u: _check_reg_dt(_parse_dt(u.get("created_at")), days_min=91),
        "未知注册时间": lambda u: _parse_dt(u.get("created_at")) is None,
    }
    return _compute_segment_stats(users, user_events, paid_emails, segments,
                                   pass_user=True)


def segment_by_frequency(users, user_events, paid_emails):
    """Segment by visit frequency. Condition receives uid string."""
    def _get_total(uid):
        return user_events.get(uid, {}).get("total_events", 0)

    segments = {
        "沉默用户 (0-2次事件)": lambda uid: _get_total(uid) <= 2,
        "轻度用户 (3-15次)": lambda uid: 2 < _get_total(uid) <= 15,
        "中度用户 (16-50次)": lambda uid: 15 < _get_total(uid) <= 50,
        "活跃用户 (>50次)": lambda uid: _get_total(uid) > 50,
    }
    return _compute_segment_stats(users, user_events, paid_emails, segments,
                                   pass_user=False)


def segment_by_page_depth(users, user_events, paid_emails):
    """Segment by page depth. Condition receives uid string."""
    def _get_depth(uid):
        return user_events.get(uid, {}).get("unique_pages", 0)

    segments = {
        "浅度浏览 (0-2页)": lambda uid: _get_depth(uid) <= 2,
        "中度浏览 (3-5页)": lambda uid: 2 < _get_depth(uid) <= 5,
        "深度浏览 (6-10页)": lambda uid: 5 < _get_depth(uid) <= 10,
        "全站浏览 (>10页)": lambda uid: _get_depth(uid) > 10,
    }
    return _compute_segment_stats(users, user_events, paid_emails, segments,
                                   pass_user=False)


def segment_by_payment(users, user_events, paid_emails):
    """Segment by payment behavior. Condition receives uid string."""
    def _is_paid(uid):
        return _email_of(users, uid) in paid_emails

    def _has_payment_intent(uid):
        return user_events.get(uid, {}).get("has_payment_event", False)

    segments = {
        "付费用户": lambda uid: _is_paid(uid),
        "免费用户（有支付意向）": lambda uid: (not _is_paid(uid) and _has_payment_intent(uid)),
        "免费用户（无支付意向）": lambda uid: (not _is_paid(uid) and not _has_payment_intent(uid)),
    }
    return _compute_segment_stats(users, user_events, paid_emails, segments,
                                   pass_user=False)


# ========================
#  Statistics computation
# ========================

def _compute_segment_stats(users, user_events, paid_emails, segments, pass_user=False):
    """
    Compute stats per segment.

    Args:
        pass_user: if True, condition receives user dict; if False, receives uid string.
    """
    user_map = {}
    for u in users:
        user_map[str(u["id"])] = u

    results = []
    for seg_name, condition in segments.items():
        members = []
        for uid, u in user_map.items():
            arg = u if pass_user else uid
            if condition(arg):
                members.append(uid)

        n_users = len(members)
        if n_users == 0:
            results.append({
                "segment": seg_name,
                "user_count": 0,
                "total_events": 0,
                "avg_events_per_user": 0.0,
                "avg_unique_pages": 0.0,
                "avg_active_days": 0.0,
                "paid_user_count": 0,
                "conversion_rate": 0.0,
                "member_ids": [],
            })
            continue

        total_events = sum(user_events.get(uid, {}).get("total_events", 0) for uid in members)
        total_pages = sum(user_events.get(uid, {}).get("unique_pages", 0) for uid in members)
        total_active_days = sum(user_events.get(uid, {}).get("active_days", 0) for uid in members)
        paid_count = sum(1 for uid in members if _email_of(users, uid) in paid_emails)

        results.append({
            "segment": seg_name,
            "user_count": n_users,
            "total_events": total_events,
            "avg_events_per_user": round(total_events / n_users, 1),
            "avg_unique_pages": round(total_pages / n_users, 1),
            "avg_active_days": round(total_active_days / n_users, 1),
            "paid_user_count": paid_count,
            "conversion_rate": round((paid_count / n_users) * 100, 1),
            "member_ids": members[:10],
        })

    results.sort(key=lambda r: r["user_count"], reverse=True)
    return results


# ========================
#  Report output
# ========================

def print_seg_table(segments, title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    print(f"  {'分群':<24s} {'用户数':>6s} {'事件数':>8s} {'人均事件':>8s} {'人均页数':>8s} {'活跃天数':>8s} {'付费转化':>8s}")
    print(f"  {'-'*24} {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
    for s in segments:
        bar = "█" * min(s["user_count"], 40) if s["user_count"] > 0 else ""
        print(f"  {s['segment']:<24s} {s['user_count']:>6d} {s['total_events']:>8d} "
              f"{s['avg_events_per_user']:>7.1f} {s['avg_unique_pages']:>7.1f} "
              f"{s['avg_active_days']:>7.1f} {s['conversion_rate']:>6.1f}%  {bar}")
    print()


def print_summary(all_results):
    print(f"\n{'='*70}")
    print(f"  用户分群分析汇总")
    print(f"{'='*70}")
    for dim, segments in all_results.items():
        total_users = sum(s["user_count"] for s in segments)
        total_paid = sum(s["paid_user_count"] for s in segments)
        conv = round(total_paid / total_users * 100, 1) if total_users else 0
        print(f"\n  >> {dim}")
        print(f"     总用户: {total_users}  |  付费: {total_paid}  |  转化率: {conv}%")

        active = [s for s in segments if s["user_count"] > 0]
        if active:
            top = max(active, key=lambda s: s["user_count"])
            best = max(active, key=lambda s: s["conversion_rate"])
            print(f"     最大分群: [{top['segment']}] ({top['user_count']}人)")
            print(f"     最佳转化: [{best['segment']}] (转化率{best['conversion_rate']}%)")


def run_full_report():
    print(f"\n{'='*70}")
    print(f"  中韩出海数智港 - 用户分群分析")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")

    users = fetch_all_users()
    user_events = fetch_user_events()
    paid_emails = fetch_paid_emails()

    if not users:
        print("\n  没有用户数据。请先运行: python3 -m backend.analytics.seed_data")
        return

    total_events = sum(d["total_events"] for d in user_events.values())
    users_with_events = sum(1 for u in users if user_events.get(str(u["id"])))

    print(f"\n  数据概览:")
    print(f"    用户数: {len(users)}")
    print(f"    付费用户: {len(paid_emails)}")
    print(f"    有事件记录的用户: {users_with_events}")
    print(f"    总事件数: {total_events}")

    all_results = {}

    print("\n  -- 维度一: 注册时间分群 --")
    reg_segs = segment_by_registration(users, user_events, paid_emails)
    all_results["注册时间分群"] = reg_segs
    print_seg_table(reg_segs, "注册时间分群")

    print("  -- 维度二: 访问频率分群 --")
    freq_segs = segment_by_frequency(users, user_events, paid_emails)
    all_results["访问频率分群"] = freq_segs
    print_seg_table(freq_segs, "访问频率分群")

    print("  -- 维度三: 页面深度分群 --")
    depth_segs = segment_by_page_depth(users, user_events, paid_emails)
    all_results["页面深度分群"] = depth_segs
    print_seg_table(depth_segs, "页面深度分群")

    print("  -- 维度四: 付费行为分群 --")
    pay_segs = segment_by_payment(users, user_events, paid_emails)
    all_results["付费行为分群"] = pay_segs
    print_seg_table(pay_segs, "付费行为分群")

    print_summary(all_results)
    print()
    print("=" * 70)
    print("  用户分群分析完成")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="中韩出海数智港 - 用户分群分析")
    parser.add_argument("--report", "-r", action="store_true", default=True, help="显示完整分群报告")
    args = parser.parse_args()
    if args.report:
        run_full_report()


if __name__ == "__main__":
    main()
