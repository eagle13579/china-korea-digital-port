# -*- coding: utf-8 -*-
"""
中韩出海数智港 — 合规知识图谱引擎 + 维度-法规映射矩阵

功能:
1. 知识图谱数据结构 (SQLite, knowledge_graph表)
2. 初始数据: K-DPA 15条 / GDPR 15条 / PIPL 15条 = 45条法规条款（中韩双语）
3. 核心功能函数: 按维度查、跨法规对比、自检建议、关键词搜索、义务清单
4. CLI命令: --init / --dimension / --compare
5. FastAPI API端点 (注册到 main.py)

纯标准库, 中韩双语, 中文回复
"""

import sqlite3
import json
import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# ─────────────────────────────────────────────
# 路径 & 数据库
# ─────────────────────────────────────────────

DATA_DIR = Path(os.environ.get("DB_DIR", Path(__file__).parent / "data"))
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "compliance_knowledge.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ─────────────────────────────────────────────
# 合规维度定义 (20个维度)
# ─────────────────────────────────────────────

DIMENSIONS = [
    {"id": "industry_access", "name_zh": "行业准入", "name_ko": "업종 진입",
     "description_zh": "中国市场行业准入、外商投资限制与资质许可",
     "description_ko": "중국 시장 업종 진입, 외국인 투자 제한 및 자격 허가",
     "risk_level": "high"},
    {"id": "data_security", "name_zh": "数据安全", "name_ko": "데이터 보안",
     "description_zh": "个人信息保护、数据跨境传输与数据安全治理",
     "description_ko": "개인정보 보호, 데이터 역외 이전 및 데이터 보안 거버넌스",
     "risk_level": "critical"},
    {"id": "intellectual_property", "name_zh": "知识产权", "name_ko": "지식재산권",
     "description_zh": "商标、专利、著作权注册与知识产权保护",
     "description_ko": "상표, 특허, 저작권 등록 및 지식재산권 보호",
     "risk_level": "high"},
    {"id": "cross_border_tax", "name_zh": "跨境财税", "name_ko": "국경 간 세무 재무",
     "description_zh": "企业所得税、增值税、关税、转让定价及双边税收协定",
     "description_ko": "법인세, 부가가치세, 관세, 이전 가격 및 양자 조세 협약",
     "risk_level": "high"},
    {"id": "labor_employment", "name_zh": "劳动用工", "name_ko": "노동 고용",
     "description_zh": "劳动合同、社会保险、外籍员工就业与劳动争议",
     "description_ko": "노동 계약, 사회보험, 외국인 근로자 취업 및 노동 분쟁",
     "risk_level": "medium"},
    {"id": "visa_immigration", "name_zh": "签证移民", "name_ko": "비자 이민",
     "description_zh": "工作签证(Z签)、居留许可与外籍人员出入境管理",
     "description_ko": "취업 비자(Z비자), 체류 허가 및 외국인 출입국 관리",
     "risk_level": "medium"},
    {"id": "company_formation", "name_zh": "公司设立", "name_ko": "회사 설립",
     "description_zh": "外商独资企业(WFOE)、合资企业(JV)、代表处设立",
     "description_ko": "외국인 독자 기업(WFOE), 합작 투자(JV), 대표처 설립",
     "risk_level": "medium"},
    {"id": "import_export", "name_zh": "进出口", "name_ko": "수출입",
     "description_zh": "海关申报、HS编码、原产地证、进出口许可证与FTA",
     "description_ko": "세관 신고, HS 코드, 원산지 증명, 수출입 허가증 및 FTA",
     "risk_level": "medium"},
    {"id": "environmental", "name_zh": "环境影响评价", "name_ko": "환경영향평가",
     "description_zh": "建设项目环评审批、环保验收与排污许可",
     "description_ko": "건설 프로젝트 환경평가 승인, 환경 보호 검수 및 배출 허가",
     "risk_level": "medium"},
    {"id": "anti_bribery", "name_zh": "反商业贿赂", "name_ko": "반뇌물",
     "description_zh": "反腐败合规、礼品招待规范与第三方尽职调查",
     "description_ko": "반부패 규제, 선물·접대 규범 및 제3자 실사",
     "risk_level": "high"},
    {"id": "foreign_exchange", "name_zh": "外汇管制", "name_ko": "외환 관리",
     "description_zh": "资本项目外汇登记、利润汇出与跨境资金流动合规",
     "description_ko": "자본 항목 외환 등록, 이익 송금 및 역외 자금 이체 규제",
     "risk_level": "high"},
    {"id": "tech_export_control", "name_zh": "技术进出口管制", "name_ko": "기술 수출입 통제",
     "description_zh": "技术进出口分类、登记与限制技术许可管理",
     "description_ko": "기술 수출입 분류, 등록 및 제한 기술 라이선스 관리",
     "risk_level": "high"},
    {"id": "product_quality", "name_zh": "产品质量标准", "name_ko": "제품 품질 기준",
     "description_zh": "CCC认证、GB国家标准与产品质量法合规",
     "description_ko": "CCC 인증, GB 국가 표준 및 제품 품질법 규제",
     "risk_level": "medium"},
    {"id": "advertising", "name_zh": "广告合规", "name_ko": "광고 규제",
     "description_zh": "广告法极限用语禁止、虚假宣传与行业广告审查",
     "description_ko": "광고법 절대적 표현 금지, 허위 광고 및 업종 광고 심사",
     "risk_level": "medium"},
    {"id": "ecommerce", "name_zh": "电子商务法规", "name_ko": "전자상거래 규제",
     "description_zh": "电商经营者登记、亮照亮证经营与消费者保护",
     "description_ko": "전자상거래 사업자 등록, 자격증 게시 및 소비자 보호",
     "risk_level": "medium"},
    {"id": "consumer_rights", "name_zh": "消费者权益保护", "name_ko": "소비자 권리 보호",
     "description_zh": "七日无理由退货、三包规定与惩罚性赔偿",
     "description_ko": "7일 무조건 반품, 3보 규정 및 징벌적 배상",
     "risk_level": "medium"},
    {"id": "labor_dispatch", "name_zh": "劳动派遣合规", "name_ko": "파견 근로 규제",
     "description_zh": "劳务派遣比例限制、三性岗位要求与同工同酬",
     "description_ko": "파견 근로 비율 제한, 3성 직무 요건 및 동일 노동 동일 임금",
     "risk_level": "medium"},
    {"id": "foreign_investment", "name_zh": "外商投资负面清单", "name_ko": "외국인 투자 네거티브 리스트",
     "description_zh": "外商投资准入特别管理措施(负面清单)与外资审查",
     "description_ko": "외국인 투자 진입 특별 관리 조치(네거티브 리스트) 및 외국인 투자 심사",
     "risk_level": "high"},
    {"id": "cybersecurity", "name_zh": "网络安全", "name_ko": "사이버 보안",
     "description_zh": "网络安全等级保护、关键信息基础设施与网络安全审查",
     "description_ko": "사이버 보안 등급 보호, 중요 정보 인프라 및 사이버 보안 심사",
     "risk_level": "critical"},
    {"id": "personal_info", "name_zh": "个人信息保护", "name_ko": "개인정보 보호",
     "description_zh": "个人信息处理规则、告知同意、敏感信息保护与跨境传输",
     "description_ko": "개인정보 처리 규칙, 고지 동의, 민감 정보 보호 및 역외 이전",
     "risk_level": "critical"},
]

DIMENSION_MAP = {d["id"]: d for d in DIMENSIONS}

# ─────────────────────────────────────────────
# 法规条款数据 (K-DPA 15条 + GDPR 15条 + PIPL 15条)
# ─────────────────────────────────────────────

ALL_ARTICLES = [
    # ===== K-DPA (韩国个人信息保护法) 15条 =====
    {
        "id": "kdpa-001", "regulation": "K-DPA", "article_number": "第3条", "article_number_ko": "제3조",
        "title": "个人信息保护原则", "title_ko": "개인정보 보호원칙",
        "summary": "个人信息处理者应在公开、公平、合法的原则下处理个人信息，确保目的明确、最小化收集、合理使用和安全管理。",
        "summary_ko": "개인정보처리자는 공개·공정·적법의 원칙에 따라 개인정보를 처리하며, 목적 명확화, 최소 수집, 합리적 사용 및 안전 관리를 보장하여야 한다.",
        "requirements": ["遵守合法公平透明原则", "目的明确且具体", "最小化收集", "安全管理义务", "公开透明义务"],
        "applicable_dimensions": ["data_security", "personal_info"],
        "risk_level": "critical", "source_url": "https://www.law.go.kr/법령/개인정보보호법",
        "effective_date": "2020-02-04"
    },
    {
        "id": "kdpa-002", "regulation": "K-DPA", "article_number": "第15条", "article_number_ko": "제15조",
        "title": "个人信息收集同意", "title_ko": "개인정보 수집 동의",
        "summary": "收集个人信息须取得信息主体的同意，同意须在充分告知收集目的、范围、保留期限后由信息主体自主作出。",
        "summary_ko": "개인정보를 수집하려면 정보주체의 동의를 받아야 하며, 충분한 고지 후 자발적 동의를 받아야 한다.",
        "requirements": ["取得明确同意", "区分必要同意与选择同意", "保存同意记录至少3年"],
        "applicable_dimensions": ["data_security", "personal_info"],
        "risk_level": "critical", "source_url": "https://www.law.go.kr/법령/개인정보보호법",
        "effective_date": "2020-02-04"
    },
    {
        "id": "kdpa-003", "regulation": "K-DPA", "article_number": "第16条", "article_number_ko": "제16조",
        "title": "最小收集原则", "title_ko": "최소 수집 원칙",
        "summary": "个人信息处理者应在实现收集目的所必需的最小范围内收集个人信息。",
        "summary_ko": "개인정보처리자는 수집 목적 달성에 필요한 최소한의 범위에서 개인정보를 수집하여야 한다.",
        "requirements": ["仅收集必要信息", "不得以未同意额外收集为由拒绝服务"],
        "applicable_dimensions": ["data_security", "personal_info"],
        "risk_level": "high", "source_url": "https://www.law.go.kr/법령/개인정보보호법",
        "effective_date": "2020-02-04"
    },
    {
        "id": "kdpa-004", "regulation": "K-DPA", "article_number": "第17条", "article_number_ko": "제17조",
        "title": "隐私政策公示义务", "title_ko": "개인정보 처리방침 공개 의무",
        "summary": "个人信息处理者须制定隐私政策并在网站首页等处公示，内容应包括处理目的、保留期限、信息主体权利等。",
        "summary_ko": "개인정보처리자는 개인정보 처리방침을 수립하여 홈페이지 첫 화면 등에 공개하여야 한다.",
        "requirements": ["制定并公示隐私政策", "政策内容包含法定事项", "政策变更时及时通知"],
        "applicable_dimensions": ["data_security", "personal_info"],
        "risk_level": "high", "source_url": "https://www.law.go.kr/법령/개인정보보호법",
        "effective_date": "2020-02-04"
    },
    {
        "id": "kdpa-005", "regulation": "K-DPA", "article_number": "第18条", "article_number_ko": "제18조",
        "title": "个人信息使用限制", "title_ko": "개인정보 사용 제한",
        "summary": "个人信息不得超出收集目的范围使用，超出范围使用须另行获得同意。",
        "summary_ko": "개인정보는 수집 목적 범위를 초과하여 사용할 수 없으며, 초과 사용 시 별도 동의를 받아야 한다.",
        "requirements": ["目的外使用须另行同意", "不得用于非法目的"],
        "applicable_dimensions": ["data_security", "personal_info"],
        "risk_level": "high", "source_url": "https://www.law.go.kr/법령/개인정보보호법",
        "effective_date": "2020-02-04"
    },
    {
        "id": "kdpa-006", "regulation": "K-DPA", "article_number": "第19条", "article_number_ko": "제19조",
        "title": "个人信息提供委托", "title_ko": "개인정보 제공·위탁",
        "summary": "将个人信息提供给第三方或委托处理时须告知信息主体并取得同意，委托合同须包含安全管理条款。",
        "summary_ko": "개인정보를 제3자에게 제공하거나 처리 위탁 시 정보주체에게 고지하고 동의를 받아야 한다.",
        "requirements": ["告知第三方提供事实", "取得同意", "委托合同含安全条款"],
        "applicable_dimensions": ["data_security", "personal_info"],
        "risk_level": "high", "source_url": "https://www.law.go.kr/법령/개인정보보호법",
        "effective_date": "2020-02-04"
    },
    {
        "id": "kdpa-007", "regulation": "K-DPA", "article_number": "第22条", "article_number_ko": "제22조",
        "title": "儿童个人信息保护", "title_ko": "아동 개인정보 보호",
        "summary": "收集14岁以下儿童个人信息须取得其法定监护人同意，儿童信息保护标准更为严格。",
        "summary_ko": "14세 미만 아동의 개인정보를 수집하려면 법정 대리인의 동의를 받아야 한다.",
        "requirements": ["监护人同意", "儿童信息特殊保护措施"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "critical", "source_url": "https://www.law.go.kr/법령/개인정보보호법",
        "effective_date": "2020-02-04"
    },
    {
        "id": "kdpa-008", "regulation": "K-DPA", "article_number": "第28条", "article_number_ko": "제28조",
        "title": "敏感信息处理限制", "title_ko": "민감정보 처리 제한",
        "summary": "敏感信息（种族、政治观点、健康信息、基因数据等）原则上禁止处理，但有法律依据或单独同意时除外。",
        "summary_ko": "민감정보(인종, 정치관, 건강정보, 유전자 정보 등)는 원칙적으로 처리 금지되나 법적 근거 또는 별도 동의 시 예외.",
        "requirements": ["原则上禁止处理敏感信息", "法律依据或单独同意时例外"],
        "applicable_dimensions": ["data_security", "personal_info"],
        "risk_level": "critical", "source_url": "https://www.law.go.kr/법령/개인정보보호법",
        "effective_date": "2020-02-04"
    },
    {
        "id": "kdpa-009", "regulation": "K-DPA", "article_number": "第29条", "article_number_ko": "제29조",
        "title": "跨境数据传输", "title_ko": "역외 데이터 전송",
        "summary": "向境外传输个人信息须取得用户同意并采取安全保护措施，向PIPC申报。",
        "summary_ko": "개인정보를 국외로 이전하려면 사용자 동의와 안전 보호 조치를 취하고 PIPC에 신고하여야 한다.",
        "requirements": ["用户同意", "安全保护措施", "向PIPC申报"],
        "applicable_dimensions": ["data_security", "cross_border_tax", "personal_info"],
        "risk_level": "critical", "source_url": "https://www.law.go.kr/법령/개인정보보호법",
        "effective_date": "2020-02-04"
    },
    {
        "id": "kdpa-010", "regulation": "K-DPA", "article_number": "第30条", "article_number_ko": "제30조",
        "title": "个人信息影响评价", "title_ko": "개인정보 영향 평가",
        "summary": "处理大规模敏感信息或涉及重大隐私风险时须进行个人信息影响评价。",
        "summary_ko": "대규모 민감정보 처리 또는 중대한 프라이버시 위험이 있는 경우 개인정보 영향 평가를 수행하여야 한다.",
        "requirements": ["高风险时进行PIA", "评价结果提交PIPC"],
        "applicable_dimensions": ["data_security", "personal_info"],
        "risk_level": "high", "source_url": "https://www.law.go.kr/법령/개인정보보호법",
        "effective_date": "2020-02-04"
    },
    {
        "id": "kdpa-011", "regulation": "K-DPA", "article_number": "第31条", "article_number_ko": "제31조",
        "title": "安全管理义务", "title_ko": "안전 관리 의무",
        "summary": "个人信息处理者须采取安全管理措施，包括内部管理制度、访问控制、加密存储和日志审计等。",
        "summary_ko": "개인정보처리자는 내부 관리 계획, 접근 통제, 암호화, 로그 감사 등 안전 관리 조치를 취하여야 한다.",
        "requirements": ["内部管理制度", "访问控制措施", "加密存储", "日志审计"],
        "applicable_dimensions": ["data_security", "cybersecurity"],
        "risk_level": "critical", "source_url": "https://www.law.go.kr/법령/개인정보보호법",
        "effective_date": "2020-02-04"
    },
    {
        "id": "kdpa-012", "regulation": "K-DPA", "article_number": "第32条", "article_number_ko": "제32조",
        "title": "个人信息保护负责人", "title_ko": "개인정보 보호 책임자",
        "summary": "个人信息处理者须指定个人信息保护负责人，负责内部合规监督和对外联络。",
        "summary_ko": "개인정보처리자는 개인정보 보호 책임자를 지정하여 내부 규제 감독 및 대외 연락을 담당하게 하여야 한다.",
        "requirements": ["指定CPO", "CPO职责明确", "CPO资格要求"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "medium", "source_url": "https://www.law.go.kr/법령/개인정보보호법",
        "effective_date": "2020-02-04"
    },
    {
        "id": "kdpa-013", "regulation": "K-DPA", "article_number": "第34条", "article_number_ko": "제34조",
        "title": "数据泄露通知", "title_ko": "데이터 유출 통지",
        "summary": "个人信息泄露时须在24小时内向PIPC报告，并及时通知受影响信息主体。",
        "summary_ko": "개인정보 유출 시 24시간 내 PIPC에 보고하고 영향을 받은 정보주체에게 통지하여야 한다.",
        "requirements": ["24小时内报告PIPC", "通知受影响主体", "制定泄露应对计划"],
        "applicable_dimensions": ["data_security", "cybersecurity"],
        "risk_level": "critical", "source_url": "https://www.law.go.kr/법령/개인정보보호법",
        "effective_date": "2020-02-04"
    },
    {
        "id": "kdpa-014", "regulation": "K-DPA", "article_number": "第35-37条", "article_number_ko": "제35-37조",
        "title": "信息主体权利", "title_ko": "정보주체 권리",
        "summary": "信息主体享有查阅权、更正权、删除权和处理停止请求权，处理者须在10日内回应。",
        "summary_ko": "정보주체는 열람권, 정정권, 삭제권 및 처리 정지 청구권을 가지며, 처리자는 10일 내 응답하여야 한다.",
        "requirements": ["10日内响应查阅请求", "更正和删除请求处理", "处理停止请求权"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "high", "source_url": "https://www.law.go.kr/법령/개인정보보호법",
        "effective_date": "2020-02-04"
    },
    {
        "id": "kdpa-015", "regulation": "K-DPA", "article_number": "第39条", "article_number_ko": "제39조",
        "title": "损害赔偿责任", "title_ko": "손해배상 책임",
        "summary": "因违反本法导致信息主体损害的，个人信息处理者须承担损害赔偿责任，且举证责任倒置。",
        "summary_ko": "본법 위반으로 정보주체에게 손해가 발생한 경우 개인정보처리자는 손해배상 책임을 지며, 입증 책임이 전환된다.",
        "requirements": ["损害赔偿责任", "举证责任倒置", "惩罚性赔偿可能"],
        "applicable_dimensions": ["personal_info", "consumer_rights"],
        "risk_level": "high", "source_url": "https://www.law.go.kr/법령/개인정보보호법",
        "effective_date": "2020-02-04"
    },

    # ===== GDPR (欧盟通用数据保护条例) 15条 =====
    {
        "id": "gdpr-001", "regulation": "GDPR", "article_number": "第5条", "article_number_ko": "제5조",
        "title": "个人数据处理原则", "title_ko": "개인정보 처리 원칙",
        "summary": "个人数据应合法公平透明处理，目的限制，数据最小化，准确性，存储限制，完整性和保密性，问责制。",
        "summary_ko": "개인정보는 적법·공정·투명하게 처리되어야 하며, 목적 제한, 데이터 최소화, 정확성, 저장 제한, 무결성 및 기밀성, 책임 원칙을 따라야 한다.",
        "requirements": ["合法公平透明", "目的限制", "数据最小化", "准确性", "存储限制", "完整性和保密性", "问责制"],
        "applicable_dimensions": ["data_security", "personal_info"],
        "risk_level": "critical", "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "effective_date": "2018-05-25"
    },
    {
        "id": "gdpr-002", "regulation": "GDPR", "article_number": "第6条", "article_number_ko": "제6조",
        "title": "处理的合法性", "title_ko": "처리의 적법성",
        "summary": "处理个人数据须基于以下之一合法性基础：同意、合同履行、法律义务、重要利益、公共利益或正当利益。",
        "summary_ko": "개인정보 처리는 동의, 계약 이행, 법적 의무, 중대한 이익, 공익 또는 정당한 이익 중 하나의 적법 근거가 필요하다.",
        "requirements": ["选择适当的合法性基础", "记录处理活动", "定期审查合法性"],
        "applicable_dimensions": ["data_security", "personal_info"],
        "risk_level": "critical", "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "effective_date": "2018-05-25"
    },
    {
        "id": "gdpr-003", "regulation": "GDPR", "article_number": "第7条", "article_number_ko": "제7조",
        "title": "同意的条件", "title_ko": "동의의 조건",
        "summary": "同意须是自由给予、具体、知情、明确表示的。默示或不作为不构成同意。撤回同意须与给予同意同样容易。",
        "summary_ko": "동의는 자유롭게, 구체적으로, 정보에 기반하여, 명확하게 표시되어야 한다. 묵시적 동의는 유효하지 않으며, 철회는 동의만큼 쉬워야 한다.",
        "requirements": ["自由给予的同意", "具体和知情", "明确表示", "撤回权同样容易"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "critical", "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "effective_date": "2018-05-25"
    },
    {
        "id": "gdpr-004", "regulation": "GDPR", "article_number": "第9条", "article_number_ko": "제9조",
        "title": "特殊类别数据", "title_ko": "특별 범주 데이터",
        "summary": "处理种族、政治观点、宗教、工会会员、基因数据、生物识别数据、健康数据或性取向信息原则上禁止。",
        "summary_ko": "인종, 정치관, 종교, 노조 가입, 유전자 데이터, 생체 인식 데이터, 건강 데이터 또는 성적 지향 정보 처리는 원칙적으로 금지된다.",
        "requirements": ["原则上禁止处理特殊类别数据", "特定例外情形（明确同意等）"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "critical", "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "effective_date": "2018-05-25"
    },
    {
        "id": "gdpr-005", "regulation": "GDPR", "article_number": "第12条", "article_number_ko": "제12조",
        "title": "透明信息和通信", "title_ko": "투명한 정보 및 통신",
        "summary": "控制者应以简洁、透明、可理解和易于访问的形式向数据主体提供信息，通常采用书面形式。",
        "summary_ko": "컨트롤러는 간결하고, 투명하며, 이해하기 쉽고 접근 가능한 형태로 정보주체에게 정보를 제공하여야 한다.",
        "requirements": ["简洁透明的隐私通知", "易于访问的形式", "免费提供信息"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "high", "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "effective_date": "2018-05-25"
    },
    {
        "id": "gdpr-006", "regulation": "GDPR", "article_number": "第13-14条", "article_number_ko": "제13-14조",
        "title": "信息提供义务", "title_ko": "정보 제공 의무",
        "summary": "收集个人数据时须向数据主体提供控制者身份、数据保护官联系方式、处理目的和合法性基础、保留期限等信息。",
        "summary_ko": "개인정보 수집 시 정보주체에게 컨트롤러 신원, DPO 연락처, 처리 목적, 적법 근거, 보유 기간 등을 제공하여야 한다.",
        "requirements": ["提供控制者身份和联系方式", "告知处理目的和合法性基础", "告知保留期限"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "high", "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "effective_date": "2018-05-25"
    },
    {
        "id": "gdpr-007", "regulation": "GDPR", "article_number": "第15条", "article_number_ko": "제15조",
        "title": "数据主体的查阅权", "title_ko": "정보주체의 열람권",
        "summary": "数据主体有权要求控制者确认是否正在处理其个人数据，并有权查阅该数据和处理相关信息。",
        "summary_ko": "정보주체는 컨트롤러에게 자신의 개인정보가 처리되고 있는지 확인하고 열람을 요구할 권리가 있다.",
        "requirements": ["30天内响应查阅请求", "提供处理目的、类别、接收者等信息", "通常免费提供副本"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "high", "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "effective_date": "2018-05-25"
    },
    {
        "id": "gdpr-008", "regulation": "GDPR", "article_number": "第17条", "article_number_ko": "제17조",
        "title": "删除权（被遗忘权）", "title_ko": "삭제권(잊힐 권리)",
        "summary": "数据主体有权要求控制者立即删除其个人数据，条件包括：数据不再必要、撤回同意、非法处理或法律义务等。",
        "summary_ko": "정보주체는 데이터가 더 이상 필요하지 않은 경우, 동의 철회 시, 불법 처리 시 등에 컨트롤러에게 데이터 삭제를 요구할 권리가 있다.",
        "requirements": ["处理删除请求", "通知第三方删除链接/副本", "评估例外情况"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "high", "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "effective_date": "2018-05-25"
    },
    {
        "id": "gdpr-009", "regulation": "GDPR", "article_number": "第20条", "article_number_ko": "제20조",
        "title": "数据可携带权", "title_ko": "데이터 이동권",
        "summary": "数据主体有权以结构化、常用和机器可读的格式获取其个人数据，并有权直接传输给另一控制者。",
        "summary_ko": "정보주체는 구조화되고 일반적으로 사용되며 기계 판독 가능한 형식으로 개인정보를 수신하고 다른 컨트롤러에게 직접 전송할 권리가 있다.",
        "requirements": ["提供机器可读格式的数据", "支持直接传输", "适用于基于同意或合同的数据"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "medium", "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "effective_date": "2018-05-25"
    },
    {
        "id": "gdpr-010", "regulation": "GDPR", "article_number": "第22条", "article_number_ko": "제22조",
        "title": "自动化决策和画像", "title_ko": "자동화된 의사 결정 및 프로파일링",
        "summary": "数据主体有权不受完全基于自动化处理（包括画像）的决策约束，该决策对其产生法律效力或类似重大影响。",
        "summary_ko": "정보주체는 법적 효력 또는 중대한 영향을 미치는 완전 자동화된 결정(프로파일링 포함)의 대상이 되지 않을 권리가 있다.",
        "requirements": ["评估是否使用自动化决策", "提供人工干预机制", "允许数据主体表达观点和质疑"],
        "applicable_dimensions": ["data_security", "personal_info"],
        "risk_level": "high", "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "effective_date": "2018-05-25"
    },
    {
        "id": "gdpr-012", "regulation": "GDPR", "article_number": "第32条", "article_number_ko": "제32조",
        "title": "处理安全", "title_ko": "처리 안전",
        "summary": "控制者和处理者须实施适当的技术和组织措施确保安全水平与风险相称，包括加密、持续保密性和可用性。",
        "summary_ko": "컨트롤러와 프로세서는 위험에 상응하는 적절한 기술적·조직적 조치(암호화, 기밀성, 가용성 등)를 구현하여야 한다.",
        "requirements": ["风险评估", "加密和假名化", "持续保密性和可用性", "定期测试和评估"],
        "applicable_dimensions": ["data_security", "cybersecurity"],
        "risk_level": "critical", "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "effective_date": "2018-05-25"
    },
    {
        "id": "gdpr-013", "regulation": "GDPR", "article_number": "第33-34条", "article_number_ko": "제33-34조",
        "title": "数据泄露通知", "title_ko": "개인정보 유출 통지",
        "summary": "个人数据泄露时须在72小时内通知监管机构，如对个人造成高风险还须通知数据主体。",
        "summary_ko": "개인정보 유출 시 72시간 내 감독 기관에 통지하고, 개인에게 고위험이 있는 경우 정보주체에게도 통지하여야 한다.",
        "requirements": ["72小时内通知监管机构", "记录所有泄露事件", "高风险时通知数据主体"],
        "applicable_dimensions": ["data_security", "cybersecurity"],
        "risk_level": "critical", "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "effective_date": "2018-05-25"
    },
    {
        "id": "gdpr-014", "regulation": "GDPR", "article_number": "第35条", "article_number_ko": "제35조",
        "title": "数据保护影响评估", "title_ko": "데이터 보호 영향 평가(DPIA)",
        "summary": "当处理类型可能对个人权利和自由产生高风险时，控制者须在事前进行数据保护影响评估。",
        "summary_ko": "처리 유형이 개인의 권리와 자유에 고위험을 초래할 수 있는 경우 컨트롤러는 사전에 DPIA를 수행하여야 한다.",
        "requirements": ["识别高风险处理活动", "进行DPIA", "需要时咨询监管机构"],
        "applicable_dimensions": ["data_security", "personal_info"],
        "risk_level": "high", "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "effective_date": "2018-05-25"
    },
    {
        "id": "gdpr-015", "regulation": "GDPR", "article_number": "第37条", "article_number_ko": "제37조",
        "title": "数据保护官", "title_ko": "데이터 보호 책임자(DPO)",
        "summary": "公共机构、大规模监控或处理特殊类别数据的组织须指定数据保护官。",
        "summary_ko": "공공 기관, 대규모 모니터링 또는 특별 범주 데이터를 처리하는 기관은 DPO를 지정하여야 한다.",
        "requirements": ["指定DPO", "DPO独立行使职责", "DPO直接向最高管理层报告"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "medium", "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "effective_date": "2018-05-25"
    },
    {
        "id": "gdpr-016", "regulation": "GDPR", "article_number": "第44-49条", "article_number_ko": "제44-49조",
        "title": "跨境数据传输", "title_ko": "역외 데이터 전송",
        "summary": "向第三国传输个人数据须满足充分性认定、标准合同条款(SCC)或约束性企业规则(BCR)等保障措施。",
        "summary_ko": "개인정보를 제3국으로 이전하려면 적정성 결정, 표준 계약 조항(SCC) 또는 구속력 있는 기업 규칙(BCR) 등이 필요하다.",
        "requirements": ["充分性认定", "标准合同条款(SCC)", "约束性企业规则(BCR)", "特殊情形例外"],
        "applicable_dimensions": ["data_security", "cross_border_tax", "personal_info"],
        "risk_level": "critical", "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "effective_date": "2018-05-25"
    },

    # ===== PIPL (中国个人信息保护法) 15条 =====
    {
        "id": "pipl-001", "regulation": "PIPL", "article_number": "第5-8条", "article_number_ko": "제5-8조",
        "title": "个人信息处理原则", "title_ko": "개인정보 처리 원칙",
        "summary": "处理个人信息应当遵循合法、正当、必要和诚信原则，不得过度处理，并确保质量和保密。",
        "summary_ko": "개인정보 처리는 적법, 정당, 필요 및 성실 원칙을 따라야 하며, 과도한 처리를 금지하고 품질과 기밀성을 보장하여야 한다.",
        "requirements": ["合法正当必要诚信", "不得过度处理", "确保信息安全"],
        "applicable_dimensions": ["data_security", "personal_info"],
        "risk_level": "critical", "source_url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjM2YTAxNzk4NTkzMDYzNjA5ODY",
        "effective_date": "2021-11-01"
    },
    {
        "id": "pipl-002", "regulation": "PIPL", "article_number": "第6条", "article_number_ko": "제6조",
        "title": "最小影响原则", "title_ko": "최소 영향 원칙",
        "summary": "收集个人信息应当限于实现处理目的的最小范围，不得过度收集。个人信息的保存期限应为实现目的所必需的最短时间。",
        "summary_ko": "개인정보 수집은 처리 목적 달성에 필요한 최소 범위에 한정되어야 하며, 보존 기간은 목적 달성에 필요한 최단 시간이어야 한다.",
        "requirements": ["限于最小范围", "最短保存期限", "目的实现后删除"],
        "applicable_dimensions": ["data_security", "personal_info"],
        "risk_level": "high", "source_url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjM2YTAxNzk4NTkzMDYzNjA5ODY",
        "effective_date": "2021-11-01"
    },
    {
        "id": "pipl-003", "regulation": "PIPL", "article_number": "第13条", "article_number_ko": "제13조",
        "title": "处理的合法性基础", "title_ko": "처리의 적법 근거",
        "summary": "个人信息处理者仅在以下情形处理个人信息：取得同意、订立合同、履行法定职责、应对突发公共卫生事件、合理范围内新闻舆论监督等。",
        "summary_ko": "개인정보처리자는 동의, 계약 체결, 법정 직무 이행, 공공 보건 비상 대응, 정당한 언론 감독 등의 경우에만 개인정보를 처리할 수 있다.",
        "requirements": ["明确合法性基础", "不得超出法定情形处理"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "high", "source_url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjM2YTAxNzk4NTkzMDYzNjA5ODY",
        "effective_date": "2021-11-01"
    },
    {
        "id": "pipl-004", "regulation": "PIPL", "article_number": "第14条", "article_number_ko": "제14조",
        "title": "同意规则", "title_ko": "동의 규칙",
        "summary": "处理个人信息须在充分知情的前提下自愿、明确作出同意。同意须单独取得（敏感信息、跨境传输、向第三方提供等）。",
        "summary_ko": "개인정보 처리는 충분한 정보에 기반하여 자발적이고 명확하게 동의를 받아야 하며, 민감정보·역외 이전·제3자 제공 시 별도 동의가 필요하다.",
        "requirements": ["自愿明确同意", "充分知情前提", "敏感信息等须单独同意", "同意记录留存"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "critical", "source_url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjM2YTAxNzk4NTkzMDYzNjA5ODY",
        "effective_date": "2021-11-01"
    },
    {
        "id": "pipl-005", "regulation": "PIPL", "article_number": "第15条", "article_number_ko": "제15조",
        "title": "撤回同意权", "title_ko": "동의 철회권",
        "summary": "个人有权撤回其同意，个人信息处理者应当提供便捷的撤回同意方式。撤回不影响此前基于同意进行的处理。",
        "summary_ko": "개인은 동의를 철회할 권리가 있으며, 개인정보처리자는 편리한 철회 방식을 제공하여야 한다.",
        "requirements": ["提供便捷撤回方式", "不得因撤回拒绝服务", "撤回前处理有效"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "high", "source_url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjM2YTAxNzk4NTkzMDYzNjA5ODY",
        "effective_date": "2021-11-01"
    },
    {
        "id": "pipl-006", "regulation": "PIPL", "article_number": "第17条", "article_number_ko": "제17조",
        "title": "告知义务", "title_ko": "고지 의무",
        "summary": "处理个人信息前须以显著方式、清晰易懂的语言真实准确完整地告知处理者身份、处理目的和方式、个人信息种类和保存期限等。",
        "summary_ko": "개인정보 처리 전에 눈에 띄는 방식과 이해하기 쉬운 언어로 처리자 신원, 목적, 방식, 정보 종류 및 보존 기간 등을 고지하여야 한다.",
        "requirements": ["显著方式告知", "清晰易懂语言", "真实准确完整", "逐项列出法定告知事项"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "high", "source_url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjM2YTAxNzk4NTkzMDYzNjA5ODY",
        "effective_date": "2021-11-01"
    },
    {
        "id": "pipl-007", "regulation": "PIPL", "article_number": "第22条", "article_number_ko": "제22조",
        "title": "委托处理", "title_ko": "위탁 처리",
        "summary": "委托他人处理个人信息的，应当约定委托目的、处理方式、信息种类、保护措施等，并对受托人进行监督。",
        "summary_ko": "개인정보 처리를 위탁하는 경우 위탁 목적, 처리 방식, 정보 종류, 보호 조치 등을 약정하고 수탁자를 감독하여야 한다.",
        "requirements": ["委托合同明确约定", "监督受托人", "委托不转移个人信息"],
        "applicable_dimensions": ["data_security", "personal_info"],
        "risk_level": "high", "source_url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjM2YTAxNzk4NTkzMDYzNjA5ODY",
        "effective_date": "2021-11-01"
    },
    {
        "id": "pipl-008", "regulation": "PIPL", "article_number": "第23条", "article_number_ko": "제23조",
        "title": "向第三方提供", "title_ko": "제3자 제공",
        "summary": "向第三方提供个人信息的，须告知接收方信息并取得单独同意。接收方须在约定范围内处理。",
        "summary_ko": "제3자에게 개인정보를 제공하는 경우 수신자 정보를 고지하고 별도 동의를 받아야 하며, 수신자는 약정 범위 내에서 처리하여야 한다.",
        "requirements": ["告知接收方信息", "取得单独同意", "接收方范围限制"],
        "applicable_dimensions": ["data_security", "personal_info"],
        "risk_level": "high", "source_url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjM2YTAxNzk4NTkzMDYzNjA5ODY",
        "effective_date": "2021-11-01"
    },
    {
        "id": "pipl-009", "regulation": "PIPL", "article_number": "第28条", "article_number_ko": "제28조",
        "title": "敏感个人信息", "title_ko": "민감 개인정보",
        "summary": "敏感个人信息包括生物识别、宗教信仰、特定身份、医疗健康、金融账户、行踪轨迹等，处理须有特定目的和充分必要性。",
        "summary_ko": "민감 개인정보에는 생체 인식, 종교 신앙, 특정 신분, 의료 건강, 금융 계좌, 위치 추적 등이 포함되며, 특정 목적과 충분한 필요성이 있어야 처리 가능하다.",
        "requirements": ["特定目的和充分必要性", "单独同意", "更严格的安全措施"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "critical", "source_url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjM2YTAxNzk4NTkzMDYzNjA5ODY",
        "effective_date": "2021-11-01"
    },
    {
        "id": "pipl-010", "regulation": "PIPL", "article_number": "第31条", "article_number_ko": "제31조",
        "title": "未成年人个人信息", "title_ko": "미성년자 개인정보",
        "summary": "处理不满14周岁未成年人个人信息须取得其父母或监护人的同意，并制定专门的未成年人信息处理规则。",
        "summary_ko": "14세 미만 미성년자의 개인정보를 처리하려면 부모 또는 보호자의 동의를 받고 전용 미성년자 정보 처리 규칙을 수립하여야 한다.",
        "requirements": ["监护人同意", "专门未成年人处理规则", "特殊保护措施"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "critical", "source_url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjM2YTAxNzk4NTkzMDYzNjA5ODY",
        "effective_date": "2021-11-01"
    },
    {
        "id": "pipl-011", "regulation": "PIPL", "article_number": "第38条", "article_number_ko": "제38조",
        "title": "跨境数据传输——条件", "title_ko": "역외 데이터 전송 - 조건",
        "summary": "向境外提供个人信息须通过安全评估、经专业机构认证或签订标准合同。特定情形还须进行个人信息保护影响评估。",
        "summary_ko": "개인정보를 역외로 제공하려면 안전 평가 통과, 전문 기관 인증 또는 표준 계약 체결이 필요하며, 영향 평가도 수행하여야 한다.",
        "requirements": ["安全评估", "专业机构认证", "标准合同", "个人信息保护影响评估"],
        "applicable_dimensions": ["data_security", "cross_border_tax", "personal_info"],
        "risk_level": "critical", "source_url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjM2YTAxNzk4NTkzMDYzNjA5ODY",
        "effective_date": "2021-11-01"
    },
    {
        "id": "pipl-012", "regulation": "PIPL", "article_number": "第40条", "article_number_ko": "제40조",
        "title": "CII和大量数据出境", "title_ko": "CII 및 대량 데이터 역외 이전",
        "summary": "关键信息基础设施运营者和处理大量个人信息的处理者，向境外提供个人信息须通过安全评估。",
        "summary_ko": "중요 정보 인프라 운영자 및 대량 개인정보를 처리하는 자는 역외 이전 시 안전 평가를 통과하여야 한다.",
        "requirements": ["CII运营者须安全评估", "大量个人信息处理者须安全评估"],
        "applicable_dimensions": ["data_security", "cybersecurity"],
        "risk_level": "critical", "source_url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjM2YTAxNzk4NTkzMDYzNjA5ODY",
        "effective_date": "2021-11-01"
    },
    {
        "id": "pipl-013", "regulation": "PIPL", "article_number": "第44-47条", "article_number_ko": "제44-47조",
        "title": "个人权利", "title_ko": "개인 권리",
        "summary": "个人享有知情权、决定权、查阅权、复制权、更正权、删除权、可携带权和死后的权利等。",
        "summary_ko": "개인은 알 권리, 결정권, 열람권, 복사권, 정정권, 삭제권, 이동권 및 사후 권리 등을 가진다.",
        "requirements": ["15个工作日内响应查阅请求", "支持数据可携带", "处理删除和更正请求"],
        "applicable_dimensions": ["personal_info", "data_security"],
        "risk_level": "high", "source_url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjM2YTAxNzk4NTkzMDYzNjA5ODY",
        "effective_date": "2021-11-01"
    },
    {
        "id": "pipl-014", "regulation": "PIPL", "article_number": "第51条", "article_number_ko": "제51조",
        "title": "内部管理义务", "title_ko": "내부 관리 의무",
        "summary": "个人信息处理者须制定内部管理制度、实施分级分类管理、采取技术安全措施、制定应急计划和定期审计。",
        "summary_ko": "개인정보처리자는 내부 관리 제도 수립, 분류 등급 관리, 기술적 안전 조치, 비상 계획 수립 및 정기 감사를 수행하여야 한다.",
        "requirements": ["内部管理制度", "分级分类管理", "安全技术措施", "应急计划", "定期审计"],
        "applicable_dimensions": ["data_security", "cybersecurity"],
        "risk_level": "critical", "source_url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjM2YTAxNzk4NTkzMDYzNjA5ODY",
        "effective_date": "2021-11-01"
    },
    {
        "id": "pipl-016", "regulation": "PIPL", "article_number": "第55-56条", "article_number_ko": "제55-56조",
        "title": "个人信息保护影响评估", "title_ko": "개인정보 보호 영향 평가",
        "summary": "处理敏感个人信息、自动化决策、委托处理、向第三方提供、跨境传输等高风险活动前须进行个人信息保护影响评估。",
        "summary_ko": "민감정보 처리, 자동화 결정, 위탁 처리, 제3자 제공, 역외 이전 등 고위험 활동 전에 개인정보 보호 영향 평가를 수행하여야 한다.",
        "requirements": ["事前进行评估", "评估内容包括处理目的和风险", "评估报告留存至少3年"],
        "applicable_dimensions": ["data_security", "personal_info"],
        "risk_level": "high", "source_url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjM2YTAxNzk4NTkzMDYzNjA5ODY",
        "effective_date": "2021-11-01"
    },
]

ARTICLE_MAP = {a["id"]: a for a in ALL_ARTICLES}

# ─────────────────────────────────────────────
# 跨法规对比主题映射 (12个主题)
# ─────────────────────────────────────────────

COMPARE_TOPICS = {
    "data_retention": {
        "label_zh": "数据保留期限", "label_ko": "데이터 보유 기간",
        "kdpa": ["kdpa-001", "kdpa-003"], "gdpr": ["gdpr-001"], "pipl": ["pipl-002", "pipl-016"],
        "cmp_zh": "【K-DPA】保留不超法定/必要期限，过期后不可恢复销毁\n【GDPR】存储限制原则，不超处理所需时间\n【PIPL】最短保存期限，目的实现后主动删除",
        "cmp_ko": "【K-DPA】법정/필요 기간 초과 불가, 만료 후 복구 불가 폐기\n【GDPR】저장 제한 원칙, 처리 목적에 필요한 기간 초과 불가\n【PIPL】최단 보존 기간, 목적 달성 후 삭제",
    },
    "consent": {
        "label_zh": "同意要求", "label_ko": "동의 요건",
        "kdpa": ["kdpa-002", "kdpa-003"], "gdpr": ["gdpr-002", "gdpr-003"], "pipl": ["pipl-004", "pipl-005"],
        "cmp_zh": "【K-DPA】明确同意，区分必要/选择，14岁以下需监护人\n【GDPR】清晰肯定行为，默示无效，撤回须同样容易\n【PIPL】自愿明确，敏感信息等须单独同意，撤回权保障",
        "cmp_ko": "【K-DPA】명시적 동의, 필수/선택 구분, 14세 미만 보호자 동의\n【GDPR】명확·적극적 행동, 묵시적 동의 무효, 철회 동등 용이\n【PIPL】자발적 명시적, 민감정보 별도 동의, 철회권 보장",
    },
    "breach_notification": {
        "label_zh": "数据泄露通知", "label_ko": "데이터 유출 통지",
        "kdpa": ["kdpa-013"], "gdpr": ["gdpr-013"], "pipl": ["pipl-014"],
        "cmp_zh": "【K-DPA】24小时内向PIPC报告\n【GDPR】72小时内通知监管机构\n【PIPL】立即补救，通知监管和个人",
        "cmp_ko": "【K-DPA】24시간 내 PIPC 보고\n【GDPR】72시간 내 감독 기관 통지\n【PIPL】즉시 구제, 규제·개인 통지",
    },
    "cross_border": {
        "label_zh": "跨境数据传输", "label_ko": "역외 데이터 전송",
        "kdpa": ["kdpa-009"], "gdpr": ["gdpr-016"], "pipl": ["pipl-011", "pipl-012"],
        "cmp_zh": "【K-DPA】用户同意+保护措施，向PIPC申报\n【GDPR】充分性认定/SCCs/BCR\n【PIPL】安全评估/认证/标准合同",
        "cmp_ko": "【K-DPA】동의+보호 조치, PIPC 신고\n【GDPR】적정성 결정/SCC/BCR\n【PIPL】안전 평가/인증/표준 계약",
    },
    "user_rights": {
        "label_zh": "用户权利", "label_ko": "정보주체 권리",
        "kdpa": ["kdpa-014"], "gdpr": ["gdpr-007", "gdpr-008", "gdpr-009"], "pipl": ["pipl-013"],
        "cmp_zh": "【K-DPA】查阅/更正/删除权，10日内\n【GDPR】DSAR(30天)、删除权、可携带权\n【PIPL】知情权、查阅/更正/删除(15工作日)、可携带权",
        "cmp_ko": "【K-DPA】열람/정정/삭제권, 10일 내\n【GDPR】DSAR(30일), 삭제권, 이동권\n【PIPL】알 권리, 열람/정정/삭제(15영업일), 이동권",
    },
    "data_security": {
        "label_zh": "安全保护措施", "label_ko": "안전 보호 조치",
        "kdpa": ["kdpa-011"], "gdpr": ["gdpr-012"], "pipl": ["pipl-014"],
        "cmp_zh": "【K-DPA】加密/访问控制/入侵防御/日志审计\n【GDPR】技术与组织措施，风险相称\n【PIPL】加密/去标识化/访问控制/审计/应急",
        "cmp_ko": "【K-DPA】암호화/접근 통제/침입 방지/로그\n【GDPR】기술·조직적 조치, 위험 상응\n【PIPL】암호화/비식별화/접근 통제/감사/대응",
    },
    "sensitive_data": {
        "label_zh": "敏感信息处理", "label_ko": "민감정보 처리",
        "kdpa": ["kdpa-008"], "gdpr": ["gdpr-004"], "pipl": ["pipl-009"],
        "cmp_zh": "【K-DPA】原则禁止，法律依据/单独同意例外\n【GDPR】明确禁止，特定例外（明确同意等）\n【PIPL】特定目的+充分必要+单独同意",
        "cmp_ko": "【K-DPA】원칙 금지, 법적 근거/별도 동의 시 예외\n【GDPR】명시적 금지, 특정 예외(명시적 동의 등)\n【PIPL】특정 목적+충분 필요성+별도 동의",
    },
    "children_data": {
        "label_zh": "儿童信息保护", "label_ko": "아동 정보 보호",
        "kdpa": ["kdpa-007"], "gdpr": ["gdpr-004"], "pipl": ["pipl-010"],
        "cmp_zh": "【K-DPA】14岁以下需监护人同意\n【GDPR】16岁以下（成员国可降至13岁）需父母同意\n【PIPL】14岁以下需父母/监护人同意+专门规则",
        "cmp_ko": "【K-DPA】14세 미만 보호자 동의\n【GDPR】16세 미만(회원국 13세 가능) 부모 동의\n【PIPL】14세 미만 부모/보호자 동의+전용 규칙",
    },
    "accountability": {
        "label_zh": "问责制与DPO", "label_ko": "책임성 및 DPO",
        "kdpa": ["kdpa-012"], "gdpr": ["gdpr-015"], "pipl": ["pipl-016"],
        "cmp_zh": "【K-DPA】指定CPO\n【GDPR】指定DPO（公共机构/大规模监控/特殊数据）\n【PIPL】大量个人信息处理者指定负责人",
        "cmp_ko": "【K-DPA】CPO 지정\n【GDPR】DPO 지정(공공 기관/대규모 모니터링/특별 데이터)\n【PIPL】대량 개인정보 처리자 책임자 지정",
    },
    "data_protection_impact": {
        "label_zh": "影响评估(PIA/DPIA)", "label_ko": "영향 평가(PIA/DPIA)",
        "kdpa": ["kdpa-010"], "gdpr": ["gdpr-014"], "pipl": ["pipl-016"],
        "cmp_zh": "【K-DPA】大规模敏感信息或重大隐私风险时需PIA\n【GDPR】高风险处理活动前需DPIA\n【PIPL】高风险活动(敏感信息/自动决策/跨境)需事前评估",
        "cmp_ko": "【K-DPA】대규모 민감정보/중대 프라이버시 위험 시 PIA\n【GDPR】고위험 처리 활동 전 DPIA\n【PIPL】고위험 활동(민감/자동 결정/역외) 사전 평가",
    },
    "data_processor": {
        "label_zh": "委托处理与第三方", "label_ko": "위탁 처리 및 제3자",
        "kdpa": ["kdpa-006"], "gdpr": ["gdpr-002"], "pipl": ["pipl-007", "pipl-008"],
        "cmp_zh": "【K-DPA】告知并取得同意，委托合同含安全条款\n【GDPR】需有处理者合同，明确双方责任\n【PIPL】委托合同约定+监督+单独同意（向第三方）",
        "cmp_ko": "【K-DPA】고지 및 동의, 위탁 계약 안전 조항\n【GDPR】프로세서 계약 필요, 쌍방 책임 명시\n【PIPL】위탁 계약 약정+감독+별도 동의(제3자)",
    },
    "automated_decision": {
        "label_zh": "自动化决策", "label_ko": "자동화 결정",
        "kdpa": ["kdpa-005"], "gdpr": ["gdpr-010"], "pipl": ["pipl-016"],
        "cmp_zh": "【K-DPA】目的外使用限制\n【GDPR】自动化决策的拒绝权，须有人工干预\n【PIPL】自动化决策须公平透明，拒绝权保障",
        "cmp_ko": "【K-DPA】목적 외 사용 제한\n【GDPR】자동화 결정 거부권, 인적 개입 필요\n【PIPL】자동화 결정 공정·투명, 거부권 보장",
    },
}

# ─────────────────────────────────────────────
# 问题-知识引用映射 (20题)
# ─────────────────────────────────────────────

QUESTION_KNOWLEDGE_REF = {
    1: ["pipl-003"],           # 行业准入 -> PIPL
    2: ["kdpa-009", "gdpr-016", "pipl-011"],  # 数据跨境
    3: [],                     # 知识产权
    4: [],                     # 跨境财税
    5: [],                     # 劳动用工
    6: [],                     # 签证移民
    7: [],                     # 公司设立
    8: [],                     # 进出口
    9: [],                     # 环境影响
    10: [],                    # 反商业贿赂
    11: ["kdpa-009"],          # 外汇管制
    12: [],                    # 技术进出口
    13: [],                    # 产品质量
    14: [],                    # 广告
    15: [],                    # 电商
    16: [],                    # 消费者权益
    17: [],                    # 劳务派遣
    18: ["pipl-003"],          # 外商投资
    19: ["kdpa-011", "gdpr-012", "pipl-014"],  # 网络安全
    20: ["kdpa-015", "gdpr-007", "pipl-013"],  # 个人信息
}


# ─────────────────────────────────────────────
# SQLite 持久化
# ─────────────────────────────────────────────

def init_knowledge_graph():
    """初始化知识图谱 SQLite 表结构并插入种子数据。"""
    conn = get_db()
    cursor = conn.cursor()

    # 创建知识图谱主表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_graph (
            id TEXT PRIMARY KEY,
            article_number TEXT NOT NULL,
            article_number_ko TEXT,
            regulation_name TEXT NOT NULL CHECK(regulation_name IN ('K-DPA','GDPR','PIPL')),
            title TEXT NOT NULL,
            title_ko TEXT,
            summary TEXT,
            summary_ko TEXT,
            requirements TEXT,
            applicable_dimensions TEXT,
            risk_level TEXT NOT NULL CHECK(risk_level IN ('low','medium','high','critical')),
            source_url TEXT,
            effective_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

    # 创建合规维度表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kg_dimensions (
            id TEXT PRIMARY KEY,
            name_zh TEXT NOT NULL,
            name_ko TEXT NOT NULL,
            description_zh TEXT,
            description_ko TEXT,
            risk_level TEXT DEFAULT 'medium'
        )""")

    # 创建法规注册表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kg_regulations (
            id TEXT PRIMARY KEY,
            full_name_zh TEXT NOT NULL,
            full_name_ko TEXT NOT NULL,
            abbreviation TEXT NOT NULL,
            jurisdiction TEXT NOT NULL,
            effective_date TEXT,
            source_url TEXT
        )""")

    # 创建问题-知识引用表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kg_question_ref (
            question_id INTEGER NOT NULL,
            article_id TEXT NOT NULL,
            PRIMARY KEY (question_id, article_id)
        )""")

    conn.commit()

    # 清空旧数据（INSERT OR REPLACE 不会删除已移除的条款）
    cursor.execute("DELETE FROM knowledge_graph")
    cursor.execute("DELETE FROM kg_dimensions")
    cursor.execute("DELETE FROM kg_regulations")
    cursor.execute("DELETE FROM kg_question_ref")

    # 插入维度数据
    for d in DIMENSIONS:
        cursor.execute("""
            INSERT OR REPLACE INTO kg_dimensions
            (id, name_zh, name_ko, description_zh, description_ko, risk_level)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (d["id"], d["name_zh"], d["name_ko"], d["description_zh"], d["description_ko"], d["risk_level"]))

    # 插入法规信息
    regulations = {
        "K-DPA": {"fn_zh": "韩国个人信息保护法", "fn_ko": "한국 개인정보 보호법",
                   "jur": "韩国", "date": "2020-02-04",
                   "url": "https://www.law.go.kr/법령/개인정보보호법"},
        "GDPR":  {"fn_zh": "欧盟通用数据保护条例", "fn_ko": "EU 일반 데이터 보호 규정",
                   "jur": "欧盟", "date": "2018-05-25",
                   "url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj"},
        "PIPL":  {"fn_zh": "中华人民共和国个人信息保护法", "fn_ko": "중화인민공화국 개인정보보호법",
                   "jur": "中国", "date": "2021-11-01",
                   "url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjM2YTAxNzk4NTkzMDYzNjA5ODY"},
    }
    for rid, rd in regulations.items():
        cursor.execute("""
            INSERT OR REPLACE INTO kg_regulations VALUES (?,?,?,?,?,?,?)""",
            (rid, rd["fn_zh"], rd["fn_ko"], rid, rd["jur"], rd["date"], rd["url"]))

    # 插入条款数据
    for a in ALL_ARTICLES:
        cursor.execute("""
            INSERT OR REPLACE INTO knowledge_graph
            (id, article_number, article_number_ko, regulation_name,
             title, title_ko, summary, summary_ko,
             requirements, applicable_dimensions, risk_level,
             source_url, effective_date, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
            (a["id"], a["article_number"], a.get("article_number_ko", ""),
             a["regulation"], a["title"], a["title_ko"],
             a["summary"], a["summary_ko"],
             json.dumps(a["requirements"], ensure_ascii=False),
             json.dumps(a["applicable_dimensions"], ensure_ascii=False),
             a["risk_level"], a["source_url"], a["effective_date"]))

    # 插入问题-知识引用
    for qid, refs in QUESTION_KNOWLEDGE_REF.items():
        for aid in refs:
            cursor.execute("INSERT OR REPLACE INTO kg_question_ref VALUES (?,?)", (qid, aid))

    conn.commit()
    conn.close()
    print(f"[知识图谱] 初始化完成: {len(ALL_ARTICLES)}条条款, {len(DIMENSIONS)}个维度")


# ─────────────────────────────────────────────
# 核心功能函数
# ─────────────────────────────────────────────

def _fix_lang(a: Dict, lang: str) -> Dict[str, Any]:
    """将文章数据格式化为指定语言的返回格式。"""
    return {
        "id": a["id"],
        "regulation": a["regulation"],
        "article_number": a["article_number"] if lang == "zh" else a.get("article_number_ko", a["article_number"]),
        "title": a.get(f"title_{lang}" if lang != "zh" else "title", a["title"]),
        "summary": a.get(f"summary_{lang}" if lang != "zh" else "summary", a["summary"]),
        "requirements": a.get("requirements", []),
        "applicable_dimensions": a.get("applicable_dimensions", []),
        "source_url": a.get("source_url", ""),
        "effective_date": a.get("effective_date", ""),
        "risk_level": a.get("risk_level", "medium"),
    }


def get_dimensions(language: str = "zh") -> List[Dict[str, Any]]:
    """获取所有合规维度列表（含条款数量统计）。"""
    result = []
    for d in DIMENSIONS:
        cnt = sum(1 for a in ALL_ARTICLES if d["id"] in a.get("applicable_dimensions", []))
        result.append({
            "id": d["id"],
            "name": d.get(f"name_{language}", d["name_zh"]),
            "description": d.get(f"description_{language}", ""),
            "risk_level": d.get("risk_level", "medium"),
            "article_count": cnt,
        })
    return result


def get_articles_by_dimension(dimension: str, language: str = "zh") -> List[Dict[str, Any]]:
    """获取某个合规维度涉及的所有法规条款。"""
    return [_fix_lang(a, language) for a in ALL_ARTICLES
            if dimension in a.get("applicable_dimensions", [])]


def compare_across_regulations(topic: str, language: str = "zh") -> Dict[str, Any]:
    """同一议题在中/韩/欧盟三方法规中的差异对比。"""
    tk = topic.lower().replace(" ", "_").replace("-", "_")
    data = COMPARE_TOPICS.get(tk)
    if not data:
        for k, v in COMPARE_TOPICS.items():
            if tk in k or k in tk:
                data = v
                break
    if not data:
        available = list(COMPARE_TOPICS.keys())
        return {
            "error": True,
            "message_zh": f"未知主题: {topic}，可用主题: {', '.join(available)}",
            "message_ko": f"알 수 없는 주제: {topic}, 가능 주제: {', '.join(available)}",
            "available_topics": available,
        }

    def _get_articles(ids):
        return [_fix_lang(ARTICLE_MAP[a], language) for a in ids if a in ARTICLE_MAP]

    return {
        "topic": data[f"label_{language}"],
        "topic_id": tk,
        "comparison": data[f"cmp_{language}"],
        "regulations": {
            "K-DPA": {"regulation_name": "K-DPA", "articles": _get_articles(data["kdpa"])},
            "GDPR":  {"regulation_name": "GDPR",  "articles": _get_articles(data["gdpr"])},
            "PIPL":  {"regulation_name": "PIPL",  "articles": _get_articles(data["pipl"])},
        },
    }


def get_recommendations(answers: Dict[int, int], language: str = "zh") -> List[Dict[str, Any]]:
    """基于自检答案(20题)给出条款级建议。"""
    try:
        from backend.compliance.questions_data import get_question_by_id
    except ImportError:
        return []

    recs = []
    for qid, score in answers.items():
        if score < 2:
            continue
        q = get_question_by_id(qid)
        if not q:
            continue
        refs = QUESTION_KNOWLEDGE_REF.get(qid, [])
        details = [_fix_lang(ARTICLE_MAP[a], language) for a in refs if a in ARTICLE_MAP]
        kref_str = q.get("knowledge_ref", {}).get(language, "")
        action_advice = q.get("action_advice", {}).get(language, "")
        recs.append({
            "question_id": qid,
            "dimension": q.get("dimension", ""),
            "dimension_label": q.get("dimension_label", {}).get(language, ""),
            "raw_score": score,
            "risk_level": "high" if score == 3 else "medium",
            "action_advice": action_advice,
            "knowledge_ref_str": kref_str,
            "regulated_articles": details,
            "knowledge_article_ids": refs,
        })
    return recs


def search_articles(keyword: str, language: str = "zh") -> List[Dict[str, Any]]:
    """关键词搜索条款（在标题、摘要、requirements和维度名称中搜索）。"""
    kw = keyword.lower().strip()
    if not kw:
        return []

    results = []
    for a in ALL_ARTICLES:
        fields_to_search = [
            a.get("title", ""), a.get("title_ko", ""),
            a.get("summary", ""), a.get("summary_ko", ""),
            a.get("article_number", ""), a.get("article_number_ko", ""),
            a["regulation"],
        ]
        fields_to_search.extend(a.get("requirements", []))
        for dim_id in a.get("applicable_dimensions", []):
            dim = DIMENSION_MAP.get(dim_id)
            if dim:
                fields_to_search.append(dim.get("name_zh", ""))
                fields_to_search.append(dim.get("name_ko", ""))

        matched = any(kw in f.lower() for f in fields_to_search if f)
        if matched:
            results.append(_fix_lang(a, language))

    return results


def list_all_obligations(language: str = "zh") -> List[Dict[str, Any]]:
    """列出所有法规义务条款。"""
    return [_fix_lang(a, language) for a in ALL_ARTICLES]


def get_knowledge_statistics() -> Dict[str, Any]:
    """获取知识图谱统计信息。"""
    by_reg = {}
    by_risk = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    by_dim = {}

    for a in ALL_ARTICLES:
        r = a["regulation"]
        by_reg[r] = by_reg.get(r, 0) + 1
        rl = a.get("risk_level", "medium")
        by_risk[rl] = by_risk.get(rl, 0) + 1

    for d in DIMENSIONS:
        cnt = sum(1 for a in ALL_ARTICLES if d["id"] in a.get("applicable_dimensions", []))
        by_dim[d["id"]] = {
            "name_zh": d["name_zh"],
            "name_ko": d["name_ko"],
            "article_count": cnt,
        }

    return {
        "total_articles": len(ALL_ARTICLES),
        "total_regulations": len(by_reg),
        "total_dimensions": len(DIMENSIONS),
        "total_compare_topics": len(COMPARE_TOPICS),
        "by_regulation": by_reg,
        "by_risk_level": by_risk,
        "by_dimension": by_dim,
    }


# ─────────────────────────────────────────────
# FastAPI 路由（供 main.py 注册）
# ─────────────────────────────────────────────

try:
    from fastapi import APIRouter, HTTPException, Query
    from typing import Optional

    router = APIRouter(prefix="/api/compliance/knowledge", tags=["compliance-knowledge-graph"])

    @router.get("/dimensions")
    async def api_get_dimensions(language: str = Query("zh", pattern="^(zh|ko)$")):
        dims = get_dimensions(language)
        return {"success": True, "dimensions": dims, "total": len(dims)}

    @router.get("/articles")
    async def api_get_articles(
        dimension: Optional[str] = Query(None),
        regulation: Optional[str] = Query(None),
        article_id: Optional[str] = Query(None),
        language: str = Query("zh", pattern="^(zh|ko)$"),
    ):
        if article_id:
            a = ARTICLE_MAP.get(article_id)
            if not a:
                raise HTTPException(status_code=404, detail=f"条款 {article_id} 未找到")
            return {"success": True, "article": _fix_lang(a, language)}

        result = []
        for a in ALL_ARTICLES:
            if dimension and dimension not in a.get("applicable_dimensions", []):
                continue
            if regulation:
                reg = regulation.upper().replace("-", "")
                if a["regulation"].upper().replace("-", "") != reg:
                    continue
            result.append(_fix_lang(a, language))
        return {"success": True, "articles": result, "total": len(result)}

    @router.get("/search")
    async def api_search_articles(
        keyword: str = Query(..., min_length=1),
        language: str = Query("zh", pattern="^(zh|ko)$"),
    ):
        results = search_articles(keyword, language)
        return {"success": True, "results": results, "total": len(results)}

    @router.get("/compare")
    async def api_compare(
        topic: str = Query(...),
        language: str = Query("zh", pattern="^(zh|ko)$"),
    ):
        result = compare_across_regulations(topic, language)
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result.get(f"message_{language}", str(result)))
        return {"success": True, **result}

    @router.get("/statistics")
    async def api_statistics():
        return {"success": True, "statistics": get_knowledge_statistics()}

    @router.get("/obligations")
    async def api_obligations(language: str = Query("zh", pattern="^(zh|ko)$")):
        obs = list_all_obligations(language)
        return {"success": True, "obligations": obs, "total": len(obs)}

    @router.get("/recommendations")
    async def api_recommendations(
        q1: Optional[int] = Query(None, ge=0, le=3),
        q2: Optional[int] = Query(None, ge=0, le=3),
        q3: Optional[int] = Query(None, ge=0, le=3),
        q4: Optional[int] = Query(None, ge=0, le=3),
        q5: Optional[int] = Query(None, ge=0, le=3),
        q6: Optional[int] = Query(None, ge=0, le=3),
        q7: Optional[int] = Query(None, ge=0, le=3),
        q8: Optional[int] = Query(None, ge=0, le=3),
        q9: Optional[int] = Query(None, ge=0, le=3),
        q10: Optional[int] = Query(None, ge=0, le=3),
        q11: Optional[int] = Query(None, ge=0, le=3),
        q12: Optional[int] = Query(None, ge=0, le=3),
        q13: Optional[int] = Query(None, ge=0, le=3),
        q14: Optional[int] = Query(None, ge=0, le=3),
        q15: Optional[int] = Query(None, ge=0, le=3),
        q16: Optional[int] = Query(None, ge=0, le=3),
        q17: Optional[int] = Query(None, ge=0, le=3),
        q18: Optional[int] = Query(None, ge=0, le=3),
        q19: Optional[int] = Query(None, ge=0, le=3),
        q20: Optional[int] = Query(None, ge=0, le=3),
        language: str = Query("zh", pattern="^(zh|ko)$"),
    ):
        answers = {}
        for i, v in enumerate([q1, q2, q3, q4, q5, q6, q7, q8, q9, q10,
                               q11, q12, q13, q14, q15, q16, q17, q18, q19, q20], 1):
            if v is not None:
                answers[i] = v
        if not answers:
            raise HTTPException(status_code=400, detail="请至少提供一道题的答案")
        recs = get_recommendations(answers, language)
        return {"success": True, "recommendations": recs, "total": len(recs)}

except ImportError:
    router = None


# ─────────────────────────────────────────────
# CLI 命令入口
# ─────────────────────────────────────────────

def cli():
    parser = argparse.ArgumentParser(
        description="中韩出海数智港 — 合规知识图谱引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 -m backend.compliance.knowledge_graph --init
  python3 -m backend.compliance.knowledge_graph --dimension data_security
  python3 -m backend.compliance.knowledge_graph --compare data_retention
  python3 -m backend.compliance.knowledge_graph --search 跨境传输
  python3 -m backend.compliance.knowledge_graph --obligations
  python3 -m backend.compliance.knowledge_graph --statistics
        """)

    parser.add_argument("--init", action="store_true", help="初始化知识图谱到SQLite")
    parser.add_argument("--dimension", type=str, help="查询某维度涉及的条款")
    parser.add_argument("--compare", type=str, help="跨法规对比某主题")
    parser.add_argument("--search", type=str, help="关键词搜索条款")
    parser.add_argument("--obligations", action="store_true", help="列出所有义务条款")
    parser.add_argument("--statistics", action="store_true", help="图谱统计信息")
    parser.add_argument("--language", type=str, default="zh", choices=["zh", "ko"], help="语言 (zh/ko)")

    args = parser.parse_args()
    lang = args.language

    if args.init:
        init_knowledge_graph()
        print(f"[CLI] 知识图谱初始化完成: {len(ALL_ARTICLES)}条条款, {len(DIMENSIONS)}个维度")

    elif args.dimension:
        articles = get_articles_by_dimension(args.dimension, lang)
        dim_info = DIMENSION_MAP.get(args.dimension, {})
        dim_name = dim_info.get(f"name_{lang}", args.dimension)
        print(f"\n{'='*60}")
        print(f"  维度: {dim_name}")
        print(f"  涉及条款数: {len(articles)}")
        print(f"{'='*60}")
        for a in articles:
            print(f"\n  [{a['regulation']}] {a['article_number']} - {a['title']}")
            print(f"  风险等级: {a['risk_level']}")
            if a['summary']:
                print(f"  摘要: {a['summary'][:100]}...")
            print(f"  ──")

    elif args.compare:
        result = compare_across_regulations(args.compare, lang)
        if result.get("error"):
            print(f"错误: {result.get(f'message_{lang}', '未知错误')}")
            sys.exit(1)
        print(f"\n{'='*60}")
        print(f"  跨法规对比: {result['topic']}")
        print(f"{'='*60}")
        print(f"\n对比总结:\n{result['comparison']}")
        for reg_name, reg_data in result["regulations"].items():
            print(f"\n  --- {reg_name} ---")
            for a in reg_data["articles"]:
                print(f"    {a['article_number']} - {a['title']}")
                if a['summary']:
                    print(f"    {a['summary'][:80]}...")

    elif args.search:
        results = search_articles(args.search, lang)
        print(f"\n{'='*60}")
        print(f"  关键词搜索: '{args.search}'")
        print(f"  结果数: {len(results)}")
        print(f"{'='*60}")
        for a in results:
            print(f"\n  [{a['regulation']}] {a['article_number']} - {a['title']}")
            if a['summary']:
                print(f"  {a['summary'][:120]}")

    elif args.obligations:
        obs = list_all_obligations(lang)
        print(f"\n{'='*60}")
        print(f"  全部义务条款清单 ({len(obs)} 项)")
        print(f"{'='*60}")
        for a in obs:
            print(f"  [{a['regulation']:5s}] {a['article_number']:15s} | {a['title']:30s} | 风险: {a['risk_level']}")

    elif args.statistics:
        stats = get_knowledge_statistics()
        print(f"\n{'='*60}")
        print(f"  知识图谱统计")
        print(f"{'='*60}")
        print(f"  总条款数:       {stats['total_articles']}")
        print(f"  法规数:         {stats['total_regulations']}")
        print(f"  合规维度数:     {stats['total_dimensions']}")
        print(f"  对比主题数:     {stats['total_compare_topics']}")
        print(f"\n  按法规分布:     {stats['by_regulation']}")
        print(f"  按风险等级分布: {stats['by_risk_level']}")
        print(f"\n  按维度分布:")
        for dim_id, dim_info in stats["by_dimension"].items():
            if dim_info["article_count"] > 0:
                print(f"    {dim_info['name_zh']:20s} ({dim_info['name_ko']}): {dim_info['article_count']}条")

    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
