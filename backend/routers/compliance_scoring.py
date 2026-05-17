"""
合规四维MECE评分引擎 — 问→测→诊→报四步流中的"评分"环节

MECE四个互斥维度:
1. 准入合规 (Access Compliance) — 外商投资准入负面清单/行业限制
2. 行业合规 (Industry Compliance) — 食品/化妆品/IT/医药等行业专项法规
3. 运营合规 (Operations Compliance) — 社保/税务/数据安全/劳动法
4. 贸易合规 (Trade Compliance) — 进出口/海关/原产地/关税

每个维度6-8个评分项，输出:
- 总评分(0-100)
- 每个维度评分(0-100)
- 风险等级(低/中/高/严重)
- 优先级行动清单

对接 compliance_diagnosis.py 的诊断session
"""

import json
import sqlite3
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/v1/compliance/scoring", tags=["compliance-scoring"])

# ── 数据库路径（复用现有 compliance_diagnosis.db） ──────────────
DIAG_DB = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data", "compliance_diagnosis.db"
)
KNOWLEDGE_DB = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data", "compliance_knowledge.db"
)


def _diag_db():
    """连接诊断session数据库"""
    conn = sqlite3.connect(DIAG_DB)
    conn.row_factory = sqlite3.Row
    return conn


def _knowledge_db():
    """连接知识图谱数据库"""
    path = KNOWLEDGE_DB
    if not os.path.exists(path):
        return None
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


# ====================================================================
# 维度一：准入合规 (Access Compliance) — 6个评分项
# ====================================================================
ACCESS_ITEMS = [
    {
        "id": "acc_01",
        "question_zh": "是否已对照《外商投资准入特别管理措施（负面清单）》确认业务领域不在限制/禁止类范围？",
        "question_ko": "「외국인투자 네거티브 리스트」를 확인하여 사업 분야가 제한·금지 업종에 해당하지 않는지 확인하셨습니까?",
        "weight": 20,
        "scoring": {
            0: "已完成对照确认，业务不在负面清单限制范围内，且未触犯外资股比限制",
            1: "已基本了解但不完全确定部分业务的分类归属",
            2: "知道有负面清单但未做正式合规检查",
            3: "完全不知道或不了解负面清单制度"
        },
        "actions": {
            0: [],
            1: ["委托专业机构对业务范围进行负面清单合规审查", "重点关注教育、文化传媒、互联网等敏感领域"],
            2: ["立即启动负面清单对照审查", "审查经营范围是否涉及限制类行业的外资股比要求"],
            3: ["安排管理层了解《外商投资法》第4-28条及负面清单制度", "聘请专业律师进行市场准入合规审查"]
        },
        "knowledge_ref": "《外商投资法》第4-28条 | 《外商投资准入特别管理措施（负面清单）》(2024年版)"
    },
    {
        "id": "acc_02",
        "question_zh": "是否已完成中国市场行业准入可行性评估并获得所需的行业资质/许可证？",
        "question_ko": "중국 시장 업종 진입 타당성 평가를 완료하고 필요한 업종 자격증/허가증을 취득하셨습니까?",
        "weight": 20,
        "scoring": {
            0: "已完成全面评估并取得全部所需资质/许可证",
            1: "正在进行评估，部分材料已准备就绪",
            2: "有计划但尚未启动评估，不清楚所需资质",
            3: "未进行过任何行业准入评估"
        },
        "actions": {
            0: [],
            1: ["加速推进剩余资质的申请流程", "评估是否需要聘请市场准入顾问加速进程"],
            2: ["立即启动行业准入可行性评估", "梳理行业所需全部资质与审批清单"],
            3: ["安排与市场准入顾问咨询会议", "制定行业准入路线图和时间表"]
        },
        "knowledge_ref": "《外商投资法》第28-30条 | 《市场准入负面清单(2024年版)》"
    },
    {
        "id": "acc_03",
        "question_zh": "是否已确定进入中国市场的投资架构（WFOE/JV/代表处）并完成注册？",
        "question_ko": "중국 시장 진입을 위한 투자 구조(WFOE/JV/대표처)를 확정하고 등록을 완료하셨습니까?",
        "weight": 18,
        "scoring": {
            0: "已完成WFOE/JV/代表处注册，架构经过专业规划",
            1: "注册正在办理中，材料已提交",
            2: "在考虑多种方案但未做出最终决定",
            3: "尚未开始考虑公司设立事宜"
        },
        "actions": {
            0: [],
            1: ["跟进注册进度，确保材料完整", "同步开通银行账户和税务登记"],
            2: ["尽快确定WFOE/JV/代表处方案", "考虑行业限制对架构选择的影响"],
            3: ["咨询公司设立顾问了解WFOE/JV/代表处的利弊", "制定公司设立计划与预算"]
        },
        "knowledge_ref": "《公司法》第23-193条 | 《外商投资法》第4-31条"
    },
    {
        "id": "acc_04",
        "question_zh": "是否已了解目标行业的注册资本要求、实缴期限和经营范围限制？",
        "question_ko": "목표 업종의 등록 자본 요건, 납입 기한 및 영업 범위 제한을 알고 계십니까?",
        "weight": 15,
        "scoring": {
            0: "完全了解，注册资本和经营范围已合规规划",
            1: "基本了解但部分细节不确定",
            2: "知道有要求但不清楚具体规定",
            3: "完全不了解注册资本和经营范围的相关规定"
        },
        "actions": {
            0: [],
            1: ["与注册代理确认注册资本和经营范围细节", "检查是否涉及前置审批项目"],
            2: ["查阅《市场主体登记管理条例》了解基本要求", "咨询专业机构进行注册资本规划"],
            3: ["了解中国公司注册的基本流程和资本要求", "参加公司设立相关培训或咨询"]
        },
        "knowledge_ref": "《市场主体登记管理条例》 | 《注册资本登记制度改革方案》"
    },
    {
        "id": "acc_05",
        "question_zh": "是否已评估行业是否涉及外商限制类领域的VIE架构合规风险？",
        "question_ko": "업종이 외국인 투자 제한 분야의 VIE 구조 규제 위험에 해당하는지 평가하셨습니까?",
        "weight": 15,
        "scoring": {
            0: "不涉及限制类领域，或已评估VIE架构合规性并采取措施",
            1: "了解VIE风险但未做正式评估",
            2: "知道VIE架构但不清楚合规风险",
            3: "完全不了解VIE架构及相关监管政策"
        },
        "actions": {
            0: [],
            1: ["委托律师进行VIE架构合规审查", "关注VIE相关监管政策变化"],
            2: ["了解VIE架构的基本风险和最新监管动态", "评估是否需要用替代架构"],
            3: ["了解什么是VIE架构及中国监管态度", "如果涉及互联网/教育/传媒行业需特别关注"]
        },
        "knowledge_ref": "《外商投资法》第4条 | 商务部关于VIE架构的监管指引"
    },
    {
        "id": "acc_06",
        "question_zh": "是否已了解并完成外商投资信息报告（FIRC）等合规备案义务？",
        "question_ko": "외국인 투자 정보 보고(FIRC) 등 규제 등록 의무를 이해하고 완료하셨습니까?",
        "weight": 12,
        "scoring": {
            0: "已完成外商投资信息报告及其他备案义务",
            1: "了解要求并正在准备材料",
            2: "知道有报告义务但不清楚具体内容",
            3: "完全不了解外商投资信息报告制度"
        },
        "actions": {
            0: [],
            1: ["尽快完成外商投资信息报告提交", "确认是否还有其他部门备案要求"],
            2: ["了解FIRC报告的内容和提交时限", "安排专人负责合规备案工作"],
            3: ["了解外商投资信息报告的基本要求", "聘请专业机构协助完成备案"]
        },
        "knowledge_ref": "《外商投资信息报告办法》 | 《外商投资法》第34条"
    }
]

# ====================================================================
# 维度二：行业合规 (Industry Compliance) — 7个评分项
# ====================================================================
INDUSTRY_ITEMS = [
    {
        "id": "ind_01",
        "question_zh": "产品是否已取得中国强制性认证（CCC认证）或符合行业特定标准（GB/GB/T）？",
        "question_ko": "제품이 중국 강제 인증(CCC 인증)을 취득했거나 업종 특정 기준(GB/GB/T)을 충족합니까?",
        "weight": 18,
        "scoring": {
            0: "所有产品已取得CCC认证并符合国家标准",
            1: "主要产品已认证但部分品类待确认",
            2: "知道需要认证但不清楚目录和流程",
            3: "完全不了解中国产品认证和标准体系"
        },
        "actions": {
            0: [],
            1: ["核查是否所有品类均在CCC目录外或已获认证", "关注GB标准更新动态"],
            2: ["查询CCC强制认证目录确认产品是否在列", "联系认证检测机构了解流程和时间"],
            3: ["了解《产品质量法》和CCC认证制度基本要求", "聘请中国标准检测机构进行合规审查"]
        },
        "knowledge_ref": "《产品质量法》第12-49条 | 《强制性产品认证管理规定》"
    },
    {
        "id": "ind_02",
        "question_zh": "广告宣传内容是否已进行合规审核，避免极限用语和虚假宣传？",
        "question_ko": "광고 홍보 내용이 규제 검토를 거쳐 절대적 표현과 허위 광고를 피했습니까?",
        "weight": 15,
        "scoring": {
            0: "所有广告经法务审核，无极限用语和虚假宣传风险",
            1: "广告基本合规但对行业特定规范了解不全面",
            2: "知道中国广告法严格但不了解具体限制",
            3: "直接将韩国广告文案翻译后在中国发布"
        },
        "actions": {
            0: [],
            1: ["加强行业特定广告规范（食品/医疗/化妆品）学习", "建立广告发布前合规审核机制"],
            2: ["学习《广告法》禁止的极限用语清单", "对现有广告内容进行全面合规审查"],
            3: ["立即停用未经审核的广告内容", "聘请专业律师进行广告合规审查"]
        },
        "knowledge_ref": "《广告法》第4-59条 | 《互联网广告管理办法》"
    },
    {
        "id": "ind_03",
        "question_zh": "如涉及电商平台销售，是否已完成平台主体登记和电商法合规义务？",
        "question_ko": "전자상거래 플랫폼 판매와 관련하여 플랫폼 사업자 등록 및 전자상거래법 규제 의무를 완료하셨습니까?",
        "weight": 15,
        "scoring": {
            0: "已完成所有平台登记，亮照亮证经营，交易记录规范",
            1: "已入驻平台并完成基本登记，但对细则不熟悉",
            2: "通过跨境电商销售但不清楚境外商家义务",
            3: "完全不了解电子商务法要求"
        },
        "actions": {
            0: [],
            1: ["审查消费者权益保护和个人信息收集条款", "建立交易记录保存机制"],
            2: ["了解跨境电商零售进口的监管要求", "完成平台海外商家备案"],
            3: ["了解《电子商务法》对境外商家的基本要求", "咨询电商合规专家"]
        },
        "knowledge_ref": "《电子商务法》第10-87条 | 《网络交易监督管理办法》"
    },
    {
        "id": "ind_04",
        "question_zh": "消费者权益保护机制是否完善（七日无理由退货、三包规定、惩罚性赔偿应对）？",
        "question_ko": "소비자 권리 보호 메커니즘(7일 무조건 반품, 3보 규정, 징벌적 배상 대응)이 완비되어 있습니까?",
        "weight": 14,
        "scoring": {
            0: "已建立完善投诉处理机制，充分保障消费者法定权利",
            1: "有基本售后但对惩罚性赔偿适用范围理解不准",
            2: "知道保护严格但不知具体适用条件",
            3: "不了解消费者权益保护法，无投诉处理机制"
        },
        "actions": {
            0: [],
            1: ["完善退换货政策和用户协议", "培训客服团队应对消费者维权"],
            2: ["审查七日无理由退货适用商品范围", "了解惩罚性赔偿的计算标准和应对策略"],
            3: ["建立消费者投诉处理机制", "制定退换货政策并公示"]
        },
        "knowledge_ref": "《消费者权益保护法》第24-55条 | 《网络购买商品七日无理由退货暂行办法》"
    },
    {
        "id": "ind_05",
        "question_zh": "如涉及食品/化妆品/医药等行业，是否已取得中国注册备案和生产许可？",
        "question_ko": "식품·화장품·의약품 등 업종에 해당하는 경우 중국 등록·비안 및 생산 허가를 취득하셨습니까?",
        "weight": 18,
        "scoring": {
            0: "已完成注册备案，取得全部生产和销售许可",
            1: "注册备案正在办理中",
            2: "知道需要注册但不清楚具体流程和要求",
            3: "未考虑行业特殊许可要求"
        },
        "actions": {
            0: [],
            1: ["跟踪注册审批进度", "准备补充材料应对审查"],
            2: ["立即启动行业特定注册备案流程", "咨询行业监管顾问了解具体要求"],
            3: ["了解目标行业在中国的监管框架（NMPA/CFSA等）", "制定注册备案时间表"]
        },
        "knowledge_ref": "《食品安全法》 | 《化妆品监督管理条例》 | 《药品管理法》"
    },
    {
        "id": "ind_06",
        "question_zh": "如涉及技术进出口（专利许可/技术秘密/软件授权），是否已完成技术合同登记？",
        "question_ko": "기술 수출입(특허 라이선스/영업 비밀/소프트웨어 라이선스)에 해당하는 경우 기술 계약 등록을 완료하셨습니까?",
        "weight": 12,
        "scoring": {
            0: "已完成技术分类评估和合同登记，限制类已取得许可",
            1: "了解要求但分类判断标准不够明确",
            2: "知道需要审批但不清楚限制出口范围",
            3: "未意识到技术进出口需要登记或审批"
        },
        "actions": {
            0: [],
            1: ["明确技术分类（禁止/限制/自由）判断标准", "确保自由类技术3个月内完成合同登记"],
            2: ["对照《中国禁止出口限制出口技术目录》评估", "启动技术出口合同登记流程"],
            3: ["了解《技术进出口管理条例》基本要求", "委托专业机构进行技术分类评估"]
        },
        "knowledge_ref": "《技术进出口管理条例》第2-48条 | 《中国禁止出口限制出口技术目录》"
    },
    {
        "id": "ind_07",
        "question_zh": "如涉及建设项目/工厂，是否已完成环境影响评价（环评）审批？",
        "question_ko": "건설 프로젝트/공장과 관련하여 환경영향평가(환평) 승인을 완료하셨습니까?",
        "weight": 8,
        "scoring": {
            0: "已完成环评审批并落实环保措施",
            1: "环评报告已提交或正在编制中",
            2: "知道需要环评但不清楚分类（报告书/报告表/登记表）",
            3: "完全不了解环评制度"
        },
        "actions": {
            0: [],
            1: ["跟进审批进度确保无延误", "准备环保验收材料"],
            2: ["确定环评类别尽早启动评估", "委托环评机构进行现场评估"],
            3: ["了解《环境影响评价法》基本要求", "聘请环评机构评估项目环评类别"]
        },
        "knowledge_ref": "《环境影响评价法》第16-31条 | 《建设项目环境保护管理条例》"
    }
]

# ====================================================================
# 维度三：运营合规 (Operations Compliance) — 8个评分项
# ====================================================================
OPERATIONS_ITEMS = [
    {
        "id": "ops_01",
        "question_zh": "是否已建立数据安全和隐私保护合规体系（数据分类分级/跨境传输评估/隐私政策）？",
        "question_ko": "데이터 보안 및 프라이버시 보호 규제 체계(데이터 분류·등급화/역외 이전 평가/프라이버시 정책)를 구축하셨습니까?",
        "weight": 16,
        "scoring": {
            0: "已完成数据分类分级和跨境传输评估，隐私政策完善",
            1: "已基本了解要求并部分落实",
            2: "知道有要求但未开始行动",
            3: "完全不了解数据安全法和个人信息保护法"
        },
        "actions": {
            0: [],
            1: ["完成剩余数据分类分级工作", "确保隐私政策符合最新法规要求"],
            2: ["立即启动数据资产梳理和分类分级", "评估是否需要数据出境安全评估"],
            3: ["安排管理层学习《数据安全法》和《个人信息保护法》", "聘请数据合规律师进行差距分析"]
        },
        "knowledge_ref": "《数据安全法》第21-31条 | 《个人信息保护法》第38-43条 | 《数据出境安全评估办法》"
    },
    {
        "id": "ops_02",
        "question_zh": "信息系统是否已完成网络安全等级保护定级、备案和测评？",
        "question_ko": "정보 시스템에 대해 네트워크 보안 등급 보호 등급 지정, 등록 및 평가를 완료하셨습니까?",
        "weight": 14,
        "scoring": {
            0: "已完成等保定级、公安备案和安全测评",
            1: "了解等保2.0要求正在推进定级备案",
            2: "知道有等保制度但不清楚系统等级",
            3: "完全不了解等保制度"
        },
        "actions": {
            0: [],
            1: ["加快安全测评进程", "持续落实等级保护安全措施"],
            2: ["确定信息系统等级（1-5级）", "启动定级备案流程"],
            3: ["了解《网络安全法》第21-38条等保要求", "委托等保测评机构进行评估"]
        },
        "knowledge_ref": "《网络安全法》第21-38条 | 《网络安全等级保护条例》"
    },
    {
        "id": "ops_03",
        "question_zh": "劳动合同是否合规签订？五险一金是否按时足额缴纳？",
        "question_ko": "노동 계약이 규정에 따라 체결되었습니까? 5대 보험과 주택 공적금이 정기적으로 납부되고 있습니까?",
        "weight": 14,
        "scoring": {
            0: "已与所有员工签订书面劳动合同，按时足额缴纳五险一金",
            1: "已签合同但对社保缴纳细则不完全了解",
            2: "正在招聘/派遣员工但用工管理体系不完善",
            3: "没有中国员工也不知道中国劳动法要求"
        },
        "actions": {
            0: [],
            1: ["审查劳动合同条款是否符合最新法规", "完善社保缴纳管理流程"],
            2: ["建立完善的员工入职和合同管理制度", "确保外籍员工办理就业许可证"],
            3: ["了解《劳动合同法》对外籍用工的基本要求", "咨询劳动法律师设计合同模板"]
        },
        "knowledge_ref": "《劳动合同法》第7-50条 | 《社会保险法》第10-60条 | 《外国人就业管理规定》"
    },
    {
        "id": "ops_04",
        "question_zh": "外籍员工（韩籍）的工作签证（Z签）和居留许可是否合规办理？",
        "question_ko": "외국인(한국인) 직원의 취업 비자(Z비자)와 체류 허가가 규정에 따라 발급되었습니까?",
        "weight": 12,
        "scoring": {
            0: "所有常驻韩籍员工均已取得工作类居留许可",
            1: "部分已办理但有些正在办理中",
            2: "准备派遣但对Z签流程不熟悉",
            3: "未考虑需工作签证，用M签长期工作"
        },
        "actions": {
            0: [],
            1: ["跟踪签证办理进度", "建立签证续期提醒机制"],
            2: ["尽快启动Z字签证申请流程", "联系签证服务机构获取支持"],
            3: ["立即停止使用M签进行长期工作", "安排所有在华韩籍员工办理Z签和居留许可"]
        },
        "knowledge_ref": "《出境入境管理法》第41-47条 | 《外国人入境出境管理条例》"
    },
    {
        "id": "ops_05",
        "question_zh": "是否已建立反商业贿赂合规制度和反腐败培训机制？",
        "question_ko": "반뇌물 규제 제도와 반부패 교육 메커니즘을 구축하셨습니까?",
        "weight": 12,
        "scoring": {
            0: "已建立完善的反商业贿赂制度，定期培训，严格合规审查",
            1: "有基本政策但对实务不熟悉",
            2: "知道重要性但未建立内控制度",
            3: "认为商务回扣是行业惯例"
        },
        "actions": {
            0: [],
            1: ["完善礼品招待规范和审批流程", "开展全员反腐败培训"],
            2: ["制定反商业贿赂合规手册", "建立第三方尽职调查机制"],
            3: ["了解《反不正当竞争法》第7-19条", "立即建立反商业贿赂基本制度"]
        },
        "knowledge_ref": "《反不正当竞争法》第7-19条 | 《刑法》第163-164条"
    },
    {
        "id": "ops_06",
        "question_zh": "外汇管理是否合规（资本金结汇/利润汇出/跨境借贷是否按规定办理）？",
        "question_ko": "외환 관리가 규정에 부합합니까(자본금 결제/이익 송금/국경 간 대출 관련)?",
        "weight": 12,
        "scoring": {
            0: "外汇管理合规，所有跨境资金流动已办理登记",
            1: "基本了解但利润汇出等实务细节不确定",
            2: "知道有外汇管制但不了解经常/资本项目区别",
            3: "通过地下钱庄等非法渠道转移资金"
        },
        "actions": {
            0: [],
            1: ["完善利润汇出操作流程", "确保审计报告和完税证明齐全"],
            2: ["了解经常项目和资本项目的区别和各自要求", "咨询专业会计师进行外汇合规规划"],
            3: ["立即停止任何非法资金转移渠道", "委托专业机构规范外汇管理"]
        },
        "knowledge_ref": "《外汇管理条例》第5-40条 | 《资本项目外汇业务指引》"
    },
    {
        "id": "ops_07",
        "question_zh": "劳务派遣用工比例是否控制在10%以内且仅限三性岗位？",
        "question_ko": "파견 근로 비율이 10% 이내이며 임시·보조·대체 직무에만 한정되어 있습니까?",
        "weight": 10,
        "scoring": {
            0: "派遣比例合规，仅限三性岗位，同工同酬落实到位",
            1: "基本合规但执行标准有待加强",
            2: "使用派遣但不清楚比例限制和三性要求",
            3: "所有员工以劳务派遣形式用工"
        },
        "actions": {
            0: [],
            1: ["审查派遣岗位是否符合三性要求", "确保同工同酬全面落实"],
            2: ["立即核算派遣用工比例", "制定整改计划将比例降至10%以内"],
            3: ["立即整改用工模式", "将核心岗位员工转为直接雇佣"]
        },
        "knowledge_ref": "《劳动合同法》第57-67条 | 《劳务派遣暂行规定》"
    },
    {
        "id": "ops_08",
        "question_zh": "是否已建立知识产权保护体系（商标注册/专利申请/著作权登记/海关备案）？",
        "question_ko": "지식재산권 보호 체계(상표 등록/특허 출원/저작권 등록/세관 등록)를 구축하셨습니까?",
        "weight": 10,
        "scoring": {
            0: "核心商标专利已注册，海关备案已完成，保护体系完善",
            1: "已提交部分申请正在等待审查",
            2: "知道需要注册但尚未行动",
            3: "未考虑知产保护，不了解注册在先原则"
        },
        "actions": {
            0: [],
            1: ["跟进审查进度，及时答复审查意见", "扩大注册类别覆盖范围"],
            2: ["立即进行中国商标检索并提交注册", "评估核心专利是否需要在中国申请"],
            3: ["了解中国「注册在先」原则", "立即启动核心商标的注册保护"]
        },
        "knowledge_ref": "《商标法》第4-30条 | 《专利法》第9-42条 | 《知识产权海关保护条例》"
    }
]

# ====================================================================
# 维度四：贸易合规 (Trade Compliance) — 6个评分项
# ====================================================================
TRADE_ITEMS = [
    {
        "id": "trd_01",
        "question_zh": "进出口商品HS编码归类是否准确？海关申报是否合规？",
        "question_ko": "수출입 상품의 HS 코드 분류가 정확합니까? 세관 신고가 규정에 부합합니까?",
        "weight": 20,
        "scoring": {
            0: "所有商品HS编码归类正确，海关申报及时准确",
            1: "委托专业报关行处理但对最新政策跟进不够",
            2: "计划开展进出口但对HS编码不熟悉",
            3: "完全不了解海关申报和HS编码制度"
        },
        "actions": {
            0: [],
            1: ["定期审查HS编码归类是否正确", "建立海关政策变动跟踪机制"],
            2: ["委托专业报关行进行HS编码归类", "参加进出口合规培训"],
            3: ["了解《海关法》第8-60条基本要求", "聘请专业报关行处理进出口业务"]
        },
        "knowledge_ref": "《海关法》第8-60条 | 《进出口税则》"
    },
    {
        "id": "trd_02",
        "question_zh": "是否已了解并利用中韩FTA原产地规则享受关税优惠？",
        "question_ko": "한중 FTA 원산지 규정을 이해하고 관세 혜택을 활용하고 계십니까?",
        "weight": 18,
        "scoring": {
            0: "已充分利用中韩FTA关税优惠，原产地证管理规范",
            1: "了解FTA优惠但未完全利用所有适用品类",
            2: "知道有中韩FTA但不清楚如何申请优惠",
            3: "完全不了解中韩FTA关税优惠"
        },
        "actions": {
            0: [],
            1: ["审查所有进出口品类是否均可享受FTA优惠", "优化供应链以满足原产地规则"],
            2: ["了解中韩FTA关税减让表和降税安排", "申请原产地证书享受关税优惠"],
            3: ["了解中韩FTA的核心内容和优惠条款", "评估产品是否满足原产地标准"]
        },
        "knowledge_ref": "《中韩自贸协定》原产地规则 | 海关总署关于中韩FTA的公告"
    },
    {
        "id": "trd_03",
        "question_zh": "跨境税务是否合规（转让定价文档/企业所得税/增值税/预提税）？",
        "question_ko": "국경 간 세무가 규정에 부합합니까(이전 가격 문서/법인세/부가가치세/원천징수세)?",
        "weight": 20,
        "scoring": {
            0: "已建立完善的跨境财税体系，转让定价文档合规",
            1: "聘请了专业会计师但对税收协定细节了解不深",
            2: "了解基本税务知识但转让定价等实务不熟悉",
            3: "完全不了解跨境税务和双重征税风险"
        },
        "actions": {
            0: [],
            1: ["完善转让定价文档和同期资料准备", "充分了解中韩税收协定的具体优惠条款"],
            2: ["进行转让定价风险评估", "确保增值税发票管理合规"],
            3: ["了解中韩跨境税务基本框架", "聘请税务顾问进行健康检查"]
        },
        "knowledge_ref": "《企业所得税法》第3-58条 | 《中韩税收协定》第7-23条 | 《增值税暂行条例》"
    },
    {
        "id": "trd_04",
        "question_zh": "进出口许可证管理是否到位（出口管制物项/两用物项/进口许可）？",
        "question_ko": "수출입 허가증 관리가 체계적입니까(수출 통제 품목/이중 용도 품목/수입 허가)?",
        "weight": 16,
        "scoring": {
            0: "已建立进出口许可证管理制度，所有需要许可的产品均已办理",
            1: "基本了解但部分品类许可要求不确定",
            2: "知道可能需要许可证但不清楚范围",
            3: "完全不了解进出口许可证制度"
        },
        "actions": {
            0: [],
            1: ["审查所有进出口产品许可要求", "建立许可证到期续期提醒"],
            2: ["对照进出口许可证目录检查产品", "启动许可证申请流程"],
            3: ["了解进出口许可证制度基本框架", "咨询报关行获取专业指导"]
        },
        "knowledge_ref": "《对外贸易法》 | 《两用物项和技术进出口许可证管理办法》"
    },
    {
        "id": "trd_05",
        "question_zh": "知识产权海关备案是否已完成（商标/专利/著作权）？",
        "question_ko": "지식재산권 세관 등록(상표/특허/저작권)을 완료하셨습니까?",
        "weight": 14,
        "scoring": {
            0: "已完成核心知识产权海关备案并建立查扣响应机制",
            1: "知道制度并准备材料但未提交",
            2: "听说过但不清楚备案作用和流程",
            3: "完全不了解海关知识产权保护制度"
        },
        "actions": {
            0: [],
            1: ["尽快提交海关备案申请", "建立海关查扣应急预案"],
            2: ["了解海关备案免费且一次备案10年有效", "准备备案所需材料"],
            3: ["了解《知识产权海关保护条例》基本内容", "评估是否需要进行海关备案"]
        },
        "knowledge_ref": "《知识产权海关保护条例》第2-24条 | 《关于<知识产权海关保护条例>的实施办法》"
    },
    {
        "id": "trd_06",
        "question_zh": "跨境电子商务零售进口是否已完成海关备案和消费者身份信息核验？",
        "question_ko": "국경 간 전자상거래 소매 수입에 대해 세관 등록과 소비자 신원 정보 확인을 완료하셨습니까?",
        "weight": 12,
        "scoring": {
            0: "已完成海关备案，消费者身份信息核验机制完善",
            1: "基本完成但部分流程有待优化",
            2: "知道跨境电商有特殊监管要求但不了解",
            3: "完全不了解跨境电商零售进口监管政策"
        },
        "actions": {
            0: [],
            1: ["优化消费者下单身份信息核验流程", "确保年度交易限额管理合规"],
            2: ["了解跨境电商零售进口正面清单", "完成海关备案手续"],
            3: ["了解跨境电商零售进口政策框架", "咨询跨境电商合规专家"]
        },
        "knowledge_ref": "《关于完善跨境电子商务零售进口监管有关工作的通知》 | 海关总署跨境电商监管公告"
    }
]

# ====================================================================
# 维度定义聚合
# ====================================================================
DIMENSIONS = [
    {
        "id": "access",
        "name_zh": "准入合规",
        "name_ko": "진입 규제",
        "description_zh": "外商投资准入负面清单、行业限制、公司设立架构与市场准入",
        "description_ko": "외국인 투자 네거티브 리스트, 업종 제한, 회사 설립 구조 및 시장 진입",
        "items": ACCESS_ITEMS,
        "icon": "🔑"
    },
    {
        "id": "industry",
        "name_zh": "行业合规",
        "name_ko": "업종 규제",
        "description_zh": "食品/化妆品/IT/医药等行业专项法规、产品质量标准、广告合规",
        "description_ko": "식품/화장품/IT/의약품 등 업종별 규제, 제품 품질 기준, 광고 규제",
        "items": INDUSTRY_ITEMS,
        "icon": "🏭"
    },
    {
        "id": "operations",
        "name_zh": "运营合规",
        "name_ko": "운영 규제",
        "description_zh": "数据安全、劳动用工、外籍签证、反商业贿赂、外汇管制",
        "description_ko": "데이터 보안, 노동 고용, 외국인 비자, 반뇌물, 외환 관리",
        "items": OPERATIONS_ITEMS,
        "icon": "⚙️"
    },
    {
        "id": "trade",
        "name_zh": "贸易合规",
        "name_ko": "무역 규제",
        "description_zh": "进出口海关、HS编码、原产地证、中韩FTA关税、跨境税务",
        "description_ko": "수출입 세관, HS 코드, 원산지 증명, 한중 FTA 관세, 국경 간 세무",
        "items": TRADE_ITEMS,
        "icon": "📦"
    }
]

# 展平所有评分项到全局映射
ALL_ITEMS = {}
for dim in DIMENSIONS:
    for item in dim["items"]:
        ALL_ITEMS[item["id"]] = {**item, "dimension": dim["id"]}

# 各维度总分权重（四维度权重相等，各25%）
DIM_WEIGHT = 25.0


# ====================================================================
# 评分核心函数
# ====================================================================

def score_item(item: dict, answer_value: int) -> dict:
    """
    对单个评分项进行评分
    answer_value: 0-3 (0=最合规, 3=最不合规)
    返回: {score, max_score, percentage, action_items}
    """
    weight = item["weight"]
    max_score = 3  # 每项满分3分
    raw = answer_value  # 0-3

    # 得分越高越好 — 转换: 3-raw 然后归一化到 weight
    # 如果 answer_value=0, 得分=weight (满分)
    # 如果 answer_value=3, 得分=0
    item_score = weight * (max_score - raw) / max_score

    actions = item.get("actions", {}).get(raw, [])
    return {
        "item_id": item["id"],
        "question_zh": item["question_zh"],
        "question_ko": item["question_ko"],
        "answer_value": raw,
        "weight": weight,
        "score": round(item_score, 1),
        "max_possible": weight,
        "percentage": round((max_score - raw) / max_score * 100, 1),
        "actions": actions
    }


def score_dimension(dim: dict, answers: Dict[str, int]) -> dict:
    """
    对某个维度的所有评分项进行评分
    answers: {item_id: answer_value(0-3)}
    返回: {dimension_id, score, max_possible, percentage, items_scores, actions}
    """
    total_weight = 0
    total_score = 0
    item_scores = []
    all_actions = []

    for item in dim["items"]:
        aid = item["id"]
        if aid in answers:
            raw = answers[aid]
        else:
            raw = 0  # 未回答默认为合规（低风险）

        result = score_item(item, raw)
        total_weight += result["weight"]
        total_score += result["score"]
        item_scores.append(result)
        all_actions.extend(result["actions"])

    percentage = round(total_score / total_weight * 100, 1) if total_weight > 0 else 100.0

    # 维度风险等级
    if percentage >= 80:
        risk = "低"
    elif percentage >= 60:
        risk = "中"
    elif percentage >= 30:
        risk = "高"
    else:
        risk = "严重"

    return {
        "dimension_id": dim["id"],
        "name_zh": dim["name_zh"],
        "name_ko": dim["name_ko"],
        "description_zh": dim["description_zh"],
        "icon": dim["icon"],
        "score": round(total_score, 1),
        "max_possible": round(total_weight, 1),
        "percentage": percentage,
        "risk_level": risk,
        "items": item_scores,
        "priority_actions": list(dict.fromkeys(all_actions))  # 去重保序
    }


def get_risk_level(percentage: float) -> str:
    """根据百分比确定风险等级 (0-100)"""
    if percentage >= 80:
        return "低"
    elif percentage >= 60:
        return "中"
    elif percentage >= 30:
        return "高"
    else:
        return "严重"


def get_risk_color(level: str) -> str:
    """风险等级对应的颜色"""
    return {"低": "green", "中": "yellow", "高": "orange", "严重": "red"}.get(level, "gray")


def calculate_total_score(dimension_results: List[dict]) -> dict:
    """
    计算总评分
    综合四个维度的加权平均（每个维度权重25%）
    """
    dim_count = len(dimension_results)
    if dim_count == 0:
        return {"total_score": 0, "total_percentage": 0, "risk_level": "未知"}

    total_percentage = round(
        sum(d["percentage"] for d in dimension_results) / dim_count, 1
    )
    total_score = round(
        sum(d["score"] for d in dimension_results), 1
    )
    total_max = round(
        sum(d["max_possible"] for d in dimension_results), 1
    )

    risk_level = get_risk_level(total_percentage)

    return {
        "total_score": total_score,
        "total_max": total_max,
        "total_percentage": total_percentage,
        "risk_level": risk_level,
        "risk_color": get_risk_color(risk_level),
        "risk_description_zh": {
            "低": "整体合规状况良好，建议持续监控法规变化",
            "中": "存在一定合规风险，建议优先处理中低分维度的问题",
            "高": "合规风险较高，需要立即制定整改计划",
            "严重": "存在严重合规隐患，建议立即启动全面合规整改"
        }.get(risk_level, ""),
        "risk_description_ko": {
            "低": "전반적 규제 상태 양호, 지속적 모니터링 권장",
            "中": "일정 수준 규제 위험 존재, 중저점 분야 우선 처리 권장",
            "高": "규제 위험 높음, 즉시 개선 계획 수립 필요",
            "严重": "심각한 규제 위험 존재, 전면적 규제 개선 즉시 시작 필요"
        }.get(risk_level, "")
    }


def compile_priority_actions(dimension_results: List[dict]) -> List[dict]:
    """
    汇总所有维度的优先级行动清单
    按严重程度排序：严重 > 高 > 中 > 低
    """
    risk_order = {"严重": 0, "高": 1, "中": 2, "低": 3}
    all_actions = []

    for dim_result in dimension_results:
        dim_risk = dim_result["risk_level"]
        for action_text in dim_result["priority_actions"]:
            all_actions.append({
                "dimension_id": dim_result["dimension_id"],
                "dimension_name_zh": dim_result["name_zh"],
                "dimension_risk": dim_risk,
                "action": action_text,
                "priority": risk_order.get(dim_risk, 99)
            })

    # 按风险优先级排序
    all_actions.sort(key=lambda x: (x["priority"], x["dimension_id"]))

    # 去重
    seen = set()
    unique_actions = []
    for a in all_actions:
        key = a["action"]
        if key not in seen:
            seen.add(key)
            unique_actions.append(a)

    return unique_actions


def compile_scoring_report(
    answers: Dict[str, int],
    session_id: Optional[str] = None,
    company_type: Optional[str] = None,
    industry: Optional[str] = None
) -> dict:
    """
    主评分函数 — 输入各评分项答案，输出完整评分报告
    answers: {item_id: 0|1|2|3}
    """
    # 评分每个维度
    dimension_results = []
    for dim in DIMENSIONS:
        result = score_dimension(dim, answers)
        dimension_results.append(result)

    # 计算总评分
    total = calculate_total_score(dimension_results)

    # 生成优先级行动清单
    priority_actions = compile_priority_actions(dimension_results)

    # 按维度排序展示评分
    dimension_results.sort(key=lambda d: d["percentage"])

    return {
        "report_id": uuid.uuid4().hex[:12],
        "session_id": session_id,
        "company_type": company_type,
        "industry": industry,
        "generated_at": datetime.now().isoformat(),
        "scoring_framework": "MECE四维合规评分引擎 v1.0",
        "total": total,
        "dimensions": dimension_results,
        "priority_actions": priority_actions,
        "summary_zh": (
            f"总评分: {total['total_percentage']}分 — 风险等级: {total['risk_level']}。"
            f"四个维度中评分最低的是「{dimension_results[0]['name_zh']}」({dimension_results[0]['percentage']}分)"
            f"，建议优先处理该维度的问题。共识别 {len(priority_actions)} 项优先级行动事项。"
        ),
        "summary_ko": (
            f"총점: {total['total_percentage']}점 — 위험 등급: {total['risk_level']}。"
            f"4개 차원 중 최저점은 '{dimension_results[0]['name_ko']}'({dimension_results[0]['percentage']}점)"
            f"，해당 차원 우선 처리 권장. 총 {len(priority_actions)}건 우선 조치 사항 식별."
        )
    }


# ====================================================================
# API接口
# ====================================================================

class ScoringAnswers(BaseModel):
    """评分答案提交请求体"""
    session_id: Optional[str] = None
    company_type: Optional[str] = None
    industry: Optional[str] = None
    answers: Dict[str, int]  # {item_id: 0|1|2|3}


class ScoringQuery(BaseModel):
    """基于诊断session的评分查询"""
    session_id: str


@router.get("/dimensions")
def get_scoring_dimensions():
    """获取评分维度定义（含所有评分项）"""
    result = []
    for dim in DIMENSIONS:
        result.append({
            "id": dim["id"],
            "name_zh": dim["name_zh"],
            "name_ko": dim["name_ko"],
            "description_zh": dim["description_zh"],
            "description_ko": dim["description_ko"],
            "icon": dim["icon"],
            "items": [
                {
                    "id": item["id"],
                    "question_zh": item["question_zh"],
                    "question_ko": item["question_ko"],
                    "weight": item["weight"],
                    "scoring": item["scoring"],
                    "knowledge_ref": item["knowledge_ref"]
                }
                for item in dim["items"]
            ]
        })
    return {
        "dimensions": result,
        "total_dimensions": len(DIMENSIONS),
        "total_items": len(ALL_ITEMS),
        "scoring_range": "0-3 (0=低风险/最合规, 3=高风险/最不合规)"
    }


@router.post("/evaluate")
def evaluate_scoring(req: ScoringAnswers):
    """
    提交答案进行合规评分
    可直接提交answers，也可关联诊断session
    """
    # 验证答案值
    for item_id, value in req.answers.items():
        if item_id not in ALL_ITEMS:
            raise HTTPException(400, f"未知的评分项ID: {item_id}")
        if value not in (0, 1, 2, 3):
            raise HTTPException(400, f"评分项 {item_id} 的值必须为0-3")

    report = compile_scoring_report(
        answers=req.answers,
        session_id=req.session_id,
        company_type=req.company_type,
        industry=req.industry
    )

    # 如果关联了诊断session，保存评分结果到数据库
    if req.session_id:
        try:
            conn = _diag_db()
            # 确保有scoring_results表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scoring_results (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    report_json TEXT,
                    total_score REAL,
                    risk_level TEXT,
                    created_at TEXT
                )
            """)
            conn.execute(
                "INSERT INTO scoring_results (id, session_id, report_json, total_score, risk_level, created_at) VALUES (?,?,?,?,?,?)",
                (
                    report["report_id"],
                    req.session_id,
                    json.dumps(report, ensure_ascii=False),
                    report["total"]["total_percentage"],
                    report["total"]["risk_level"],
                    datetime.now().isoformat()
                )
            )
            conn.commit()
            conn.close()
        except Exception as e:
            # 数据库错误不应阻断评分返回
            pass

    return report


@router.get("/result/{session_id}")
def get_scoring_result(session_id: str):
    """
    从诊断session获取已保存的评分结果
    """
    conn = _diag_db()
    try:
        row = conn.execute(
            "SELECT * FROM scoring_results WHERE session_id=? ORDER BY created_at DESC LIMIT 1",
            (session_id,)
        ).fetchone()
        conn.close()

        if not row:
            raise HTTPException(404, "该会话暂无评分结果，请先通过 /evaluate 接口提交答案")

        return {
            "report_id": row["id"],
            "session_id": row["session_id"],
            "total_score": row["total_score"],
            "risk_level": row["risk_level"],
            "generated_at": row["created_at"],
            "report": json.loads(row["report_json"])
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(500, f"查询评分结果失败: {str(e)}")


@router.get("/from-diag/{session_id}")
def score_from_diagnosis(session_id: str):
    """
    从诊断session的答案自动映射到评分引擎
    将compliance_diagnosis的答案映射到MECE评分项的答案
    """
    conn = _diag_db()
    session = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not session:
        conn.close()
        raise HTTPException(404, "诊断会话不存在")

    answers_raw = conn.execute(
        "SELECT * FROM answers WHERE session_id=?", (session_id,)
    ).fetchall()
    conn.close()

    if not answers_raw:
        raise HTTPException(400, "该会话暂无答案数据，请先提交诊断答案")

    # 诊断维度和评分项维度映射
    DIAG_TO_SCORE_DIM = {
        "industry_access": "access",
        "data_security": "operations",
        "intellectual_property": "operations",
        "cross_border_tax": "trade",
        "labor_employment": "operations",
        "visa_immigration": "operations",
        "company_formation": "access",
        "import_export": "trade"
    }

    # 诊断答案分值(0-2) → 评分项分值(0-3) 映射
    diag_answers = {}
    for a in answers_raw:
        dim = a["dimension"]
        raw_score = a["score"]  # 0, 1, or 2
        # 将0-2映射到0-3 (0->0, 1->1.5->映射到2, 2->3)
        mapped_score = min(3, raw_score * 3 // 2) if raw_score > 0 else 0
        # 映射到评分项
        score_dim = DIAG_TO_SCORE_DIM.get(dim, "operations")
        # 找到对应的评分维度第一个匹配项
        for d in DIMENSIONS:
            if d["id"] == score_dim:
                if d["items"]:
                    first_item_id = d["items"][0]["id"]
                    diag_answers[first_item_id] = mapped_score
                break

    if not diag_answers:
        raise HTTPException(400, "无法从诊断答案映射到评分项")

    # 使用诊断session的company_type和industry
    company_type = session["company_type"] if session["company_type"] else None
    industry = session["industry"] if session["industry"] else None

    report = compile_scoring_report(
        answers=diag_answers,
        session_id=session_id,
        company_type=company_type,
        industry=industry
    )

    # 保存结果
    try:
        conn2 = _diag_db()
        conn2.execute("""
            CREATE TABLE IF NOT EXISTS scoring_results (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                report_json TEXT,
                total_score REAL,
                risk_level TEXT,
                created_at TEXT
            )
        """)
        conn2.execute(
            "INSERT INTO scoring_results (id, session_id, report_json, total_score, risk_level, created_at) VALUES (?,?,?,?,?,?)",
            (
                report["report_id"],
                session_id,
                json.dumps(report, ensure_ascii=False),
                report["total"]["total_percentage"],
                report["total"]["risk_level"],
                datetime.now().isoformat()
            )
        )
        conn2.commit()
        conn2.close()
    except Exception:
        pass

    return {
        "message_zh": "基于诊断会话自动生成MECE合规评分",
        "message_ko": "진단 세션 기반 MECE 규제 점수 자동 생성",
        "mapped_from": "compliance_diagnosis",
        "mapped_item_count": len(diag_answers),
        **report
    }


@router.get("/knowledge-refs")
def get_knowledge_references(dimension: Optional[str] = None):
    """
    获取所有评分项的知识引用（关联合规知识图谱）
    """
    refs = []
    for dim in DIMENSIONS:
        if dimension and dim["id"] != dimension:
            continue
        for item in dim["items"]:
            refs.append({
                "item_id": item["id"],
                "dimension_id": dim["id"],
                "dimension_name_zh": dim["name_zh"],
                "question_zh": item["question_zh"],
                "knowledge_ref": item["knowledge_ref"]
            })

    # 尝试从知识图谱数据库获取补充引用
    try:
        kb = _knowledge_db()
        if kb:
            for ref in refs:
                dim_id = ref["dimension_id"]
                articles = kb.execute(
                    "SELECT regulation, article_number, title, summary FROM knowledge_graph WHERE dimension_id=? LIMIT 3",
                    (dim_id,)
                ).fetchall()
                if articles:
                    ref["articles"] = [
                        {
                            "regulation": a["regulation"],
                            "article": a["article_number"],
                            "title": a["title"],
                            "summary": a["summary"][:100] if a["summary"] else ""
                        }
                        for a in articles
                    ]
            kb.close()
    except Exception:
        pass

    return {"references": refs, "total": len(refs)}


@router.get("/stats")
def get_scoring_stats():
    """
    评分引擎统计信息
    """
    stats = {
        "framework": "MECE四维合规评分引擎 v1.0",
        "total_dimensions": len(DIMENSIONS),
        "total_scoring_items": len(ALL_ITEMS),
        "dimensions": [
            {
                "id": d["id"],
                "name_zh": d["name_zh"],
                "name_ko": d["name_ko"],
                "items_count": len(d["items"]),
                "total_weight": sum(i["weight"] for i in d["items"])
            }
            for d in DIMENSIONS
        ],
        "risk_levels": {
            "低": "80-100分 - 合规状况良好，持续监控",
            "中": "60-79分 - 存在一定风险，需关注中低分项",
            "高": "30-59分 - 高风险，需要立即整改",
            "严重": "0-29分 - 严重不合规，需紧急全面整顿"
        },
        "scoring_method": "每项0-3分制，按权重加权计算维度分，四维等权(各25%)计算总分"
    }

    # 统计已保存的评分结果
    try:
        conn = _diag_db()
        total = conn.execute("SELECT COUNT(*) as c FROM scoring_results").fetchone()[0]
        avg = conn.execute("SELECT AVG(total_score) as avg FROM scoring_results").fetchone()[0]
        conn.close()
        stats["saved_results"] = {"total": total, "average_score": round(avg, 1) if avg else 0}
    except Exception:
        stats["saved_results"] = {"total": 0, "average_score": 0}

    return stats
