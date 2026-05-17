"""
中韩出海数智港 - AI数字员工对话API路由

API端点:
  POST /api/chat/send    — 发送消息，返回AI回复
  GET  /api/chat/history — 获取历史记录
  POST /api/chat/clear   — 清除对话
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from backend.database import get_db
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from knowledge_graph import get_db as kg_get_db, search_articles, get_articles_by_dimension
from backend.ai_dialogue import chat_send

router = APIRouter(prefix="/api/chat", tags=["ai-dialogue"])


# ── Pydantic 模型 ──────────────────────────────────────

class ChatSendRequest(BaseModel):
    message: str


class ChatMessage(BaseModel):
    id: int
    role: str  # "user" or "assistant"
    content: str
    dimension: Optional[str] = None
    dimension_label: Optional[str] = None
    source: Optional[str] = None
    created_at: str


class ChatSendResponse(BaseModel):
    success: bool = True
    reply: str
    dimension: Optional[str] = None
    dimension_label: Optional[str] = None
    source: str
    language: str


class ChatHistoryResponse(BaseModel):
    success: bool = True
    messages: List[ChatMessage] = []
    total: int = 0


class ChatClearResponse(BaseModel):
    success: bool = True
    message: str = "对话已清除"


# ── 辅助函数 ──────────────────────────────────────────

def _init_chat_table():
    """确保 chat_history 表存在"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            dimension TEXT,
            dimension_label TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def _save_message(role: str, content: str, dimension: Optional[str] = None,
                  dimension_label: Optional[str] = None, source: Optional[str] = None):
    """保存消息到数据库"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO chat_history (role, content, dimension, dimension_label, source)
           VALUES (?, ?, ?, ?, ?)""",
        (role, content, dimension, dimension_label, source),
    )
    conn.commit()
    message_id = cursor.lastrowid
    conn.close()
    return message_id


# ── API端点 ─────────────────────────────────────────────

@router.post("/send", response_model=ChatSendResponse)
async def chat_send_endpoint(request: ChatSendRequest):
    """发送消息到AI数字员工，获取合规问答回复"""
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    user_message = request.message.strip()

    # 1. 保存用户消息
    _init_chat_table()
    _save_message("user", user_message)

    # 2. 调用AI引擎
    try:
        result = chat_send(user_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI处理失败: {str(e)}")

    # 3. 保存AI回复
    _save_message(
        role="assistant",
        content=result["reply"],
        dimension=result.get("dimension"),
        dimension_label=result.get("dimension_label"),
        source=result.get("source"),
    )

    return ChatSendResponse(
        reply=result["reply"],
        dimension=result.get("dimension"),
        dimension_label=result.get("dimension_label"),
        source=result.get("source", "mock_faq"),
        language=result.get("language", "zh"),
    )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(limit: int = 50, offset: int = 0):
    """获取对话历史记录"""
    _init_chat_table()
    conn = get_db()
    cursor = conn.cursor()

    # 查询总数
    cursor.execute("SELECT COUNT(*) FROM chat_history")
    total = cursor.fetchone()[0]

    # 查询消息列表（按时间倒序，前端正序展示）
    cursor.execute(
        """SELECT id, role, content, dimension, dimension_label, source,
                  COALESCE(created_at, '') as created_at
           FROM chat_history
           ORDER BY id DESC
           LIMIT ? OFFSET ?""",
        (limit, offset),
    )
    rows = cursor.fetchall()
    messages = []
    for row in rows:
        messages.append(ChatMessage(
            id=row["id"],
            role=row["role"],
            content=row["content"],
            dimension=row["dimension"],
            dimension_label=row["dimension_label"],
            source=row["source"],
            created_at=row["created_at"],
        ))

    # 降序排列 -> 升序排列（前端展示需要）
    messages.reverse()

    conn.close()
    return ChatHistoryResponse(messages=messages, total=total)


# ── 韩语AI智能客服 ─────────────────────────────────────
#
# 韩国企业常见问题（关税/物流/合规/支付/电商/营销/法务/公司设立）
KR_FAQ = [
    {
        "question": "중국 시장에 진출하려면 어떤 절차가 필요한가요?",
        "answer": "중국 시장 진출 절차는 다음과 같습니다:\n\n1️⃣ **사업 유형 선택**\n   - WFOE(외국인 독자 기업): 대부분의 한국 기업이 선택하는 방식\n   - 합작 투자(JV): 일부 규제 산업에서 필요\n   - 대표 사무소(RO): 직접 영업 불가, 연락 업무만 가능\n\n2️⃣ **회사 등록 절차**\n   - 상호 승인 → 공상 등록 → 도장 제작 → 은행 계좌 개설 → 세무 등록\n   - 소요 기간: 약 2~3개월\n   - 필요 서류: 사업 계획서, 투자자 신분 증명, 임대 계약서 등\n\n3️⃣ **등록 자본**\n   - 2024년 신회사법 시행으로 5년 내 납입 완료 필요\n   - 업종별 최저 등록 자본 요건 상이\n\n💡 **전문가 조언**: 중국 시장 진입 전 반드시 업종별 시장 진입 타당성 평가를 진행하세요."
    },
    {
        "question": "한국 기업의 관세 및 통관 절차는 어떻게 되나요?",
        "answer": "한국 기업의 중국 관세·통관 핵심 사항:\n\n1️⃣ **HS 코드 분류**\n   - 정확한 HS 코드 분류가 통관의 기본\n   - 오분류 시 벌금 및 통관 지연 발생\n\n2️⃣ **한중 FTA 활용**\n   - 한중 FTA 원산지 증명서 제출 시 관세 혜택\n   - 품목별 협정 세율 확인 필수\n\n3️⃣ **필요 서류**\n   - 상업 송장, 선하 증권(B/L), 포장 명세서\n   - 원산지 증명서, 수입 허가증(해당 품목)\n\n4️⃣ **관세 계산**\n   - 관세 = 과세 가격 × 관세율\n   - 부가가치세 13% 별도\n   - 일부 품목은 소비세 추가\n\n5️⃣ **통관 시간**\n   - 일반 통관: 1~3일\n   - 검사 대상: 5~7일\n\n⚠️ **주의**: 최근 중국 세관의 검사 강화로 서류 준비에 각별히 주의하세요."
    },
    {
        "question": "중국에서 상표 등록하는 방법을 알려주세요.",
        "answer": "중국 상표 등록 가이드:\n\n1️⃣ **중국은 선출원주의**\n   - 먼저 출원하는 사람이 권리를 가짐\n   - 한국에서 사용 중인 브랜드도 중국에서 선점 등록 위험\n   - 반드시 중국 시장 진출 전에 상표 등록 완료 권장\n\n2️⃣ **등록 절차**\n   - 상표 검색 → 출원(CNIPA) → 심사(약 6~9개월) → 등록\n   - 이의 신청 기간: 3개월\n   - 총 소요 기간: 약 12~18개월\n\n3️⃣ **필요 서류**\n   - 상표 도안(JPEG), 상품/서비스 목록\n   - 출원인 신분 증명서\n   - 위임장\n\n4️⃣ **비용**\n   - 공식 출원 비용: 약 300~500위안/클래스\n   - 변리사 수수료 별도\n\n5️⃣ **전략적 조언**\n   - 핵심 클래스(한국 기업은 보통 3, 5, 9, 25, 29, 30, 35, 43类) 우선 출원\n   - 한자+영문+한글 복합 출원 권장\n\n🔔 **중요**: 중국에서의 상표권 침해는 한국보다 제재가 강력하므로 사전 보호가 필수입니다."
    },
    {
        "question": "중국 내 한국 기업의 물류 및 배송 전략은?",
        "answer": "중국 내 물류·배송 전략:\n\n1️⃣ **창고 전략**\n   - 중국 내 창고(FTZ 보세 창고 활용 권장)\n   - 주요 거점: 상하이, 광저우, 칭다오, 톈진\n   - 한국-중국 간 물류는 인천-칭다오/인천-웨이하이 노선 인기\n\n2️⃣ **라스트마일 배송**\n   - 주요 협력사: SF Express(顺丰), JD Logistics, Cainiao\n   - 도시 내 당일/익일 배송 가능\n   - 3~4선 도시는 2~3일 소요\n\n3️⃣ **크로스보더 이커머스 물류**\n   - B2C: 해외 직구 모델(9610/1210 방식)\n   - B2B: 일반 무역 통관\n   - 보세 직발송 모델 활용 시 관세 혜택\n\n4️⃣ **비용 최적화**\n   - 물량 기반 운임 협상\n   - 복수 물류사 비교 견적\n   - 시즌별 물동량 변동 고려\n\n📊 **추천**: 초기에는 제3자 물류(3PL) 활용 후 물량 증가 시 자체 물류망 구축 고려."
    },
    {
        "question": "중국 전자상거래 플랫폼에 입점하려면?",
        "answer": "중국 이커머스 플랫폼 입점 가이드:\n\n1️⃣ **주요 플랫폼**\n   - 🏆 **티몰(Tmall, 天猫)**: 프리미엄 브랜드, 한국 브랜드 인기 높음\n   - 🏆 **징둥(JD.com, 京东)**: 전자제품/가전 강세\n   - 🏆 **도우인(Douyin, 抖音)**: 라이브 커머스 중심\n   - 🏆 **샤오홍슈( Xiaohongshu, 小红书)**: 뷰티/패션/라이프스타일\n   - 🏆 **핀둬둬(Pinduoduo, 拼多多)**: 가성비 중심\n\n2️⃣ **입점 조건**\n   - 중국 내 법인 필수(외국 기업 직입점 제한 있음)\n   - 브랜드 상표 등록증(중국 등록 필수)\n   - 식품/화장품: 중국 현지 허가증 필수\n   - 보증금: 티몰 기준 5~15만 위안\n\n3️⃣ **성공 전략**\n   - 한국적 스토리텔링과 한류 콘텐츠 활용\n   - KOL(키오피) 마케팅 병행\n   - 중국 소비자 트렌드 분석 필수\n   - 프로모션 캘린더(광군제 등) 맞춤 전략\n\n💡 **초보자 팁**: 티몰 글로벌(Tmall Global)을 통해 한국 법인 상태로도 입점 가능합니다."
    },
    {
        "question": "한국 기업의 중국 진출 시 주요 법적 리스크는?",
        "answer": "한국 기업 중국 진출 시 주요 법적 리스크:\n\n1️⃣ **⚠️ 지식재산권 리스크**\n   - 상표/특허 선점 등록(타인이 먼저 등록)\n   - 위조품 유통 문제\n   - 영업 비밀 유출 위험\n\n2️⃣ **⚠️ 데이터 규제 리스크**\n   - 개인정보보호법(PIPL) 위반 시 과징금 최대 연매출 5%\n   - 데이터 역외 이전 규제\n   - 네트워크 보안 심사\n\n3️⃣ **⚠️ 노동법 리스크**\n   - 근로 계약 미체결 시 최대 11개월 임금 2배 지급\n   - 사회보험 미가입 시 제재\n   - 외국인 직원 불법 취업 문제\n\n4️⃣ **⚠️ 세무 리스크**\n   - 이전 가격 과세 위험\n   - 이중 과세 문제\n   - 허위 신고 시 높은 과태료\n\n5️⃣ **⚠️ 계약 리스크**\n   - 중국어 계약서 우선(영문/한글 계약은 보조적 효력)\n   - 분쟁 해결 조항(중국 중재 vs 국제 중재 선택)\n   - 담보 설정의 어려움\n\n🛡️ **권장 조치**: 중국 전문 변호사 상담 후 법률 실사(due diligence) 필수 진행"
    },
    {
        "question": "중국 내 결제 시스템 및 환전 방법은?",
        "answer": "중국 결제 시스템 및 환전 안내:\n\n1️⃣ **주요 결제 방식**\n   - **위챗페이(WeChat Pay, 微信支付)**: 시장 점유율 1위\n   - **알리페이(Alipay, 支付宝)**: 2위, 글로벌 사용 가능\n   - **은행 카드**: UnionPay(银联) 필수\n   - **QR 코드 결제**: 중국 전역 보편화\n\n2️⃣ **외국인 결제**\n   - 해외 신용카드: 대형 호텔/백화점만 가능\n   - 위챗페이/알리페이 외국인 계정 개설 가능\n   - 한국 카드: 일부 가맹점에서 가능(제한적)\n\n3️⃣ **환전 방법**\n   - 은행 환전: 1인당 연간 5만 달러 한도\n   - 사기업: 수익금 위안화 → 달러 환전 시 세무서 신고 필요\n   - 음성적 환전소(지하 환전) 절대 금지\n\n4️⃣ **B2B 결제**\n   - 은행 송금(TT) 일반적\n   - 신용장(L/C): 대규모 거래에 활용\n   - 알리바바의 무역 보증 서비스 활용 가능\n\n💰 **팁**: 한국 기업의 위안화 수익금 해외 송금 시 세무 신고 및 외환 관리 규정을 반드시 확인하세요."
    },
    {
        "question": "중국 시장에서의 디지털 마케팅 전략은?",
        "answer": "중국 디지털 마케팅 전략:\n\n1️⃣ **중국 주요 SNS 플랫폼**\n   - **위챗(微信, WeChat)**: OA(공식 계정) + 미니 프로그램 운영 필수\n   - **웨이보(微博, Weibo)**: 브랜드 홍보 및 KOL 협업\n   - **도우인(抖音, Douyin)**: 숏폼 콘텐츠 + 라이브 커머스\n   - **샤오홍슈(小红书, Xiaohongshu)**: 한국 브랜드 필수 채널\n   - **빌리빌리(Bilibili, B站)**: MZ세대 타겟팅\n\n2️⃣ **한국 브랜드 성공 사례**\n   - K-뷰티: 한국 화장품의 중국 SNS 바이럴 전략\n   - K-푸드: 한국 식품의 중국 취향 현지화\n   - K-패션: 한국 스타일의 중국 내 유행 선도\n\n3️⃣ **KOL/인플루언서 마케팅**\n   - 중국 KOL 등급: 超级头部(1000만+) > 头部(100만+) > 腰部(10만+) > 尾部\n   - 한국 브랜드는 腰部 KOL과의 협업 효율 높음\n   - 라이브 커머스: 중국 소비자 구매 결정의 60% 영향\n\n4️⃣ **콘텐츠 전략**\n   - 한중 문화 교류 콘텐츠\n   - 제품 제조 과정 공개(신뢰도 향상)\n   - 중국 소비자 리뷰 및 사용 후기 활용\n\n📈 **핵심 지표(KPI)**: 노출수, 클릭률(CTR), 전환율, 고객 획득 비용(CAC), 고객 생애 가치(LTV)"
    },
]


class KRChatRequest(BaseModel):
    message: str


class KRChatResponse(BaseModel):
    success: bool = True
    reply: str
    source: str = "deepseek_api"
    language: str = "ko"


def _call_deepseek_ko(user_message: str) -> str:
    """调用DeepSeek API获取韩语回复"""
    import urllib.request
    import json as _json
    import base64

    api_key_b64 = "c2stNDY2YTFlOTFiMjEwNGY4ZWE3ODNjZjg3OTQ1MDRkNWM="
    try:
        api_key = base64.b64decode(api_key_b64).decode("utf-8")
    except Exception:
        api_key = ""

    if not api_key:
        return get_kr_faq_reply(user_message)

    system_prompt = (
        "당신은 한중 해역 디지털 포트의 한국어 고객센터 어시스턴트입니다. "
        "한국 기업의 중국 시장 진출에 관한 질문에 전문적이고 구체적으로 답변합니다. "
        "항상 한국어로 답변하며, 실용적인 정보와 실행 가능한 조언을 제공합니다. "
        "관세, 통관, 물류, 상표권, 법률 리스크, 이커머스, 결제 시스템, "
        "디지털 마케팅, 회사 설립 등 중국 비즈니스 전반에 대해 도움을 드립니다. "
        "답변은 간결하면서도 핵심을 전달하고, 필요한 경우 bullet point를 활용하세요."
    )

    payload = _json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read().decode("utf-8"))
            reply = result["choices"][0]["message"]["content"]
            return reply
    except Exception as e:
        print(f"  ⚠ DeepSeek API(KO) 호출 실패: {e}")
        return get_kr_faq_reply(user_message)


def get_kr_faq_reply(user_message: str) -> str:
    """根据韩国企业常见问题FAQ返回匹配的回复"""
    msg_lower = user_message.lower()

    # 尝试FAQ精确匹配
    for faq in KR_FAQ:
        # 检查用户消息是否包含FAQ问题关键词
        q_words = faq["question"].lower().replace("?", "").split()
        match_count = sum(1 for w in q_words if len(w) > 1 and w in msg_lower)
        if match_count >= 3:
            return faq["answer"]

    # 模糊匹配
    keywords_map = [
        (["관세", "통관", "세관", "hs", "수입", "수출"], "한국 기업의 관세 및 통관 절차는 어떻게 되나요?"),
        (["상표", "특허", "지식재산", "등록", "브랜드", "ip"], "중국에서 상표 등록하는 방법을 알려주세요."),
        (["물류", "배송", "창고", "택배", "운송"], "중국 내 한국 기업의 물류 및 배송 전략은?"),
        (["이커머스", "전자상거래", "티몰", "징둥", "플랫폼", "입점", "온라인"], "중국 전자상거래 플랫폼에 입점하려면?"),
        (["법률", "리스크", "규제", "법적", "계약", "분쟁"], "한국 기업의 중국 진출 시 주요 법적 리스크는?"),
        (["결제", "환전", "송금", "은행", "위안", "외환"], "중국 내 결제 시스템 및 환전 방법은?"),
        (["마케팅", "광고", "sns", "소셜", "kpi", "콘텐츠"], "중국 시장에서의 디지털 마케팅 전략은?"),
        (["회사", "설립", "등록", "wfoe", "진출", "절차"], "중국 시장에 진출하려면 어떤 절차가 필요한가요?"),
    ]

    for keywords, faq_question in keywords_map:
        if any(kw in msg_lower for kw in keywords):
            for faq in KR_FAQ:
                if faq["question"] == faq_question:
                    return faq["answer"]

    # 默认回复
    return (
        "안녕하세요! 한중 해역 디지털 포트의 AI 고객센터입니다. 😊\n\n"
        "한국 기업의 중국 시장 진출에 관한 다양한 정보를 제공해 드립니다.\n\n"
        "📌 **주요 상담 분야**\n"
        "• 🇨🇳 중국 시장 진출 절차 및 회사 설립\n"
        "• 📦 관세, 통관 및 물류 전략\n"
        "• ™️ 상표 등록 및 지식재산권 보호\n"
        "• 🛒 전자상거래 플랫폼 입점\n"
        "• ⚖️ 법률 리스크 관리\n"
        "• 💳 결제 시스템 및 환전\n"
        "• 📱 디지털 마케팅 전략\n\n"
        "궁금하신 점을 구체적으로 질문해 주시면 더 자세히 안내해 드리겠습니다! 💪"
    )


@router.post("/ko", response_model=KRChatResponse)
async def chat_ko_endpoint(request: KRChatRequest):
    """韩语AI智能客服 - 韩国企业进入中国市场的智能问答"""
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="메시지 내용을 입력해 주세요.")

    user_message = request.message.strip()
    print(f"  🇰🇷 韩语AI客服收到: {user_message[:100]}")

    # 调用DeepSeek API（带FAQ降级）
    try:
        reply = _call_deepseek_ko(user_message)
    except Exception as e:
        print(f"  ⚠ 韩语AI客服错误: {e}")
        reply = get_kr_faq_reply(user_message)

    return KRChatResponse(
        reply=reply,
        source="deepseek_api",
        language="ko",
    )


@router.post("/clear", response_model=ChatClearResponse)
async def clear_chat_history():
    """清除对话历史"""
    _init_chat_table()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history")
    conn.commit()
    conn.close()
    return ChatClearResponse(message="对话已清除")
