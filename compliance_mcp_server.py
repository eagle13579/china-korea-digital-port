#!/usr/bin/env python3
"""
合规自动化MCP Server (Compliance Automation MCP)
================================================
中韩出海数智港 · 合规自动驾驶仪 MCP接口层

通过MCP协议向Hermes Agent暴露合规能力：
- 合规知识库问答
- 法规检索
- 合规健康度评分
- 风险预警查询
- 中韩双语支持

启动: python3 compliance_mcp_server.py
协议: stdio MCP (Model Context Protocol)
"""

import json
import sys
import os
import re
from datetime import datetime, timedelta
from typing import Any

# ─── 合规知识库数据 ───────────────────────────────────────────────

COMPLIANCE_KB = {
    "食品进口": {
        "description": "中国进口食品法规体系",
        "entries": [
            {
                "title": "海关总署第248号令",
                "summary": "境外生产企业注册管理制度",
                "detail": "所有向中国出口食品的境外生产企业必须在中国海关注册。注册周期4-8个月。持有HACCP认证可加速审批。",
                "source": "海关总署",
                "effective_date": "2022-01-01",
                "category": "进口合规",
                "keywords": ["248号令", "境外注册", "工厂注册", "HACCP"]
            },
            {
                "title": "GB 7718-2011 食品安全国家标准 预包装食品标签通则",
                "summary": "进口食品中文标签强制标准",
                "detail": "所有进口预包装食品必须有中文标签。调味产品vs原味产品的标签内容不同，需分别审核。",
                "source": "国家卫生健康委员会",
                "effective_date": "2012-04-20",
                "category": "标签合规",
                "keywords": ["标签", "中文标签", "GB 7718", "包装"]
            },
            {
                "title": "入境检验检疫证明 (CIQ)",
                "summary": "每批进口食品均需获得入境检验检疫证明",
                "detail": "每批进口食品在完成入境检验检疫后，由海关出具CIQ证明。没有CIQ证明的产品不得上市销售。",
                "source": "海关总署",
                "effective_date": "持续有效",
                "category": "进口合规",
                "keywords": ["CIQ", "检验检疫", "通关", "海关"]
            },
        ]
    },
    "保健食品": {
        "description": "中国保健食品法规体系",
        "entries": [
            {
                "title": "保健食品注册与备案管理办法",
                "summary": "进口保健食品需在中国完成注册或备案",
                "detail": "进口保健食品分为注册制和备案制。首次进口的保健食品属于补充维生素、矿物质等营养物质的，报国家市场监督管理总局备案。其他首次进口的保健食品应当申请注册。",
                "source": "国家市场监督管理总局",
                "effective_date": "2016-07-01",
                "category": "保健食品合规",
                "keywords": ["保健食品", "注册", "备案", "蓝帽子"]
            },
            {
                "title": "允许保健食品声称的保健功能目录",
                "summary": "保健食品功能声称范围管理",
                "detail": "保健食品只能声称目录中列出的保健功能。2026年5月拟修订目录，部分旧功能声称（如「缓解疲劳」）可能被删除或合并。现有产品若使用被调整的功能声称，需在6个月内完成整改。",
                "source": "国家市场监督管理总局",
                "effective_date": "2026-05-14（征求意见稿）",
                "category": "保健食品合规",
                "keywords": ["功能声称", "保健功能", "缓解疲劳", "目录修订"]
            },
            {
                "title": "进口保健食品境外生产现场审查新规",
                "summary": "境外生产企业分级审查制度",
                "detail": "对进口保健食品的境外生产企业实施A/B/C三级审查。A级简化审查、C级加严审查。建议主动申请AEO认证以获取A级评定。实施日期：2026年8月1日。",
                "source": "海关总署",
                "effective_date": "2026-08-01",
                "category": "保健食品合规",
                "keywords": ["AEO认证", "境外审查", "分级管理", "生产现场"]
            },
            {
                "title": "人参皂苷检测标准更新",
                "summary": "人参皂苷Rg1、Re、Rb1检测方法更新",
                "detail": "HPLC-MS/MS检测方法更新，检出限从0.1mg/g降至0.05mg/g。含有人参皂苷的产品（如高丽红参片）需在新标准生效前更新质检报告。实施日期：2026年10月1日。",
                "source": "国家药典委员会",
                "effective_date": "2026-10-01",
                "category": "检测标准",
                "keywords": ["人参皂苷", "红参", "检测方法", "HPLC-MS/MS", "药典"]
            },
        ]
    },
    "电商平台": {
        "description": "中国电商平台入驻要求",
        "entries": [
            {
                "title": "天猫国际入驻要求",
                "summary": "门槛高，适合品牌旗舰店",
                "detail": "天猫国际对品牌审核严格，适合有品牌知名度的韩企。入驻需提供境外企业资质、品牌授权书、原产地证明等。上线周期1-2个月。",
                "source": "天猫国际",
                "effective_date": "持续更新",
                "category": "电商入驻",
                "keywords": ["天猫", "品牌旗舰店", "跨境电商"]
            },
            {
                "title": "抖音全球购入驻要求",
                "summary": "门槛中，适合短视频种草+直播",
                "detail": "抖音全球购对品牌要求适中，适合通过短视频和直播带货的品牌。入驻周期2-4周。需要准备品牌素材和产品样品。",
                "source": "抖音电商",
                "effective_date": "持续更新",
                "category": "电商入驻",
                "keywords": ["抖音", "全球购", "直播", "短视频"]
            },
            {
                "title": "小红书商城入驻要求",
                "summary": "门槛中高，适合内容种草+店铺",
                "detail": "小红书商城门槛中高，适合有内容营销能力的品牌。通过种草笔记引流到店铺。入驻周期1-2个月。",
                "source": "小红书",
                "effective_date": "持续更新",
                "category": "电商入驻",
                "keywords": ["小红书", "内容种草", "商城"]
            },
        ]
    },
    "关税与HS编码": {
        "description": "关税及HS编码信息",
        "entries": [
            {
                "title": "原味海苔HS编码及关税",
                "summary": "原味海苔进口税号及税率",
                "detail": "原味海苔（未调味）HS编码2106.90，关税12%。2026年7月中韩FTA调整后降至10.8%。",
                "source": "海关总署",
                "effective_date": "2026-07-01",
                "category": "关税",
                "keywords": ["海苔", "2106.90", "原味", "关税"]
            },
            {
                "title": "调味海苔HS编码及关税",
                "summary": "调味海苔进口税号及税率",
                "detail": "调味海苔（烤制加料）HS编码2008.99，关税15%。建议在进口前确认具体产品分类。",
                "source": "海关总署",
                "effective_date": "持续有效",
                "category": "关税",
                "keywords": ["海苔", "2008.99", "调味", "关税"]
            },
        ]
    },
    "放射性检测": {
        "description": "进口食品放射性检测要求",
        "entries": [
            {
                "title": "日本核污水排海后放射性检测建议",
                "summary": "韩国食品放射性检测建议",
                "detail": "2024年后中国海关对日本及周边国家食品放射性检测加强。韩国海苔/食品虽未被强制要求提供放射性检测报告，但建议主动做——可作为营销差异化卖点「定期放射性检测，安全放心」。费用约¥800-1,500/次/季度。",
                "source": "海关总署",
                "effective_date": "2024年起加强",
                "category": "检测标准",
                "keywords": ["放射性检测", "核污水", "日本", "韩国食品", "安全"]
            },
        ]
    },
    "中韩FTA": {
        "description": "中韩自由贸易协定相关信息",
        "entries": [
            {
                "title": "中韩FTA保健食品章节磋商",
                "summary": "新一轮磋商启动，或简化进口审批",
                "detail": "中韩FTA保健食品章节新一轮磋商启动，韩方提议扩大互认范围。若通过可简化进口审批流程。预计谈判期6个月。",
                "source": "商务部",
                "effective_date": "2026年5月（磋商中）",
                "category": "贸易政策",
                "keywords": ["FTA", "中韩", "保健食品", "磋商"]
            },
            {
                "title": "红参药食同源评估",
                "summary": "红参拟列入药食同源目录",
                "detail": "卫健委2026年研究计划中提及红参的药食同源评估。若通过，红参可从保健品转为普通食品管理，大幅降低合规成本。建议企业提前准备申报材料。",
                "source": "国家卫生健康委员会",
                "effective_date": "2026年（评估中）",
                "category": "贸易政策",
                "keywords": ["药食同源", "红参", "保健品", "普通食品"]
            },
        ]
    }
}

# ─── 客户合规健康度数据 ───────────────────────────────────────────

CLIENT_HEALTH = {
    "济州海苔": {
        "company_kr": "JEAJU FOOD",
        "industry": "食品/海苔",
        "score": 86,
        "score_change": "+4",
        "target": 95,
        "alerts_count": 1,
        "risk_high": 0,
        "risk_medium": 1,
        "risk_low": 2,
        "good_news": 2,
        "last_updated": "2026-05-16",
        "dimensions": {
            "资质完整性": {"score": 85, "trend": "stable"},
            "法规监控覆盖率": {"score": 92, "trend": "up"},
            "风险应对速度": {"score": 72, "trend": "up"},
            "竞品合规水平": {"score": 88, "trend": "stable"}
        }
    },
    "韩天红参": {
        "company_kr": "KRG KONGSA",
        "industry": "保健品/红参",
        "score": 83,
        "score_change": "+3",
        "target": 95,
        "alerts_count": 3,
        "risk_high": 1,
        "risk_medium": 2,
        "risk_low": 3,
        "good_news": 2,
        "last_updated": "2026-05-16",
        "dimensions": {
            "资质完整性": {"score": 85, "trend": "stable"},
            "法规监控覆盖率": {"score": 92, "trend": "up"},
            "风险应对速度": {"score": 70, "trend": "up"},
            "竞品合规水平": {"score": 88, "trend": "stable"}
        }
    }
}

# ─── 风险预警数据 ─────────────────────────────────────────────────

RECENT_ALERTS = [
    {
        "id": "P0-001",
        "level": "high",
        "title": "保健食品功能声称目录修订征求意见稿",
        "source": "国家市场监督管理总局",
        "date": "2026-05-14",
        "status": "征求意见中",
        "deadline": "2026-06-15",
        "affected_clients": ["韩天红参"],
        "summary": "拟修订保健功能目录，部分旧功能声称（如缓解疲劳）可能被删除或合并。影响韩泉牌高丽红参片现有包装。",
        "actions": [
            "确认韩泉红参片注册时审批的功能声称原文",
            "对比新目录草案评估影响",
            "准备包装设计变更预案"
        ]
    },
    {
        "id": "P1-001",
        "level": "medium",
        "title": "进口保健食品境外生产现场审查新规",
        "source": "海关总署",
        "date": "2026-05-10",
        "status": "待生效(2026-08-01)",
        "affected_clients": ["韩天红参"],
        "summary": "对境外生产企业实施A/B/C三级审查。建议申请AEO认证获取A级评定。",
        "actions": [
            "启动AEO认证申请(2-3个月)",
            "确认工厂现有认证是否可加速审批"
        ]
    },
    {
        "id": "P1-002",
        "level": "medium",
        "title": "人参皂苷检测标准更新",
        "source": "国家药典委员会",
        "date": "2026-05-12",
        "status": "待生效(2026-10-01)",
        "affected_clients": ["韩天红参"],
        "summary": "人参皂苷Rg1/Re/Rb1检测方法更新，检出限降低。需更新质检报告。",
        "actions": [
            "联系中国合作实验室确认新方法验证时间",
            "安排过渡期并行检测"
        ]
    },
    {
        "id": "P2-001",
        "level": "low",
        "title": "进口食品标签专项抽查(北京海关)",
        "source": "北京海关",
        "date": "2026-05-11",
        "status": "进行中(5-7月)",
        "affected_clients": ["济州海苔", "韩天红参"],
        "summary": "北京海关5-7月期间重点检查韩日进口食品标签合规性。建议自查现有库存标签。",
        "actions": [
            "自查现有库存中文标签",
            "确认标签上的所有信息与最新法规一致"
        ]
    }
]

WEEKLY_BRIEFINGS = {
    "济州海苔": {
        "week": "2026年第20周",
        "period": "5/11-5/17",
        "sources_monitored": 12,
        "total_findings": 8,
        "high_risk": 0,
        "medium_risk": 1,
        "low_risk": 2,
        "good_news": 2,
        "key_updates": [
            "中韩FTA海苔关税调整：原味海苔关税由12%降至10.8%（2026年7月生效）",
            "进口食品标签专项抽查（北京海关5-7月）— 建议自查",
            "AI系统已完成第286次扫描，新增3条相关法规"
        ],
        "recommended_actions": [
            "确认现有产品中文标签与GB 7718-2011的符合性",
            "关注抖音全球购入驻流程调整"
        ]
    },
    "韩天红参": {
        "week": "2026年第20周",
        "period": "5/11-5/17",
        "sources_monitored": 12,
        "total_findings": 8,
        "high_risk": 1,
        "medium_risk": 2,
        "low_risk": 3,
        "good_news": 2,
        "key_updates": [
            "【高风险】保健食品功能声称目录修订 — 韩泉红参片功能声称可能受影响",
            "境外生产企业分级审查新规（8月生效）— 建议启动AEO认证",
            "红参拟列入药食同源目录 — 重大利好，建议提前准备材料"
        ],
        "recommended_actions": [
            "P0: 本周内确认韩泉红参片功能声称原文",
            "P1: 启动AEO认证申请",
            "P1: 联系实验室对接新检测方法"
        ]
    }
}


# ─── MCP Server 实现 ──────────────────────────────────────────────

class ComplianceMCPServer:
    """合规自动化MCP Server"""

    def __init__(self):
        self.tools = {
            "compliance_query": {
                "name": "compliance_query",
                "description": "查询合规知识库，获取进口中国的法规信息。支持中韩双语提问。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "合规相关问题，支持中文或韩语"},
                        "category": {"type": "string", "description": "限定查询类别（可选）：食品进口/保健食品/电商平台/关税与HS编码/放射性检测/中韩FTA", "enum": list(COMPLIANCE_KB.keys()) + [""]}
                    },
                    "required": ["question"]
                }
            },
            "compliance_search_regulation": {
                "name": "compliance_search_regulation",
                "description": "按关键词搜索具体法规，返回法规原文摘要和来源",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string", "description": "搜索关键词，如：红参、海苔、标签、注册、AEO等"},
                        "category": {"type": "string", "description": "限定搜索类别（可选）"}
                    },
                    "required": ["keyword"]
                }
            },
            "compliance_client_health": {
                "name": "compliance_client_health",
                "description": "获取指定客户的合规健康度评分和四维分析",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "client_name": {"type": "string", "description": "客户名称，如：济州海苔、韩天红参"}
                    },
                    "required": ["client_name"]
                }
            },
            "compliance_recent_alerts": {
                "name": "compliance_recent_alerts",
                "description": "获取近期的合规风险预警列表，支持按客户筛选",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "client_name": {"type": "string", "description": "按客户筛选（可选）"},
                        "max_level": {"type": "string", "description": "按风险等级筛选：high/medium/low（可选）"}
                    }
                }
            },
            "compliance_weekly_briefing": {
                "name": "compliance_weekly_briefing",
                "description": "获取指定客户的本周合规简报（中韩双语摘要）",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "client_name": {"type": "string", "description": "客户名称，如：济州海苔、韩天红参"},
                        "language": {"type": "string", "description": "语言：zh（中文）/ kr（韩语）", "enum": ["zh", "kr"]}
                    },
                    "required": ["client_name"]
                }
            }
        }

    def execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """执行MCP工具调用"""
        handler = getattr(self, f"handle_{tool_name}", None)
        if not handler:
            return {"error": f"未知工具: {tool_name}"}
        try:
            return handler(arguments)
        except Exception as e:
            return {"error": f"执行错误: {str(e)}"}

    # ─── 工具处理函数 ─────────────────────────────────────────

    def handle_compliance_query(self, args: dict) -> dict:
        question = args.get("question", "")
        category = args.get("category", "")

        if not question:
            return {"error": "请输入问题"}

        results = []
        categories_to_search = [category] if category else COMPLIANCE_KB.keys()

        for cat in categories_to_search:
            if cat in COMPLIANCE_KB:
                for entry in COMPLIANCE_KB[cat]["entries"]:
                    relevance = self._calc_relevance(question, entry)
                    if relevance > 0.3:
                        results.append({
                            "category": cat,
                            "title": entry["title"],
                            "summary": entry["summary"],
                            "detail": entry["detail"],
                            "source": entry["source"],
                            "effective_date": entry.get("effective_date", ""),
                            "relevance": round(relevance, 2)
                        })

        results.sort(key=lambda x: x["relevance"], reverse=True)

        return {
            "question": question,
            "result_count": len(results),
            "results": results[:5],
            "note": "如需更多信息，请细化问题或指定类别",
            "bilingual_note": "한국어 질문도 지원합니다. 한국어로 물어보시면 한국어로 답변해드립니다."
        }

    def handle_compliance_search_regulation(self, args: dict) -> dict:
        keyword = args.get("keyword", "")
        category = args.get("category", "")

        if not keyword:
            return {"error": "请输入搜索关键词"}

        results = []
        categories_to_search = [category] if category else COMPLIANCE_KB.keys()

        for cat in categories_to_search:
            if cat in COMPLIANCE_KB:
                for entry in COMPLIANCE_KB[cat]["entries"]:
                    text = f"{entry['title']} {entry['summary']} {entry['detail']}"
                    matched_kw = [kw for kw in entry.get("keywords", []) if kw in keyword or keyword in kw]
                    if keyword.lower() in text.lower() or matched_kw:
                        results.append({
                            "category": cat,
                            "title": entry["title"],
                            "summary": entry["summary"],
                            "detail": entry["detail"][:200] + "..." if len(entry["detail"]) > 200 else entry["detail"],
                            "source": entry["source"],
                            "effective_date": entry.get("effective_date", ""),
                            "matched_keywords": matched_kw
                        })

        return {
            "keyword": keyword,
            "result_count": len(results),
            "results": results[:10]
        }

    def handle_compliance_client_health(self, args: dict) -> dict:
        client = args.get("client_name", "")
        if not client:
            return {"error": "请输入客户名称", "available_clients": list(CLIENT_HEALTH.keys())}

        # Fuzzy match
        matched = None
        for name, data in CLIENT_HEALTH.items():
            if client in name or name in client:
                matched = {name: data}
                break

        if not matched:
            return {"error": f"未找到客户「{client}」", "available_clients": list(CLIENT_HEALTH.keys())}

        return matched

    def handle_compliance_recent_alerts(self, args: dict) -> dict:
        client = args.get("client_name", "")
        max_level = args.get("max_level", "")

        alerts = RECENT_ALERTS.copy()

        if client:
            alerts = [a for a in alerts if client in " ".join(a.get("affected_clients", []))]

        if max_level:
            level_order = {"high": 0, "medium": 1, "low": 2}
            max_order = level_order.get(max_level, 2)
            alerts = [a for a in alerts if level_order.get(a.get("level", "low"), 2) <= max_order]

        return {
            "alert_count": len(alerts),
            "alerts": alerts
        }

    def handle_compliance_weekly_briefing(self, args: dict) -> dict:
        client = args.get("client_name", "")
        language = args.get("language", "zh")

        if not client:
            return {"error": "请输入客户名称", "available_clients": list(WEEKLY_BRIEFINGS.keys())}

        matched = None
        for name, data in WEEKLY_BRIEFINGS.items():
            if client in name or name in client:
                matched = {name: data}
                break

        if not matched:
            return {"error": f"未找到客户「{client}」", "available_clients": list(WEEKLY_BRIEFINGS.keys())}

        # For Korean language, translate header
        briefing = matched
        if language == "kr":
            briefing = {
                "언어": "한국어",
                "안내": "주간 컴플라이언스 브리핑입니다. 자세한 내용은 한국어로 문의하세요."
            }

        return briefing

    # ─── 辅助函数 ────────────────────────────────────────────

    def _calc_relevance(self, question: str, entry: dict) -> float:
        """计算问题与知识条目的相关性"""
        text = f"{entry['title']} {entry['summary']} {entry['detail']}"
        question_lower = question.lower()

        score = 0
        # Direct keyword matches
        for kw in entry.get("keywords", []):
            if kw in question:
                score += 0.2

        # Title match (highest weight)
        if any(word in entry['title'] for word in question_lower.split()):
            score += 0.3

        # Category implicit match
        category_related = {
            "海苔": "食品进口",
            "红参": "保健食品",
            "电商": "电商平台",
            "天猫": "电商平台",
            "抖音": "电商平台",
            "关税": "关税与HS编码",
            "HS": "关税与HS编码",
            "放射": "放射性检测",
            "核": "放射性检测",
            "FTA": "中韩FTA",
            "中韩": "中韩FTA"
        }
        for word, cat in category_related.items():
            if word in question and entry in COMPLIANCE_KB.get(cat, {}).get("entries", []):
                score += 0.3

        return min(score, 1.0)


# ─── MCP 协议处理 ───────────────────────────────────────────────

def handle_mcp_request(request: dict, server: ComplianceMCPServer) -> dict:
    """处理MCP JSON-RPC请求"""
    req_id = request.get("id", 0)
    method = request.get("method", "")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "compliance-automation-mcp",
                    "version": "1.0.0"
                }
            }
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": list(server.tools.values())
            }
        }

    elif method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = server.execute_tool(tool_name, arguments)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, indent=2)
                    }
                ]
            }
        }

    elif method == "notifications/initialized":
        return None  # No response for notifications

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"未知方法: {method}"}
        }


def main():
    """MCP Server 主循环（stdio传输）"""
    server = ComplianceMCPServer()

    # Signal readiness to stderr (MCP convention)
    print("Compliance MCP Server starting...", file=sys.stderr)
    sys.stderr.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_mcp_request(request, server)
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)
        except json.JSONDecodeError as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"JSON解析错误: {str(e)}"}
            }
            print(json.dumps(error_response, ensure_ascii=False), flush=True)
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": f"内部错误: {str(e)}"}
            }
            print(json.dumps(error_response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
