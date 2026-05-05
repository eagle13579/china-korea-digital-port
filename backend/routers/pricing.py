"""
定价查询API路由
"""
from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.models import PricingInquiry, APIResponse

router = APIRouter(tags=["pricing"])


@router.get("/api/v1/pricing")
async def get_pricing():
    """获取定价方案"""
    return {
        "success": True,
        "plans": [
            {
                "name": "免费初评",
                "name_ko": "무료 초기 평가",
                "price": "¥0",
                "type": "free",
                "features": [
                    "30分钟在线咨询",
                    "中国市场概况报告",
                    "基础合规清单"
                ],
                "description": "适合初步了解中国市场的韩企"
            },
            {
                "name": "深度方案",
                "name_ko": "심층 컨설팅 패키지",
                "price": "¥9,800",
                "type": "one-time",
                "features": [
                    "全案市场进入策划",
                    "中韩双语品牌内容",
                    "SEO优化方案",
                    "竞品深度分析",
                    "合规完整诊断"
                ],
                "description": "适合已决定进入中国市场的韩企"
            },
            {
                "name": "年订阅",
                "name_ko": "연간 구독",
                "price": "¥58,000/年",
                "type": "annual",
                "features": [
                    "含深度方案全部内容",
                    "不限次AI数字员工分析",
                    "实时市场情报",
                    "优先技术支持",
                    "季度战略复盘"
                ],
                "description": "适合持续运营中国业务的韩企"
            }
        ]
    }


@router.post("/api/v1/pricing/inquiry", response_model=APIResponse)
async def submit_pricing_inquiry(form: PricingInquiry):
    """提交定价咨询"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO pricing_inquiries (name, company, email, phone, plan_type, message, status)
               VALUES (?, ?, ?, ?, ?, ?, 'new')""",
            (form.name, form.company, form.email, form.phone,
             form.plan_type, form.message),
        )
        conn.commit()
        conn.close()
        return APIResponse(
            success=True,
            message="您的咨询已收到！销售团队将主动联系您。"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")
