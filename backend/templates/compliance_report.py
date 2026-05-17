"""
合规报告 HTML 渲染引擎 v2.0
渲染符合8模块+7条硬约束的企业级合规报告 HTML
"""

import json
from datetime import datetime


def render_report_html(report_data: dict) -> str:
    """渲染完整企业级合规报告HTML"""
    lang = report_data.get("language", "zh-CN")
    is_ko = lang == "ko-KR"

    overall_score = report_data["score_data"]["overall_score"]
    risk_level = report_data["score_data"]["risk_level"]
    dim_scores = report_data["score_data"]["dimension_scores"]
    risk_matrix = report_data["risk_matrix"]
    deep_dive = report_data["deep_dive"]
    roadmap = report_data["roadmap"]
    reg_comparison = report_data["regulation_comparison"]
    regulatory_alerts = report_data["regulatory_alerts"]
    percentiles = report_data["percentiles"]
    executive_summary = report_data["executive_summary"]
    methodology = report_data["methodology"]

    # 颜色
    overall_color = "#10B981" if overall_score >= 80 else ("#F59E0B" if overall_score >= 60 else ("#EF4444" if overall_score >= 40 else "#7F1D1D"))

    # 构建各模块HTML
    module_1 = _render_module_1(executive_summary, overall_score, overall_color, risk_level, dim_scores, is_ko)
    module_2 = _render_module_2(methodology, is_ko)
    module_3 = _render_module_3(dim_scores, overall_score, overall_color, is_ko)
    module_4 = _render_module_4(risk_matrix, is_ko)
    module_5 = _render_module_5(deep_dive, is_ko)
    module_6 = _render_module_6(reg_comparison, is_ko)
    module_7 = _render_module_7(roadmap, is_ko)
    module_8 = _render_module_8(regulatory_alerts, percentiles, report_data, is_ko)

    company = report_data.get("company_name", "")
    report_no = report_data.get("report_no", "")
    gen_date = report_data.get("generated_at_display", "")

    t = _T if not is_ko else _T_KO

    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{t('REPORT_TITLE')} - {company}</title>
<style>
{_CSS_STYLES}
</style>
</head>
<body>
<div class="report-enterprise">
    <!-- 报告头部 -->
    <div class="report-header">
        <div class="header-brand">
            <span class="brand-icon">🏛️</span>
            <span class="brand-text">{t('BRAND')}</span>
        </div>
        <h1 class="report-title">{t('REPORT_TITLE')}</h1>
        <p class="report-subtitle">{t('REPORT_SUBTITLE')}</p>
        <div class="report-meta">
            <div class="meta-item"><span class="meta-label">{t('REPORT_NO')}</span><span class="meta-value">{report_no}</span></div>
            <div class="meta-item"><span class="meta-label">{t('COMPANY')}</span><span class="meta-value">{company}</span></div>
            <div class="meta-item"><span class="meta-label">{t('DATE')}</span><span class="meta-value">{gen_date}</span></div>
            <div class="meta-item"><span class="meta-label">{t('VERSION')}</span><span class="meta-value">v2.0 {t('ENTERPRISE')}</span></div>
        </div>
    </div>

    <!-- ===== 模块①: 执行摘要（独立成页 - 约束5）===== -->
    {module_1}

    <!-- ===== 模块②: 方法论与范围 ===== -->
    {module_2}

    <!-- ===== 模块③: 全景仪表盘雷达图 ===== -->
    {module_3}

    <!-- ===== 模块④: 风险矩阵4×4热力图（约束2）===== -->
    {module_4}

    <!-- ===== 模块⑤: 逐维度深挖（约束1: 法规编号）===== -->
    {module_5}

    <!-- ===== 模块⑥: 中韩法规对比表 ===== -->
    {module_6}

    <!-- ===== 模块⑦: 整改路线图P0/P1/P2（约束3: 时间线+负责人）===== -->
    {module_7}

    <!-- ===== 模块⑧: 附录（约束6: 行业对标百分位 + 约束7: 法规预警）===== -->
    {module_8}

    <!-- 页脚 -->
    <div class="report-footer">
        <p class="disclaimer">{t('DISCLAIMER')}</p>
        <p class="copyright">{t('COPYRIGHT')}</p>
    </div>
</div>
</body>
</html>"""
    return html


class TranslationDict(dict):
    """可调用字典：t('KEY') 等价于 t['KEY']"""
    def __call__(self, key):
        return self.get(key, key)


# ── 多语言文本 ─────────────────────────────────
_T = TranslationDict({
    "REPORT_TITLE": "企业级合规健康度评估报告",
    "REPORT_SUBTITLE": "Enterprise Compliance Health Assessment Report",
    "BRAND": "中韩出海数智港",
    "REPORT_NO": "报告编号",
    "COMPANY": "评估对象",
    "DATE": "生成日期",
    "VERSION": "版本类型",
    "ENTERPRISE": "企业付费版",

    # Module 1
    "M1_TITLE": "一、执行摘要",
    "M1_SUBTITLE": "Executive Summary",
    "M1_SCORE": "综合合规得分",
    "M1_LEVEL": "风险等级",
    "M1_HIGH_RISK": "需关注维度",
    "M1_CRITICAL": "紧急维度",
    "M1_TOTAL": "评估维度",
    "M1_KF": "关键发现",
    "M1_KF1": "数据安全评分低 — 需关注跨境传输合规 (PIPL第38-43条)",
    "M1_KF2": "反商业贿赂评分低 — 需建立反腐败制度",
    "M1_KF3": "行业准入评分需提升 — 需完成负面清单审查 (外商投资法第4条)",

    # Module 2
    "M2_TITLE": "二、方法论与范围",
    "M2_SUBTITLE": "Methodology & Scope",
    "M2_SCOPE": "评估范围",
    "M2_METHOD": "评估方法",
    "M2_STANDARDS": "参考标准",
    "M2_LIMIT": "免责声明",
    "M2_DIMS": "覆盖合规维度",
    "M2_REGS": "法规引用数",

    # Module 3
    "M3_TITLE": "三、全景合规仪表盘",
    "M3_SUBTITLE": "Compliance Dashboard",
    "M3_RADAR": "合规雷达图",
    "M3_SCORE": "综合评分",
    "M3_SIX": "六大核心维度概览",

    # Module 4
    "M4_TITLE": "四、风险矩阵4×4热力图",
    "M4_SUBTITLE": "Risk Matrix Heatmap (4×4)",
    "M4_IMPACT": "影响程度",
    "M4_PROB": "发生概率",
    "M4_LOW": "低",
    "M4_MED": "中",
    "M4_HIGH": "高",
    "M4_CRITICAL": "严重",
    "M4_P0": "P0: 立即行动",
    "M4_P1": "P1: 短期整改",
    "M4_P2": "P2: 持续监控",
    "M4_LEGEND": "风险等级图例",

    # Module 5
    "M5_TITLE": "五、逐维度深度分析",
    "M5_SUBTITLE": "Dimension Deep-dive Analysis",
    "M5_SCORE": "评分",
    "M5_FINDINGS": "主要发现",
    "M5_RECOMMEND": "整改建议",
    "M5_REGS": "法规引用",
    "M5_OWNER": "负责人",
    "M5_RISK_MATRIX": "4×4矩阵定位",

    # Module 6
    "M6_TITLE": "六、中韩法规对比表",
    "M6_SUBTITLE": "CN-KR Regulation Comparison",
    "M6_TOPIC": "合规主题",
    "M6_CN": "中国法规",
    "M6_KR": "韩国法规",
    "M6_CN_REQ": "中国要求",
    "M6_KR_REQ": "韩国要求",
    "M6_GAP": "差异分析",

    # Module 7
    "M7_TITLE": "七、整改路线图 P0/P1/P2",
    "M7_SUBTITLE": "Remediation Roadmap",
    "M7_P0": "P0 — 紧急 (2周内)",
    "M7_P1": "P1 — 短期 (1-2个月)",
    "M7_P2": "P2 — 中期 (3-6个月)",
    "M7_DEADLINE": "时间线",
    "M7_OWNER": "负责人",
    "M7_ACTIONS": "行动项",

    # Module 8
    "M8_TITLE": "八、附录",
    "M8_SUBTITLE": "Appendix",
    "M8_BENCHMARK": "行业对标百分位分析",
    "M8_ALERTS": "未来3个月法规预警",
    "M8_ALERT_DATE": "日期",
    "M8_ALERT_TITLE": "预警事项",
    "M8_ALERT_IMPACT": "潜在影响",
    "M8_ALERT_ACTION": "建议行动",
    "M8_PERCENTILE": "百分位",
    "M8_GAP": "与行业均值差距",

    "DISCLAIMER": "※ 本报告由AI数字员工基于您提供的信息自动生成，仅供一般性参考，不构成正式法律意见或合规建议。针对具体情况，建议咨询持证专业人士。",
    "COPYRIGHT": "© 2026 中韩出海数智港 · China-Korea Digital Trade Gateway · All Rights Reserved",
})

_T_KO = TranslationDict({
    "REPORT_TITLE": "기업급 규정 준수 건강도 평가 보고서",
    "REPORT_SUBTITLE": "Enterprise Compliance Health Assessment Report",
    "BRAND": "한중 디지털 무역 포털",
    "REPORT_NO": "보고서 번호",
    "COMPANY": "평가 대상",
    "DATE": "생성일자",
    "VERSION": "버전 유형",
    "ENTERPRISE": "기업 유료 버전",

    "M1_TITLE": "1. 경영 요약",
    "M1_SUBTITLE": "Executive Summary",
    "M1_SCORE": "종합 규제 점수",
    "M1_LEVEL": "위험 등급",
    "M1_HIGH_RISK": "주의 차원",
    "M1_CRITICAL": "긴급 차원",
    "M1_TOTAL": "평가 차원",
    "M1_KF": "주요 발견 사항",
    "M1_KF1": "데이터 보안 점수 낮음 — 역외 이전 규제 주의 (PIPL 제38-43조)",
    "M1_KF2": "반뇌물 점수 낮음 — 반부패 제도 수립 필요",
    "M1_KF3": "업종 진입 점수 개선 필요 — 네거티브 리스트 검토 (외국인투자법 제4조)",

    "M2_TITLE": "2. 방법론 및 범위",
    "M2_SUBTITLE": "Methodology & Scope",
    "M2_SCOPE": "평가 범위",
    "M2_METHOD": "평가 방법",
    "M2_STANDARDS": "참고 기준",
    "M2_LIMIT": "면책 조항",
    "M2_DIMS": "커버 규제 차원",
    "M2_REGS": "법규 인용 수",

    "M3_TITLE": "3. 종합 규제 대시보드",
    "M3_SUBTITLE": "Compliance Dashboard",
    "M3_RADAR": "규제 레이더 차트",
    "M3_SCORE": "종합 점수",
    "M3_SIX": "6대 핵심 차원 개요",

    "M4_TITLE": "4. 리스크 매트릭스 4×4 열지도",
    "M4_SUBTITLE": "Risk Matrix Heatmap (4×4)",
    "M4_IMPACT": "영향 정도",
    "M4_PROB": "발생 확률",
    "M4_LOW": "낮음",
    "M4_MED": "중간",
    "M4_HIGH": "높음",
    "M4_CRITICAL": "심각",
    "M4_P0": "P0: 즉시 조치",
    "M4_P1": "P1: 단기 개선",
    "M4_P2": "P2: 지속 모니터링",
    "M4_LEGEND": "위험 등급 범례",

    "M5_TITLE": "5. 차원별 심층 분석",
    "M5_SUBTITLE": "Dimension Deep-dive Analysis",
    "M5_SCORE": "점수",
    "M5_FINDINGS": "주요 발견",
    "M5_RECOMMEND": "개선 제안",
    "M5_REGS": "법규 인용",
    "M5_OWNER": "담당자",
    "M5_RISK_MATRIX": "4×4 매트릭스 위치",

    "M6_TITLE": "6. 한중 법규 비교표",
    "M6_SUBTITLE": "CN-KR Regulation Comparison",
    "M6_TOPIC": "규제 주제",
    "M6_CN": "중국 법규",
    "M6_KR": "한국 법규",
    "M6_CN_REQ": "중국 요건",
    "M6_KR_REQ": "한국 요건",
    "M6_GAP": "차이 분석",

    "M7_TITLE": "7. 개선 로드맵 P0/P1/P2",
    "M7_SUBTITLE": "Remediation Roadmap",
    "M7_P0": "P0 — 긴급 (2주 이내)",
    "M7_P1": "P1 — 단기 (1-2개월)",
    "M7_P2": "P2 — 중기 (3-6개월)",
    "M7_DEADLINE": "일정",
    "M7_OWNER": "담당자",
    "M7_ACTIONS": "액션 항목",

    "M8_TITLE": "8. 부록",
    "M8_SUBTITLE": "Appendix",
    "M8_BENCHMARK": "업계 벤치마크 백분위 분석",
    "M8_ALERTS": "향후 3개월 법규 경보",
    "M8_ALERT_DATE": "날짜",
    "M8_ALERT_TITLE": "경보 사항",
    "M8_ALERT_IMPACT": "잠재적 영향",
    "M8_ALERT_ACTION": "권장 조치",
    "M8_PERCENTILE": "백분위",
    "M8_GAP": "업계 평균과 차이",

    "DISCLAIMER": "※ 본 보고서는 AI 디지털 직원이 귀사가 제공한 정보를 바탕으로 자동 생성되었으며, 일반적인 참고용으로만 제공됩니다. 공식적인 법률 의견이나 규정 준수 조언을 구성하지 않습니다. 구체적인 상황에 대해서는 자격을 갖춘 전문가에게 문의하시기 바랍니다.",
    "COPYRIGHT": "© 2026 한중 디지털 무역 포털 · China-Korea Digital Trade Gateway · All Rights Reserved",
})


# ── 模块渲染函数 ─────────────────────────────────

def _render_module_1(exec_summary: dict, overall: int, color: str, risk: str, dim_scores: dict, is_ko: bool) -> str:
    """Module ①: 执行摘要（独立成页 - 约束5）"""
    t = _T_KO if is_ko else _T
    kf_list = exec_summary.get("key_findings_ko" if is_ko else "key_findings_zh", [])

    dim_bars = ""
    dim_order = ["industry_access", "data_security", "intellectual_property", "cross_border_tax",
                 "labor_employment", "visa_immigration", "trade_compliance", "anti_bribery"]
    dim_names = {
        "industry_access": ("行业准入", "업종 진입"),
        "data_security": ("数据安全", "데이터 보안"),
        "intellectual_property": ("知识产权", "지식재산권"),
        "cross_border_tax": ("跨境财税", "국경 간 세무"),
        "labor_employment": ("劳动用工", "노동 고용"),
        "visa_immigration": ("签证移民", "비자 이민"),
        "trade_compliance": ("贸易合规", "무역 규제"),
        "anti_bribery": ("反商业贿赂", "반뇌물"),
    }
    for dim_id in dim_order:
        s = dim_scores.get(dim_id, 0)
        n = dim_names.get(dim_id, (dim_id, dim_id))
        name = n[1 if is_ko else 0]
        c = "#10B981" if s >= 80 else ("#F59E0B" if s >= 60 else ("#EF4444" if s >= 40 else "#7F1D1D"))
        dim_bars += f"""
        <div class="dim-bar-row">
            <div class="dim-bar-label">{name}</div>
            <div class="dim-bar-track"><div class="dim-bar-fill" style="width:{s}%;background:{c};"></div></div>
            <div class="dim-bar-score" style="color:{c};">{s}</div>
        </div>"""

    summary_text = exec_summary.get("summary_ko" if is_ko else "summary_zh", "")

    return f"""
    <div class="module page-break" id="module-1">
        <div class="module-header">
            <h2>{t('M1_TITLE')}</h2>
            <p class="module-subtitle">{t('M1_SUBTITLE')}</p>
        </div>
        <div class="exec-summary-grid">
            <div class="exec-score-section">
                <div class="overall-score-circle" style="border-color:{color};color:{color};">
                    <span class="score-number">{overall}</span>
                    <span class="score-unit">/100</span>
                </div>
                <div class="risk-badge" style="background:{color};">{t('M1_LEVEL')}: {risk}</div>
                <div class="score-meta-row">
                    <div class="score-meta-item">
                        <span class="meta-num" style="color:{'#EF4444' if exec_summary.get('high_risk_count', 0) > 0 else '#10B981'};">{exec_summary.get('high_risk_count', 0)}</span>
                        <span class="meta-desc">{t('M1_HIGH_RISK')}</span>
                    </div>
                    <div class="score-meta-item">
                        <span class="meta-num" style="color:{'#7F1D1D' if exec_summary.get('critical_count', 0) > 0 else '#10B981'};">{exec_summary.get('critical_count', 0)}</span>
                        <span class="meta-desc">{t('M1_CRITICAL')}</span>
                    </div>
                    <div class="score-meta-item">
                        <span class="meta-num">{exec_summary.get('total_dimensions', 0)}</span>
                        <span class="meta-desc">{t('M1_TOTAL')}</span>
                    </div>
                </div>
            </div>
            <div class="exec-detail-section">
                <div class="exec-summary-text">{summary_text}</div>
                <div class="key-findings">
                    <h4>🔍 {t('M1_KF')}</h4>
                    <ul>"""
    for kf in kf_list:
        html += f'<li>{kf}</li>'
    html += f"""
                    </ul>
                </div>
                <div class="dim-bars-compact">
                    {dim_bars}
                </div>
            </div>
        </div>
    </div>"""
    return html


def _render_module_2(methodology: dict, is_ko: bool) -> str:
    """Module ②: 方法论与范围"""
    t = _T_KO if is_ko else _T
    scope = methodology.get("scope_ko" if is_ko else "scope_zh", "")
    method = methodology.get("method_ko" if is_ko else "method_zh", "")
    limitations = methodology.get("limitations_ko" if is_ko else "limitations_zh", "")
    standards = methodology.get("standards_ko" if is_ko else "standards_zh", [])
    dims = methodology.get("dimensions_covered", 8)
    regs = methodology.get("regulations_referenced", 0)

    standards_html = "".join(f'<span class="std-badge">{s}</span>' for s in standards)

    return f"""
    <div class="module" id="module-2">
        <div class="module-header">
            <h2>{t('M2_TITLE')}</h2>
            <p class="module-subtitle">{t('M2_SUBTITLE')}</p>
        </div>
        <div class="methodology-grid">
            <div class="method-card">
                <div class="method-icon">🎯</div>
                <h4>{t('M2_SCOPE')}</h4>
                <p>{scope}</p>
            </div>
            <div class="method-card">
                <div class="method-icon">⚙️</div>
                <h4>{t('M2_METHOD')}</h4>
                <p>{method}</p>
            </div>
            <div class="method-card wide-card">
                <div class="method-icon">📚</div>
                <h4>{t('M2_STANDARDS')}</h4>
                <div class="standards-row">{standards_html}</div>
            </div>
            <div class="method-stats">
                <div class="stat-item"><span class="stat-num">{dims}</span><span>{t('M2_DIMS')}</span></div>
                <div class="stat-item"><span class="stat-num">{regs}</span><span>{t('M2_REGS')}</span></div>
            </div>
            <div class="method-disclaimer">
                <strong>{t('M2_LIMIT')}:</strong> {limitations}
            </div>
        </div>
    </div>"""


def _render_module_3(dim_scores: dict, overall: int, color: str, is_ko: bool) -> str:
    """Module ③: 全景仪表盘雷达图"""
    t = _T_KO if is_ko else _T

    # 生成雷达图SVG
    radar_svg = _generate_radar_chart_svg(dim_scores, is_ko)

    # 六维度概览卡片
    dim_order = ["industry_access", "data_security", "intellectual_property", "cross_border_tax",
                 "labor_employment", "visa_immigration"]
    dim_names_short = {
        "industry_access": ("行业准入", "업종 진입"),
        "data_security": ("数据安全", "데이터 보안"),
        "intellectual_property": ("知识产权", "지식재산권"),
        "cross_border_tax": ("跨境财税", "국경 간 세무"),
        "labor_employment": ("劳动用工", "노동 고용"),
        "visa_immigration": ("签证移民", "비자 이민"),
    }
    cards = ""
    for dim_id in dim_order:
        s = dim_scores.get(dim_id, 0)
        n = dim_names_short.get(dim_id, (dim_id, dim_id))
        name = n[1 if is_ko else 0]
        c = "#10B981" if s >= 80 else ("#F59E0B" if s >= 60 else ("#EF4444" if s >= 40 else "#7F1D1D"))
        pct = s
        cards += f"""
        <div class="dim-card" style="border-left:4px solid {c};">
            <div class="dim-card-header">
                <span class="dim-card-name">{name}</span>
                <span class="dim-card-score" style="color:{c};">{s}</span>
            </div>
            <div class="dim-card-bar"><div class="dim-card-fill" style="width:{pct}%;background:{c};"></div></div>
        </div>"""

    return f"""
    <div class="module page-break" id="module-3">
        <div class="module-header">
            <h2>{t('M3_TITLE')}</h2>
            <p class="module-subtitle">{t('M3_SUBTITLE')}</p>
        </div>
        <div class="dashboard-grid">
            <div class="radar-section">
                <h4>{t('M3_RADAR')}</h4>
                {radar_svg}
                <div class="overall-score-badge" style="background:{color};">
                    <span class="osb-label">{t('M3_SCORE')}</span>
                    <span class="osb-value">{overall}</span>
                </div>
            </div>
            <div class="dim-cards-section">
                <h4>{t('M3_SIX')}</h4>
                <div class="dim-cards-grid">{cards}</div>
            </div>
        </div>
    </div>"""


def _generate_radar_chart_svg(dim_scores: dict, is_ko: bool) -> str:
    """用纯SVG生成合规雷达图"""
    dim_order = ["industry_access", "data_security", "intellectual_property",
                 "cross_border_tax", "labor_employment", "visa_immigration"]
    dim_labels = {
        "industry_access": ("行业准入", "업종 진입"),
        "data_security": ("数据安全", "데이터 보안"),
        "intellectual_property": ("知识产权", "지식재산권"),
        "cross_border_tax": ("跨境财税", "국경 간 세무"),
        "labor_employment": ("劳动用工", "노동 고용"),
        "visa_immigration": ("签证移民", "비자 이민"),
    }

    cx, cy, r = 180, 180, 140
    n = len(dim_order)
    points = []
    label_positions = []
    for i, dim_id in enumerate(dim_order):
        angle = -90 + i * (360 / n)
        rad = angle * 3.14159 / 180
        score = dim_scores.get(dim_id, 0) / 100.0
        px = cx + r * score * 0.85 * _cos(rad)
        py = cy + r * score * 0.85 * _sin(rad)
        points.append(f"{px},{py}")

        lx = cx + (r + 28) * _cos(rad)
        ly = cy + (r + 28) * _sin(rad)
        label = dim_labels.get(dim_id, (dim_id, dim_id))[1 if is_ko else 0]
        # 分数显示
        score_val = dim_scores.get(dim_id, 0)
        sx = cx + (r + 8) * _cos(rad)
        sy = cy + (r + 8) * _sin(rad)
        label_positions.append((lx, ly, label, sx, sy, score_val))

    # 网格
    grid_lines = ""
    for level in [0.2, 0.4, 0.6, 0.8, 1.0]:
        pts = []
        for i, dim_id in enumerate(dim_order):
            angle = -90 + i * (360 / n)
            rad = angle * 3.14159 / 180
            px = cx + r * level * _cos(rad)
            py = cy + r * level * _sin(rad)
            pts.append(f"{px},{py}")
        grid_lines += f'<polygon points="{" ".join(pts)}" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>'

    # 轴线
    axis_lines = ""
    for i, dim_id in enumerate(dim_order):
        angle = -90 + i * (360 / n)
        rad = angle * 3.14159 / 180
        ex = cx + (r + 5) * _cos(rad)
        ey = cy + (r + 5) * _sin(rad)
        axis_lines += f'<line x1="{cx}" y1="{cy}" x2="{ex}" y2="{ey}" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>'

    # 数据区域
    data_polygon = f'<polygon points="{" ".join(points)}" fill="rgba(139,92,246,0.3)" stroke="#8B5CF6" stroke-width="2"/>'
    data_dots = ""
    for pt in points:
        x, y = pt.split(",")
        data_dots += f'<circle cx="{x}" cy="{y}" r="4" fill="#8B5CF6"/>'

    # 标签
    labels_svg = ""
    for lx, ly, label, sx, sy, score_val in label_positions:
        labels_svg += f'<text x="{lx}" y="{ly}" text-anchor="middle" dominant-baseline="middle" fill="#94A3B8" font-size="11">{label}</text>'
        labels_svg += f'<text x="{sx}" y="{sy + 4}" text-anchor="middle" dominant-baseline="middle" fill="#8B5CF6" font-size="12" font-weight="bold">{score_val}</text>'

    return f"""
    <div class="radar-svg-container">
        <svg viewBox="0 0 360 360" width="100%" height="100%" style="max-width:360px;margin:0 auto;display:block;">
            {grid_lines}
            {axis_lines}
            {data_polygon}
            {data_dots}
            {labels_svg}
            <circle cx="{cx}" cy="{cy}" r="4" fill="#8B5CF6"/>
        </svg>
    </div>"""


def _cos(rad):
    import math
    return math.cos(rad)


def _sin(rad):
    import math
    return math.sin(rad)


def _render_module_4(risk_matrix: list, is_ko: bool) -> str:
    """Module ④: 风险矩阵4×4热力图（约束2）"""
    t = _T_KO if is_ko else _T

    # 4×4矩阵网格
    grid_cells = ""
    for impact in [4, 3, 2, 1]:
        grid_cells += '<div class="matrix-row">'
        for prob in [1, 2, 3, 4]:
            rs = impact * prob
            if rs >= 12:
                bg = "#7F1D1D"; fg = "#fff"
            elif rs >= 8:
                bg = "#EF4444"; fg = "#fff"
            elif rs >= 4:
                bg = "#F59E0B"; fg = "#fff"
            else:
                bg = "#10B981"; fg = "#fff"

            # 查哪些维度落在此单元格
            cell_dims = [c for c in risk_matrix if c["impact"] == impact and c["probability"] == prob]
            dim_names = ""
            for c in cell_dims:
                name = c.get("name_ko" if is_ko else "name_zh", "")
                risk_l = c.get("risk_label_ko" if is_ko else "risk_label_zh", "")
                dim_names += f'<div class="matrix-dim-tag" style="border-color:{c["risk_color"]};color:{c["risk_color"]};">{name} ({risk_l})</div>'

            grid_cells += f"""
            <div class="matrix-cell" style="background:{bg};">
                <div class="matrix-cell-content">
                    <div class="matrix-rs">{rs}</div>
                    <div class="matrix-dims">{dim_names}</div>
                </div>
            </div>"""
        grid_cells += "</div>"

    # 图例
    legend = f"""
    <div class="matrix-legend">
        <div class="legend-item"><div class="legend-color" style="background:#7F1D1D;"></div><span>{t('M4_CRITICAL')} (12-16)</span></div>
        <div class="legend-item"><div class="legend-color" style="background:#EF4444;"></div><span>{t('M4_HIGH')} (8-9)</span></div>
        <div class="legend-item"><div class="legend-color" style="background:#F59E0B;"></div><span>{t('M4_MED')} (4-6)</span></div>
        <div class="legend-item"><div class="legend-color" style="background:#10B981;"></div><span>{t('M4_LOW')} (1-3)</span></div>
    </div>"""

    # 维度定位表
    dim_rows = ""
    for c in risk_matrix:
        name = c.get("name_ko" if is_ko else "name_zh", "")
        risk_l = c.get("risk_label_ko" if is_ko else "risk_label_zh", "")
        dim_rows += f"""
        <tr>
            <td>{name}</td>
            <td><div class="impact-bar"><div class="impact-fill" style="width:{(c['impact']/4)*100}%;background:{c['risk_color']};"></div></div><span class="impact-label">{c['impact']}/4</span></td>
            <td><div class="impact-bar"><div class="impact-fill" style="width:{(c['probability']/4)*100}%;background:{c['risk_color']};"></div></div><span class="impact-label">{c['probability']}/4</span></td>
            <td><span class="risk-score-badge" style="background:{c['risk_color']};">{c['risk_score']}</span></td>
            <td style="color:{c['risk_color']};font-weight:600;">{risk_l}</td>
            <td>{c.get('owner_ko' if is_ko else 'owner_zh', '-')}</td>
        </tr>"""

    return f"""
    <div class="module page-break" id="module-4">
        <div class="module-header">
            <h2>{t('M4_TITLE')}</h2>
            <p class="module-subtitle">{t('M4_SUBTITLE')}</p>
        </div>
        <div class="risk-matrix-grid">
            <div class="matrix-section">
                <div class="matrix-axis-label y-label">{t('M4_IMPACT')} ↑</div>
                <div class="matrix-container">
                    <div class="matrix-header">
                        <div class="matrix-corner"></div>
                        <div class="matrix-col-label">{t('M4_LOW')} ← {t('M4_PROB')} →</div>
                        <div class="matrix-col-label">{t('M4_MED')}</div>
                        <div class="matrix-col-label">{t('M4_HIGH')}</div>
                        <div class="matrix-col-label">{t('M4_CRITICAL')}</div>
                    </div>
                    <div class="matrix-header-row">
                        <div class="matrix-row-label">{t('M4_CRITICAL')}</div>
                        {grid_cells[:4*200]}
                    </div>
                </div>
                {legend}
            </div>
            <div class="matrix-table-section">
                <h4>{t('M4_P0')} / {t('M4_P1')} / {t('M4_P2')}</h4>
                <table class="matrix-dim-table">
                    <thead><tr><th>{t('M5_TITLE')}</th><th>{t('M4_IMPACT')}</th><th>{t('M4_PROB')}</th><th>{t('M4_LEGEND')}</th><th>{t('M1_LEVEL')}</th><th>{t('M5_OWNER')}</th></tr></thead>
                    <tbody>{dim_rows}</tbody>
                </table>
            </div>
        </div>
    </div>"""


def _render_module_5(deep_dive: list, is_ko: bool) -> str:
    """Module ⑤: 逐维度深挖（约束1: 法规编号）"""
    t = _T_KO if is_ko else _T
    sections = ""
    for i, dd in enumerate(deep_dive):
        findings = dd.get("findings_ko" if is_ko else "findings_zh", [])
        recommendations = dd.get("recommendations_ko" if is_ko else "recommendations_zh", [])
        reg_refs = dd.get("regulation_refs", [])
        rmc = dd.get("risk_matrix_cell", {})
        pctl = dd.get("percentile", {})
        score = dd["score"]
        risk_l = dd.get("risk_level_ko" if is_ko else "risk_level_zh", "")
        c = "#10B981" if score >= 80 else ("#F59E0B" if score >= 60 else ("#EF4444" if score >= 40 else "#7F1D1D"))

        findings_html = "".join(f"<li>{f}</li>" for f in findings)
        rec_html = "".join(f"<li>{r}</li>" for r in recommendations)
        reg_html = "".join(f'<span class="regulation-ref"><span class="reg-badge">{r["regulation"]}</span> {r["article"]} — {r.get("title_ko" if is_ko else "title_zh", "")}</span>' for r in reg_refs)
        if not reg_html:
            reg_html = '<span class="regulation-ref" style="color:#64748B;">' + ("无特定法规引用" if not is_ko else "특정 법규 인용 없음") + '</span>'

        owner = dd.get("owner_ko" if is_ko else "owner_zh", "-")
        icon = dd.get("icon", "📋")

        percentile_str = ""
        if pctl:
            rank = pctl.get("rank_ko" if is_ko else "rank_zh", "")
            gap = pctl.get("gap", 0)
            gap_str = f"{'+' if gap >= 0 else ''}{gap}"
            percentile_str = f'{t("M8_PERCENTILE")}: {pctl.get("percentile", 0)}% | {rank} | {t("M8_GAP")}: {gap_str}'

        sections += f"""
        <div class="deep-dive-item" style="border-left:4px solid {c};">
            <div class="dd-header">
                <div class="dd-title-row">
                    <span class="dd-icon">{icon}</span>
                    <h4>{dd.get("name_ko" if is_ko else "name_zh", "")}</h4>
                    <span class="dd-score" style="color:{c};">{score}</span>
                    <span class="dd-risk-badge" style="background:{c};">{risk_l}</span>
                </div>
                <div class="dd-meta-row">
                    <span class="dd-owner">👤 {t('M5_OWNER')}: {owner}</span>
                    <span class="dd-matrix">
                        🎯 {t('M5_RISK_MATRIX')}: {t('M4_IMPACT')}={rmc.get('impact', '-')}/4, {t('M4_PROB')}={rmc.get('probability', '-')}/4
                        → <strong style="color:{rmc.get('risk_color', '#666')};">{rmc.get('risk_label_ko' if is_ko else 'risk_label_zh', '')}</strong>
                    </span>
                </div>
                {('<div class="dd-percentile">📊 ' + percentile_str + '</div>') if percentile_str else ''}
            </div>
            <div class="dd-body">
                <div class="dd-findings">
                    <h5>🔍 {t('M5_FINDINGS')}</h5>
                    <ul>{findings_html}</ul>
                </div>
                <div class="dd-recommendations">
                    <h5>💡 {t('M5_RECOMMEND')}</h5>
                    <ul>{rec_html}</ul>
                </div>
                <div class="dd-regulations">
                    <h5>📜 {t('M5_REGS')}</h5>
                    <div class="reg-refs-row">{reg_html}</div>
                </div>
            </div>
        </div>"""

    return f"""
    <div class="module page-break" id="module-5">
        <div class="module-header">
            <h2>{t('M5_TITLE')}</h2>
            <p class="module-subtitle">{t('M5_SUBTITLE')}</p>
        </div>
        <div class="deep-dive-list">
            {sections}
        </div>
    </div>"""


def _render_module_6(reg_comparison: list, is_ko: bool) -> str:
    """Module ⑥: 中韩法规对比表"""
    t = _T_KO if is_ko else _T
    rows = ""
    for i, rc in enumerate(reg_comparison):
        rows += f"""
        <tr>
            <td><strong>{rc.get("topic_ko" if is_ko else "topic_zh", "")}</strong></td>
            <td><span class="reg-badge cn">{rc["cn_regulation"]}</span></td>
            <td><span class="reg-badge kr">{rc["kr_regulation"]}</span></td>
            <td style="font-size:13px;">{rc.get("cn_requirement_ko" if is_ko else "cn_requirement_zh", "")}</td>
            <td style="font-size:13px;">{rc.get("kr_requirement_ko" if is_ko else "kr_requirement_zh", "")}</td>
            <td style="font-size:13px;color:#F59E0B;">{rc.get("gap_analysis_ko" if is_ko else "gap_analysis_zh", "")}</td>
        </tr>"""

    return f"""
    <div class="module" id="module-6">
        <div class="module-header">
            <h2>{t('M6_TITLE')}</h2>
            <p class="module-subtitle">{t('M6_SUBTITLE')}</p>
        </div>
        <div class="comparison-table-wrapper">
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>{t('M6_TOPIC')}</th>
                        <th>{t('M6_CN')}</th>
                        <th>{t('M6_KR')}</th>
                        <th>{t('M6_CN_REQ')}</th>
                        <th>{t('M6_KR_REQ')}</th>
                        <th>{t('M6_GAP')}</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </div>"""


def _render_module_7(roadmap: list, is_ko: bool) -> str:
    """Module ⑦: 整改路线图P0/P1/P2（约束3: 时间线+负责人）"""
    t = _T_KO if is_ko else _T

    p0_items = [r for r in roadmap if r["priority"] == "P0"]
    p1_items = [r for r in roadmap if r["priority"] == "P1"]
    p2_items = [r for r in roadmap if r["priority"] == "P2"]

    def render_priority_section(items, pclass, plabel):
        if not items:
            return f'<div class="roadmap-section {pclass}"><h4>{plabel}</h4><p class="no-items">✅ ' + (t('M1_SCORE') + ' 良好，无需紧急整改' if not is_ko else '양호, 긴급 개선 불필요') + '</p></div>'
        items_html = ""
        for item in items:
            tl = item.get("timeline_ko" if is_ko else "timeline_zh", "")
            owner = item.get("owner_ko" if is_ko else "owner_zh", "")
            deadline = item.get("deadline_ko" if is_ko else "deadline_zh", "")
            name = item.get("name_ko" if is_ko else "name_zh", "")
            icon = item.get("icon", "📋")
            items_html += f"""
            <div class="roadmap-item {pclass}">
                <div class="rm-item-header">
                    <span class="rm-icon">{icon}</span>
                    <span class="rm-name">{name}</span>
                    <span class="rm-deadline">{deadline}</span>
                    <span class="rm-owner">👤 {owner}</span>
                </div>
                <div class="rm-timeline">📅 {t('M7_DEADLINE')}: {tl}</div>
            </div>"""
        return f'<div class="roadmap-section {pclass}"><h4>{plabel}</h4>{items_html}</div>'

    p0_html = render_priority_section(p0_items, "p0", t("M7_P0"))
    p1_html = render_priority_section(p1_items, "p1", t("M7_P1"))
    p2_html = render_priority_section(p2_items, "p2", t("M7_P2"))

    return f"""
    <div class="module page-break" id="module-7">
        <div class="module-header">
            <h2>{t('M7_TITLE')}</h2>
            <p class="module-subtitle">{t('M7_SUBTITLE')}</p>
        </div>
        <div class="roadmap-container">
            {p0_html}
            {p1_html}
            {p2_html}
        </div>
    </div>"""


def _render_module_8(regulatory_alerts: list, percentiles: dict, report_data: dict, is_ko: bool) -> str:
    """Module ⑧: 附录（约束6: 百分位 + 约束7: 法规预警）"""
    t = _T_KO if is_ko else _T

    # 法规预警
    alert_rows = ""
    for alert in regulatory_alerts:
        alert_rows += f"""
        <tr>
            <td style="white-space:nowrap;">{alert["date"]}</td>
            <td><strong>{alert.get("title_ko" if is_ko else "title_zh", "")}</strong></td>
            <td style="color:#EF4444;font-size:13px;">{alert.get("impact_ko" if is_ko else "impact_zh", "")}</td>
            <td style="font-size:13px;">{alert.get("action_required_ko" if is_ko else "action_required_zh", "")}</td>
            <td>{alert.get("regulation_ref", "")}</td>
        </tr>"""

    # 百分位对标
    percentile_rows = ""
    dim_order = ["industry_access", "data_security", "intellectual_property", "cross_border_tax",
                 "labor_employment", "visa_immigration", "trade_compliance", "anti_bribery"]
    dim_names = {
        "industry_access": ("行业准入", "업종 진입"),
        "data_security": ("数据安全", "데이터 보안"),
        "intellectual_property": ("知识产权", "지식재산권"),
        "cross_border_tax": ("跨境财税", "국경 간 세무"),
        "labor_employment": ("劳动用工", "노동 고용"),
        "visa_immigration": ("签证移民", "비자 이민"),
        "trade_compliance": ("贸易合规", "무역 규제"),
        "anti_bribery": ("反商业贿赂", "반뇌물"),
    }
    for dim_id in dim_order:
        p = percentiles.get(dim_id, {})
        n = dim_names.get(dim_id, (dim_id, dim_id))
        name = n[1 if is_ko else 0]
        score = p.get("score", 0)
        avg = p.get("industry_avg", 0)
        gap = p.get("gap", 0)
        pct = p.get("percentile", 0)
        rank = p.get("rank_ko" if is_ko else "rank_zh", "")
        c = "#10B981" if gap >= 0 else "#EF4444"
        percentile_rows += f"""
        <tr>
            <td>{name}</td>
            <td><strong>{score}</strong></td>
            <td>{avg}</td>
            <td style="color:{c};font-weight:600;">{'+' if gap >= 0 else ''}{gap}</td>
            <td>{pct}%</td>
            <td>{rank}</td>
        </tr>"""

    return f"""
    <div class="module" id="module-8">
        <div class="module-header">
            <h2>{t('M8_TITLE')}</h2>
            <p class="module-subtitle">{t('M8_SUBTITLE')}</p>
        </div>

        <!-- 约束7: 未来3个月法规预警 -->
        <div class="appendix-section">
            <h4>🚨 {t('M8_ALERTS')}</h4>
            <div class="alerts-table-wrapper">
                <table class="alerts-table">
                    <thead><tr><th>{t('M8_ALERT_DATE')}</th><th>{t('M8_ALERT_TITLE')}</th><th>{t('M8_ALERT_IMPACT')}</th><th>{t('M8_ALERT_ACTION')}</th><th>{t('M5_REGS')}</th></tr></thead>
                    <tbody>{alert_rows}</tbody>
                </table>
            </div>
        </div>

        <!-- 约束6: 行业对标百分位 -->
        <div class="appendix-section">
            <h4>📊 {t('M8_BENCHMARK')}</h4>
            <div class="benchmark-table-wrapper">
                <table class="benchmark-table">
                    <thead><tr><th>{t('M5_TITLE')}</th><th>{t('M5_SCORE')}</th><th>{t('M8_GAP')}</th><th>{t('M8_PERCENTILE')}</th><th>{t('M8_ALERT_TITLE')}</th></tr></thead>
                    <tbody>{percentile_rows}</tbody>
                </table>
            </div>
        </div>

        <div class="appendix-section">
            <h4>📋 {t('M2_REGS')} {report_data.get('score_data', {}).get('regulation_refs', [])}</h4>
        </div>
    </div>"""


# ── CSS Styles ─────────────────────────────────
_CSS_STYLES = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0A0A0F; color: #F1F5F9; padding: 20px; }
.report-enterprise { max-width: 1100px; margin: 0 auto; background: #12121A; border: 1px solid rgba(255,255,255,0.08); border-radius: 24px; overflow: hidden; }
.module { padding: 40px 48px; }
.page-break { page-break-before: always; }
.module-header { margin-bottom: 28px; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 16px; }
.module-header h2 { font-size: 24px; font-weight: 700; background: linear-gradient(135deg,#8B5CF6,#06B6D4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.module-subtitle { font-size: 13px; color: #64748B; margin-top: 4px; text-transform: uppercase; letter-spacing: 1px; }

/* Header */
.report-header { padding: 48px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.08); background: linear-gradient(180deg,rgba(139,92,246,0.05),transparent); }
.header-brand { display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 12px; }
.brand-icon { font-size: 24px; }
.brand-text { font-size: 16px; font-weight: 600; color: #8B5CF6; }
.report-title { font-size: 32px; font-weight: 800; background: linear-gradient(135deg,#8B5CF6,#06B6D4,#10B981); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 8px; }
.report-subtitle { color: #64748B; font-size: 14px; letter-spacing: 1px; }
.report-meta { display: flex; justify-content: center; gap: 32px; margin-top: 24px; flex-wrap: wrap; }
.meta-item { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.meta-label { font-size: 11px; color: #64748B; text-transform: uppercase; letter-spacing: 1px; }
.meta-value { font-size: 14px; font-weight: 600; color: #E2E8F0; }

/* M1: Executive Summary */
.exec-summary-grid { display: grid; grid-template-columns: 1fr 2fr; gap: 32px; }
.exec-score-section { text-align: center; padding: 32px; background: rgba(255,255,255,0.02); border-radius: 16px; }
.overall-score-circle { width: 160px; height: 160px; border-radius: 50%; border: 6px solid; display: flex; flex-direction: column; align-items: center; justify-content: center; margin: 0 auto 20px; }
.score-number { font-size: 52px; font-weight: 800; line-height: 1; }
.score-unit { font-size: 18px; font-weight: 600; }
.risk-badge { display: inline-block; padding: 8px 24px; border-radius: 20px; font-size: 14px; font-weight: 600; margin-bottom: 24px; }
.score-meta-row { display: flex; justify-content: center; gap: 24px; }
.score-meta-item { text-align: center; }
.meta-num { font-size: 28px; font-weight: 800; display: block; }
.meta-desc { font-size: 12px; color: #64748B; }
.exec-detail-section { padding: 16px 0; }
.exec-summary-text { font-size: 15px; line-height: 1.7; color: #CBD5E1; margin-bottom: 20px; }
.key-findings { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); border-radius: 12px; padding: 20px; margin-bottom: 20px; }
.key-findings h4 { font-size: 14px; color: #EF4444; margin-bottom: 12px; }
.key-findings ul { list-style: none; }
.key-findings li { font-size: 13px; color: #FCA5A5; padding: 4px 0; padding-left: 16px; position: relative; }
.key-findings li::before { content: '⚠️'; position: absolute; left: -4px; top: 4px; font-size: 12px; }
.dim-bars-compact { margin-top: 16px; }
.dim-bar-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.dim-bar-label { width: 90px; font-size: 13px; color: #94A3B8; flex-shrink: 0; }
.dim-bar-track { flex: 1; height: 14px; background: rgba(255,255,255,0.06); border-radius: 8px; overflow: hidden; }
.dim-bar-fill { height: 100%; border-radius: 8px; transition: width 1s ease; }
.dim-bar-score { width: 32px; font-size: 14px; font-weight: 700; text-align: right; }

/* M2: Methodology */
.methodology-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.method-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; padding: 24px; }
.method-card.wide-card { grid-column: 1 / -1; }
.method-icon { font-size: 28px; margin-bottom: 12px; }
.method-card h4 { font-size: 15px; font-weight: 600; margin-bottom: 8px; color: #E2E8F0; }
.method-card p { font-size: 13px; line-height: 1.7; color: #94A3B8; }
.standards-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.std-badge { padding: 6px 14px; background: rgba(139,92,246,0.12); border: 1px solid rgba(139,92,246,0.25); border-radius: 20px; font-size: 12px; color: #A78BFA; }
.method-stats { display: flex; gap: 24px; align-items: center; }
.stat-item { text-align: center; padding: 16px 24px; background: rgba(255,255,255,0.03); border-radius: 12px; }
.stat-num { font-size: 32px; font-weight: 800; color: #8B5CF6; display: block; }
.stat-item span:last-child { font-size: 12px; color: #64748B; }
.method-disclaimer { grid-column: 1 / -1; padding: 16px; background: rgba(251,191,36,0.06); border: 1px solid rgba(251,191,36,0.15); border-radius: 12px; font-size: 12px; color: #94A3B8; line-height: 1.6; }

/* M3: Dashboard */
.dashboard-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; }
.radar-section { text-align: center; position: relative; }
.radar-section h4, .dim-cards-section h4 { font-size: 14px; color: #64748B; margin-bottom: 16px; }
.overall-score-badge { position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%); width: 80px; height: 80px; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; opacity: 0; pointer-events: none; }
.dim-cards-grid { display: flex; flex-direction: column; gap: 12px; }
.dim-card { background: rgba(255,255,255,0.03); border-radius: 12px; padding: 14px 18px; }
.dim-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.dim-card-name { font-size: 14px; font-weight: 500; }
.dim-card-score { font-size: 20px; font-weight: 800; }
.dim-card-bar { height: 6px; background: rgba(255,255,255,0.06); border-radius: 4px; overflow: hidden; }
.dim-card-fill { height: 100%; border-radius: 4px; transition: width 1s ease; }

/* M4: Risk Matrix */
.risk-matrix-grid { display: grid; grid-template-columns: 1fr; gap: 32px; }
.matrix-section { }
.matrix-container { display: inline-grid; grid-template-columns: auto repeat(4,1fr); gap: 4px; }
.matrix-header { display: contents; }
.matrix-corner { grid-column: 1; }
.matrix-col-label { font-size: 11px; color: #64748B; text-align: center; padding: 4px; }
.matrix-header-row { display: contents; }
.matrix-row-label { font-size: 11px; color: #64748B; display: flex; align-items: center; padding: 4px; writing-mode: vertical-lr; }
.matrix-row { display: contents; }
.matrix-cell { min-width: 70px; min-height: 70px; border-radius: 8px; padding: 8px; display: flex; align-items: center; justify-content: center; }
.matrix-cell-content { text-align: center; }
.matrix-rs { font-size: 18px; font-weight: 800; color: #fff; }
.matrix-dims { margin-top: 4px; }
.matrix-dim-tag { font-size: 9px; border: 1px solid; border-radius: 4px; padding: 1px 4px; margin: 2px 0; background: rgba(0,0,0,0.3); }
.matrix-legend { display: flex; gap: 16px; margin-top: 16px; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #94A3B8; }
.legend-color { width: 16px; height: 16px; border-radius: 4px; }
.matrix-dim-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 16px; }
.matrix-dim-table th { background: rgba(255,255,255,0.03); padding: 10px 12px; text-align: left; font-weight: 600; color: #94A3B8; font-size: 12px; }
.matrix-dim-table td { padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.04); }
.impact-bar { display: inline-block; width: 60px; height: 8px; background: rgba(255,255,255,0.06); border-radius: 4px; vertical-align: middle; overflow: hidden; }
.impact-fill { height: 100%; border-radius: 4px; }
.impact-label { font-size: 12px; margin-left: 6px; }
.risk-score-badge { padding: 2px 10px; border-radius: 12px; font-weight: 600; font-size: 13px; }

/* M5: Deep Dive */
.deep-dive-list { display: flex; flex-direction: column; gap: 20px; }
.deep-dive-item { background: rgba(255,255,255,0.02); border-radius: 16px; padding: 24px; }
.dd-header { margin-bottom: 16px; }
.dd-title-row { display: flex; align-items: center; gap: 12px; }
.dd-icon { font-size: 20px; }
.dd-title-row h4 { font-size: 18px; font-weight: 600; flex: 1; }
.dd-score { font-size: 28px; font-weight: 800; }
.dd-risk-badge { padding: 4px 14px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.dd-meta-row { display: flex; gap: 20px; margin-top: 8px; font-size: 12px; color: #64748B; }
.dd-percentile { margin-top: 6px; font-size: 12px; color: #8B5CF6; }
.dd-body { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.dd-findings, .dd-recommendations { background: rgba(255,255,255,0.03); border-radius: 12px; padding: 16px; }
.dd-regulations { grid-column: 1 / -1; background: rgba(139,92,246,0.05); border: 1px solid rgba(139,92,246,0.1); border-radius: 12px; padding: 16px; }
.dd-body h5 { font-size: 13px; color: #94A3B8; margin-bottom: 8px; }
.dd-body ul { list-style: none; }
.dd-body li { font-size: 13px; color: #CBD5E1; padding: 4px 0; padding-left: 16px; position: relative; }
.dd-body li::before { content: '•'; position: absolute; left: 0; color: #8B5CF6; }
.reg-refs-row { display: flex; flex-wrap: wrap; gap: 8px; }
.regulation-ref { font-size: 12px; color: #A78BFA; }
.reg-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.reg-badge.cn { background: rgba(239,68,68,0.12); color: #FCA5A5; }
.reg-badge.kr { background: rgba(59,130,246,0.12); color: #93C5FD; }

/* M6: Comparison Table */
.comparison-table-wrapper { overflow-x: auto; }
.comparison-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.comparison-table th { background: rgba(255,255,255,0.03); padding: 12px; text-align: left; font-weight: 600; color: #94A3B8; }
.comparison-table td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.04); vertical-align: top; color: #CBD5E1; }

/* M7: Roadmap */
.roadmap-container { display: flex; flex-direction: column; gap: 24px; }
.roadmap-section { border-radius: 16px; padding: 24px; }
.roadmap-section.p0 { background: rgba(239,68,68,0.06); border: 1px solid rgba(239,68,68,0.2); }
.roadmap-section.p1 { background: rgba(245,158,11,0.06); border: 1px solid rgba(245,158,11,0.2); }
.roadmap-section.p2 { background: rgba(16,185,129,0.06); border: 1px solid rgba(16,185,129,0.2); }
.roadmap-section h4 { font-size: 16px; font-weight: 700; margin-bottom: 16px; }
.roadmap-section.p0 h4 { color: #EF4444; }
.roadmap-section.p1 h4 { color: #F59E0B; }
.roadmap-section.p2 h4 { color: #10B981; }
.no-items { font-size: 13px; color: #94A3B8; padding: 12px; }
.roadmap-item { padding: 16px; border-radius: 12px; margin-bottom: 12px; }
.roadmap-item.p0 { background: rgba(239,68,68,0.08); }
.roadmap-item.p1 { background: rgba(245,158,11,0.08); }
.roadmap-item.p2 { background: rgba(16,185,129,0.08); }
.rm-item-header { display: flex; align-items: center; gap: 12px; }
.rm-icon { font-size: 18px; }
.rm-name { font-weight: 600; flex: 1; font-size: 14px; }
.rm-deadline { font-size: 12px; padding: 3px 10px; border-radius: 8px; }
.roadmap-item.p0 .rm-deadline { background: rgba(239,68,68,0.15); color: #FCA5A5; }
.roadmap-item.p1 .rm-deadline { background: rgba(245,158,11,0.15); color: #FDE68A; }
.roadmap-item.p2 .rm-deadline { background: rgba(16,185,129,0.15); color: #A7F3D0; }
.rm-owner { font-size: 12px; color: #94A3B8; }
.rm-timeline { margin-top: 8px; font-size: 13px; color: #CBD5E1; padding-left: 30px; }

/* M8: Appendix */
.appendix-section { margin-bottom: 28px; }
.appendix-section h4 { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #E2E8F0; }
.alerts-table-wrapper, .benchmark-table-wrapper { overflow-x: auto; }
.alerts-table, .benchmark-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.alerts-table th, .benchmark-table th { background: rgba(255,255,255,0.03); padding: 10px 12px; text-align: left; font-weight: 600; color: #94A3B8; font-size: 12px; }
.alerts-table td, .benchmark-table td { padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.04); color: #CBD5E1; }

/* Footer */
.report-footer { padding: 32px 48px; border-top: 1px solid rgba(255,255,255,0.06); text-align: center; }
.disclaimer { font-size: 11px; color: #64748B; line-height: 1.6; max-width: 800px; margin: 0 auto 12px; }
.copyright { font-size: 11px; color: #475569; }

/* Responsive */
@media (max-width: 768px) {
    .exec-summary-grid { grid-template-columns: 1fr; }
    .dashboard-grid { grid-template-columns: 1fr; }
    .methodology-grid { grid-template-columns: 1fr; }
    .dd-body { grid-template-columns: 1fr; }
    .report-meta { gap: 16px; }
    .module { padding: 24px 20px; }
    .report-header { padding: 32px 20px; }
    .overall-score-circle { width: 120px; height: 120px; }
    .score-number { font-size: 40px; }
    .score-meta-row { gap: 12px; }
}

/* Print */
@media print {
    body { background: #fff; color: #333; padding: 0; }
    .report-enterprise { background: #fff; border: none; border-radius: 0; box-shadow: none; }
    .module-header h2 { -webkit-text-fill-color: #333; }
    .report-title { -webkit-text-fill-color: #333; }
    .key-findings { background: #fef2f2; }
    .deep-dive-item, .method-card { background: #f9fafb; border-color: #e5e7eb; }
    .dim-bar-track, .dim-card-bar { background: #e5e7eb; }
    .risk-matrix-cell { }
}
"""

# ── 清理格式 ─────────────────────────────────
def _clean_css(css: str) -> str:
    """Remove leading spaces from multi-line CSS"""
    import textwrap
    return textwrap.dedent(css)
