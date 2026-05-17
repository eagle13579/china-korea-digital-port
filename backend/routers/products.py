"""
中韩出海数智港 — 产品数据API
提供抹茶拿铁/济州海苔/韩天红参产品信息
数据来源：合规MCP + 静态数据
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api", tags=["products"])

PRODUCTS = [
    {
        "id": "matcha-latte",
        "name_zh": "CAFE MORI 抹茶拿铁",
        "name_kr": "CAFE MORI 말차라떼",
        "name_en": "CAFE MORI Matcha Latte",
        "company_kr": "JARDIN",
        "brand": "CAFE MORI",
        "founded": 1989,
        "category": "食品/饮料",
        "category_kr": "식품/음료",
        "tags_zh": ["韩国37年老牌", "济州岛有机绿茶", "6种口味"],
        "tags_kr": ["한국 37년 전통", "제주도 유기농 녹차", "6가지 맛"],
        "price_fob": 1.80,
        "price_unit": "条",
        "moq": 1000,
        "moq_unit": "条",
        "description_zh": "韩国37年老牌JARDIN旗下，采用济州岛有机绿茶研磨的超细抹茶粉，6种口味（原味/香草/草莓/蓝莓/花生/燕麦），每条不到5元。",
        "description_kr": "한국 37년 전통 JARDIN의 CAFE MORI 브랜드, 제주도 유기농 녹차로 만든 고급 말차 라떼.",
        "specs": [
            {"name": "原味", "posts": 48, "engagement": "7.2%", "heat": 96},
            {"name": "香草", "posts": 42, "engagement": "6.8%", "heat": 88},
            {"name": "草莓", "posts": 36, "engagement": "5.9%", "heat": 75},
            {"name": "蓝莓", "posts": 28, "engagement": "5.1%", "heat": 62},
        ],
        "status": "active"
    },
    {
        "id": "jeju-seaweed",
        "name_zh": "济州海苔",
        "name_kr": "제주 김",
        "name_en": "Jeju Seaweed",
        "company_kr": "JEAJU FOOD",
        "brand": "JEAJU",
        "founded": 1976,
        "category": "食品/海苔",
        "category_kr": "식품/김",
        "tags_zh": ["1976年创立", "韩国代表海苔品牌", "中国代理：上海香德粒"],
        "tags_kr": ["1976년 설립", "한국 대표 김 브랜드"],
        "price_fob": 2.50,
        "price_unit": "包",
        "moq": 500,
        "moq_unit": "箱",
        "description_zh": "1976年创立的韩国海苔代表企业，通过上海香德粒出口中国11年。提供原味海苔和调味海苔系列，HS编码2106.90/2008.99。",
        "description_kr": "1976년 설립된 한국 대표 김 브랜드. 중국 수출 11년차.",
        "specs": [
            {"name": "原味海苔", "posts": 36, "engagement": "6.5%", "heat": 85},
            {"name": "调味海苔", "posts": 28, "engagement": "5.8%", "heat": 72},
            {"name": "海苔碎", "posts": 18, "engagement": "4.2%", "heat": 55},
        ],
        "status": "active",
        "compliance_check": True
    },
    {
        "id": "korean-ginseng",
        "name_zh": "韩天红参",
        "name_kr": "한천 홍삼",
        "name_en": "KRG Red Ginseng",
        "company_kr": "KRG KONGSA",
        "brand": "韩泉牌",
        "founded": 2005,
        "category": "保健品/红参",
        "category_kr": "건강기능식품/홍삼",
        "tags_zh": ["高端滋补", "6年根", "韩国正品"],
        "tags_kr": ["고급 보양", "6년근", "한국 정품"],
        "price_fob": 35.00,
        "price_unit": "盒",
        "moq": 100,
        "moq_unit": "盒",
        "description_zh": "韩国6年根红参浓缩液，传统工艺萃取。富含人参皂苷，增强免疫力、抗疲劳。适合企业团购和礼品市场。",
        "description_kr": "한국 6년근 홍삼 농축액, 전통 방식으로 추출. 면역력 증진, 피로 회복에 효과적.",
        "specs": [
            {"name": "6年根浓缩液", "posts": 32, "engagement": "7.8%", "heat": 96},
            {"name": "礼盒装", "posts": 18, "engagement": "5.6%", "heat": 72},
            {"name": "切片红参", "posts": 15, "engagement": "4.9%", "heat": 58},
            {"name": "红参茶包", "posts": 10, "engagement": "3.2%", "heat": 40},
        ],
        "status": "active",
        "compliance_check": True
    }
]


@router.get("/products")
async def list_products():
    """获取所有产品列表"""
    return {"products": PRODUCTS, "total": len(PRODUCTS)}


@router.get("/products/{product_id}")
async def get_product(product_id: str):
    """获取单个产品信息"""
    for p in PRODUCTS:
        if p["id"] == product_id:
            return p
    return JSONResponse(status_code=404, content={"error": "产品不存在"})


PLATFORM_STATS = {
    "platforms": [
        {"name_zh": "小红书", "name_kr": "샤오홍슈", "name_en": "RED", "icon": "📕", "color": "#FF4747",
         "engagement": 7.2, "posts_per_week": 48, "wow_change": 15},
        {"name_zh": "抖音", "name_kr": "틱톡 중국", "name_en": "Douyin", "icon": "🎵", "color": "#000000",
         "engagement": 8.9, "posts_per_week": 36, "wow_change": 22},
        {"name_zh": "微信", "name_kr": "위챗", "name_en": "WeChat", "icon": "💬", "color": "#07C160",
         "engagement": 5.1, "posts_per_week": 24, "wow_change": 5},
        {"name_zh": "B站", "name_kr": "B스테이션", "name_en": "Bilibili", "icon": "📺", "color": "#FB7299",
         "engagement": 6.3, "posts_per_week": 18, "wow_change": 8},
    ],
    "total_posts_this_week": 126,
    "avg_engagement": 6.9,
    "total_clients": 3,
    "total_revenue": 29800
}


@router.get("/stats/platforms")
async def get_platform_stats():
    """获取平台表现数据"""
    return PLATFORM_STATS
