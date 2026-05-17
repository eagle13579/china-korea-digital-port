"""
合规自检工具 — PDF报告模板（P0任务1版）

技术说明:
  - 使用 reportlab 生成PDF
  - 中韩双语内容由 report_data 的 language 字段控制
  - 雷达图使用 reportlab 手动绘制
  - PDF直接响应下载请求，无需中间文件
"""
from io import BytesIO
from datetime import datetime
import math

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white, gray
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Polygon, Circle, Line, String, Group
from reportlab.graphics import renderPDF

# ── 颜色方案 ──────────────────────────────────────────
BRAND_BLUE = HexColor("#1a56db")
BRAND_DARK = HexColor("#111827")
BRAND_GRAY = HexColor("#6b7280")
LIGHT_BLUE = HexColor("#e0e7ff")
LIGHT_GRAY = HexColor("#f3f4f6")

# 风险等级色
COLOR_LOW = HexColor("#059669")    # 低风险 - 绿色
COLOR_MED = HexColor("#d97706")    # 中风险 - 橙色
COLOR_HIGH = HexColor("#dc2626")   # 高风险 - 红色

RISK_COLORS = {
    "低风险": COLOR_LOW,
    "중위험": COLOR_MED,
    "고위험": COLOR_HIGH,
}

# 维度状态色
STATUS_OK = HexColor("#059669")
STATUS_WARN = HexColor("#d97706")
STATUS_DANGER = HexColor("#dc2626")


# ── 样式定义 ──────────────────────────────────────────

styles = getSampleStyleSheet()

def _make_styles(language="zh"):
    """生成PDF样式"""
    font_name = "Helvetica"
    return {
        "title": ParagraphStyle("ReportTitle", fontName=font_name, fontSize=24, leading=32,
                                alignment=TA_CENTER, textColor=BRAND_DARK, spaceAfter=6*mm),
        "subtitle": ParagraphStyle("ReportSubtitle", fontName=font_name, fontSize=14, leading=20,
                                   alignment=TA_CENTER, textColor=BRAND_GRAY, spaceAfter=15*mm),
        "section_title": ParagraphStyle("SectionTitle", fontName=font_name, fontSize=16, leading=22,
                                        textColor=BRAND_BLUE, spaceBefore=10*mm, spaceAfter=5*mm),
        "body": ParagraphStyle("Body", fontName=font_name, fontSize=10, leading=16,
                               textColor=BRAND_DARK, spaceAfter=3*mm),
        "small": ParagraphStyle("Small", fontName=font_name, fontSize=8, leading=12, textColor=BRAND_GRAY),
        "score_num": ParagraphStyle("ScoreNum", fontName=font_name, fontSize=48, leading=56,
                                    alignment=TA_CENTER, textColor=BRAND_BLUE),
        "score_label": ParagraphStyle("ScoreLabel", fontName=font_name, fontSize=12, leading=16,
                                      alignment=TA_CENTER, textColor=BRAND_GRAY),
        "priority_title": ParagraphStyle("PriorityTitle", fontName=font_name, fontSize=11, leading=15,
                                         textColor=BRAND_DARK, spaceBefore=4*mm, spaceAfter=2*mm),
        "priority_body": ParagraphStyle("PriorityBody", fontName=font_name, fontSize=9, leading=14,
                                        textColor=BRAND_GRAY, leftIndent=10*mm, spaceAfter=4*mm),
        "disclaimer": ParagraphStyle("Disclaimer", fontName=font_name, fontSize=7, leading=10,
                                     textColor=BRAND_GRAY, alignment=TA_CENTER, spaceBefore=10*mm),
    }


# ── PDF生成主函数 ──────────────────────────────────────

def generate_report_pdf(report_data: dict) -> bytes:
    """生成合规报告PDF

    Args:
        report_data: generate_report_data() 返回的数据字典

    Returns:
        PDF字节流，可直接作为HTTP响应返回
    """
    buf = BytesIO()
    lang = report_data.get("language", "zh")
    s = _make_styles(lang)

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=20*mm,
        bottomMargin=20*mm,
        leftMargin=20*mm,
        rightMargin=20*mm,
        title=report_data.get("report_title_zh", "合规健康度评估报告"),
    )

    story = []

    # ================================================================
    # 第1页: 封面 / 报告头部 + 总分 + 评级
    # ================================================================

    # 平台名称
    platform_name = report_data.get("platform_name", "中韩出海数智港")
    report_title = report_data.get(f"report_title_{lang}", "合规健康度评估报告")
    story.append(Paragraph(platform_name, s["title"]))
    story.append(Paragraph(report_title, s["subtitle"]))

    # 报告信息表
    info_data = [
        [_label("企业名称", "회사명", lang),
         report_data.get("company_name", "-")],
        [_label("报告编号", "보고서 번호", lang),
         f"CHC-{report_data.get('report_token', 'N/A')}"],
        [_label("生成日期", "생성일자", lang),
         report_data.get("generated_at", datetime.now().strftime("%Y-%m-%d"))],
    ]
    info_table = Table(info_data, colWidths=[40*mm, 120*mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_GRAY),
        ("TEXTCOLOR", (1, 0), (1, -1), BRAND_DARK),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4*mm),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 10*mm))

    # ── 总分大数字 ──
    total_score = report_data["total_score"]
    risk_level = report_data.get("risk_level", "")
    risk_label = report_data.get("risk_label", "")

    # 根据风险等级选择颜色
    risk_color = COLOR_LOW
    if total_score < 60:
        risk_color = COLOR_HIGH
    elif total_score < 80:
        risk_color = COLOR_MED

    score_table = Table(
        [[Paragraph(f"{total_score}", ParagraphStyle("ScoreNum2", fontName=s["score_num"].fontName,
                     fontSize=48, leading=56, alignment=TA_CENTER, textColor=risk_color))],
         [Paragraph(_t("综合评分 / 종합 점수", lang), s["score_label"])],
         [Paragraph(f"[{risk_level}] {risk_label}", s["score_label"])]],
        colWidths=[100*mm],
    )
    score_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 1, LIGHT_GRAY),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 8*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8*mm),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 5*mm))

    # 评级摘要
    summary_text = report_data.get("summary", "")
    story.append(Paragraph(summary_text, s["body"]))
    story.append(Spacer(1, 5*mm))

    # 分隔线
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_GRAY))
    story.append(Spacer(1, 5*mm))

    # ================================================================
    # 第2部分: 各维度评分详情 + 雷达图
    # ================================================================

    section_title = _t("各维度评分详情", lang, ko="분야별 점수 상세")
    story.append(Paragraph(section_title, s["section_title"]))

    # 维度评分表
    dim_header = _t(["维度", "得分/100", "状态"], lang, ko=["분야", "점수/100", "상태"])

    table_data = [[Paragraph(h, s["small"]) for h in dim_header]]

    for dim in report_data["dimensions"]:
        dim_name = dim["dimension_label"]
        dim_score = dim["dim_score"]
        status = f"{dim['status_icon']} {dim['status_label']}"

        score_color = STATUS_OK
        if dim_score < 50:
            score_color = STATUS_DANGER
        elif dim_score < 70:
            score_color = STATUS_WARN

        row = [
            Paragraph(dim_name, s["body"]),
            Paragraph(f'<font color="{score_color.hexval()}">{dim_score}</font>', s["body"]),
            Paragraph(status, s["body"]),
        ]
        table_data.append(row)

    dim_table = Table(table_data, colWidths=[55*mm, 30*mm, 55*mm])
    dim_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY),
        ("GRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 3*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3*mm),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(dim_table)

    # ── 雷达图 ──
    story.append(Spacer(1, 8*mm))
    radar_title = _t("合规维度雷达图", lang, ko="규제 준수 분야 레이더 차트")
    story.append(Paragraph(radar_title, s["section_title"]))

    # 用reportlab RadarChart绘制雷达图
    dim_labels = [d["dimension_label"] for d in report_data["dimensions"]]
    dim_scores = [d["dim_score"] for d in report_data["dimensions"]]

    radar_drawing = _draw_radar_chart(dim_labels, dim_scores, lang)
    story.append(radar_drawing)

    # ── 分页 ──
    story.append(PageBreak())

    # ================================================================
    # 第3部分: 优先行动建议清单
    # ================================================================

    priority_title = _t("优先改进建议", lang, ko="우선 개선 제안")
    story.append(Paragraph(priority_title, s["section_title"]))

    if report_data["priorities"]:
        for i, p in enumerate(report_data["priorities"], 1):
            p_title = f"{i}. {p['dimension_label']} ({p['dim_score']}分)"
            story.append(Paragraph(p_title, s["priority_title"]))
            advice = p["action_advice"]
            story.append(Paragraph(advice, s["priority_body"]))

        story.append(Spacer(1, 8*mm))
    else:
        no_priority = _t("恭喜！您的企业各维度合规状况良好，暂无需要优先改进的事项。",
                         lang,
                         ko="축하합니다! 귀사의 모든 규제 준수 분야가 양호하며, 우선 개선 사항이 없습니다.")
        story.append(Paragraph(no_priority, s["body"]))

    # ── 分隔线 ──
    story.append(Spacer(1, 10*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_GRAY))

    # ── 免责声明 ──
    disclaimer_title = _t("免责声明", lang, ko="면책 조항")
    story.append(Paragraph(disclaimer_title, s["small"]))
    story.append(Paragraph(report_data.get("disclaimer", ""), s["disclaimer"]))

    # 构建PDF
    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes


# ── 雷达图绘制 ──────────────────────────────────────

def _draw_radar_chart(labels, scores, language="zh"):
    """绘制合规维度雷达图

    Args:
        labels: 维度标签列表
        scores: 维度得分列表 (0-100)
        language: "zh" 或 "ko"

    Returns:
        Drawing对象（reportlab platypus Flowable）
    """
    n = len(labels)
    if n == 0:
        return Spacer(1, 50)

    # 尺寸
    w, h = 480, 420
    cx, cy = w / 2, h / 2 - 10  # 中心
    r = 170  # 半径

    drawing = Drawing(w, h)

    # 画同心圆网格 (从中心到外圈 5层)
    for i in range(1, 6):
        radius = r * i / 5
        # 我们只画多边形轮廓（八边形），不画圆
        points = []
        for j in range(n):
            angle = math.radians(90 - j * 360 / n)
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            points.append((x, y))
        # 画多边形
        polygon_points = []
        for px, py in points:
            polygon_points.extend([px, py])
        poly = Polygon(polygon_points, strokeColor=HexColor("#d1d5db"),
                       strokeWidth=0.5, fillColor=None)
        drawing.add(poly)

    # 画维度轴线和对角线
    for j in range(n):
        angle = math.radians(90 - j * 360 / n)
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        line = Line(cx, cy, x, y, strokeColor=HexColor("#d1d5db"), strokeWidth=0.5)
        drawing.add(line)

    # 画数据多边形
    data_points = []
    for j in range(n):
        score = scores[j] / 100.0 if j < len(scores) else 0
        score = max(0.05, min(1.0, score))  # 至少5%
        angle = math.radians(90 - j * 360 / n)
        px = cx + r * score * math.cos(angle)
        py = cy + r * score * math.sin(angle)
        data_points.append((px, py))

    data_poly_points = []
    for px, py in data_points:
        data_poly_points.extend([px, py])
    data_poly = Polygon(data_poly_points, strokeColor=BRAND_BLUE,
                        strokeWidth=2, fillColor=HexColor("#1a56db40"),
                        fillOpacity=0.25)
    drawing.add(data_poly)

    # 数据点标记
    for px, py in data_points:
        circle = Circle(px, py, 4, fillColor=BRAND_BLUE, strokeColor=white, strokeWidth=1)
        drawing.add(circle)

    # 标签
    for j in range(n):
        label = labels[j] if j < len(labels) else f"Dim{j+1}"
        # 截断长标签
        if len(label) > 8:
            label = label[:7] + "."
        angle = math.radians(90 - j * 360 / n)
        lx = cx + (r + 30) * math.cos(angle)
        ly = cy + (r + 30) * math.sin(angle)

        # 根据方向调整对齐
        text_anchor = "middle"
        if abs(math.cos(angle)) < 0.1:
            text_anchor = "middle"
        elif math.cos(angle) > 0:
            text_anchor = "start"
        else:
            text_anchor = "end"

        txt = String(lx, ly, label, textAnchor=text_anchor,
                     fontSize=9, fontName="Helvetica", fillColor=BRAND_DARK)
        drawing.add(txt)

    # 中心分数
    center_txt = String(cx, cy, str(int(sum(scores) / len(scores))) if scores else "0",
                        textAnchor="middle", fontSize=18, fontName="Helvetica-Bold",
                        fillColor=BRAND_BLUE)
    drawing.add(center_txt)
    avg_label = _t("均分", language, ko="평균")
    avg_txt = String(cx, cy - 16, avg_label,
                     textAnchor="middle", fontSize=9, fontName="Helvetica",
                     fillColor=BRAND_GRAY)
    drawing.add(avg_txt)

    return drawing


# ── 辅助函数 ──────────────────────────────────────────

def _label(zh: str, ko: str, lang: str) -> str:
    """双语标签"""
    return f"{zh} / {ko}" if lang == "zh" else f"{ko} / {zh}"


def _t(zh, lang, ko=None):
    """简单双语文本选择"""
    if ko is None:
        return zh
    return ko if lang == "ko" else zh


# ── 快速测试 ──────────────────────────────────────────

if __name__ == "__main__":
    from backend.compliance.report_score import generate_report_data

    test_answers = {
        1: 0, 2: 2, 3: 0,
        4: 1, 5: 1, 6: 0,
        7: 2, 8: 1,
    }
    company_info = {
        "company_name": "㈜한국테크",
        "contact_name": "김민수",
        "email": "kms@koreatech.co.kr",
        "report_token": "CHC-20260514-A3B4",
        "generated_at": "2026-05-14",
    }

    # 中文报告
    report_data = generate_report_data(test_answers, company_info, language="zh")
    pdf_bytes = generate_report_pdf(report_data)
    print(f"中文PDF生成成功: {len(pdf_bytes)} bytes")

    # 韩文报告
    report_data_ko = generate_report_data(test_answers, company_info, language="ko")
    pdf_bytes_ko = generate_report_pdf(report_data_ko)
    print(f"韩文PDF生成成功: {len(pdf_bytes_ko)} bytes")