"""
中韩出海数智港 - AI数字员工对话引擎（基于DeepSeek的合规问答）

功能：
1. 基于DeepSeek API的合规问答引擎
2. 中韩双语支持（自动识别语言）
3. 读取PRD/和合规/目录下的文档作为RAG上下文
4. 上下文筛选：根据用户问题自动搜索相关文档片段
5. 无API key时使用模拟模式（基于预定义合规FAQ回复）
"""
import os
import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 知识图谱引擎
BACKEND_DIR = Path(__file__).parent  # backend/
sys.path.insert(0, str(BACKEND_DIR))
from knowledge_graph import get_db as kg_get_db, search_articles, get_articles_by_dimension, ALL_ARTICLES, DIMENSIONS, DIMENSION_MAP  # china-korea-digital-port/

# ── 知识库路径 ──────────────────────────────────────────
PRD_DIR = PROJECT_ROOT / "PRD"
COMPLIANCE_DIR = PROJECT_ROOT / "合规"
# 注意：也可能叫 "合规自检目录"，这里提供两个可能路径
COMPLIANCE_DIR2 = PROJECT_ROOT / "合规自检"
COMPLIANCE_BACKEND_DIR = BACKEND_DIR / "compliance"

# ── DeepSeek配置 ────────────────────────────────────────
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
USE_MOCK = False

# ── 合规维度关键词映射 ──────────────────────────────────
DIMENSION_KEYWORDS = {
    "industry_access": {
        "zh": ["行业准入", "市场准入", "资质", "许可证", "经营许可", "外资限制", "准入评估", "行业门槛"],
        "ko": ["업종 진입", "시장 진입", "자격증", "허가증", "외국인 투자 제한", "진입 장벽"],
    },
    "data_security": {
        "zh": ["数据安全", "个人信息", "数据跨境", "数据出境", "隐私", "网络安全", "数据保护", "PIPL", "DSL"],
        "ko": ["데이터 보안", "개인정보", "데이터 역외 이전", "프라이버시", "네트워크 보안", "데이터 보호"],
    },
    "intellectual_property": {
        "zh": ["知识产权", "商标", "专利", "著作权", "版权", "IP", "抢注", "注册在先"],
        "ko": ["지식재산권", "상표", "특허", "저작권", "IP", "선출원주의"],
    },
    "cross_border_tax": {
        "zh": ["跨境财税", "税务", "增值税", "企业所得税", "关税", "转让定价", "税收协定", "利润汇出", "预提税"],
        "ko": ["국경 간 세무", "세금", "부가가치세", "법인세", "관세", "이전 가격", "조세 협약", "원천징수"],
    },
    "labor_employment": {
        "zh": ["劳动用工", "劳动合同", "社保", "五险一金", "员工", "就业", "劳动争议", "外籍员工"],
        "ko": ["노동 고용", "노동 계약", "사회보험", "5대 보험", "직원", "취업", "노동 분쟁"],
    },
    "visa_immigration": {
        "zh": ["签证", "移民", "工作签证", "居留许可", "Z签", "外国人", "就业证", "非法就业"],
        "ko": ["비자", "이민", "취업 비자", "체류 허가", "Z비자", "외국인", "불법 취업"],
    },
    "company_formation": {
        "zh": ["公司设立", "注册公司", "WFOE", "外商独资", "合资", "代表处", "注册资本", "经营范围"],
        "ko": ["회사 설립", "법인 등록", "WFOE", "외국인 독자 기업", "합작 투자", "대표처", "등록 자본"],
    },
    "import_export": {
        "zh": ["进出口", "海关", "报关", "HS编码", "原产地", "关税", "许可证", "FTA"],
        "ko": ["수출입", "세관", "통관", "HS 코드", "원산지", "관세", "FTA"],
    },
}

# ── 模拟模式预定义FAQ回复 ──────────────────────────────
MOCK_FAQ = {
    "industry_access": {
        "zh": {
            "title": "行业准入",
            "answer": "韩国企业进入中国市场，首先需明确目标行业是否属于《外商投资准入特别管理措施（负面清单）》的限制或禁止类行业。\n\n**关键要点：**\n1. **负面清单查询**：不同行业的外资准入要求不同，如教育、医疗、金融等行业有特殊审批要求\n2. **资质许可证**：部分行业需要前置审批（如食品经营许可证、医疗器械注册证等）\n3. **注册资本要求**：某些行业有最低注册资本要求\n4. **股比限制**：部分行业对外资持股比例有限制\n\n**建议行动：**\n- 立即启动中国市场行业准入可行性评估\n- 咨询专业市场准入顾问获取行业定制化准入路线图\n- 参考中韩FTA及中国最新外商投资法规",
        },
        "ko": {
            "title": "업종 진입",
            "answer": "한국 기업이 중국 시장에 진입하려면 먼저 대상 업종이 '외국인 투자 진입 특별 관리 조치(네거티브 리스트)'의 제한 또는 금지 업종에 해당하는지 확인해야 합니다.\n\n**주요 사항:**\n1. **네거티브 리스트 확인**: 업종별 외국인 투자 진입 요건이 다름 (교육, 의료, 금융 등 특별 승인 필요)\n2. **자격증/허가증**: 일부 업종은 사전 승인이 필요 (식품 경영 허가증, 의료기기 등록증 등)\n3. **등록 자본 요건**: 일부 업종에 최저 등록 자본 요건이 있음\n4. **지분 제한**: 일부 업종은 외국인 지분율에 제한이 있음\n\n**권장 조치:**\n- 중국 시장 업종 진입 타당성 평가 즉시 시작\n- 전문 시장 진입 컨설턴트에게 맞춤형 로드맵 문의",
        },
    },
    "data_security": {
        "zh": {
            "title": "数据安全",
            "answer": "数据安全是中国合规监管的重中之重，涉及《数据安全法》《个人信息保护法》《网络安全法》三部核心法律。\n\n**关键要点：**\n1. **数据分类分级**：对企业数据进行梳理和分类分级是第一步\n2. **数据出境安全评估**：向境外提供重要数据或个人信息的，可能需要通过安全评估\n3. **标准合同**：个人信息出境可采用标准合同方式（PIISCC）\n4. **认证机制**：可通过专业机构的数据安全认证\n5. **个人信息保护影响评估（PIPIA）**：处理敏感个人信息或数据出境前需进行评估\n\n**建议行动：**\n- 立即实施数据梳理和分类分级\n- 评估数据出境需求，确定适用路径（安全评估/标准合同/认证）\n- 建立数据安全管理制度",
        },
        "ko": {
            "title": "데이터 보안",
            "answer": "데이터 보안은 중국 규제의 최우선 사항이며, '데이터 안전법', '개인정보보호법', '네트워크 보안법' 세 가지 핵심 법률이 적용됩니다.\n\n**주요 사항:**\n1. **데이터 분류 및 등급화**: 기업 데이터 현황 파악 및 분류가 첫 단계\n2. **데이터 역외 안전 평가**: 중요 데이터 또는 개인정보의 역외 이전 시 안전 평가 필요\n3. **표준 계약**: 개인정보 역외 이전 시 표준 계약 방식 사용 가능\n4. **인증 메커니즘**: 전문 기관의 데이터 보안 인증 취득 가능\n\n**권장 조치:**\n- 데이터 현황 파악 및 분류·등급화 즉시 진행\n- 데이터 역외 이전 경로 결정",
        },
    },
    "intellectual_property": {
        "zh": {
            "title": "知识产权",
            "answer": "中国实行「注册在先」原则，商标和专利被抢注的风险极高。\n\n**关键要点：**\n1. **商标注册**：中国为注册在先原则，建议在进入中国市场前尽早提交核心类别的商标注册申请\n2. **专利保护**：中国发明专利需经过实质审查，周期约2-4年。实用新型和外观设计专利审查较快\n3. **著作权登记**：虽然著作权自创作完成即产生，但登记可提供更有力的证据\n4. **域名保护**：建议同步注册.cn域名\n5. **商业秘密**：通过保密协议和内部管理制度保护\n\n**建议行动：**\n- 立即进行中国商标检索并提交核心类别注册申请\n- 评估是否需要申请中国专利\n- 建立全方位的知识产权保护策略",
        },
        "ko": {
            "title": "지식재산권",
            "answer": "중국은 '선출원주의' 원칙을 채택하여 상표와 특허의 선점 등록 위험이 매우 높습니다.\n\n**주요 사항:**\n1. **상표 등록**: 중국은 선출원주의, 중국 시장 진입 전 핵심 카테고리 상표 등록 출원 필요\n2. **특허 보호**: 중국 발명 특허는 실질 심사 필요 (2-4년 소요)\n3. **저작권 등록**: 창작과 동시에 발생하나 등록 시 더 강력한 증거 확보\n\n**권장 조치:**\n- 즉시 중국 상표 검색 및 핵심 카테고리 등록 출원\n- 중국 특허 출원 필요성 평가",
        },
    },
    "cross_border_tax": {
        "zh": {
            "title": "跨境财税",
            "answer": "跨境财税是韩企进入中国最常见的合规盲区，涉及多个税务层面。\n\n**关键要点：**\n1. **企业所得税**：标准税率25%，高新技术企业可享受15%优惠税率\n2. **增值税**：一般纳税人税率6%/9%/13%（视行业而定），小规模纳税人征收率3%/5%\n3. **中韩税收协定**：避免双重征税，提供股息、利息、特许权使用费的优惠预提税率\n4. **转让定价**：关联交易需符合独立交易原则，准备转让定价同期资料\n5. **利润汇出**：汇出利润需缴纳10%预提所得税（税收协定可降至5%）\n\n**建议行动：**\n- 进行税务健康检查\n- 审查转让定价文档准备情况\n- 合理利用中韩税收协定优惠",
        },
        "ko": {
            "title": "국경 간 세무·재무",
            "answer": "국경 간 세무는 한국 기업이 중국에 진출할 때 가장 흔한 규제 사각지대입니다.\n\n**주요 사항:**\n1. **법인세**: 표준 세율 25%, 하이테크 기업 15% 우대 세율\n2. **부가가치세**: 일반 납세자 6%/9%/13%\n3. **한중 조세 협약**: 이중 과세 방지, 배당/이자/사용료 우대 원천징수 세율\n4. **이전 가격**: 특수관계 거래는 독립 거래 원칙 준수 필요\n\n**권장 조치:**\n- 세무 건강 검진 실시\n- 이전 가격 문서 준비 상태 검토",
        },
    },
    "labor_employment": {
        "zh": {
            "title": "劳动用工",
            "answer": "中国劳动法对韩企有特殊要求，合规用工至关重要。\n\n**关键要点：**\n1. **书面劳动合同**：必须在用工之日起1个月内签订，否则需支付双倍工资\n2. **五险一金**：养老保险、医疗保险、失业保险、工伤保险、生育保险+住房公积金\n3. **试用期**：劳动合同期限3年以上，试用期不超过6个月\n4. **外籍员工**：需办理外国人就业许可证和工作类居留许可\n5. **劳动合同解除**：需严格遵守法定条件和程序\n\n**建议行动：**\n- 进行用工合规审计和劳动合同审查\n- 确保外籍员工持合法工作签证\n- 建立完善的劳动人事管理制度",
        },
        "ko": {
            "title": "노동 고용",
            "answer": "중국 노동법은 한국 기업에 특별한 요구사항이 있습니다.\n\n**주요 사항:**\n1. **서면 노동 계약**: 근무 개시일로부터 1개월 내 체결 필수, 위반 시 2배 임금 지급\n2. **5대 보험 및 주택 공적금**: 의무 가입\n3. **외국인 직원**: 취업 허가증 및 취업류 체류 허가 필요\n\n**권장 조치:**\n- 고용 규제 감사 및 노동 계약 검토\n- 외국인 직원 합법 비자 확인",
        },
    },
    "visa_immigration": {
        "zh": {
            "title": "签证移民",
            "answer": "持商务签证（M签）在中国境内长期工作属于非法就业，面临严重法律后果。\n\n**关键要点：**\n1. **Z字签证**：来华工作的韩国籍员工必须持Z字签证入境\n2. **工作类居留许可**：入境后30日内需申领工作类居留许可（有效期通常1年）\n3. **外国人工作许可证**：由外国专家局颁发\n4. **家属签证**：随行家属可申请S1签证（长期）或S2签证（短期）\n5. **非法就业后果**：罚款（5000-20000元）、拘留（5-15天）、驱逐出境\n\n**建议行动：**\n- 立即咨询签证专家办理一站式工作签证和居留许可服务\n- 检查现有员工的签证状态\n- 建立签证管理制度",
        },
        "ko": {
            "title": "비자·이민",
            "answer": "상용 비자(M비자)로 중국 내 장기 근무는 불법 취업에 해당합니다.\n\n**주요 사항:**\n1. **Z비자**: 중국에서 근무하는 한국인 직원은 반드시 Z비자로 입국\n2. **취업류 체류 허가**: 입국 후 30일 내 신청 (유효기간 보통 1년)\n3. **외국인 취업 허가증**: 외국 전문가국 발급\n4. **불법 취업 제재**: 벌금, 구류, 강제 퇴거\n\n**권장 조치:**\n- 비자 전문가에게 원스톱 취업 비자 서비스 문의\n- 기존 직원 비자 상태 확인",
        },
    },
    "company_formation": {
        "zh": {
            "title": "公司设立",
            "answer": "公司设立是进入中国市场的第一步，也是最关键的决策之一。\n\n**关键要点：**\n1. **公司类型选择**：\n   - **WFOE（外商独资企业）**：大多数韩企首选，100%控股\n   - **JV（合资企业）**：部分受限行业需要中国合作伙伴\n   - **代表处（RO）**：只能从事联络活动，不能直接经营\n2. **注册资本**：2024年新公司法实施后，有限责任公司需在5年内缴足注册资本（认缴制）\n3. **经营范围**：需明确描述，实际经营不得超过经营范围\n4. **注册流程**：名称核准→工商登记→刻章→银行开户→税务登记\n\n**建议行动：**\n- 尽快确定设立方案并启动注册流程\n- 咨询专业公司注册服务机构\n- 新公司法对注册资本认缴期限有重大变化，需注意",
        },
        "ko": {
            "title": "회사 설립",
            "answer": "회사 설립은 중국 시장 진출의 첫걸음이자 가장 중요한 결정 중 하나입니다.\n\n**주요 사항:**\n1. **회사 유형 선택**:\n   - **WFOE(외국인 독자 기업)**: 대부분 한국 기업 선호, 100% 지분 보유\n   - **JV(합작 투자)**: 일부 제한 업종에서 중국 파트너 필요\n   - **대표처(RO)**: 연락 업무만 가능, 직접 영업 불가\n2. **등록 자본**: 2024년 신회사법 시행 후 5년 내 납입 필요\n3. **영업 범위**: 명확히 기재 필요, 실제 영업은 범위 내에서만 가능\n\n**권장 조치:**\n- 설립 방안 신속히 확정\n- 전문 회사 설립 서비스 기관 상담",
        },
    },
    "import_export": {
        "zh": {
            "title": "进出口",
            "answer": "中韩进出口合规涉及复杂的海关申报、HS编码归类等环节。\n\n**关键要点：**\n1. **HS编码归类**：正确归类是合规报关的基础，错误归类可能导致罚款\n2. **中韩FTA原产地证明**：享受关税优惠需提供原产地证书\n3. **进出口许可证**：部分商品需办理进口许可证或出口许可证\n4. **海关申报**：需通过中国国际贸易单一窗口进行电子申报\n5. **关税计算**：关税=完税价格×关税税率（含最惠国税率、协定税率等）\n\n**建议行动：**\n- 委托专业报关行处理进出口业务\n- 进行进出口合规内部培训\n- 建立HS编码管理台账",
        },
        "ko": {
            "title": "수출입",
            "answer": "한중 수출입 규제는 복잡한 세관 신고, HS 코드 분류 등 여러 단계를 포함합니다.\n\n**주요 사항:**\n1. **HS 코드 분류**: 올바른 분류가 규정 준수 통관의 기본\n2. **한중 FTA 원산지 증명**: 관세 혜택을 위해 원산지 증명서 필요\n3. **수출입 허가증**: 일부 상품은 허가증 필요\n4. **세관 신고**: 중국 국제무역 단일 창구를 통한 전자 신고\n\n**권장 조치:**\n- 전문 통관사 위임\n- 수출입 규제 내부 교육 실시",
        },
    },
}

# ── 综合FAQ（不针对特定维度）────────────────────────────
MOCK_GENERAL_FAQ = {
    "zh": {
        "title": "中韩出海数智港合规咨询",
        "answer": "您好！我是中韩出海数智港的AI数字员工合规顾问。我可以帮助您解答关于以下合规维度的问题：\n\n1. 📌 **行业准入** — 中国市场外资准入限制和资质要求\n2. 🔒 **数据安全** — 数据跨境传输和个人信息保护\n3. ⚖️ **知识产权** — 商标、专利、著作权布局和保护\n4. 💰 **跨境财税** — 税务合规、转让定价和中韩税收协定\n5. 👥 **劳动用工** — 劳动合同、社保和外籍员工管理\n6. 🛂 **签证移民** — 工作签证、居留许可和合规用工\n7. 🏢 **公司设立** — WFOE、JV、代表处的选择和注册\n8. 📦 **进出口** — 海关申报、HS编码和中韩FTA原产地证明\n\n请直接输入您的问题，我会为您提供专业的合规建议！如需韩语服务，可直接用韩语提问（한국어로 질문하시면 한국어로 답변해 드립니다）。",
    },
    "ko": {
        "title": "한중 해외 진출 디지털 포트 규제 상담",
        "answer": "안녕하세요! 저는 한중 해외 진출 디지털 포트의 AI 디지털 직원 규제 컨설턴트입니다. 다음 규제 차원에 대한 질문에 답변해 드릴 수 있습니다:\n\n1. 📌 **업종 진입** — 중국 시장 외국인 투자 진입 제한 및 자격 요건\n2. 🔒 **데이터 보안** — 데이터 역외 이전 및 개인정보 보호\n3. ⚖️ **지식재산권** — 상표, 특허, 저작권 포트폴리오 및 보호\n4. 💰 **국경 간 세무** — 세무 규정 준수, 이전 가격, 한중 조세 협약\n5. 👥 **노동 고용** — 노동 계약, 사회보험, 외국인 직원 관리\n6. 🛂 **비자·이민** — 취업 비자, 체류 허가, 합법 고용\n7. 🏢 **회사 설립** — WFOE, JV, 대표처 선택 및 등록\n8. 📦 **수출입** — 세관 신고, HS 코드, 한중 FTA 원산지 증명\n\n질문을 입력하시면 전문적인 규제 조언을 제공해 드립니다! 中文提问也可以获得中文回答。",
    },
}


def detect_language(text: str) -> str:
    """检测用户输入的语言：自动识别中文或韩文"""
    if not text:
        return "zh"

    # 韩文字符范围: AC00-D7AF (韩文音节), 1100-11FF (韩文字母), 3130-318F (韩文兼容字母)
    korean_pattern = re.compile(r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]+')
    korean_chars = korean_pattern.findall(text)
    total_korean = sum(len(chunk) for chunk in korean_chars)

    # 中文字符范围
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    chinese_chars = chinese_pattern.findall(text)
    total_chinese = sum(len(chunk) for chunk in chinese_chars)

    if total_korean > total_chinese and total_korean > 0:
        return "ko"
    return "zh"


def detect_dimension(text: str, language: str = "zh") -> Optional[str]:
    """检测用户问题涉及的合规维度"""
    text_lower = text.lower()
    for dim, keywords in DIMENSION_KEYWORDS.items():
        for kw in keywords.get(language, []):
            if kw.lower() in text_lower:
                return dim
        # 同时也检查另一种语言的关键词
        other_lang = "ko" if language == "zh" else "zh"
        for kw in keywords.get(other_lang, []):
            if kw.lower() in text_lower:
                return dim
    return None


# ── 知识库文档加载 ──────────────────────────────────────

def load_knowledge_docs() -> List[Dict[str, Any]]:
    """加载PRD和合规目录下的所有文档"""
    docs = []
    sources = []

    # 收集所有可能的文档目录
    dirs_to_check = []
    for d in [PRD_DIR, COMPLIANCE_DIR, COMPLIANCE_DIR2, COMPLIANCE_BACKEND_DIR]:
        if d.exists():
            dirs_to_check.append(d)

    # 递归搜索所有.md和.txt文件
    for doc_dir in dirs_to_check:
        if doc_dir.exists():
            for ext in ["*.md", "*.txt"]:
                for fpath in sorted(doc_dir.rglob(ext)):
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="replace")
                        # 只取非空文件
                        if content.strip():
                            rel_path = str(fpath.relative_to(PROJECT_ROOT))
                            docs.append({
                                "path": rel_path,
                                "filename": fpath.name,
                                "content": content,
                                "dir": doc_dir.name,
                            })
                            sources.append(rel_path)
                    except Exception as e:
                        print(f"  ⚠ 加载文档失败 {fpath}: {e}")

    if sources:
        print(f"  📚 已加载 {len(sources)} 个知识库文档:")
        for s in sources[:10]:
            print(f"     - {s}")
        if len(sources) > 10:
            print(f"     ... 及其他 {len(sources)-10} 个文件")
    else:
        print("  📚 知识库文档目录未找到，将仅使用FAQ回复")

    return docs


def search_relevant_context(query: str, docs: List[Dict], dimension: Optional[str] = None, max_chars: int = 3000) -> str:
    """从知识图谱+知识库混合检索（知识图谱结构化条款优先，MD文档补充）"""
    result_parts = []

    # 方法1: 知识图谱结构化检索（优先）
    try:
        articles = search_articles(query[:50], "zh")
        for a in articles[:5]:
            title = a.get("title", "") or a.get("title_ko", "法规条款")
            number = a.get("article_number", "") or a.get("article_number_ko", "")
            reg = a.get("regulation", "中国相关法规")
            summary = a.get("summary", "") or a.get("summary_ko", "") or ""
            entry = "[法规条款] " + title + " (" + reg + ")"
            if number:
                entry += " 第" + number + "条"
            entry += "\n" + summary[:600]
            reqs = a.get("requirements", [])
            if reqs:
                entry += "\n合规义务:\n" + "\n".join("- " + r[:100] for r in reqs[:3])
            result_parts.append(entry)
    except Exception as e:
        print(f"KG检索错误: {e}")

    # 方法2: MD知识库关键词检索（补充）
    if docs:
        import hashlib
        query_words = set(query.lower().split())
        seen = set()
        for doc in docs:
            paras = [p.strip() for p in doc["content"].split("\n\n") if len(p.strip()) > 30]
            for para in paras:
                score = sum(1 for w in query_words if len(w) > 1 and w in para.lower())
                h = hashlib.md5(para[:100].encode()).hexdigest()[:8]
                if score >= 3 and h not in seen:
                    seen.add(h)
                    result_parts.append("[知识库参考]\n" + para[:800])
                    break

    if not result_parts and dimension:
        dim_label = dimension
        if dimension in DIMENSION_KEYWORDS:
            kw = DIMENSION_KEYWORDS[dimension].get("zh", [])
            if kw:
                dim_label = kw[0]
        result_parts.append("[" + dim_label + "] 请咨询专业合规顾问获取定制化建议。")

    return "\n\n---\n\n".join(result_parts[:5])


def get_mock_reply(user_message: str, language: str) -> Dict[str, Any]:
    """模拟模式下，基于预定义的合规FAQ回复"""
    dimension = detect_dimension(user_message, language)

    if dimension and dimension in MOCK_FAQ:
        faq = MOCK_FAQ[dimension][language]
        return {
            "reply": faq["answer"],
            "dimension": dimension,
            "dimension_label": faq["title"],
            "source": "mock_faq",
        }

    # 未命中的维度，回复综合介绍
    general = MOCK_GENERAL_FAQ[language]
    return {
        "reply": general["answer"],
        "dimension": None,
        "dimension_label": general["title"],
        "source": "mock_faq_general",
    }


def get_ai_reply(user_message: str, language: str, context: str = "") -> Dict[str, Any]:
    """调用DeepSeek API获取回复"""
    from openai import OpenAI

    dimension = detect_dimension(user_message, language)
    dim_label = ""
    if dimension and dimension in DIMENSION_KEYWORDS:
        dim_label = DIMENSION_KEYWORDS[dimension][language][0] if DIMENSION_KEYWORDS[dimension][language] else dimension

        system_prompt = f"""你是中韩出海数智港的AI合规顾问，专业提供中国市场合规咨询。

【核心能力】
1. 覆盖20+合规维度：行业准入、数据安全、知识产权、跨境财税、劳动用工、签证移民、公司设立、进出口、环评、食品药品、广告、电商、金融等
2. 中韩双语回应：中文提问中文答，韩语提问韩语答
3. 法规依据：严格基于知识图谱中的中国现行法规条款回答

【回答四原则】
1. 引用标注：每条建议标注所依据的法规名称
2. 置信度三级标注：
   - 确定(有明确法规依据)
   - 建议(基于行业经验)
   - 待确认(信息不足，会追问)
3. 行动导向：每条建议附带可执行的下步动作
4. 保守专业：不确定绝不编造

当前检测维度：{dim_label or '综合咨询'}
用户语言：{'한국어' if language == 'ko' else '中文'}
"""

    # 如果有知识库上下文，加入
    if context:
        system_prompt += f"\n\n【知识库参考片段】\n以下是从项目文档中检索到的相关参考信息：\n\n{context}\n\n请注意：以上信息仅供参考，请结合你的专业知识进行回答。"

    try:
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )

        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=2000,
        )

        reply = response.choices[0].message.content.strip()

        return {
            "reply": reply,
            "dimension": dimension,
            "dimension_label": dim_label,
            "source": "deepseek_api",
        }

    except Exception as e:
        error_msg = str(e)
        print(f"  ⚠ DeepSeek API调用失败: {error_msg}")

        # 如果API调用失败，降级到模拟模式
        fallback = get_mock_reply(user_message, language)
        fallback["source"] = "mock_fallback"
        fallback["error"] = error_msg
        return fallback


def chat_send(user_message: str) -> Dict[str, Any]:
    """
    主入口：处理用户消息，返回AI回复

    Args:
        user_message: 用户输入的消息文本

    Returns:
        dict: {
            "reply": str,           # AI回复内容
            "dimension": str|None,  # 检测到的合规维度
            "dimension_label": str, # 维度中文/韩文名称
            "source": str,          # 回复来源(mock_faq/deepseek_api/mock_fallback)
            "language": str,        # 检测到的语言(zh/ko)
        }
    """
    # 1. 检测语言
    language = detect_language(user_message)
    print(f"  🌐 检测语言: {language}")

    # 2. 检测合规维度
    dimension = detect_dimension(user_message, language)
    print(f"  📌 检测维度: {dimension or '综合咨询'}")

    # 3. 加载知识库文档（懒加载）
    if not hasattr(chat_send, "_docs_loaded"):
        chat_send._docs_loaded = True
        chat_send._kb_docs = load_knowledge_docs()

    docs = getattr(chat_send, "_kb_docs", [])

    # 4. 搜索相关上下文
    context = search_relevant_context(user_message, docs, dimension)

    # 5. 获取回复
    if USE_MOCK:
        print("  🤖 使用模拟模式（无API Key）")
        result = get_mock_reply(user_message, language)
    else:
        print("  🤖 调用DeepSeek API")
        result = get_ai_reply(user_message, language, context)

    result["language"] = language
    return result


# ── 测试入口 ────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  中韩出海数智港 - AI数字员工对话引擎")
    print("=" * 60)
    print(f"  API Key: {'已配置' if DEEPSEEK_API_KEY else '未配置（模拟模式）'}")
    print(f"  知识库: {PRD_DIR}")
    print()

    # 测试中文
    test_queries = [
        "我想了解韩国企业进入中国市场的行业准入要求",
        "数据跨境传输需要什么条件？",
        "회사 설립 절차에 대해 알려주세요",
        "중국에서 상표 등록하는 방법",
    ]

    for query in test_queries:
        print(f"\n{'─' * 60}")
        print(f"用户: {query}")
        print(f"{'─' * 60}")
        result = chat_send(query)
        print(f"\nAI [{result['source']}]:")
        print(result["reply"][:500])
        if len(result["reply"]) > 500:
            print("... (篇幅限制)")
        print()
