"""
合规自检工具API路由 - 中韩出海数智港
PRD-007: 合规自检工具
POST /api/v1/compliance/check → 提交自检答案，生成评分和报告
GET  /api/v1/compliance/questions → 获取自检问卷题目
GET  /api/v1/compliance/report/{token} → 获取已生成的报告数据
GET  /api/v1/compliance/report/{token}/pdf → 下载报告PDF
"""

import json
import uuid
import os
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List

from backend.database import get_db

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])

# ─── 问卷题目定义 ───
# 覆盖6大合规维度：行业准入、数据安全、知识产权、财税、用工、签证
# PRD-007 的8道题，每道题4个选项，分值 0/0.5/1/2

QUESTIONS = [
    {
        "id": "q1",
        "dimension": "行业准入",
        "dimension_ko": "업종 허가",
        "employee": "徐准",
        "employee_ko": "서준",
        "question_zh": "您的企业是否已完成中国市场的行业准入可行性评估？",
        "question_ko": "귀사는 중국 시장의 업종 진입 가능성 평가를 완료하셨습니까?",
        "options": [
            {"value": 0, "label_zh": "已完成全面评估，确定不在负面清单限制范围内", "label_ko": "전면 평가 완료, 네거티브 리스트 제한 범위 밖 확인"},
            {"value": 1, "label_zh": "正在进行评估，尚未最终确认", "label_ko": "평가 진행 중, 최종 확인 전"},
            {"value": 1.5, "label_zh": "已确认属于限制类行业，正在准备应对方案", "label_ko": "제한 업종 확인, 대응 방안 준비 중"},
            {"value": 2, "label_zh": "尚未进行任何行业准入评估", "label_ko": "아직 업종 진입 평가를 진행하지 않음"},
        ]
    },
    {
        "id": "q2",
        "dimension": "行业准入",
        "dimension_ko": "업종 허가",
        "employee": "徐准",
        "employee_ko": "서준",
        "question_zh": "您的企业是否已确立进入中国市场的投资架构（WFOE/JV/代表处）？",
        "question_ko": "귀사는 중국 시장 진입을 위한 투자 구조(WFOE/JV/대표처)를 확립하셨습니까?",
        "options": [
            {"value": 0, "label_zh": "已确定WFOE架构，并完成可行性研究", "label_ko": "WFOE 구조 확정, 타당성 연구 완료"},
            {"value": 1, "label_zh": "正在比较不同架构方案的优劣", "label_ko": "다양한 구조方案 비교 중"},
            {"value": 1.5, "label_zh": "已确定JV合作方，正在谈判阶段", "label_ko": "JV 파트너 확정, 협상 단계"},
            {"value": 2, "label_zh": "尚未考虑投资架构问题", "label_ko": "아직 투자 구조를 고려하지 않음"},
        ]
    },
    {
        "id": "q3",
        "dimension": "数据安全",
        "dimension_ko": "데이터 보안",
        "employee": "丹书",
        "employee_ko": "유진",
        "question_zh": "您的企业是否涉及个人信息或数据的跨境传输？",
        "question_ko": "귀사는 개인정보 또는 데이터의 국경 간 전송에 관련되어 있습니까?",
        "options": [
            {"value": 0, "label_zh": "完全不涉及个人信息处理和数据跨境传输", "label_ko": "개인정보 처리 및 데이터 국경 간 전송 미해당"},
            {"value": 1, "label_zh": "有少量个人信息处理，但不涉及跨境传输", "label_ko": "소량 개인정보 처리, 국경 간 전송 없음"},
            {"value": 1.5, "label_zh": "涉及少量数据跨境传输，已了解安全评估要求", "label_ko": "소량 데이터 국경 간 전송, 안전 평가 요건 인지"},
            {"value": 2, "label_zh": "有大量数据跨境传输需求，尚未启动安全评估", "label_ko": "대량 데이터 국경 간 전송 필요, 안전 평가 미시작"},
        ]
    },
    {
        "id": "q4",
        "dimension": "知识产权",
        "dimension_ko": "지식재산권",
        "employee": "金镇宇",
        "employee_ko": "지호",
        "question_zh": "您的企业在中国是否已完成商标/专利的知识产权布局？",
        "question_ko": "귀사는 중국에서 상표/특허의 지식재산권 포트폴리오를 완료하셨습니까?",
        "options": [
            {"value": 0, "label_zh": "已完成核心商标和专利的中国注册", "label_ko": "핵심 상표 및 특허 중국 등록 완료"},
            {"value": 1, "label_zh": "正在进行商标注册申请", "label_ko": "상표 등록 출원 진행 중"},
            {"value": 1.5, "label_zh": "已了解注册流程但尚未启动", "label_ko": "등록 절차 인지했으나 아직 시작 전"},
            {"value": 2, "label_zh": "尚未考虑知识产权保护", "label_ko": "아직 지식재산권 보호 고려하지 않음"},
        ]
    },
    {
        "id": "q5",
        "dimension": "财税",
        "dimension_ko": "재무세무",
        "employee": "朴泰俊",
        "employee_ko": "재현",
        "question_zh": "您的企业是否了解中韩税收协定及跨境税务合规要求？",
        "question_ko": "귀사는 한중 조세협정 및 국경 간 세무 규정 준수 요건을 이해하고 계십니까?",
        "options": [
            {"value": 0, "label_zh": "已聘请专业税务顾问，充分了解中韩税收协定", "label_ko": "전문 세무 자문 고용, 한중 조세협정 충분히 이해"},
            {"value": 1, "label_zh": "了解基本税收政策，但缺乏专业税务筹划", "label_ko": "기본 세무 정책 이해, 전문 세무 계획 부족"},
            {"value": 1.5, "label_zh": "知道有中韩税收协定但具体内容不清楚", "label_ko": "한중 조세협정 존재는 알지만 구체적 내용 미파악"},
            {"value": 2, "label_zh": "完全不了解中国的税收合规要求", "label_ko": "중국의 세무 규정 요건 전혀 모름"},
        ]
    },
    {
        "id": "q6",
        "dimension": "财税",
        "dimension_ko": "재무세무",
        "employee": "朴泰俊",
        "employee_ko": "재현",
        "question_zh": "您的企业是否已完成FDI外汇登记及资本金汇入安排？",
        "question_ko": "귀사는 FDI 외환 등록 및 자본금 송금 준비를 완료하셨습니까?",
        "options": [
            {"value": 0, "label_zh": "已完成外汇登记，资本金汇入渠道畅通", "label_ko": "외환 등록 완료, 자본금 송금 채널 확보"},
            {"value": 1, "label_zh": "正在办理外汇登记手续", "label_ko": "외환 등록 절차 진행 중"},
            {"value": 1.5, "label_zh": "了解外汇登记要求但尚未启动", "label_ko": "외환 등록 요건 인지했으나 미시작"},
            {"value": 2, "label_zh": "不了解资本金跨境汇入的合规流程", "label_ko": "자본금 국경 간 송금 규정 절차 미파악"},
        ]
    },
    {
        "id": "q7",
        "dimension": "用工",
        "dimension_ko": "고용",
        "employee": "李朴",
        "employee_ko": "현우",
        "question_zh": "您的企业是否有中国境内的员工或计划派遣韩籍员工？",
        "question_ko": "귀사는 중국 내 직원이 있거나 한국인 직원 파견을 계획하고 계십니까?",
        "options": [
            {"value": 0, "label_zh": "已有中国本地团队，劳动合同及社保均合规", "label_ko": "중국 현지 팀 보유, 근로계약 및 사회보험合规"},
            {"value": 1, "label_zh": "计划招聘中国员工，对劳动合同法有基本了解", "label_ko": "중국 직원 채용 계획, 노동계약법 기본 이해"},
            {"value": 1.5, "label_zh": "计划派遣韩籍员工，了解工作签证要求", "label_ko": "한국인 직원 파견 계획, 취업 비자 요건 인지"},
            {"value": 2, "label_zh": "不了解中国劳动用工法规和社保要求", "label_ko": "중국 노동 고용 규정 및 사회보험 요건 미파악"},
        ]
    },
    {
        "id": "q8",
        "dimension": "签证",
        "dimension_ko": "비자",
        "employee": "崔敏智",
        "employee_ko": "미영",
        "question_zh": "您的企业是否了解韩籍员工在华工作签证及居留许可要求？",
        "question_ko": "귀사는 한국인 직원의 중국 취업 비자 및 거류 허가 요건을 이해하고 계십니까?",
        "options": [
            {"value": 0, "label_zh": "已为韩籍员工办妥工作签证和居留许可", "label_ko": "한국인 직원 취업 비자 및 거류 허가 완료"},
            {"value": 1, "label_zh": "了解签证流程，正准备申请材料", "label_ko": "비자 절차 이해, 신청 서류 준비 중"},
            {"value": 1.5, "label_zh": "知道需要工作签证但不清楚具体要求和流程", "label_ko": "취업 비자 필요성 인지, 구체적 요건 및 절차 미파악"},
            {"value": 2, "label_zh": "完全不清楚外籍员工在华工作的签证要求", "label_ko": "외국인 직원 중국 취업 비자 요건 전혀 모름"},
        ]
    }
]

# ─── 维度名称映射 ───
DIMENSION_NAMES_ZH = {
    "行业准入": "行业准入",
    "数据安全": "数据安全",
    "知识产权": "知识产权",
    "财税": "财税",
    "用工": "用工",
    "签证": "签证"
}

DIMENSION_NAMES_KO = {
    "行业准入": "업종 허가",
    "数据安全": "데이터 보안",
    "知识产权": "지식재산권",
    "财税": "재무세무",
    "用工": "고용",
    "签证": "비자"
}

# ─── Request / Response Models ───

class ComplianceCheckRequest(BaseModel):
    answers: dict = Field(..., description="答案字典 {question_id: answer_value}")
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    language: str = "zh-CN"

class ComplianceCheckResponse(BaseModel):
    success: bool = True
    token: str = ""
    score: int = 0
    score_detail: dict = {}
    report_html: str = ""
    message: str = ""


# ─── 评分引擎 ───

def calculate_score(answers: dict) -> tuple:
    """
    计算评分
    每题满分2分，共8题，满分16分
    映射到100分制：总分 = (sum / 16) * 100
    返回 (总得分0-100, 各维度得分详情dict)
    """
    total = 0.0
    dimension_scores = {}

    for q in QUESTIONS:
        qid = q["id"]
        dim = q["dimension"]
        val = answers.get(qid, None)
        if val is None:
            val = 2  # 未回答视为最高风险
        total += float(val)

        if dim not in dimension_scores:
            dimension_scores[dim] = {"score": 0, "max": 0, "count": 0}
        dimension_scores[dim]["score"] += float(val)
        dimension_scores[dim]["max"] += 2
        dimension_scores[dim]["count"] += 1

    # 计算百分比
    max_score = len(QUESTIONS) * 2  # 16
    score_pct = round((total / max_score) * 100)

    # 各维度百分比
    dim_detail = {}
    for dim, data in dimension_scores.items():
        dim_pct = round((data["score"] / data["max"]) * 100)
        dim_detail[dim] = {
            "score": dim_pct,
            "level": _get_level(dim_pct)
        }

    return score_pct, dim_detail


def _get_level(score: int) -> str:
    if score >= 80:
        return "优秀"
    elif score >= 60:
        return "良好"
    elif score >= 40:
        return "关注"
    else:
        return "危险"


def get_level_label_en(level: str) -> str:
    return {"优秀": "Excellent", "良好": "Good", "关注": "Attention", "危险": "Dangerous"}.get(level, "Unknown")


def _generate_report_html(score: int, score_detail: dict, company_name: str, language: str, token: str) -> str:
    """生成合规健康度报告HTML"""
    is_ko = language == "ko-KR"

    # 颜色分类
    if score >= 80:
        color = "#10B981"
        level = "优秀" if not is_ko else "우수"
        level_en = "Excellent"
    elif score >= 50:
        color = "#F59E0B"
        level = "良好" if not is_ko else "양호"
        level_en = "Good"
    else:
        color = "#EF4444"
        level = "关注" if not is_ko else "주의"
        level_en = "Attention"

    # 推荐方案
    if score >= 80:
        plan_zh = "免费初评报告"
        plan_ko = "무료 초기 평가 보고서"
        plan_desc_zh = "您的合规状况总体良好，建议下载完整报告，并在需要时咨询数字员工获取针对性建议。"
        plan_desc_ko = "규정 준수 상태가 전반적으로 양호합니다. 전체 보고서를 다운로드하고 필요시 디지털 직원에게 문의하세요."
    elif score >= 50:
        plan_zh = "深度合规方案"
        plan_ko = "심층 규정 준수方案"
        plan_desc_zh = "您在多个维度存在合规风险，建议升级到深度方案，由数字合规官提供一对一诊断。"
        plan_desc_ko = "여러 영역에서 규정 준수 리스크가 있습니다. 심층方案으로 업그레이드하여 디지털 규제 전문가의 1:1 진단을 받으세요."
    else:
        plan_zh = "年订阅合规保障"
        plan_ko = "연간 구독 규정 준수 보장"
        plan_desc_zh = "您的合规风险较高，建议立即启动年订阅保障计划，全链路合规官团队全程陪跑。"
        plan_desc_ko = "규정 준수 리스크가 높습니다. 즉시 연간 구독 보장 플랜을 시작하여 전 영역 규제 전문가 팀의 지원을 받으세요."

    plan = plan_ko if is_ko else plan_zh
    plan_desc = plan_desc_ko if is_ko else plan_desc_zh

    date_str = datetime.now().strftime("%Y-%m-%d")
    report_no = f"CHC-{datetime.now().strftime('%Y%m%d')}-{token[:8].upper()}"

    # 维度条状图
    dim_names = DIMENSION_NAMES_KO if is_ko else DIMENSION_NAMES_ZH
    bars_html = ""
    dim_order = ["行业准入", "数据安全", "知识产权", "财税", "用工", "签证"]
    for dim in dim_order:
        dim_name = dim_names.get(dim, dim)
        data = score_detail.get(dim, {"score": 0, "level": "危险"})
        dim_score = data["score"]
        dim_level = data["level"]
        dim_level_en = get_level_label_en(dim_level)
        level_ko = {"优秀": "우수", "良好": "양호", "关注": "주의", "危险": "위험"}.get(dim_level, dim_level)

        bar_color = "#10B981" if dim_score >= 80 else ("#F59E0B" if dim_score >= 50 else "#EF4444")
        level_label = level_ko if is_ko else dim_level

        bars_html += f"""
        <div class="dimension-bar-row">
            <div class="dim-label">{dim_name}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width:{dim_score}%;background:{bar_color};"></div>
            </div>
            <div class="dim-score" style="color:{bar_color};">{dim_score}</div>
            <div class="dim-level" style="color:{bar_color};">{level_label}</div>
        </div>"""

    # 改善建议
    low_dims = [(dim, data) for dim, data in score_detail.items() if data["score"] < 60]
    suggestions_zh = []
    suggestions_ko = []

    suggestion_map_zh = {
        "行业准入": "建议尽快完成行业准入可行性评估和投资架构设计。推荐咨询徐准（首席合规官）。",
        "数据安全": "建议启动数据分类分级和跨境传输安全评估。推荐咨询丹书（数据合规官）。",
        "知识产权": "建议尽快完成商标和专利的中国注册布局，防止抢注风险。推荐咨询金镇宇（知产合规官）。",
        "财税": "建议聘请专业税务顾问，完成中韩税收筹划和FDI外汇登记。推荐咨询朴泰俊（财税合规官）。",
        "用工": "建议规范劳动合同和社保缴纳流程。推荐咨询李朴（用工合规官）。",
        "签证": "建议了解外籍员工工作签证和居留许可要求。推荐咨询崔敏智（签证合规官）。"
    }
    suggestion_map_ko = {
        "行业准入": "업종 진입 가능성 평가 및 투자 구조 설계를 신속히 완료하세요. 서준(수석 규제 책임자)에게 문의하세요.",
        "数据安全": "데이터 분류·등급 및 국경 간 전송 안전 평가를 시작하세요. 유진(데이터 규제 전문가)에게 문의하세요.",
        "知识产权": "중국 내 상표·특허 등록 포트폴리오를 신속히 완료하여 선점 등록 리스크를 방지하세요. 지호(지식재산 규제 전문가)에게 문의하세요.",
        "财税": "전문 세무 자문을 고용하고 한중 세무 계획 및 FDI 외환 등록을 완료하세요. 재현(재무세무 규제 전문가)에게 문의하세요.",
        "用工": "근로계약 및 사회보험 납부 절차를 표준화하세요. 현우(고용 규제 전문가)에게 문의하세요.",
        "签证": "외국인 직원 취업 비자 및 거류 허가 요건을 확인하세요. 미영(비자 규제 전문가)에게 문의하세요."
    }

    for dim, data in low_dims:
        if is_ko:
            suggestions_ko.append(f"• <strong>{dim_names.get(dim, dim)}</strong>（{data['score']}점）- {suggestion_map_ko.get(dim, '')}")
        else:
            suggestions_zh.append(f"• <strong>{dim}</strong>（{data['score']}分）- {suggestion_map_zh.get(dim, '')}")

    suggestions_html = ""
    if is_ko:
        if suggestions_ko:
            suggestions_html = "<div class='suggestions'><h4>📌 우선 개선 제안</h4>" + "<br>".join(suggestions_ko) + "</div>"
        else:
            suggestions_html = "<div class='suggestions'><h4>✅ 규정 준수 상태 우수</h4><p>모든 차원에서 양호한 규정 준수 상태를 유지하고 있습니다.</p></div>"
    else:
        if suggestions_zh:
            suggestions_html = "<div class='suggestions'><h4>📌 优先改进建议</h4>" + "<br>".join(suggestions_zh) + "</div>"
        else:
            suggestions_html = "<div class='suggestions'><h4>✅ 合规状况优秀</h4><p>您在各个维度均保持良好的合规状况。</p></div>"

    company_display = company_name or ("我的企业" if not is_ko else "내 기업")
    title = "合规健康度评估报告" if not is_ko else "규정 준수 건강도 평가 보고서"
    subtitle = "COMPLIANCE HEALTH CHECK REPORT"
    disclaimer = "※ 本报告由AI数字员工基于您提供的信息自动生成，仅供一般性参考，不构成正式法律意见或合规建议。针对具体情况，建议咨询持证专业人士。" if not is_ko else "※ 본 보고서는 AI 디지털 직원이 귀사가 제공한 정보를 바탕으로 자동 생성되었으며, 일반적인 참고용으로만 제공됩니다. 공식적인 법률 의견이나 규정 준수 조언을 구성하지 않습니다. 구체적인 상황에 대해서는 자격을 갖춘 전문가에게 문의하시기 바랍니다."
    report_for = "评估对象" if not is_ko else "평가 대상"
    score_text = "综合评分" if not is_ko else "종합 점수"
    plan_text = "推荐方案" if not is_ko else "추천方案"
    report_no_text = "报告编号" if not is_ko else "보고서 번호"
    date_text = "生成日期" if not is_ko else "생성일자"
    get_report_btn = "获取完整PDF报告" if not is_ko else "전체 PDF 보고서 받기"

    report_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{title}</title>
<style>
    body {{ font-family: 'Inter','-apple-system',sans-serif; background: #0A0A0F; color: #F1F5F9; padding: 30px; }}
    .report-container {{ max-width: 800px; margin: 0 auto; background: #12121A; border: 1px solid rgba(255,255,255,0.08); border-radius: 20px; padding: 40px; }}
    .report-header {{ text-align: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 24px; margin-bottom: 28px; }}
    .report-header h2 {{ font-size: 28px; font-weight: 700; background: linear-gradient(135deg,#8B5CF6,#06B6D4,#10B981); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
    .report-header p {{ color: #94A3B8; font-size: 14px; }}
    .report-meta {{ display: flex; justify-content: space-between; font-size: 14px; color: #64748B; margin-bottom: 28px; }}
    .score-section {{ text-align: center; padding: 30px; background: rgba(255,255,255,0.03); border-radius: 16px; margin-bottom: 28px; }}
    .score-circle {{ width: 120px; height: 120px; border-radius: 50%; border: 6px solid {color}; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px; font-size: 36px; font-weight: 800; color: {color}; }}
    .score-level {{ font-size: 18px; font-weight: 600; color: {color}; }}
    .dimension-bars {{ margin-bottom: 28px; }}
    .dimension-bar-row {{ display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }}
    .dim-label {{ width: 100px; font-size: 14px; color: #94A3B8; flex-shrink: 0; }}
    .bar-track {{ flex: 1; height: 18px; background: rgba(255,255,255,0.06); border-radius: 10px; overflow: hidden; }}
    .bar-fill {{ height: 100%; border-radius: 10px; transition: width 1s ease; }}
    .dim-score {{ width: 40px; font-size: 16px; font-weight: 700; text-align: right; }}
    .dim-level {{ width: 50px; font-size: 13px; text-align: left; }}
    .suggestions {{ background: rgba(255,255,255,0.03); border-radius: 16px; padding: 24px; margin-bottom: 28px; line-height: 1.8; }}
    .suggestions h4 {{ font-size: 16px; margin-bottom: 12px; color: #F1F5F9; }}
    .plan-section {{ background: linear-gradient(135deg,rgba(139,92,246,0.1),rgba(6,182,212,0.1)); border: 1px solid rgba(139,92,246,0.2); border-radius: 16px; padding: 24px; margin-bottom: 28px; }}
    .plan-section h4 {{ font-size: 16px; color: #8B5CF6; margin-bottom: 8px; }}
    .plan-section p {{ font-size: 14px; color: #94A3B8; line-height: 1.6; }}
    .disclaimer {{ font-size: 12px; color: #64748B; line-height: 1.6; margin-top: 24px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.08); }}
    .get-report-btn {{ display: inline-block; padding: 14px 32px; background: linear-gradient(135deg,#8B5CF6,#06B6D4); color: #fff; border: none; border-radius: 12px; font-size: 16px; font-weight: 600; cursor: pointer; text-decoration: none; transition: all 0.3s; }}
    .get-report-btn:hover {{ transform: translateY(-2px); box-shadow: 0 8px 24px rgba(139,92,246,0.4); }}
    @media print {{ body {{ background: #fff; color: #333; }} .report-container {{ background: #fff; border: none; box-shadow: none; }} .score-circle {{ border-color: #333; color: #333; }} .bar-track {{ background: #eee; }} .get-report-btn {{ display: none; }} }}
    @media (max-width: 600px) {{ .report-container {{ padding: 20px; }} .dim-label {{ width: 80px; font-size: 12px; }} }}
</style>
</head>
<body>
<div class="report-container">
    <div class="report-header">
        <h2>{title}</h2>
        <p>{subtitle}</p>
    </div>
    <div class="report-meta">
        <span>{report_no_text}: {report_no}</span>
        <span>{date_text}: {date_str}</span>
        <span>{report_for}: {company_display}</span>
    </div>
    <div class="score-section">
        <div class="score-circle">{score}</div>
        <div class="score-level">{score_text}: {level} ({level_en})</div>
    </div>
    <div class="dimension-bars">
        {bars_html}
    </div>
    {suggestions_html}
    <div class="plan-section">
        <h4>🎯 {plan_text}: {plan}</h4>
        <p>{plan_desc}</p>
        <div style="text-align:center;margin-top:16px;">
            <a href="/api/v1/compliance/report/{token}/pdf" class="get-report-btn">{get_report_btn}</a>
        </div>
    </div>
    <div class="disclaimer">{disclaimer}</div>
</div>
</body>
</html>"""

    return report_html


# ─── 合规咨询知识库 ───
# 用于徐准AI合规咨询DEMO的预设问答

COMPLIANCE_KNOWLEDGE_BASE = [
    {
        "keywords": ["审批", "流程", "审批流程", "手续", "设立", "登记", "许可", "approval", "procedure", "registration"],
        "answer_zh": """韩企进入中国市场的一般审批流程如下：

**第一步：行业准入评估**
确认拟进入行业是否在《外商投资准入特别管理措施（负面清单）》内。不在负面清单内的行业，实行备案管理；在负面清单内的限制类行业，需进行核准。

**第二步：选择投资架构**
根据业务需求选择 WFOE（外商独资企业）、JV（合资企业）或代表处，不同架构的审批要求不同。

**第三步：名称预先核准**
向市场监督管理局申请企业名称预先核准。

**第四步：申请外商投资备案/核准**
- 备案制：负面清单外行业，通过商务部"外商投资综合管理信息系统"在线备案
- 核准制：负面清单内限制类行业，需向商务部和发改委提交核准申请

**第五步：工商登记**
取得备案/核准文件后，向市场监督管理局申请营业执照。

**第六步：后续登记**
- 刻制公章 → 银行开户 → 税务登记 → 外汇登记 → 海关登记（如需进出口）

**第七步：行业许可（如需）**
部分行业需取得特定资质许可，如：食品经营许可证、ICP许可证、增值电信业务许可证等。

⏱ 一般耗时：WFOE备案制约20-30个工作日，核准制约60-90个工作日。""",
        "answer_ko": """한국 기업의 중국 시장 진입 일반 승인 절차는 다음과 같습니다:

**1단계: 업종 진입 평가**
진입하려는 업종이 '외국인 투자 진입 특별 관리 조치(네거티브 리스트)'에 포함되는지 확인합니다. 네거티브 리스트에 없는 업종은 등록 관리, 제한 업종은 승인이 필요합니다.

**2단계: 투자 구조 선택**
WFOE(외국인 독자 기업), JV(합자 기업) 또는 대표처 중 선택하며, 구조별 승인 요건이 다릅니다.

**3단계: 상호 사전 승인**
시장 감독 관리국에 기업 상호 사전 승인을 신청합니다.

**4단계: 외국인 투자 등록/승인 신청**
- 등록제: 네거티브 리스트 외 업종, 상무부 시스템을 통해 온라인 등록
- 승인제: 제한 업종은 상무부와 발개위에 승인 신청

**5단계: 공상 등록**
등록/승인 서류를 받아 영업 허가증 신청.

**6단계: 후속 등록**
인감 제작 → 은행 계좌 개설 → 세무 등록 → 외환 등록 → 세관 등록

**7단계: 업종 허가**
일부 업종은 식품, ICP, 부가 통신 등 특정 자격 허가 필요.

⏱ 일반 소요 시간: WFOE 등록제 약 20-30영업일, 승인제 약 60-90영업일."""
    },
    {
        "keywords": ["负面清单", "外资准入负面清单", "限制", "受限", "禁止", "行业", "negative list", "restricted", "prohibited"],
        "answer_zh": """**《外商投资准入特别管理措施（负面清单）》** 是中国对外商投资实施管理的核心文件，列明了外资不得进入（禁止）或受限制（限制）的领域。

**2024年版负面清单（缩减至29条）主要限制行业包括：**

🚫 **禁止类（外资不得进入）：**
- 新闻、出版、广播、影视制作
- 互联网新闻信息服务、网络视听节目服务
- 人体干细胞、基因诊断与治疗技术开发和应用
- 烟草制品生产
- 义务教育机构
- 中国法律事务（不得担任中国法律事务代理人）

⚠️ **限制类（外资有条件进入）：**
- 增值电信业务（外资股比不超过50%）
- 基础电信业务（外资股比不超过49%）
- 医疗机构（限于合资）
- 证券公司（外资股比不超过51%）
- 寿险公司（外资股比不超过51%）
- 演出经纪机构（限于合资，中方控股）
- 民用机场建设运营（限于合资，中方相对控股）

💡 **提示：** 负面清单大幅缩减中，2024年版已比2017年版减少近60%。建议定期关注发改委和商务部发布的最新版本。""",
        "answer_ko": """**'외국인 투자 진입 특별 관리 조치(네거티브 리스트)'** 는 중국이 외국인 투자를 관리하는 핵심 문서로, 외국인 투자가 불가능(금지)하거나 제한되는 분야를 명시합니다.

**2024년판 네거티브 리스트(29개 항목으로 축소) 주요 제한 업종:**

🚫 **금지 업종:**
- 뉴스, 출판, 방송, 영화 제작
- 인터넷 뉴스 정보 서비스, 네트워크 시청각 프로그램 서비스
- 인간 줄기세포, 유전자 진단 치료 기술 개발 및 응용
- 담배 제품 생산
- 의무 교육 기관
- 중국 법률 업무

⚠️ **제한 업종:**
- 부가 통신 서비스(외국인 지분 50% 이하)
- 기초 통신 서비스(외국인 지분 49% 이하)
- 의료 기관(합자에 한함)
- 증권 회사(외국인 지분 51% 이하)
- 생명 보험 회사(외국인 지분 51% 이하)
- 공연 중개 기관(합자, 중국 측 지배)

💡 네거티브 리스트는 지속적으로 축소 중이며, 2024년판은 2017년 대비 약 60% 감소했습니다."""
    },
    {
        "keywords": ["WFOE", "JV", "合资", "独资", "外商独资", "架构", "适合", "类型", "joint venture", "wholly foreign owned"],
        "answer_zh": """**WFOE（外商独资企业）vs JV（合资企业）的选择指南：**

---

### ✅ WFOE（Wholly Foreign-Owned Enterprise）适合：
**独资经营，外资100%控股**
- 需要完全控制经营决策的韩企
- 拥有核心技术/知识产权，不希望外泄
- 行业不在负面清单限制类内（或限制条件可满足）
- 已有成熟商业模式，不需要中方合作伙伴的本地资源
- 常见：制造业、信息技术、研发、贸易、咨询、餐饮

**优点：** 决策权独立、利润独享、管理高效
**缺点：** 缺乏中方本地资源，对华市场理解可能不足

---

### ✅ JV（Joint Venture）合资企业适合：
**与中方合作伙伴共同投资经营**
- 行业在负面清单限制类内（如增值电信、医疗、证券等）
- 需要中方合作伙伴的政府关系、渠道资源、品牌背书
- 对华市场不熟悉，需要本地化运营支持
- 拟进入受严格监管的行业

**优点：** 获得中方资源和牌照资质、市场进入更快
**缺点：** 利润分享、决策需要协商、存在控制权风险

---

### 💡 决策建议：
1. 负面清单外行业 → 首选 **WFOE**（更灵活高效）
2. 限制类行业 → 必须选择 **JV**（满足股比要求）
3. 不确定市场 → 可先设代表处调研，再升级为WFOE/JV""",
        "answer_ko": """**WFOE(외국인 독자 기업) vs JV(합자 기업) 선택 가이드:**

---

### ✅ WFOE 적합 유형:
**독자 경영, 외국인 100% 지분**
- 경영 결정권 완전 통제 필요
- 핵심 기술/지식재산 보호
- 네거티브 리스트 제한 업종 아님
- 중국 파트너 로컬 자원 불필요
- 일반: 제조, IT, R&D, 무역, 컨설팅, 외식

**장점:** 독립적 의사결정, 이익 독점, 효율적 관리
**단점:** 중국 현지 자원 부족

---

### ✅ JV 적합 유형:
**중국 파트너와 공동 투자**
- 네거티브 리스트 제한 업종
- 중국 파트너의 관계, 채널, 브랜드 필요
- 중국 시장 미숙, 로컬 지원 필요
- 엄격한 규제 업종

**장점:** 현지 자원 및 면허 획득, 시장 진입 용이
**단점:** 이익 공유, 의사결정 협의 필요"""
    },
    {
        "keywords": ["外商投资法", "外商投资", "foreign investment law", "foreign investment"],
        "answer_zh": """**《中华人民共和国外商投资法》** 自2020年1月1日起施行，是中国外商投资领域的基础性法律，取代原有的"外资三法"（中外合资经营企业法、中外合作经营企业法、外资企业法）。

### 核心要点：

**1️⃣ 准入前国民待遇+负面清单制度**
外国投资者在市场准入阶段即享受不低于本国投资者的待遇（负面清单除外），是外资管理模式的根本性变革。

**2️⃣ 备案制替代审批制**
负面清单外的外商投资由"审批制"改为"备案制"，大幅简化流程。

**3️⃣ 保护外国投资者权益**
- 不强制要求技术转让
- 知识产权严格保护
- 不得行政强制征收
- 自由汇兑（经常项目）

**4️⃣ 外商投资信息报告**
实行外商投资信息报告制度，取代原有的联合年报制度。

**5️⃣ 法律适用过渡**
外商投资法实施前设立的外商投资企业，给予5年过渡期（至2024年12月31日），可继续保留原组织形式。""",
        "answer_ko": """**'중화인민공화국 외국인 투자법'** 은 2020년 1월 1일부터 시행되었으며, 중국 외국인 투자 분야의 기본법으로 기존 '외자 3법'을 대체합니다.

### 핵심 사항:

**1️⃣ 진입 전 내국민 대우 + 네거티브 리스트 제도**
외국인 투자자는 시장 진입 단계에서부터 내국인 투자자와 동등한 대우를 받습니다.

**2️⃣ 등록제가 승인제 대체**
네거티브 리스트 외 투자는 '승인제'에서 '등록제'로 전환되어 절차 대폭 간소화.

**3️⃣ 외국인 투자자 권익 보호**
- 기술 이전 강제 금지
- 지식재산권 엄격 보호
- 행정적 강제 수용 금지
- 자유로운 자금 송금"""
    },
    {
        "keywords": ["备案制", "审批制", "备案", "核准", "备案 vs 审批", "registration", "approval", "record"],
        "answer_zh": """**备案制 vs 审批制：外商投资管理两大模式对比**

---

### 📋 备案制（负面清单外行业）
| 项目 | 内容 |
|------|------|
| **适用范围** | 负面清单以外的行业 |
| **办理部门** | 商务部（在线系统） |
| **流程** | 在线填报→系统受理→完成备案 |
| **时限** | 一般3-5个工作日 |
| **难度** | ★☆☆☆☆ 简单 |
| **主要材料** | 备案申请表、营业执照、投资方证明 |

### 🔍 审批制（负面清单内限制类行业）
| 项目 | 内容 |
|------|------|
| **适用范围** | 负面清单内的限制类行业 |
| **办理部门** | 商务部 + 发改委（联审） |
| **流程** | 提交申请→初审→专家评审→核准 |
| **时限** | 一般30-60个工作日 |
| **难度** | ★★★★★ 复杂 |
| **主要材料** | 项目申请报告、可行性研究报告、合资协议等 |

---

### 💡 关键区别：
1. **备案制**是事后监管，企业承诺合规即可；**审批制**是事前审查，需政府核准
2. 备案制企业取得《备案回执》，审批制企业取得《核准文件》
3. 备案制转审批制不可逆——如果行业被列入负面清单，必须走审批制

**建议：** 绝大多数韩企进入中国的行业都在负面清单外，走备案制即可。建议在启动前由专业合规顾问评估行业归属。""",
        "answer_ko": """**등록제 vs 승인제: 외국인 투자 관리 두 가지 방식 비교**

---

### 📋 등록제 (네거티브 리스트 외 업종)
| 항목 | 내용 |
|------|------|
| 적용 범위 | 네거티브 리스트 외 업종 |
| 처리 기관 | 상무부(온라인 시스템) |
| 절차 | 온라인 제출 → 접수 → 완료 |
| 기간 | 일반 3-5영업일 |
| 난이도 | ★☆☆☆☆ 간단 |

### 🔍 승인제 (네거티브 리스트 내 제한 업종)
| 항목 | 내용 |
|------|------|
| 적용 범위 | 네거티브 리스트 제한 업종 |
| 처리 기관 | 상무부 + 발개위(공동 심사) |
| 절차 | 신청 → 예비 심사 → 전문가 평가 → 승인 |
| 기간 | 일반 30-60영업일 |
| 난이도 | ★★★★★ 복잡 |

---

### 💡 핵심 차이:
1. 등록제는 사후 감독, 승인제는 사전 심사
2. 등록제 기업은 '등록 확인증', 승인제 기업은 '승인 문서' 취득"""
    }
]


class ComplianceAskRequest(BaseModel):
    question: str = Field(..., description="用户咨询的问题")
    employee: str = Field(default="徐准", description="数字员工姓名")


class ComplianceAskResponse(BaseModel):
    success: bool = True
    answer: str = ""
    employee: str = ""


def find_answer(question: str) -> str:
    """基于关键词匹配查找预设回答"""
    q = question.lower()

    # 计算每个知识条目的匹配分数
    best_match = None
    best_score = 0

    for entry in COMPLIANCE_KNOWLEDGE_BASE:
        score = 0
        for kw in entry["keywords"]:
            if kw.lower() in q:
                score += 1
        if score > best_score:
            best_score = score
            best_match = entry

    if best_match and best_score > 0:
        # 判断语言：如果问题含韩文则返回韩文回答
        import re
        has_korean = bool(re.search(r'[\uac00-\ud7af]', question))
        return best_match["answer_ko"] if has_korean else best_match["answer_zh"]

    # 默认兜底回答
    return _get_default_answer(question)


def _get_default_answer(question: str) -> str:
    """当问题无法匹配知识库时的默认回答"""
    import re
    has_korean = bool(re.search(r'[\uac00-\ud7af]', question))

    if has_korean:
        return """죄송합니다. 해당 질문에 대한 답변이 현재 지식 베이스에 없습니다.

다음 주제에 대해 문의해 주시면 상세히 안내해 드릴 수 있습니다:
• 한국 기업의 중국 시장 진입 승인 절차
• 외국인 투자 네거티브 리스트
• WFOE/JV 선택 가이드
• 외국인 투자법 개요
• 등록제와 승인제 비교

또는 아래 빠른 질문 버튼을 이용해 주세요.

※ 서준 · 수석 규정준수 책임자 · AI 디지털 직원"""
    else:
        return """抱歉，您的问题目前不在我的知识库范围内。

建议您咨询以下主题，我可以为您提供专业解答：
• 韩企进入中国的审批流程
• 外资准入负面清单解读
• WFOE和JV架构选择
• 外商投资法核心要点
• 备案制与审批制对比

或者点击下方的快捷问题按钮。

※ 徐准 · 首席合规官 · AI数字员工"""


@router.post("/ask", response_model=ComplianceAskResponse)
async def compliance_ask(request: ComplianceAskRequest):
    """AI合规咨询问答接口——数字员工徐准的咨询问答"""
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    answer = find_answer(question)

    return ComplianceAskResponse(
        success=True,
        answer=answer,
        employee=request.employee
    )


@router.get("/questions")
async def get_questions(language: str = "zh-CN"):
    """获取自检问卷题目"""
    return {
        "success": True,
        "data": QUESTIONS,
        "total": len(QUESTIONS)
    }


@router.post("/check")
async def compliance_check(request: ComplianceCheckRequest):
    """提交自检答案，生成评分和报告"""
    answers = request.answers
    language = request.language

    # 验证答案
    for q in QUESTIONS:
        if q["id"] not in answers:
            raise HTTPException(status_code=400, detail=f"缺少问题 {q['id']} 的答案")

    # 计算评分
    score, score_detail = calculate_score(answers)

    # 生成唯一 token
    token = uuid.uuid4().hex

    # 设置优先级
    priority = "high" if score < 50 else ("normal" if score < 80 else "low")

    # 存入数据库
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO compliance_checks
            (token, answers, company_name, contact_name, email, phone, language, score, score_detail, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')
        """, (
            token,
            json.dumps(answers, ensure_ascii=False),
            request.company_name,
            request.contact_name,
            request.email,
            request.phone,
            language,
            score,
            json.dumps(score_detail, ensure_ascii=False)
        ))

        check_id = cursor.lastrowid

        # 如果有邮箱，创建线索
        if request.email:
            cursor.execute("""
                INSERT INTO compliance_leads
                (check_id, token, email, company_name, contact_name, phone, language, score, score_detail, priority, status, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', '合规自检')
            """, (
                check_id,
                token,
                request.email,
                request.company_name,
                request.contact_name,
                request.phone,
                language,
                score,
                json.dumps(score_detail, ensure_ascii=False),
                priority
            ))

        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")

    conn.close()

    # 生成报告HTML
    report_html = _generate_report_html(score, score_detail, request.company_name or "", language, token)

    return ComplianceCheckResponse(
        success=True,
        token=token,
        score=score,
        score_detail=score_detail,
        report_html=report_html,
        message="自检完成"
    )


@router.get("/report/{token}")
async def get_report(token: str):
    """获取已生成的报告数据"""
    conn = get_db()
    cursor = conn.execute(
        "SELECT * FROM compliance_checks WHERE token = ?",
        (token,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="报告不存在")

    score_detail = json.loads(row["score_detail"])
    report_html = _generate_report_html(
        row["score"],
        score_detail,
        row["company_name"] or "",
        row["language"],
        token
    )

    return {
        "success": True,
        "token": token,
        "score": row["score"],
        "score_detail": score_detail,
        "company_name": row["company_name"],
        "contact_name": row["contact_name"],
        "email": row["email"],
        "language": row["language"],
        "report_html": report_html,
        "created_at": row["created_at"]
    }


@router.get("/report/{token}/pdf")
async def download_report_pdf(token: str):
    """下载报告PDF（HTML直接下载，浏览器打印即可保存为PDF）"""
    conn = get_db()
    cursor = conn.execute(
        "SELECT * FROM compliance_checks WHERE token = ?",
        (token,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="报告不存在")

    # 标记已下载
    conn = get_db()
    conn.execute(
        "UPDATE compliance_checks SET report_downloaded = report_downloaded + 1 WHERE token = ?",
        (token,)
    )
    conn.commit()
    conn.close()

    score_detail = json.loads(row["score_detail"])
    report_html = _generate_report_html(
        row["score"],
        score_detail,
        row["company_name"] or "",
        row["language"],
        token
    )

    from fastapi.responses import HTMLResponse
    return HTMLResponse(
        content=report_html,
        status_code=200,
        headers={
            "Content-Type": "text/html; charset=utf-8",
            "Content-Disposition": f'inline; filename="compliance-report-{token[:8]}.html"'
        }
    )
