"""
Membership upgrade helper.
Called when an order transitions to 'paid' to activate/upgrade membership.

Plan-to-Membership mapping:
  free    -> basic    (30 days)
  depth   -> silver   (365 days)
  annual  -> gold     (365 days)
  source  -> platinum (730 days)
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

PLAN_TO_LEVEL = {'free': 'basic', 'depth': 'silver', 'annual': 'gold', 'source': 'platinum'}
PLAN_DAYS = {'free': 30, 'depth': 365, 'annual': 365, 'source': 730}
UPGRADE_THRESHOLDS = [('platinum', 29999), ('gold', 9999), ('silver', 999), ('basic', 0)]

def get_target_level(plan_type: str) -> str:
    return PLAN_TO_LEVEL.get(plan_type, 'basic')

def get_expiry_date(plan_type: str) -> datetime:
    days = PLAN_DAYS.get(plan_type, 30)
    return datetime.utcnow() + timedelta(days=days)

def calculate_level_from_spent(total_spent: float) -> str:
    for level, threshold in UPGRADE_THRESHOLDS:
        if total_spent >= threshold:
            return level
    return 'basic'

def check_and_auto_upgrade(user_id: int, conn=None) -> Optional[str]:
    from backend.database import get_db
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True
    try:
        cur = conn.execute(
            'SELECT id, membership_level, total_spent, membership_expires FROM member_profiles WHERE user_id = ?',
            (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        cols = [desc[0] for desc in cur.description]
        prof = dict(zip(cols, row))
        best = calculate_level_from_spent(prof['total_spent'])
        rank = {'basic': 0, 'silver': 1, 'gold': 2, 'platinum': 3}
        if rank.get(best, 0) > rank.get(prof['membership_level'], 0):
            conn.execute(
                'UPDATE member_profiles SET membership_level = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?',
                (best, user_id))
            conn.commit()
            return best
        return None
    finally:
        if close_conn:
            conn.close()

def activate_membership(user_email: str, plan_type: str, price: float, conn=None) -> Dict[str, Any]:
    from backend.database import get_db
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True
    try:
        cur = conn.execute('SELECT id, username, email FROM users WHERE email = ?', (user_email,))
        row = cur.fetchone()
        if not row:
            cur = conn.execute('SELECT id, username, email FROM users WHERE username = ?', (user_email,))
            row = cur.fetchone()
        if not row:
            print(f'  W activate_membership: no user for {user_email}')
            return {'activated': False, 'reason': 'user_not_found'}
        user_id = row[0]
        cur = conn.execute('SELECT id, membership_level, total_spent, membership_expires FROM member_profiles WHERE user_id = ?', (user_id,))
        prof_row = cur.fetchone()
        target_level = get_target_level(plan_type)
        new_expiry = get_expiry_date(plan_type)
        if prof_row:
            cols = [desc[0] for desc in cur.description]
            prof = dict(zip(cols, prof_row))
            old_expires = prof.get('membership_expires')
            if old_expires:
                try:
                    old_dt = datetime.fromisoformat(old_expires)
                    if old_dt > new_expiry:
                        new_expiry = old_dt + timedelta(days=PLAN_DAYS.get(plan_type, 30))
                except (ValueError, TypeError):
                    pass
            new_total = prof['total_spent'] + price
            conn.execute(
                'UPDATE member_profiles SET membership_level = ?, total_spent = ?, membership_expires = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?',
                (target_level, new_total, new_expiry.isoformat(), user_id))
            conn.commit()
            upgraded = check_and_auto_upgrade(user_id, conn)
            final_level = upgraded or target_level
            print(f'  + Membership activated: user={user_email} plan={plan_type} level={final_level} spent={new_total}')
            return {'activated': True, 'user_id': user_id, 'membership_level': final_level, 'total_spent': new_total, 'membership_expires': new_expiry.isoformat(), 'upgraded': upgraded is not None}
        else:
            conn.execute(
                'INSERT INTO member_profiles (user_id, company_name, contact_person, contact_email, membership_level, total_spent, membership_expires) VALUES (?, '', '', ?, ?, ?, ?)',
                (user_id, user_email, target_level, price, new_expiry.isoformat()))
            conn.commit()
            print(f'  + Membership created: user={user_email} plan={plan_type} level={target_level}')
            return {'activated': True, 'user_id': user_id, 'membership_level': target_level, 'total_spent': price, 'membership_expires': new_expiry.isoformat(), 'upgraded': False}
    except Exception as e:
        print(f'  X Membership error: {e}')
        return {'activated': False, 'reason': str(e)}
    finally:
        if close_conn:
            conn.close()
