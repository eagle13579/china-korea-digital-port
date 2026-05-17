"""
合规自检工具 — 评分算法引擎（P0任务2版：8题→20题升级）

评分算法说明:
  评分模型: 20维 × 4级风险分

  每题选项分值: 0 (合规) / 1 (轻微) / 2 (关注) / 3 (危险)
  满分: 20题 × 3分 = 60分
  总分 = ((60 - sum(raw_scores)) / 60) * 100
       = 转化为 0-100 分制（100分=完全合规）

  风险等级:
    >80: 低风险 = 合规状况良好
    60-80: 中风险 = 存在合规缺口需要关注
    <60: 高风险 = 存在重大合规风险
"""

from backend.compliance.questions_data import QUESTIONS, get_question_by_id

# ── 常量定义 ──────────────────────────────────────────

MAX_RAW_SCORE = 60  # 20题 × 最高3分

# 风险等级阈值（按照P0任务1要求）
# >80=低风险, 60-80=中风险, <60=高风险
RISK_THRESHOLDS = [
    (80, "低风险", {"zh": "低风险", "ko": "저위험"},
     {"zh": "您的企业在合规方面表现良好，整体风险可控。建议继续保持并定期复查。",
      "ko": "귀사는 규제 준수 측면에서 양호한 상태이며, 전반적인 위험이 통제 가능합니다. 계속 유지하고 정기적으로 재검토하시기 바랍니다."}),
    (60, "中风险", {"zh": "中风险", "ko": "중위험"},
     {"zh": "您的企业存在一定合规风险，部分领域需要改善。建议优先处理低分维度。",
      "ko": "귀사에 일정 수준의 규제 위험이 있으며, 일부 분야의 개선이 필요합니다. 낮은 점수 분야를 우선 처리하시기 바랍니다."}),
    (0, "高风险", {"zh": "高风险", "ko": "고위험"},
     {"zh": "您的企业存在重大合规风险，大部分领域需要紧急处理，建议立即寻求专业合规顾问介入。",
      "ko": "귀사에 중대한 규제 위험이 있습니다. 대부분의 분야에서 긴급 조치가 필요합니다. 즉시 전문 규제 컨설턴트의 개입을 받으시기 바랍니다."}),
]

# 每道题最大分值是3，单维度的行动建议
SCORE_URGENCY = {
    0: {"level": "✅", "zh": "合规", "ko": "준수"},
    1: {"level": "⚡", "zh": "需优化", "ko": "개선 필요"},
    2: {"level": "⚠️", "zh": "需改善", "ko": "개선 필요"},
    3: {"level": "🔴", "zh": "立即行动", "ko": "즉시 조치 필요"},
}


# ── 核心评分函数 ──────────────────────────────────────

def calculate_score(answers: dict, language: str = "zh") -> dict:
    """计算合规评分

    Args:
        answers: {question_id: option_value} 格式的答案字典
        language: "zh" 或 "ko"

    Returns:
        完整的评分报告数据结构
    """
    # 1. 计算各维度原始分
    dimensions = []
    raw_sum = 0
    priorities = []

    for q in QUESTIONS:
        qid = q["id"]
        raw_score = answers.get(qid, 0)  # 默认0
        raw_sum += raw_score

        # 该维度得分（0-100分制）
        dim_score = round(((3 - raw_score) / 3) * 100)

        # 该维度的紧急程度
        urgency = SCORE_URGENCY.get(raw_score, SCORE_URGENCY[0])
        urgency_label = urgency["level"]
        status_label = urgency[language]

        dimensions.append({
            "id": qid,
            "dimension": q["dimension"],
            "dimension_label": q["dimension_label"][language],
            "raw_score": raw_score,       # 0-3
            "dim_score": dim_score,       # 0-100
            "status_icon": urgency_label,
            "status_label": status_label,
            "action_advice": q["action_advice"][language],
        })

        # 收集需要优先处理的项目
        if raw_score >= 2:
            priorities.append({
                "id": qid,
                "dimension_label": q["dimension_label"][language],
                "dim_score": dim_score,
                "raw_score": raw_score,
                "action_advice": q["action_advice"][language],
            })

    # 2. 计算总分
    total_score = round(((MAX_RAW_SCORE - raw_sum) / MAX_RAW_SCORE) * 100, 1)

    # 3. 风险等级
    risk = _get_risk(total_score, language)

    # 4. 按紧急程度排序优先项目
    priorities.sort(key=lambda x: x["raw_score"], reverse=True)

    # 5. 免责声明
    disclaimer = (
        "本报告由AI系统基于您提供的信息自动生成，仅供一般性参考，不构成正式法律意见或合规建议。"
        "针对具体情况，建议咨询持证专业人士。" if language == "zh" else
        "본 보고서는 AI 시스템이 귀하가 제공한 정보를 기반으로 자동 생성된 것으로, 일반적인 참고용입니다."
        "공식적인 법률 의견이나 규제 준수 조언을 구성하지 않습니다. 구체적인 상황에 대해서는 자격을 갖춘 전문가에게 문의하시기 바랍니다."
    )

    return {
        "total_score": total_score,
        "total_raw": raw_sum,
        "risk_level": risk["level"],
        "risk_label": risk["label"],
        "summary": risk["summary"],
        "dimensions": dimensions,
        "priorities": priorities,
        "disclaimer": disclaimer,
        "language": language,
    }


def _get_risk(score: float, language: str) -> dict:
    """根据分数获取风险等级"""
    for threshold, level, label, summary in RISK_THRESHOLDS:
        if score >= threshold:
            return {
                "level": level,
                "label": label[language],
                "summary": summary[language],
            }
    # fallback - should never reach here
    return {
        "level": "高风险",
        "label": "高风险" if language == "zh" else "고위험",
        "summary": "请联系我们获取紧急合规支持" if language == "zh" else "긴급 규제 지원이 필요합니다. 저희에게 연락하십시오.",
    }


# ── 报告生成接口 ──────────────────────────────────────

def generate_report_data(answers: dict, company_info: dict = None, language: str = "zh") -> dict:
    """生成完整的报告数据（用于PDF渲染和前端展示）

    Args:
        answers: {question_id: option_value}
        company_info: {
            "company_name": str,
            "contact_name": str,
            "email": str,
            "report_token": str,
        }
        language: "zh" 或 "ko"

    Returns:
        完整的报告数据结构
    """
    if company_info is None:
        company_info = {}

    score_result = calculate_score(answers, language)

    report = {
        "report_type": "compliance_health_check",
        "report_title_zh": "合规健康度评估报告",
        "report_title_ko": "규제 준수 건강 상태 평가 보고서",
        "platform_name": "中韩出海数智港",
        "platform_name_ko": "중한 출해 스마트 포트",

        # 企业信息
        "company_name": company_info.get("company_name", ""),
        "contact_name": company_info.get("contact_name", ""),
        "email": company_info.get("email", ""),
        "report_token": company_info.get("report_token", ""),
        "generated_at": company_info.get("generated_at", ""),

        # 评分结果
        "total_score": score_result["total_score"],
        "risk_level": score_result["risk_level"],
        "risk_label": score_result["risk_label"],
        "summary": score_result["summary"],

        # 各维度
        "dimensions": score_result["dimensions"],

        # 优先行动建议
        "priorities": score_result["priorities"],

        # 免责声明
        "disclaimer": score_result["disclaimer"],

        # 语言
        "language": language,
    }

    return report


# ── 自检工具函数 ──────────────────────────────────────

def score_from_answers(answers: dict) -> float:
    """快速计算总分（不含维度和评级详情）"""
    raw_sum = sum(answers.values())
    return round(((MAX_RAW_SCORE - raw_sum) / MAX_RAW_SCORE) * 100, 1)


def level_from_score(score: float, language: str = "zh") -> str:
    """根据分数返回评级标签"""
    risk = _get_risk(score, language)
    return f"{risk['level']} - {risk['label']}"


# ── 快速测试 ──────────────────────────────────────────

if __name__ == "__main__":
    # 模拟一个典型答案集（20题完整版）
    # 模拟一个典型答案集（20题完整版）    # 模拟一个典型答案集（20题完整版）
    test_answers = {
        1: 0,   # 行业准入
        2: 2,   # 数据安全
        3: 0,   # 知识产权
        4: 1,   # 跨境财税
        5: 1,   # 劳动用工
        6: 0,   # 签证移民
        7: 2,   # 公司设立
        8: 1,   # 进出口
        9: 0,   # 环境影响评价
        10: 1,  # 反商业贿赂
        11: 0,  # 外汇管制
        12: 1,  # 技术进出口管制
        13: 0,  # 产品质量标准
        14: 2,  # 广告合规
        15: 1,  # 电子商务法规
        16: 0,  # 消费者权益保护
        17: 2,  # 劳动派遣合规
        18: 0,  # 外商投资负面清单
        19: 1,  # 网络安全等级保护
        20: 0,  # 知识产权海关备案
    }

    result = calculate_score(test_answers, language="zh")
    print(f"总分: {result['total_score']}")
    print(f"风险等级: {result['risk_level']} - {result['risk_label']}")
    print(f"摘要: {result['summary']}")
    print()
    print("维度详情:")
    for d in result["dimensions"]:
        print(f"  {d['status_icon']} {d['dimension_label']}: {d['dim_score']}分 ({d['status_label']})")
    print()
    print("优先行动建议:")
    for p in result["priorities"]:
        print(f"  🔸 {p['dimension_label']} ({p['dim_score']}分)")
        print(f"     {p['action_advice'][:50]}...")
    print()

    # 韩语测试
    result_ko = calculate_score(test_answers, language="ko")
    print(f"总分: {result_ko['total_score']}")
    print(f"风险等级: {result_ko['risk_level']} - {result_ko['risk_label']}")
