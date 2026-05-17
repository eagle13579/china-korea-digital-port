"""
한국 기업 중국 진입 규정 준수 데이터 모듈
=========================================
화장품 · 식품 · 건강기능식품 3대 업종의 중국 수입 요구사항

Korean Enterprise China Entry Compliance Data Module
Cosmetics, Food, and Health Supplements Import Requirements
"""

# ─── 업종 분류 (Industry Categories) ───

INDUSTRIES = {
    "cosmetics": {
        "id": "cosmetics",
        "name_ko": "화장품",
        "name_zh": "化妆品",
        "name_en": "Cosmetics",
        "icon": "💄",
        "description_ko": "한국 화장품의 중국 수입을 위한 규정 준수 체크리스트",
        "description_zh": "韩国化妆品进口中国的合规检查清单",
    },
    "food": {
        "id": "food",
        "name_ko": "식품",
        "name_zh": "食品",
        "name_en": "Food",
        "icon": "🍜",
        "description_ko": "한국 식품의 중국 수입을 위한 규정 준수 체크리스트",
        "description_zh": "韩国食品进口中国的合规检查清单",
    },
    "health_supplements": {
        "id": "health_supplements",
        "name_ko": "건강기능식품",
        "name_zh": "保健品",
        "name_en": "Health Supplements",
        "icon": "💊",
        "description_ko": "한국 건강기능식품의 중국 수입을 위한 규정 준수 체크리스트",
        "description_zh": "韩国保健食品进口中国的合规检查清单",
    },
}

# ─── 화장품 규정 준수 데이터 ───
# Cosmetics Compliance Data

COSMETICS_COMPLIANCE = {
    "industry_id": "cosmetics",
    "industry_ko": "화장품",
    "industry_zh": "化妆品",
    "overview_ko": "중국 화장품 시장은 2024년 기준 약 5,000억 위안 규모로, 한국 화장품 수출 1위 시장입니다. 2021년 시행된 '화장품 감독 관리 조례'에 따라 등록·신고 관리가 강화되었습니다.",
    "overview_zh": "中国化妆品市场2024年约5000亿元规模，是韩国化妆品第一大出口市场。2021年《化妆品监督管理条例》实施，注册备案管理加强。",

    "checklist": [
        {
            "id": "cos-01",
            "category_ko": "제품 등록·신고",
            "category_zh": "产品注册备案",
            "items": [
                {
                    "id": "cos-01-01",
                    "title_ko": "NMPA 화장품 등록/신고 완료",
                    "title_zh": "完成NMPA化妆品注册/备案",
                    "description_ko": "일반 화장품은 신고제, 기능성 화장품은 등록제. NMPA(국약감독관리국)에 제품 정보를 제출해야 합니다.",
                    "description_zh": "普通化妆品实行备案制，特殊化妆品实行注册制。需向NMPA（国家药监局）提交产品信息。",
                    "risk_level": "high",
                    "estimated_time_ko": "3~6개월",
                    "estimated_time_zh": "3-6个月",
                    "required_docs_ko": ["제품 성분표", "안전성 평가 보고서", "제조 공정 설명서", "제품 규격 기준"],
                    "required_docs_zh": ["产品成分表", "安全性评估报告", "生产工艺说明", "产品规格标准"],
                },
                {
                    "id": "cos-01-02",
                    "title_ko": "화장품 안전성 평가 보고서",
                    "title_zh": "化妆品安全评估报告",
                    "description_ko": "중국 내 또는 해외 공인 기관에서 발급한 안전성 평가 보고서 필요. 신규 성분은 추가 안전성 자료 필요.",
                    "description_zh": "需由中国境内或境外认可机构出具的安全评估报告。新原料需额外安全资料。",
                    "risk_level": "high",
                    "estimated_time_ko": "1~3개월",
                    "estimated_time_zh": "1-3个月",
                    "required_docs_ko": ["안전성 평가 보고서", "원료 안전성 자료", "독성학 시험 데이터"],
                    "required_docs_zh": ["安全评估报告", "原料安全性资料", "毒理学试验数据"],
                },
                {
                    "id": "cos-01-03",
                    "title_ko": "금지·제한 원료 확인",
                    "title_zh": "禁用/限用原料确认",
                    "description_ko": "중국 화장품 금지 원료 목록 및 제한 원료 목록에 포함되지 않았는지 확인. 《화장품 안전 기술 규범》에 따라 검토.",
                    "description_zh": "确认不属于中国化妆品禁用和限用原料目录。按《化妆品安全技术规范》审核。",
                    "risk_level": "high",
                    "estimated_time_ko": "2주~1개월",
                    "estimated_time_zh": "2周-1个月",
                    "required_docs_ko": ["원료 성분 분석표", "금지 원료 미포함 증명서"],
                    "required_docs_zh": ["原料成分分析表", "不含禁用原料证明"],
                },
            ],
        },
        {
            "id": "cos-02",
            "category_ko": "라벨 및 포장",
            "category_zh": "标签与包装",
            "items": [
                {
                    "id": "cos-02-01",
                    "title_ko": "중국어 라벨 부착",
                    "title_zh": "中文标签标注",
                    "description_ko": "모든 수입 화장품은 중국어 라벨 필수. 《화장품 라벨 관리 방법》에 따라 제품명, 성분, 제조사, 수입업체 등 표기.",
                    "description_zh": "所有进口化妆品必须加贴中文标签。按《化妆品标签管理办法》标注产品名称、成分、生产商、进口商等信息。",
                    "risk_level": "medium",
                    "estimated_time_ko": "1~2주",
                    "estimated_time_zh": "1-2周",
                    "required_docs_ko": ["중국어 라벨 원고", "라벨 번역 증명서"],
                    "required_docs_zh": ["中文标签样稿", "标签翻译证明"],
                },
                {
                    "id": "cos-02-02",
                    "title_ko": "효능 표시 규정 준수",
                    "title_zh": "功效宣称合规",
                    "description_ko": "화장품 효능 표시는 NMPA 발표 '화장품 효능 표시 규범'에 따라야 함. 26가지 효능 분류 중에 속해야 함.",
                    "description_zh": "化妆品功效宣称须符合NMPA《化妆品功效宣称评价规范》，须在26类功效分类范围内。",
                    "risk_level": "medium",
                    "estimated_time_ko": "1~2개월",
                    "estimated_time_zh": "1-2个月",
                    "required_docs_ko": ["효능 평가 증빙 자료", "효능 성분 함량 증명서"],
                    "required_docs_zh": ["功效评价佐证材料", "功效成分含量证明"],
                },
            ],
        },
        {
            "id": "cos-03",
            "category_ko": "검사 및 통관",
            "category_zh": "检验与通关",
            "items": [
                {
                    "id": "cos-03-01",
                    "title_ko": "출입경 검사 검역국 검사",
                    "title_zh": "海关检验检疫",
                    "description_ko": "수입 화장품은 세관(Customs)의 강제성 검사 필수. 검사 합격 후 '입경 화장품 검사 검역 증명서' 발급.",
                    "description_zh": "进口化妆品须经海关强制性检验。检验合格后签发《入境货物检验检疫证明》。",
                    "risk_level": "high",
                    "estimated_time_ko": "2주~1개월",
                    "estimated_time_zh": "2周-1个月",
                    "required_docs_ko": ["수입 계약서", "송장", "포장 명세서", "원산지 증명서", "위생 증명서"],
                    "required_docs_zh": ["进口合同", "发票", "装箱单", "原产地证", "卫生证书"],
                },
                {
                    "id": "cos-03-02",
                    "title_ko": "수출입 경영자 등록",
                    "title_zh": "进出口经营备案",
                    "description_ko": "중국 수입업체는 '수출입 경영자 등록' 완료 필수. 해외 제조사도 NMPA에 해외 제조사 등록 필요.",
                    "description_zh": "中国进口商须完成进出口经营备案。境外生产企业也须在NMPA进行境外生产企业备案。",
                    "risk_level": "medium",
                    "estimated_time_ko": "2~4주",
                    "estimated_time_zh": "2-4周",
                    "required_docs_ko": ["영업 허가증", "수출입 경영자 등록 증명서"],
                    "required_docs_zh": ["营业执照", "进出口经营者备案证明"],
                },
            ],
        },
    ],

    "key_regulations_ko": [
        "《화장품 감독 관리 조례》 (2021.01.01 시행)",
        "《화장품 등록·신고 관리 방법》",
        "《화장품 안전 기술 규범》 (2015年版)",
        "《화장품 효능 표시 규범》",
        "《화장품 라벨 관리 방법》",
    ],
    "key_regulations_zh": [
        "《化妆品监督管理条例》(2021.01.01施行)",
        "《化妆品注册备案管理办法》",
        "《化妆品安全技术规范》(2015年版)",
        "《化妆品功效宣称评价规范》",
        "《化妆品标签管理办法》",
    ],
    "risk_tips_ko": [
        "⚠️ 2021년 이후 등록·신고 제도가 대폭 강화되었습니다. 반드시 최신 규정을 확인하세요.",
        "⚠️ '중국 표준' 성분과 다른 성분명 사용 시 통관 거부될 수 있습니다.",
        "⚠️ 온라인 판매(타오바오·징둥) 시에도 동일한 등록·신고 요건이 적용됩니다.",
    ],
    "risk_tips_zh": [
        "⚠️ 2021年后注册备案制度大幅加强，务必确认最新规定。",
        "⚠️ 成分名称与中国标准不一致可能导致通关被拒。",
        "⚠️ 线上销售（淘宝/京东）同样适用注册备案要求。",
    ],
}

# ─── 식품 규정 준수 데이터 ───
# Food Compliance Data

FOOD_COMPLIANCE = {
    "industry_id": "food",
    "industry_ko": "식품",
    "industry_zh": "食品",
    "overview_ko": "중국 식품 시장은 한국 식품 수출의 핵심 시장입니다. 《중국 식품 안전법》 및 수입 식품 관리 규정에 따라 엄격한 통관 심사가 이루어집니다.",
    "overview_zh": "中国食品市场是韩国食品出口的核心市场。依据《中国食品安全法》及进口食品管理规定进行严格通关审查。",

    "checklist": [
        {
            "id": "food-01",
            "category_ko": "수입 식품 허가",
            "category_zh": "进口食品许可",
            "items": [
                {
                    "id": "food-01-01",
                    "title_ko": "해외 제조업체 등록",
                    "title_zh": "境外生产企业注册",
                    "description_ko": "중국으로 식품을 수출하는 모든 해외 제조업체는 중국 세관에 등록 필수. 18개 고위험 식품(육류·수산물·유제품 등)은 현장 심사 필요.",
                    "description_zh": "所有向中国出口食品的境外生产企业须在中国海关总署注册。18类高风险食品（肉、水产、乳制品等）需现场审核。",
                    "risk_level": "high",
                    "estimated_time_ko": "1~6개월",
                    "estimated_time_zh": "1-6个月",
                    "required_docs_ko": ["제조업체 등록 신청서", "위생 관리 증명서", "HACCP/ISO22000 인증서"],
                    "required_docs_zh": ["生产企业注册申请书", "卫生管理体系证明", "HACCP/ISO22000认证"],
                },
                {
                    "id": "food-01-02",
                    "title_ko": "수입 식품 라벨 사전 심사",
                    "title_zh": "进口食品标签预审",
                    "description_ko": "모든 수입 식품에 중국어 라벨 필수. GB 7718(식품 라벨 규칙) 및 GB 28050(영양 성분 표시 기준) 준수해야 함.",
                    "description_zh": "所有进口食品须加贴中文标签。须符合GB 7718《预包装食品标签通则》和GB 28050《营养标签通则》。",
                    "risk_level": "high",
                    "estimated_time_ko": "2~4주",
                    "estimated_time_zh": "2-4周",
                    "required_docs_ko": ["중국어 라벨 샘플", "영양 성분 분석표", "원재료 성분표"],
                    "required_docs_zh": ["中文标签样本", "营养成分分析表", "原料成分表"],
                },
                {
                    "id": "food-01-03",
                    "title_ko": "검역 허가 (특정 식품)",
                    "title_zh": "检疫准入（特定食品）",
                    "description_ko": "육류·수산물·유제품·곡물 등 특정 식품은 중국과 한국 간 검역 협정 필요. 검역 허가 목록에 포함되어야 수출 가능.",
                    "description_zh": "肉类、水产、乳制品、谷物等特定食品需中韩两国间检疫协议。须在检疫准入名单内方可出口。",
                    "risk_level": "high",
                    "estimated_time_ko": "3~12개월",
                    "estimated_time_zh": "3-12个月",
                    "required_docs_ko": ["검역 허가 신청서", "위생 검역 증명서", "무역 계약서"],
                    "required_docs_zh": ["检疫准入申请书", "卫生检疫证书", "贸易合同"],
                },
            ],
        },
        {
            "id": "food-02",
            "category_ko": "식품 첨가물 및 기준",
            "category_zh": "食品添加剂与标准",
            "items": [
                {
                    "id": "food-02-01",
                    "title_ko": "식품 첨가물 GB 기준 적합",
                    "title_zh": "食品添加剂符合GB标准",
                    "description_ko": "사용된 모든 식품 첨가물이 GB 2760《식품 첨가물 사용 기준》에 적합해야 함. 한국에서 허용되나 중국에서 금지된 첨가물 확인 필수.",
                    "description_zh": "所有使用的食品添加剂须符合GB 2760《食品添加剂使用标准》。须确认韩国允许但中国禁止的添加剂。",
                    "risk_level": "high",
                    "estimated_time_ko": "1~2개월",
                    "estimated_time_zh": "1-2个月",
                    "required_docs_ko": ["식품 첨가물 사용 명세서", "GB 2760 적합성 분석 보고서"],
                    "required_docs_zh": ["食品添加剂使用明细表", "GB 2760符合性分析报告"],
                },
                {
                    "id": "food-02-02",
                    "title_ko": "식품 중 농약·중금속 잔류 기준",
                    "title_zh": "农药/重金属残留标准",
                    "description_ko": "GB 2762 및 GB 2763에 따른 농약·중금속 잔류 허용 기준 충족 필요. 한국과 중국의 기준이 다를 수 있으므로 사전 분석 필수.",
                    "description_zh": "须符合GB 2762和GB 2763规定的农药残留和重金属限量。中韩标准可能存在差异，须事先检测分析。",
                    "risk_level": "medium",
                    "estimated_time_ko": "2~4주",
                    "estimated_time_zh": "2-4周",
                    "required_docs_ko": ["잔류 농약 분석 보고서", "중금속 분석 보고서", "미생물 검사 보고서"],
                    "required_docs_zh": ["农药残留检测报告", "重金属检测报告", "微生物检测报告"],
                },
            ],
        },
        {
            "id": "food-03",
            "category_ko": "통관 및 유통",
            "category_zh": "通关与流通",
            "items": [
                {
                    "id": "food-03-01",
                    "title_ko": "수입 식품 통관 검사",
                    "title_zh": "进口食品通关查验",
                    "description_ko": "세관에서 수입 식품에 대해 서류 심사, 현장 검사, 실험실 검사 진행. 검사 합격 후 '입경 검사 검역 증명서' 발급.",
                    "description_zh": "海关对进口食品实施单证审核、现场查验、实验室检验。检验合格后签发《入境检验检疫证明》。",
                    "risk_level": "high",
                    "estimated_time_ko": "2주~2개월",
                    "estimated_time_zh": "2周-2个月",
                    "required_docs_ko": ["수입 계약서", "송장", "포장 명세서", "원산지 증명서", "위생 증명서", "제조업체 등록 증명서"],
                    "required_docs_zh": ["进口合同", "发票", "装箱单", "原产地证", "卫生证书", "生产企业注册证明"],
                },
                {
                    "id": "food-03-02",
                    "title_ko": "식품 수입·판매 기록 관리",
                    "title_zh": "食品进口/销售记录管理",
                    "description_ko": "수입 식품의 수입 기록, 유통 기록, 판매 기록을 2년 이상 보관 필수. 역추적 시스템 구축 필요.",
                    "description_zh": "须保存进口食品进口记录、流通记录、销售记录不少于2年。须建立追溯体系。",
                    "risk_level": "medium",
                    "estimated_time_ko": "1~2주",
                    "estimated_time_zh": "1-2周",
                    "required_docs_ko": ["수입 기록 대장", "유통 기록 대장", "역추적 시스템 구축 증명"],
                    "required_docs_zh": ["进口记录台账", "流通记录台账", "追溯系统建设证明"],
                },
            ],
        },
    ],

    "key_regulations_ko": [
        "《중국 식품 안전법》 및 시행 조례",
        "《수입 식품 관리 방법》",
        "GB 7718-2011《예포장 식품 라벨 통칙》",
        "GB 28050-2011《영양 성분 표시 기준》",
        "GB 2760-2024《식품 첨가물 사용 기준》",
        "GB 2762-2022《식품 중 오염물질 한계》",
    ],
    "key_regulations_zh": [
        "《中华人民共和国食品安全法》及实施条例",
        "《进口食品管理办法》",
        "GB 7718-2011《预包装食品标签通则》",
        "GB 28050-2011《营养标签通则》",
        "GB 2760-2024《食品添加剂使用标准》",
        "GB 2762-2022《食品中污染物限量》",
    ],
    "risk_tips_ko": [
        "⚠️ 2022년부터 해외 제조업체 등록 제도가 전면 시행되어 등록 미완료 시 수입 불가",
        "⚠️ 한국과 중국의 식품 첨가물 사용 기준이 다를 수 있음, 사전 전문가 검토 필수",
        "⚠️ 코로나19 이후 수입 식품에 대한 세관 검사가 강화되었음",
    ],
    "risk_tips_zh": [
        "⚠️ 2022年起境外生产企业注册制度全面实施，未注册不得进口",
        "⚠️ 中韩食品添加剂使用标准可能存在差异，须事先经专家审核",
        "⚠️ 疫情后海关对进口食品的查验力度加强",
    ],
}

# ─── 건강기능식품 규정 준수 데이터 ───
# Health Supplements Compliance Data

HEALTH_SUPPLEMENTS_COMPLIANCE = {
    "industry_id": "health_supplements",
    "industry_ko": "건강기능식품",
    "industry_zh": "保健食品",
    "overview_ko": "중국 건강기능식품(보건식품) 시장은 2024년 기준 약 3,000억 위안 규모입니다. 한국 인삼·홍삼 제품이 특히 인기가 높으나, CFDA(식약청) 등록이 필수입니다.",
    "overview_zh": "中国保健食品市场2024年约3000亿元规模。韩国高丽参/红参产品尤其受欢迎，但须经CFDA（原食药监局）注册。",

    "checklist": [
        {
            "id": "health-01",
            "category_ko": "제품 등록·허가",
            "category_zh": "产品注册审批",
            "items": [
                {
                    "id": "health-01-01",
                    "title_ko": "CFDA 보건식품 등록 완료",
                    "title_zh": "CFDA保健食品注册",
                    "description_ko": "모든 수입 건강기능식품은 중국 국가시장감독관리총국(SAMR)에 제품 등록 필수. 등록 기간은 1~3년 소요.",
                    "description_zh": "所有进口保健食品须在中国国家市场监督管理总局(SAMR)进行产品注册。注册周期1-3年。",
                    "risk_level": "critical",
                    "estimated_time_ko": "12~36개월",
                    "estimated_time_zh": "12-36个月",
                    "required_docs_ko": ["제품 등록 신청서", "안전성 평가 보고서", "기능성 시험 보고서", "안정성 시험 보고서", "위생학 시험 보고서"],
                    "required_docs_zh": ["产品注册申请表", "安全性评价报告", "功能性试验报告", "稳定性试验报告", "卫生学试验报告"],
                },
                {
                    "id": "health-01-02",
                    "title_ko": "보건식품 허가 기능 범위 확인",
                    "title_zh": "保健食品允许功能范围确认",
                    "description_ko": "중국에서 허용되는 24가지 보건식품 기능 범위 내에 있는지 확인. '면역력 강화', '항피로', '혈당 조절' 등으로 제한됨.",
                    "description_zh": "确认产品功能是否在中国允许的24种保健食品功能范围内。限制在'增强免疫力'、'抗疲劳'、'辅助降血糖'等。",
                    "risk_level": "high",
                    "estimated_time_ko": "1~3개월",
                    "estimated_time_zh": "1-3个月",
                    "required_docs_ko": ["기능성 시험 보고서", "임상 시험 자료 (필요시)"],
                    "required_docs_zh": ["功能性试验报告", "临床试验资料（如需）"],
                },
            ],
        },
        {
            "id": "health-02",
            "category_ko": "성분 및 기준",
            "category_zh": "成分与标准",
            "items": [
                {
                    "id": "health-02-01",
                    "title_ko": "보건식품 원료·성분 목록 적합",
                    "title_zh": "保健食品原料/成分目录合规",
                    "description_ko": "사용 원료가 '보건식품 허용 원료 목록' 및 '보건식품 금지 원료 목록'에 적합해야 함.",
                    "description_zh": "所用原料须符合《保健食品原料目录》及《保健食品禁用物品目录》。",
                    "risk_level": "high",
                    "estimated_time_ko": "1~2개월",
                    "estimated_time_zh": "1-2个月",
                    "required_docs_ko": ["원료 성분 분석표", "원료 적합성 증명서"],
                    "required_docs_zh": ["原料成分分析表", "原料合规性证明"],
                },
                {
                    "id": "health-02-02",
                    "title_ko": "중국 약전 기준 적합",
                    "title_zh": "符合中国药典标准",
                    "description_ko": "건강기능식품 원료 및 제품의 품질 기준이 《중국 약전》(Chinese Pharmacopoeia) 기준에 부합해야 함.",
                    "description_zh": "保健食品原料和产品质量标准须符合《中国药典》(Chinese Pharmacopoeia)标准。",
                    "risk_level": "medium",
                    "estimated_time_ko": "1~3개월",
                    "estimated_time_zh": "1-3个月",
                    "required_docs_ko": ["품질 기준 분석서", "약전 기준 적합 보고서"],
                    "required_docs_zh": ["质量标准分析书", "药典标准合规报告"],
                },
            ],
        },
        {
            "id": "health-03",
            "category_ko": "라벨 및 광고",
            "category_zh": "标签与广告",
            "items": [
                {
                    "id": "health-03-01",
                    "title_ko": "보건식품 라벨 규정 준수",
                    "title_zh": "保健食品标签合规",
                    "description_ko": "'남성용', '여성용' 등 특정 표현 사용 금지. '보건식품 비의약품' 표시 필수. 블루햇(Blue Hat) 마크 필수 부착.",
                    "description_zh": "禁止使用'男性'、'女性'等特定表述。须标注'保健食品不是药品'。须加贴蓝帽子标志。",
                    "risk_level": "high",
                    "estimated_time_ko": "2~4주",
                    "estimated_time_zh": "2-4周",
                    "required_docs_ko": ["중국어 라벨 샘플", "블루햇 마크 디자인"],
                    "required_docs_zh": ["中文标签样稿", "蓝帽子标志设计"],
                },
                {
                    "id": "health-03-02",
                    "title_ko": "광고 심사 등록",
                    "title_zh": "广告审查备案",
                    "description_ko": "보건식품 광고는 사전 심사 필수. 질병 치료 효과 암시 금지. 광고 내용은 등록된 기능 범위를 초과할 수 없음.",
                    "description_zh": "保健食品广告须经事前审查。禁止暗示疾病治疗功效。广告内容不得超出注册的功能范围。",
                    "risk_level": "medium",
                    "estimated_time_ko": "1~2개월",
                    "estimated_time_zh": "1-2个月",
                    "required_docs_ko": ["광고 심사 신청서", "광고 내용 원고", "제품 등록 증명서"],
                    "required_docs_zh": ["广告审查申请表", "广告内容样稿", "产品注册证明"],
                },
            ],
        },
    ],

    "key_regulations_ko": [
        "《중국 식품 안전법》 (보건식품 관련 조항)",
        "《보건식품 등록·신고 관리 방법》 (2016)",
        "《보건식품 허용 원료 목록》",
        "《보건식품 기능 범위》 (24가지 기능)",
        "《보건식품 광고 심사 잠정 규정》",
    ],
    "key_regulations_zh": [
        "《中华人民共和国食品安全法》(保健食品相关条款)",
        "《保健食品注册与备案管理办法》(2016)",
        "《保健食品原料目录》",
        "《保健食品功能范围》(24种功能)",
        "《保健食品广告审查暂行规定》",
    ],
    "risk_tips_ko": [
        "⚠️ 보건식품 등록은 1~3년 소요되므로 충분한 시간 계획 필요",
        "⚠️ 2023년부터 보건식품 기능성 평가 기준이 강화되었습니다",
        "⚠️ 광고 내용이 허가받은 기능 범위를 초과할 경우 과징금 및 판매 중지 처분",
    ],
    "risk_tips_zh": [
        "⚠️ 保健食品注册需1-3年，须预留充足时间计划",
        "⚠️ 2023年起保健食品功能评价标准加强",
        "⚠️ 广告内容超出批准功能范围将面临罚款和停售处罚",
    ],
}

# ─── 종합 데이터 매핑 ───
# Master data mapping

COMPLIANCE_DATA = {
    "cosmetics": COSMETICS_COMPLIANCE,
    "food": FOOD_COMPLIANCE,
    "health_supplements": HEALTH_SUPPLEMENTS_COMPLIANCE,
}

# ─── FAQ 데이터 ───

FAQ_KR = [
    {
        "question": "한국 화장품을 중국에 수출하려면 가장 먼저 무엇을 해야 하나요?",
        "answer": "가장 먼저 NMPA(중국 국가약품감독관리국)에 제품 등록 또는 신고를 해야 합니다. 일반 화장품은 온라인 신고(备案)로 비교적 간단하지만, 기능성 화장품(미백·자외선차단·탈모 등)은 등록(注册)이 필요하며 추가 시험 자료가 필요합니다. 또한 중국 내 수입업체 지정과 해외 제조업체 등록도 필수입니다.",
    },
    {
        "question": "중국 수입 식품 라벨의 주요 규정은 무엇인가요?",
        "answer": "중국 수입 식품 라벨은 GB 7718(예포장 식품 라벨 통칙)과 GB 28050(영양 성분 표시 기준)을 따라야 합니다. 필수 표기 사항: 제품명, 원재료명, 식품 첨가물, 제조일자, 유통기한, 제조업체 정보, 수입업체 정보, 영양 성분표(5+2), 원산지 등. 한국어에서 중국어로 번역 시 정확성과 GB 용어 일치가 중요합니다.",
    },
    {
        "question": "한국 건강기능식품(홍삼 등)의 중국 CFDA 등록은 얼마나 걸리나요?",
        "answer": "일반적으로 1년에서 3년 정도 소요됩니다. 등록 절차: 서류 준비(3~6개월) → 시험 의뢰(3~6개월) → 접수 및 기술 심사(6~12개월) → 등록 증서 발급(1~3개월). 제품 성분과 기능성 시험 자료의 완비성에 따라 기간이 달라집니다. SAMR(국가시장감독관리총국)에서 심사합니다.",
    },
    {
        "question": "중국 내 한국 기업의 대표적인 진입 장벽은 무엇인가요?",
        "answer": "주요 장벽: ① 네거티브 리스트 확인 - 일부 업종은 외국인 투자 제한 ② 인허가 기간 - 건강기능식품 등록 1~3년 ③ 라벨 규정 - 중국어 라벨 의무, 중한 기준 차이 ④ 지식재산권 - 상표 선등록 리스크 ⑤ 전자상거래 플랫폼 규제 - 크로스보더 E-Commerce 정책 변화 ⑥ 데이터 보안 - 개인정보보호법, 데이터 현지화 요구.",
    },
    {
        "question": "중국 크로스보더 전자상거래를 통해 한국 제품을 판매할 수 있나요?",
        "answer": "네, 가능합니다. 중국 크로스보더 전자상거래(Cross-Border E-Commerce, CBEC)는 정식 수입 통관보다 간소화된 절차를 제공합니다. 다만 CBEC는 개인 소비 용도로만 허용되며, B2B 도매 거래는 정식 수입 통관이 필요합니다. 주요 플랫폼: 티몰 글로벌(天猫国际), 징둥 글로벌(京东国际), 카올라(考拉海购) 등. CBEC의 경우 제품 등록이 면제되는 경우가 있으나 각 플랫폼의 입점 요건을 별도로 충족해야 합니다.",
    },
]

FAQ_ZH = [
    {
        "question": "韩国化妆品出口中国，首先要做什么？",
        "answer": "首先需要在NMPA（国家药品监督管理局）进行产品注册或备案。普通化妆品网上备案相对简单，特殊化妆品（美白、防晒、防脱发等）需要注册，需额外试验资料。同时须指定中国进口商并完成境外生产企业备案。",
    },
    {
        "question": "中国进口食品标签的主要规定是什么？",
        "answer": "中国进口食品标签须符合GB 7718《预包装食品标签通则》和GB 28050《营养标签通则》。必须标注：品名、配料表、食品添加剂、生产日期、保质期、生产企业信息、进口商信息、营养成分表(5+2)、原产国等。从韩语翻译成中文时需确保准确性和GB术语一致。",
    },
    {
        "question": "韩国保健食品（红参等）的中国CFDA注册需要多久？",
        "answer": "一般需要1-3年。注册流程：资料准备(3-6个月)→委托检测(3-6个月)→受理与技术审评(6-12个月)→颁发注册证书(1-3个月)。根据产品成分和功能试验资料的完整性，周期会有所不同。由国家市场监督管理总局(SAMR)审评。",
    },
]

# ─── API 헬퍼 함수 ───

def get_compliance_data(industry: str = None, language: str = "ko"):
    """
    규정 준수 데이터 반환
    Returns compliance data for specified industry or all industries
    
    Args:
        industry: 'cosmetics', 'food', 'health_supplements', or None (all)
        language: 'ko' or 'zh'
    """
    if industry and industry in COMPLIANCE_DATA:
        data = COMPLIANCE_DATA[industry].copy()
        data["industry_info"] = INDUSTRIES.get(industry)
        return data
    
    if not industry:
        return {
            "industries": INDUSTRIES,
            "data": COMPLIANCE_DATA,
        }
    
    return {"error": f"Unknown industry: {industry}"}


def get_checklist_summary(industry: str, language: str = "ko"):
    """
    체크리스트 요약 반환 (전체 개수, 완료 항목 등)
    Returns checklist summary with counts
    """
    if industry not in COMPLIANCE_DATA:
        return {"error": f"Unknown industry: {industry}"}
    
    data = COMPLIANCE_DATA[industry]
    total_items = 0
    high_risk = 0
    medium_risk = 0
    low_risk = 0
    
    for category in data["checklist"]:
        for item in category["items"]:
            total_items += 1
            if item["risk_level"] == "critical":
                high_risk += 1
            elif item["risk_level"] == "high":
                high_risk += 1
            elif item["risk_level"] == "medium":
                medium_risk += 1
            else:
                low_risk += 1
    
    return {
        "industry_id": industry,
        "industry_name": INDUSTRIES.get(industry, {}).get(f"name_{language}", industry),
        "total_items": total_items,
        "critical_and_high_risk_items": high_risk,
        "medium_risk_items": medium_risk,
        "low_risk_items": low_risk,
        "estimated_min_months": min(
            _extract_time(item)
            for cat in data["checklist"] for item in cat["items"]
        ) if total_items > 0 else 0,
    }


def _extract_time(item):
    """Extract numeric months from estimated_time string for sorting"""
    import re
    time_str = item.get("estimated_time_ko", "")
    numbers = re.findall(r'\d+', time_str)
    if numbers:
        return int(numbers[0])
    return 99


def get_faq(language: str = "ko"):
    """FAQ 데이터 반환"""
    if language == "ko":
        return FAQ_KR
    return FAQ_ZH
