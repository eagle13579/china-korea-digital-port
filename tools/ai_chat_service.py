#!/usr/bin/env python3
"""
AI 客服聊天服务 — AI Chat Service
====================================
独立 Flask 服务，提供 AI 客服对话 API。

API 端点：
  - POST /api/chat  输入 {message, language(zh/ko/en)} → {reply}
  - GET  /health     健康检查

端口：5198

依赖：
  pip install flask flask-cors python-dotenv openai

用法：
  python3 tools/ai_chat_service.py           # 前台运行
  python3 tools/ai_chat_service.py --port 5199  # 自定义端口
"""

import os
import sys
import json
import re
import logging
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# ── 路径设置 ──────────────────────────────────────────────
# 项目根目录（此文件在 tools/ 下，父目录为项目根）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 加载 .env（从项目根目录）
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# ── DeepSeek 配置 ────────────────────────────────────────
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
USE_MOCK = not bool(DEEPSEEK_API_KEY)

# ── 日志 ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ai_chat_service")

# ═══════════════════════════════════════════════════════════════
# 模拟模式回复（三语）
# ═══════════════════════════════════════════════════════════════

MOCK_REPLIES = {
    "zh": {
        "welcome": "您好！我是中韩出海数智港的AI客服助手。我可以为您提供关于中韩贸易合规、市场准入、公司设立等方面的专业咨询。请随时提问！",
        "fallback": "感谢您的咨询！作为AI客服助手，我可以帮助您解答以下方面的问题：\n\n1. 📌 **行业准入** — 中国市场外资准入限制和资质要求\n2. 🔒 **数据安全** — 数据跨境传输和个人信息保护\n3. ⚖️ **知识产权** — 商标、专利、著作权布局和保护\n4. 💰 **跨境财税** — 税务合规、转让定价和中韩税收协定\n5. 👥 **劳动用工** — 劳动合同、社保和外籍员工管理\n6. 🛂 **签证移民** — 工作签证、居留许可和合规用工\n7. 🏢 **公司设立** — WFOE、JV、代表处的选择和注册\n8. 📦 **进出口** — 海关申报、HS编码和中韩FTA原产地证明\n\n请直接输入您的问题，我会为您提供专业的建议！(模拟回复)",
        "greeting": ["你好", "您好", "嗨", "hello", "hi", "在吗", "在不在"],
        "greeting_reply": "您好！欢迎来到中韩出海数智港！我是您的AI客服助手，有什么可以帮您的吗？(模拟回复)",
    },
    "ko": {
        "welcome": "안녕하세요! 저는 한중 해외 진출 디지털 포트의 AI 고객 서비스 어시스턴트입니다. 한중 무역 규제, 시장 진입, 회사 설립 등에 관한 전문적인 상담을 제공해 드립니다. 언제든지 질문해 주세요!",
        "fallback": "문의해 주셔서 감사합니다! AI 고객 서비스 어시스턴트로서 다음 분야에 대해 도움을 드릴 수 있습니다:\n\n1. 📌 **업종 진입** — 중국 시장 외국인 투자 진입 제한\n2. 🔒 **데이터 보안** — 데이터 역외 이전 및 개인정보 보호\n3. ⚖️ **지식재산권** — 상표, 특허, 저작권 보호\n4. 💰 **국경 간 세무** — 세무 규정 준수, 한중 조세 협약\n5. 👥 **노동 고용** — 노동 계약, 사회보험, 외국인 직원 관리\n6. 🛂 **비자·이민** — 취업 비자, 체류 허가\n7. 🏢 **회사 설립** — WFOE, JV, 대표처 선택 및 등록\n8. 📦 **수출입** — 세관 신고, HS 코드, 한중 FTA\n\n질문을 입력하시면 전문적인 조언을 제공해 드립니다! (모의 응답)",
        "greeting": ["안녕", "안녕하세요", "여보세요", "hello", "hi"],
        "greeting_reply": "안녕하세요! 한중 해외 진출 디지털 포트에 오신 것을 환영합니다! AI 고객 서비스 어시스턴트입니다. 무엇을 도와드릴까요? (모의 응답)",
    },
    "en": {
        "welcome": "Hello! I'm the AI Customer Service Assistant of China-Korea Digital Port. I can provide professional consultation on China-Korea trade compliance, market access, company formation, and more. Feel free to ask!",
        "fallback": "Thank you for your inquiry! As an AI customer service assistant, I can help with the following areas:\n\n1. 📌 **Industry Access** — Foreign investment restrictions in China\n2. 🔒 **Data Security** — Cross-border data transfer & privacy protection\n3. ⚖️ **Intellectual Property** — Trademark, patent, copyright protection\n4. 💰 **Cross-border Tax** — Tax compliance, transfer pricing, China-Korea tax treaty\n5. 👥 **Labor & Employment** — Employment contracts, social insurance\n6. 🛂 **Visa & Immigration** — Work visa, residence permit\n7. 🏢 **Company Formation** — WFOE, JV, Representative Office\n8. 📦 **Import & Export** — Customs declaration, HS codes, China-Korea FTA\n\nPlease enter your question and I'll provide professional advice! (Simulated reply)",
        "greeting": ["hello", "hi", "hey", "greetings", "hi there"],
        "greeting_reply": "Hello! Welcome to China-Korea Digital Port! I'm your AI customer service assistant. How can I help you today? (Simulated reply)",
    },
}


# ═══════════════════════════════════════════════════════════════
# AI 回复逻辑
# ═══════════════════════════════════════════════════════════════

def get_mock_reply(message: str, language: str) -> Dict[str, Any]:
    """模拟模式下生成回复"""
    lang_data = MOCK_REPLIES.get(language, MOCK_REPLIES["zh"])

    # 检查问候语
    msg_lower = message.lower().strip()
    for g in lang_data.get("greeting", []):
        if g in msg_lower or msg_lower == g:
            return {"reply": lang_data["greeting_reply"]}

    # 对其他消息返回综合介绍
    return {"reply": lang_data["fallback"]}


def get_ai_reply(message: str, language: str) -> Dict[str, Any]:
    """调用 DeepSeek API 获取回复"""
    from openai import OpenAI

    lang_name_map = {
        "zh": "中文",
        "ko": "한국어",
        "en": "English",
    }
    lang_name = lang_name_map.get(language, "中文")
    system_lang_instruction = {
        "zh": "请用中文回答。你是中韩出海数智港的AI客服助手，专业、热情、有条理。",
        "ko": "한국어로 답변해주세요. 당신은 한중 해외 진출 디지털 포트의 AI 고객 서비스 어시스턴트입니다. 전문적이고 친절하며 체계적으로 답변해주세요.",
        "en": "Please reply in English. You are the AI customer service assistant of China-Korea Digital Port. Be professional, friendly, and well-structured.",
    }

    system_prompt = f"""{system_lang_instruction.get(language, system_lang_instruction["zh"])}

【核心能力】
1. 中韩贸易合规咨询：行业准入、数据安全、知识产权、跨境财税、劳动用工、签证移民、公司设立、进出口
2. 回答基于中国现行法律法规和中韩FTA相关政策
3. 不确定的事项明确说明，不编造法规条款

【回答风格】
- 清晰结构化：使用小标题、要点列表
- 行动导向：每条建议附带可执行的下步行动
- 友好专业：保持热情专业的客服口吻"""

    try:
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )

        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.5,
            max_tokens=1500,
        )

        reply = response.choices[0].message.content.strip()
        return {"reply": reply}

    except Exception as e:
        logger.warning(f"DeepSeek API 调用失败: {e}")
        fallback = get_mock_reply(message, language)
        fallback["reply"] += "\n\n⚠️ (API 临时不可用，已切换为模拟回复)"
        return fallback


def get_chat_reply(message: str, language: str) -> Dict[str, Any]:
    """主入口：处理用户消息，返回AI回复"""
    logger.info(f"收到请求: lang={language}, msg={message[:50]}...")

    if USE_MOCK:
        logger.info("使用模拟模式")
        reply = get_mock_reply(message, language)
        reply["reply"] += "\n\n[模拟回复]"
        return reply

    logger.info("调用 DeepSeek API")
    return get_ai_reply(message, language)


# ═══════════════════════════════════════════════════════════════
# Flask 应用
# ═══════════════════════════════════════════════════════════════

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


@app.route("/health", methods=["GET"])
def health_check():
    """健康检查端点"""
    return jsonify({
        "status": "ok",
        "service": "ai-chat-service",
        "version": "1.0.0",
        "mode": "mock" if USE_MOCK else "deepseek",
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """聊天 API 端点

    请求体:
        {
            "message": str,       # 用户消息
            "language": str       # "zh" | "ko" | "en"
        }

    响应:
        {
            "reply": str          # AI 回复内容
        }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体必须为 JSON 格式"}), 400

    message = data.get("message", "").strip()
    language = data.get("language", "zh").strip().lower()

    if not message:
        return jsonify({"error": "message 字段不能为空"}), 400

    if language not in ("zh", "ko", "en"):
        language = "zh"

    try:
        result = get_chat_reply(message, language)
        return jsonify(result)
    except Exception as e:
        logger.exception("处理消息时出错")
        return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "服务器内部错误"}), 500


# ═══════════════════════════════════════════════════════════════
# 启动入口
# ═══════════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(description="AI Chat Service")
    parser.add_argument("--port", type=int, default=5198, help="服务端口 (默认: 5198)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址 (默认: 0.0.0.0)")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    args = parser.parse_args()

    print("=" * 60)
    print("  AI 客服聊天服务")
    print("=" * 60)
    print(f"  端口:     {args.port}")
    print(f"  模式:     {'模拟 (Mock)' if USE_MOCK else 'DeepSeek API'}")
    print(f"  API Key:  {'已配置' if DEEPSEEK_API_KEY else '未配置（模拟模式）'}")
    print(f"  API端点:  POST http://localhost:{args.port}/api/chat")
    print(f"  健康检查: GET  http://localhost:{args.port}/health")
    print("=" * 60)

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
