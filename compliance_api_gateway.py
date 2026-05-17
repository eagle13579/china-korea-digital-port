#!/usr/bin/env python3
"""
合规自动化MCP - HTTP API Gateway
==================================
为合规MCP提供HTTP REST接口，方便前端调用。

启动: python3 compliance_api_gateway.py
端口: 5125
"""

import sys
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compliance_mcp_server import ComplianceMCPServer, handle_mcp_request
from backend.compliance_kr_data import get_compliance_data, get_checklist_summary, get_faq, INDUSTRIES

SERVER = ComplianceMCPServer()
PORT = 5126

# ─── 产品数据 ──────────────────────────────────────────────

PRODUCTS = [
    {
        "id": "matcha-latte", "name_zh": "CAFE MORI 抹茶拿铁", "name_kr": "CAFE MORI 말차라떼",
        "company_kr": "JARDIN", "category_zh": "食品/饮料", "category_kr": "식품/음료",
        "tags_zh": ["韩国37年老牌", "济州岛有机绿茶", "6种口味"], "tags_kr": ["한국 37년 전통", "제주도 유기농 녹차", "6가지 맛"],
        "price_fob": 1.80, "price_unit_zh": "条", "moq": 1000,
        "description_zh": "韩国37年老牌JARDIN旗下，济州岛有机绿茶研磨，6种口味，每条不到5元。",
        "description_kr": "한국 37년 전통 JARDIN 브랜드, 제주도 유기농 녹차 말차 라떼.",
        "specs": [
            {"name": "原味", "posts": 48, "engagement": "7.2%", "heat": 96},
            {"name": "香草", "posts": 42, "engagement": "6.8%", "heat": 88},
            {"name": "草莓", "posts": 36, "engagement": "5.9%", "heat": 75},
        ]
    },
    {
        "id": "jeju-seaweed", "name_zh": "济州海苔", "name_kr": "제주 김",
        "company_kr": "JEAJU FOOD", "category_zh": "食品/海苔", "category_kr": "식품/김",
        "tags_zh": ["1976年创立", "韩国代表海苔品牌", "中国代理：上海香德粒"], "tags_kr": ["1976년 설립", "한국 대표 김 브랜드"],
        "price_fob": 2.50, "price_unit_zh": "包", "moq": 500,
        "description_zh": "1976年创立的韩国海苔代表企业，通过上海香德粒出口中国11年。",
        "description_kr": "1976년 설립된 한국 대표 김 브랜드. 중국 수출 11년차.",
        "specs": [
            {"name": "原味海苔", "posts": 36, "engagement": "6.5%", "heat": 85},
            {"name": "调味海苔", "posts": 28, "engagement": "5.8%", "heat": 72},
        ]
    },
    {
        "id": "korean-ginseng", "name_zh": "韩天红参", "name_kr": "한천 홍삼",
        "company_kr": "KRG KONGSA", "category_zh": "保健品/红参", "category_kr": "건강기능식품/홍삼",
        "tags_zh": ["高端滋补", "6年根", "韩国正品"], "tags_kr": ["고급 보양", "6년근", "한국 정품"],
        "price_fob": 35.00, "price_unit_zh": "盒", "moq": 100,
        "description_zh": "韩国6年根红参浓缩液，传统工艺萃取。富含人参皂苷。",
        "description_kr": "한국 6년근 홍삼 농축액, 전통 방식으로 추출.",
        "specs": [
            {"name": "6年根浓缩液", "posts": 32, "engagement": "7.8%", "heat": 96},
            {"name": "礼盒装", "posts": 18, "engagement": "5.6%", "heat": 72},
        ]
    }
]

PLATFORM_STATS = {
    "platforms": [
        {"name_zh": "小红书", "name_kr": "샤오홍슈", "icon": "📕", "engagement": 7.2, "posts_per_week": 48, "wow_change": 15},
        {"name_zh": "抖音", "name_kr": "틱톡 중국", "icon": "🎵", "engagement": 8.9, "posts_per_week": 36, "wow_change": 22},
        {"name_zh": "微信", "name_kr": "위챗", "icon": "💬", "engagement": 5.1, "posts_per_week": 24, "wow_change": 5},
    ],
    "total_posts_this_week": 126,
    "avg_engagement": 6.9,
    "total_clients": 3
}


class ComplianceAPIHandler(BaseHTTPRequestHandler):
    """REST API handler that wraps MCP tools"""

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def do_OPTIONS(self):
        self._send_json({})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/" or path == "":
            self._send_json({
                "service": "合规自动化MCP Gateway",
                "version": "1.0.0",
                "status": "running",
                "endpoints": {
                    "GET /": "此页面",
                    "GET /tools": "列出可用工具",
                    "GET /health/<client>": "客户合规健康度",
                    "GET /alerts": "风险预警列表",
                    "GET /briefing/<client>": "客户周报",
                    "POST /query": "合规知识库问答",
                    "POST /search": "法规搜索"
                }
            })

        elif path == "/tools":
            mcp_req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
            mcp_resp = handle_mcp_request(mcp_req, SERVER)
            self._send_json(mcp_resp["result"])

        elif path == "/api/products":
            self._send_json({"products": PRODUCTS, "total": len(PRODUCTS)})

        elif path == "/api/stats":
            self._send_json(PLATFORM_STATS)

        elif path == "/api/compliance/kr/check":
            params = parse_qs(parsed.query)
            industry = params.get("industry", ["all"])[0]
            lang = params.get("language", ["ko"])[0]
            result = self._get_kr_compliance(industry, lang)
            self._send_json(result)

        elif path == "/api/health":
            params = parse_qs(parsed.query)
            client = params.get("client", [""])[0]
            if not client:
                self._send_json({"error": "请指定 ?client=客户名称"}, 400)
                return
            mcp_req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "compliance_client_health", "arguments": {"client_name": client}}}
            mcp_resp = handle_mcp_request(mcp_req, SERVER)
            result = json.loads(mcp_resp["result"]["content"][0]["text"])
            self._send_json(result)

        elif path.startswith("/health/"):
            raw = path.split("/health/")[1]
            client = unquote(raw)
            # Handle double-encoding from curl
            if '%' in client:
                client = unquote(client)
            mcp_req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "compliance_client_health", "arguments": {"client_name": client}}}
            mcp_resp = handle_mcp_request(mcp_req, SERVER)
            result = json.loads(mcp_resp["result"]["content"][0]["text"])
            self._send_json(result)

        elif path == "/alerts":
            params = parse_qs(parsed.query)
            max_level = params.get("max_level", [""])[0]
            client = params.get("client", [""])[0]
            args = {}
            if max_level: args["max_level"] = max_level
            if client: args["client_name"] = client
            mcp_req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "compliance_recent_alerts", "arguments": args}}
            mcp_resp = handle_mcp_request(mcp_req, SERVER)
            result = json.loads(mcp_resp["result"]["content"][0]["text"])
            self._send_json(result)

        elif path.startswith("/briefing/"):
            client = path.split("/briefing/")[1]
            params = parse_qs(parsed.query)
            lang = params.get("lang", ["zh"])[0]
            mcp_req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "compliance_weekly_briefing", "arguments": {"client_name": client, "language": lang}}}
            mcp_resp = handle_mcp_request(mcp_req, SERVER)
            result = json.loads(mcp_resp["result"]["content"][0]["text"])
            self._send_json(result)

        else:
            self._send_json({"error": "Not found", "path": path}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b"{}"

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        if path == "/query":
            question = data.get("question", "")
            category = data.get("category", "")
            mcp_req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "compliance_query", "arguments": {"question": question, "category": category}}}
            mcp_resp = handle_mcp_request(mcp_req, SERVER)
            result = json.loads(mcp_resp["result"]["content"][0]["text"])
            self._send_json(result)

        elif path == "/api/compliance/kr/check":
            industry = data.get("industry", "all")
            lang = data.get("language", "ko")
            result = self._get_kr_compliance(industry, lang)
            self._send_json(result)

        elif path == "/search":
            keyword = data.get("keyword", "")
            category = data.get("category", "")
            mcp_req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "compliance_search_regulation", "arguments": {"keyword": keyword, "category": category}}}
            mcp_resp = handle_mcp_request(mcp_req, SERVER)
            result = json.loads(mcp_resp["result"]["content"][0]["text"])
            self._send_json(result)

        else:
            self._send_json({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}", file=sys.stderr)

    def _get_kr_compliance(self, industry="all", language="ko"):
        """Get Korean compliance data"""
        lang = language if language in ("ko", "zh") else "ko"

        try:
            if industry and industry != "all" and industry in ("cosmetics", "food", "health_supplements"):
                data = get_compliance_data(industry)
                summary = get_checklist_summary(industry, lang)
                industry_info = INDUSTRIES.get(industry)
                return {
                    "success": True,
                    "data": data,
                    "summary": summary,
                    "industry_info": industry_info,
                    "faq": get_faq(lang),
                }

            # All industries
            all_data = get_compliance_data(None)
            summaries = {}
            for ind_id in ("cosmetics", "food", "health_supplements"):
                summaries[ind_id] = get_checklist_summary(ind_id, lang)

            return {
                "success": True,
                "industries": INDUSTRIES,
                "data": all_data.get("data", all_data),
                "summaries": summaries,
                "faq": get_faq(lang),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


def main():
    server = HTTPServer(("0.0.0.0", PORT), ComplianceAPIHandler)
    print(f"✅ 合规自动化MCP Gateway 启动于 http://localhost:{PORT}", file=sys.stderr)
    print(f"   📋 GET  /tools   — 查看可用工具", file=sys.stderr)
    print(f"   📋 GET  /health/<client> — 客户合规健康度", file=sys.stderr)
    print(f"   📋 POST /query   — 合规问答", file=sys.stderr)
    print(f"   📋 POST /search  — 法规搜索", file=sys.stderr)
    print(f"   📋 GET  /alerts  — 风险预警", file=sys.stderr)
    print(f"   📋 GET  /briefing/<client> — 客户周报", file=sys.stderr)
    sys.stderr.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...", file=sys.stderr)
        server.server_close()


if __name__ == "__main__":
    main()
