"""
中韩出海数智港 - 法规变化追踪系统 (Regulatory Change Monitor)
============================================================
监控韩国法制处(NLIC)、中国司法部、欧盟官方公报(EU OJ)的法规变化
模拟监控器 - 使用内置模拟数据返回最近的法规变化

纯标准库实现 | SQLite持久化 | 中韩双语
"""

import sqlite3
import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any

# ───────────────────────────────────────────────────────────
# 数据库路径(复用 portal.db)
# ───────────────────────────────────────────────────────────
DATA_DIR = Path(os.environ.get("DB_DIR", Path(__file__).parent.parent / "data"))
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "portal.db"


# ───────────────────────────────────────────────────────────
# 监控源配置
# ───────────────────────────────────────────────────────────
MONITORED_SOURCES = [
    {
        "name": "韩国法制处 (National Law Information Center)",
        "name_ko": "한국 법제처 (국가법령정보센터)",
        "base_url": "https://www.law.go.kr",
        "check_interval_hours": 24,
        "regulation": "K-DPA",
    },
    {
        "name": "中国司法部法规更新",
        "name_zh": "中华人民共和国司法部",
        "base_url": "https://www.moj.gov.cn",
        "check_interval_hours": 48,
        "regulation": "PIPL",
    },
    {
        "name": "欧盟官方公报 (EU Official Journal)",
        "name_en": "Official Journal of the European Union",
        "base_url": "https://eur-lex.europa.eu",
        "check_interval_hours": 24,
        "regulation": "GDPR",
    },
]

# ───────────────────────────────────────────────────────────
# 风险等级
# ───────────────────────────────────────────────────────────
RISK_LEVELS = {
    "high": {"zh": "高风险 [红]", "en": "High Risk", "ko": "고위험"},
    "medium": {"zh": "中风险 [黄]", "en": "Medium Risk", "ko": "중위험"},
    "low": {"zh": "低风险 [绿]", "en": "Low Risk", "ko": "저위험"},
    "info": {"zh": "信息 [蓝]", "en": "Informational", "ko": "정보"},
}

# ───────────────────────────────────────────────────────────
# 模拟法规更新数据(至少10条, 覆盖 K-DPA / GDPR / PIPL)
# ───────────────────────────────────────────────────────────
MOCK_REGULATION_UPDATES = [
    {
        "source": "韩国法制处 (National Law Information Center)",
        "title": "K-DPA 修正案: 跨境数据传输新规",
        "title_ko": "K-DPA 개정안: 해외 데이터 전송 신규 규정",
        "summary": "韩国个人信息保护委员会(PIPC)发布了K-DPA修正案, 要求向境外传输个人数据的企业必须进行影响评估并提交报告。新规将于2026年7月1日生效。",
        "summary_ko": "개인정보보호위원회(PIPC)는 해외로 개인정보를 전송하는 기업이 영향평가를 실시하고 보고서를 제출하도록 요구하는 K-DPA 개정안을 발표했습니다. 새로운 규정은 2026년 7월 1일부터 시행됩니다.",
        "effective_date": "2026-07-01",
        "affected_dimensions": "跨境传输,cross-border",
        "risk_level": "high",
    },
    {
        "source": "韩国法制处 (National Law Information Center)",
        "title": "K-DPA 罚款上限提高至全球营收的3%",
        "title_ko": "K-DPA 과징금 상한선 글로벌 매출의 3%로 인상",
        "summary": "韩国国会通过了K-DPA修正案, 将行政罚款上限从当前水平提高至企业全球年营收的3%, 大幅提升了违法成本。",
        "summary_ko": "한국 국회는 K-DPA 개정안을 통과시켜 행정 과징금 상한을 기업 글로벌 연간 매출의 3%로 인상하여 위반 비용을 크게 높였습니다.",
        "effective_date": "2026-09-15",
        "affected_dimensions": "罚款,penalty,合规治理,governance",
        "risk_level": "high",
    },
    {
        "source": "韩国法制处 (National Law Information Center)",
        "title": "K-DPA 儿童个人信息保护强化指南",
        "title_ko": "K-DPA 아동 개인정보 보호 강화 지침",
        "summary": "PIPC发布了关于加强14岁以下儿童个人信息保护的指南, 要求采用年龄验证技术和监护人同意机制。",
        "summary_ko": "PIPC는 14세 미만 아동의 개인정보 보호 강화를 위한 지침을 발표하여 연령 확인 기술 및 법정 대리인 동의 메커니즘 도입을 요구했습니다.",
        "effective_date": "2026-05-01",
        "affected_dimensions": "儿童保护,children,同意,consent",
        "risk_level": "medium",
    },
    {
        "source": "韩国法制处 (National Law Information Center)",
        "title": "K-DPA 数据泄露24小时报告义务细化",
        "title_ko": "K-DPA 데이터 유출 24시간 보고 의무 세부화",
        "summary": "修订后的K-DPA实施令细化了数据泄露报告义务, 明确了24小时内向PIPC报告的具体流程和内容要求。",
        "summary_ko": "개정된 K-DPA 시행령은 데이터 유출 보고 의무를 세분화하여 24시간 이내 PIPC에 보고하는 구체적인 절차와 내용 요구사항을 명시했습니다.",
        "effective_date": "2026-06-01",
        "affected_dimensions": "数据泄露,breach,安全,security",
        "risk_level": "high",
    },
    {
        "source": "欧盟官方公报 (EU Official Journal)",
        "title": "GDPR 数据保护官(DPO)任命指南更新",
        "title_ko": "GDPR 개인정보보호책임자(DPO) 임명 지침 업데이트",
        "summary": "EDPB发布了更新后的DPO任命指南, 扩展了需要强制任命DPO的情形, 包括AI系统开发和大规模数据处理活动。",
        "summary_ko": "EDPB는 AI 시스템 개발 및 대규모 데이터 처리 활동을 포함하여 DPO 의무 임명이 필요한 상황을 확대한 업데이트된 DPO 임명 지침을 발표했습니다.",
        "effective_date": "2026-04-15",
        "affected_dimensions": "DPO,治理,governance",
        "risk_level": "medium",
    },
    {
        "source": "欧盟官方公报 (EU Official Journal)",
        "title": "EU-US 数据隐私框架(DPF)第三轮充分性认定",
        "title_ko": "EU-US 데이터 개인정보 보호 프레임워크(DPF) 3차 적정성 결정",
        "summary": "欧盟委员会通过了EU-US数据隐私框架第三轮充分性认定, 新增了参与企业名单和投诉处理机制变更。",
        "summary_ko": "유럽위원회는 EU-US 데이터 개인정보 보호 프레임워크 3차 적정성 결정을 승인하여 참여 기업 목록 및 불만 처리 메커니즘 변경 사항을 추가했습니다.",
        "effective_date": "2026-05-20",
        "affected_dimensions": "跨境传输,cross-border,充分性,adequacy",
        "risk_level": "medium",
    },
    {
        "source": "欧盟官方公报 (EU Official Journal)",
        "title": "GDPR 自动化决策透明度新规",
        "title_ko": "GDPR 자동화 의사결정 투명성 신규 규정",
        "summary": "欧洲议会通过了关于自动化决策透明度的补充条例, 要求算法决策系统提供详细解释和人工审查选项。",
        "summary_ko": "유럽의회는 알고리즘 기반 의사결정 시스템에 대한 상세한 설명 및 인적 검토 옵션을 요구하는 자동화 의사결정 투명성에 관한 보충 규정을 승인했습니다.",
        "effective_date": "2026-08-01",
        "affected_dimensions": "自动化决策,automation,透明度,transparency",
        "risk_level": "high",
    },
    {
        "source": "欧盟官方公报 (EU Official Journal)",
        "title": "GDPR 数据可携带权实施细则更新",
        "title_ko": "GDPR 데이터 이동권 시행 세부 규칙 업데이트",
        "summary": "欧盟委员会更新了数据可携带权的实施细则, 新增了实时数据传输API标准和社交数据互操作性要求。",
        "summary_ko": "유럽위원회는 데이터 이동권 시행 세부 규칙을 업데이트하여 실시간 데이터 전송 API 표준 및 소셜 데이터 상호운용성 요구사항을 추가했습니다.",
        "effective_date": "2026-10-01",
        "affected_dimensions": "数据可携带,portability,用户权利,rights",
        "risk_level": "low",
    },
    {
        "source": "中国司法部法规更新",
        "title": "PIPL 个人信息出境标准合同备案新规",
        "title_ko": "PIPL 개인정보 해외이전 표준계약서 등록 신규 규정",
        "summary": "国家网信办发布了新版个人信息出境标准合同备案指南, 简化了备案流程, 但加强了对数据接收方的监督要求。",
        "summary_ko": "국가인터넷정보판공실은 개인정보 해외이전 표준계약서 등록 지침을 새로 발표하여 등록 절차를 간소화했지만 데이터 수신자에 대한 감독 요구사항을 강화했습니다.",
        "effective_date": "2026-06-15",
        "affected_dimensions": "跨境传输,cross-border,标准合同,SCC",
        "risk_level": "high",
    },
    {
        "source": "中国司法部法规更新",
        "title": "PIPL 敏感个人信息处理规则细化",
        "title_ko": "PIPL 민감 개인정보 처리 규칙 세분화",
        "summary": "中国网信办发布了细化后的敏感个人信息处理规则, 明确了生物识别、行踪轨迹、金融账户等敏感信息的单独同意要求。",
        "summary_ko": "중국 인터넷정보판공실은 생체인식, 위치 추적, 금융 계정 등 민감 정보에 대한 별도 동의 요구사항을 명확히 한 세분화된 민감 개인정보 처리 규칙을 발표했습니다.",
        "effective_date": "2026-07-01",
        "affected_dimensions": "敏感信息,sensitive,同意,consent",
        "risk_level": "high",
    },
    {
        "source": "中国司法部法规更新",
        "title": "PIPL 个人信息保护负责人任职要求更新",
        "title_ko": "PIPL 개인정보 보호 책임자 자격 요건 업데이트",
        "summary": "网信办更新了个人信息保护负责人的任职要求, 明确了需具备数据保护法律背景和CISP/PIP认证资质。",
        "summary_ko": "인터넷정보판공실은 개인정보 보호 책임자의 자격 요건을 업데이트하여 데이터 보호 법률 배경 및 CISP/PIP 인증 자격을 갖추도록 명시했습니다.",
        "effective_date": "2026-05-01",
        "affected_dimensions": "个人信息保护负责人,officer,治理,governance",
        "risk_level": "low",
    },
    {
        "source": "中国司法部法规更新",
        "title": "PIPL 自动化决策算法备案要求",
        "title_ko": "PIPL 자동화 의사결정 알고리즘 등록 요구사항",
        "summary": "国家网信办发布了算法备案新规, 要求使用个人信息进行自动化决策的企业必须在监管平台完成算法备案。",
        "summary_ko": "국가인터넷정보판공실은 개인정보를 활용한 자동화 의사결정을 하는 기업이 규제 플랫폼에 알고리즘 등록을 완료하도록 요구하는 알고리즘 등록 신규 규정을 발표했습니다.",
        "effective_date": "2026-09-01",
        "affected_dimensions": "自动化决策,automation,算法备案,algorithm",
        "risk_level": "medium",
    },
]


# ───────────────────────────────────────────────────────────
# 数据库操作
# ───────────────────────────────────────────────────────────
def get_db() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_tables():
    """
    初始化法规监控相关数据表
    - monitored_sources: 监控源配置
    - regulation_updates: 法规更新记录
    """
    conn = get_db()
    cursor = conn.cursor()

    # 监控源配置表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitored_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            base_url TEXT NOT NULL,
            last_check TIMESTAMP,
            check_interval_hours INTEGER NOT NULL DEFAULT 24,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK(status IN ('active', 'inactive', 'error'))
        )
    """)

    # 法规更新记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regulation_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            title_ko TEXT,
            summary TEXT NOT NULL,
            summary_ko TEXT,
            effective_date TEXT,
            affected_dimensions TEXT,
            risk_level TEXT NOT NULL DEFAULT 'medium'
                CHECK(risk_level IN ('high', 'medium', 'low', 'info')),
            status TEXT NOT NULL DEFAULT 'new'
                CHECK(status IN ('new', 'read', 'acknowledged')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def init_source_configs():
    """初始化监控源配置(如不存在则插入)"""
    conn = get_db()
    cursor = conn.cursor()

    for src in MONITORED_SOURCES:
        cursor.execute(
            "SELECT id FROM monitored_sources WHERE name = ?",
            (src["name"],),
        )
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO monitored_sources (name, base_url, check_interval_hours, status)
                VALUES (?, ?, ?, 'active')
            """, (src["name"], src["base_url"], src["check_interval_hours"]))

    conn.commit()
    conn.close()


def seed_mock_data():
    """初始化模拟法规更新数据(仅当表为空时)"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM regulation_updates")
    count = cursor.fetchone()["cnt"]
    if count > 0:
        print(f"法规更新表已有 {count} 条记录, 跳过种子数据")
        conn.close()
        return

    for update in MOCK_REGULATION_UPDATES:
        cursor.execute("""
            INSERT INTO regulation_updates
                (source, title, title_ko, summary, summary_ko,
                 effective_date, affected_dimensions, risk_level, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new')
        """, (
            update["source"],
            update["title"],
            update.get("title_ko", ""),
            update["summary"],
            update.get("summary_ko", ""),
            update["effective_date"],
            update["affected_dimensions"],
            update["risk_level"],
        ))

    conn.commit()
    conn.close()
    print(f"已插入 {len(MOCK_REGULATION_UPDATES)} 条模拟法规更新记录")


def init_all():
    """完整初始化: 建表 + 源配置 + 种子数据"""
    init_tables()
    init_source_configs()
    seed_mock_data()
    print("法规变化追踪系统初始化完成")


# ───────────────────────────────────────────────────────────
# 核心功能函数
# ───────────────────────────────────────────────────────────
def check_all_sources() -> List[Dict[str, Any]]:
    """
    检查所有监控源(模拟实现)
    - 从数据库中读取已有的未处理更新
    - 模拟返回最近新增的法规变化
    - 更新 last_check 时间戳
    """
    conn = get_db()
    cursor = conn.cursor()

    # 列出所有活跃的监控源并更新检查时间
    cursor.execute("SELECT id, name FROM monitored_sources WHERE status = 'active'")
    sources = cursor.fetchall()

    now = datetime.now().isoformat()
    for src in sources:
        cursor.execute(
            "UPDATE monitored_sources SET last_check = ? WHERE id = ?",
            (now, src["id"]),
        )

    # 获取最近30天内的更新记录(模拟新发现的法规变化)
    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
    cursor.execute("""
        SELECT ru.*, ms.last_check
        FROM regulation_updates ru
        LEFT JOIN monitored_sources ms ON ru.source = ms.name
        WHERE ru.created_at >= ?
        ORDER BY ru.created_at DESC
    """, (thirty_days_ago,))

    updates = [dict(row) for row in cursor.fetchall()]
    conn.commit()
    conn.close()

    print(f"已检查 {len(sources)} 个监控源, 发现 {len(updates)} 条近期法规变化")
    return updates


def get_pending_updates() -> List[Dict[str, Any]]:
    """获取所有未处理的法规更新(status = 'new')"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM regulation_updates
        WHERE status = 'new'
        ORDER BY risk_level DESC, effective_date DESC
    """)

    updates = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return updates


def acknowledge_update(update_id: int) -> bool:
    """
    确认某条法规更新已处理
    返回: True=成功, False=未找到
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE regulation_updates SET status = 'acknowledged', updated_at = ? WHERE id = ? AND status != 'acknowledged'",
        (datetime.now().isoformat(), update_id),
    )
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()

    if success:
        print(f"已确认更新 ID={update_id}")
    else:
        print(f"更新 ID={update_id} 不存在或已被确认")
    return success


def get_alerts_by_dimension(dimension: str) -> List[Dict[str, Any]]:
    """
    按维度获取相关法规预警(模糊匹配 affected_dimensions 字段)
    支持中英文搜索, 例如: 跨境传输, cross-border, 同意, consent
    """
    conn = get_db()
    cursor = conn.cursor()

    keyword = f"%{dimension}%"
    cursor.execute("""
        SELECT * FROM regulation_updates
        WHERE affected_dimensions LIKE ?
        ORDER BY risk_level DESC, effective_date DESC
    """, (keyword,))

    updates = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return updates


def get_monitor_stats() -> Dict[str, Any]:
    """获取监控统计信息"""
    conn = get_db()
    cursor = conn.cursor()

    # 各状态统计
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM regulation_updates
        GROUP BY status
    """)
    status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

    # 各风险等级统计
    cursor.execute("""
        SELECT risk_level, COUNT(*) as count
        FROM regulation_updates
        GROUP BY risk_level
    """)
    risk_counts = {row["risk_level"]: row["count"] for row in cursor.fetchall()}

    # 各来源统计
    cursor.execute("""
        SELECT source, COUNT(*) as count
        FROM regulation_updates
        GROUP BY source
    """)
    source_counts = {row["source"]: row["count"] for row in cursor.fetchall()}

    # 各维度涉及的更新数量(按逗号分隔的维度词统计)
    cursor.execute("SELECT affected_dimensions FROM regulation_updates")
    dimension_items = {}
    for row in cursor.fetchall():
        dims = row["affected_dimensions"].split(",")
        for d in dims:
            d = d.strip()
            if d:
                dimension_items[d] = dimension_items.get(d, 0) + 1

    # 监控源状态
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM monitored_sources
        GROUP BY status
    """)
    source_status = {row["status"]: row["count"] for row in cursor.fetchall()}

    # 最近检查时间
    cursor.execute("""
        SELECT MAX(last_check) as last_check FROM monitored_sources
    """)
    row = cursor.fetchone()
    last_check = row["last_check"] if row else None

    conn.close()

    return {
        "total_updates": sum(status_counts.values()),
        "status_breakdown": status_counts,
        "risk_breakdown": risk_counts,
        "source_breakdown": source_counts,
        "dimension_breakdown": dimension_items,
        "source_status": source_status,
        "last_check_timestamp": last_check,
        "pending_count": status_counts.get("new", 0),
    }


def format_update(update: Dict[str, Any], verbose: bool = False) -> str:
    """格式化单条法规更新记录为可读文本"""
    rid = update["id"]
    risk = RISK_LEVELS.get(update["risk_level"], {}).get("zh", update["risk_level"])
    status_map = {
        "new": "[新] 未处理",
        "read": "[*] 已读",
        "acknowledged": "[V] 已确认",
    }
    status_str = status_map.get(update["status"], update["status"])
    title = update["title"]
    eff_date = update.get("effective_date") or "未指定"
    source = update["source"]

    lines = [
        f"  [{rid}] {risk} | {status_str}",
        f"  来源: {source}",
        f"  标题: {title}",
        f"  生效: {eff_date}",
    ]
    if verbose:
        lines.append(f"  摘要: {update['summary']}")
        if update.get("title_ko"):
            lines.append(f"  KO:  {update['title_ko']}")
        lines.append(f"  维度: {update['affected_dimensions']}")

    return "\n".join(lines)


# ───────────────────────────────────────────────────────────
# API 响应构建 (供后端 main.py 调用)
# ───────────────────────────────────────────────────────────
def build_alert_response(updates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """构建预警API响应"""
    alerts = []
    for u in updates:
        alerts.append({
            "id": u["id"],
            "source": u["source"],
            "title": u["title"],
            "title_ko": u.get("title_ko", ""),
            "summary": u["summary"],
            "summary_ko": u.get("summary_ko", ""),
            "effective_date": u.get("effective_date", ""),
            "affected_dimensions": u["affected_dimensions"].split(",") if u["affected_dimensions"] else [],
            "risk_level": u["risk_level"],
            "risk_label": RISK_LEVELS.get(u["risk_level"], {}).get("zh", u["risk_level"]),
            "status": u["status"],
            "created_at": u.get("created_at", ""),
        })
    return {
        "total": len(alerts),
        "alerts": alerts,
        "timestamp": datetime.now().isoformat(),
    }


def build_stats_response(stats: Dict[str, Any]) -> Dict[str, Any]:
    """构建统计API响应"""
    risk_labels = {}
    for k, v in RISK_LEVELS.items():
        risk_labels[k] = v["zh"]

    return {
        **stats,
        "risk_labels": risk_labels,
        "timestamp": datetime.now().isoformat(),
    }


# ───────────────────────────────────────────────────────────
# CLI 入口
# ───────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="中韩出海数智港 - 法规变化追踪系统 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 -m backend.compliance.regulatory_monitor --init
  python3 -m backend.compliance.regulatory_monitor --check
  python3 -m backend.compliance.regulatory_monitor --alerts
  python3 -m backend.compliance.regulatory_monitor --alerts --dimension cross-border
  python3 -m backend.compliance.regulatory_monitor --acknowledge 5
  python3 -m backend.compliance.regulatory_monitor --stats
        """,
    )
    parser.add_argument("--init", action="store_true", help="初始化数据库表和种子数据")
    parser.add_argument("--check", action="store_true", help="检查所有监控源, 获取最新法规变化")
    parser.add_argument("--alerts", action="store_true", help="列出所有未处理的法规预警")
    parser.add_argument("--dimension", type=str, default=None, help="按维度筛选预警(与--alerts配合使用)")
    parser.add_argument("--acknowledge", type=int, default=None, metavar="ID", help="确认处理某条预警(指定ID)")
    parser.add_argument("--stats", action="store_true", help="显示监控统计信息")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    # 默认无参数时显示帮助
    has_action = any([args.init, args.check, args.alerts, args.acknowledge is not None, args.stats])
    if not has_action:
        parser.print_help()
        sys.exit(0)

    # 确保表存在
    init_tables()

    if args.init:
        init_all()
        return

    if args.check:
        updates = check_all_sources()
        if not updates:
            print("未发现新的法规变化")
        else:
            print(f"\n{'='*60}")
            print(f"  近期法规变化 ({len(updates)} 条)")
            print(f"{'='*60}\n")
            for u in updates:
                print(format_update(u, verbose=args.verbose))
        return

    if args.alerts:
        if args.dimension:
            updates = get_alerts_by_dimension(args.dimension)
            title = f"维度 [{args.dimension}] 相关预警"
        else:
            updates = get_pending_updates()
            title = "待处理法规预警"

        if not updates:
            print("没有待处理的法规预警")
        else:
            print(f"\n{'='*60}")
            print(f"  {title} ({len(updates)} 条)")
            print(f"{'='*60}\n")
            for u in updates:
                print(format_update(u, verbose=args.verbose))
        return

    if args.acknowledge is not None:
        success = acknowledge_update(args.acknowledge)
        sys.exit(0 if success else 1)

    if args.stats:
        stats = get_monitor_stats()
        print(f"\n{'='*60}")
        print(f"  法规变化追踪 - 监控统计")
        print(f"{'='*60}")
        print(f"  总记录数:      {stats['total_updates']}")
        print(f"  待处理:        {stats['pending_count']}")
        print(f"  最后检查时间:  {stats['last_check_timestamp'] or '尚未检查'}")
        print()
        print(f"  -- 状态分布 --")
        for k, v in stats["status_breakdown"].items():
            print(f"    {k}: {v}")
        print()
        print(f"  -- 风险等级分布 --")
        for k, v in stats["risk_breakdown"].items():
            label = RISK_LEVELS.get(k, {}).get("zh", k)
            print(f"    {label}: {v}")
        print()
        print(f"  -- 监控源状态 --")
        for k, v in stats["source_status"].items():
            print(f"    {k}: {v} 个源")
        print()
        print(f"  -- 各来源更新数 --")
        for k, v in stats["source_breakdown"].items():
            print(f"    {k}: {v} 条")
        print()
        print(f"  -- 涉及维度统计 (Top 10) --")
        sorted_dims = sorted(stats["dimension_breakdown"].items(), key=lambda x: -x[1])
        for k, v in sorted_dims[:10]:
            print(f"    {k}: {v} 条")
        print(f"{'='*60}")
        return


if __name__ == "__main__":
    main()
