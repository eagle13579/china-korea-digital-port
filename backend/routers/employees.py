"""
数字员工API路由 - 中韩出海数智港
GET /api/v1/digital-employees → 返回所有数字员工列表
GET /api/v1/digital-employees/{id} → 返回单个员工详情
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1", tags=["digital-employees"])

# MVP阶段：静态数据，无需数据库
EMPLOYEES_DATA = [
    {
        "id": 1,
        "name_zh": "徐准",
        "name_ko": "서준",
        "title": "首席合规官",
        "level": "P9",
        "price": 999,
        "cost_comparison": "资深合规经理 ¥30,000+",
        "capabilities": [
            "中国市场准入全链路诊断（12年经验）",
            "跨境投资政策合规解读",
            "WFOE/JV/代表处设立架构"
        ],
        "experience": "服务过30+韩企完成中国子公司设立",
        "avatar_color": "#8B5CF6"
    },
    {
        "id": 2,
        "name_zh": "朴泰俊",
        "name_ko": "박태준",
        "title": "合规战略官",
        "level": "P10",
        "price": 1499,
        "cost_comparison": "合规总监 ¥50,000+",
        "capabilities": [
            "企业合规体系搭建",
            "跨境投资架构设计",
            "风险评估与应对策略"
        ],
        "experience": "主导过50+跨境合规项目",
        "avatar_color": "#06B6D4"
    },
    {
        "id": 3,
        "name_zh": "丹书",
        "name_ko": "단서",
        "title": "数据合规官",
        "level": "P8",
        "price": 799,
        "cost_comparison": "数据隐私律师 ¥25,000+",
        "capabilities": [
            "个人信息保护合规",
            "数据跨境传输方案",
            "算法备案与安全评估"
        ],
        "experience": "处理过20+企业数据合规整改",
        "avatar_color": "#10B981"
    },
    {
        "id": 4,
        "name_zh": "李朴",
        "name_ko": "이박",
        "title": "劳动合规官",
        "level": "P8",
        "price": 699,
        "cost_comparison": "劳动法律师 ¥22,000+",
        "capabilities": [
            "中国劳动法合规诊断",
            "薪酬社保体系搭建",
            "外籍员工派遣合规"
        ],
        "experience": "服务过15+韩企在华用工合规",
        "avatar_color": "#F59E0B"
    },
    {
        "id": 5,
        "name_zh": "金镇宇",
        "name_ko": "김진우",
        "title": "法律合规官",
        "level": "P8",
        "price": 899,
        "cost_comparison": "企业法律顾问 ¥28,000+",
        "capabilities": [
            "合同审核与法律审查",
            "争议解决策略",
            "外商投资法律咨询"
        ],
        "experience": "审核过200+跨境商务合同",
        "avatar_color": "#EF4444"
    },
    {
        "id": 6,
        "name_zh": "崔敏智",
        "name_ko": "최민지",
        "title": "公司设立官",
        "level": "P7",
        "price": 599,
        "cost_comparison": "注册代理 ¥18,000+",
        "capabilities": [
            "外商投资企业设立",
            "资质许可办理",
            "公司架构设计"
        ],
        "experience": "完成过50+外资企业注册",
        "avatar_color": "#EC4899"
    }
]


@router.get("/digital-employees")
async def list_employees():
    """获取所有数字员工列表"""
    return {
        "success": True,
        "data": EMPLOYEES_DATA
    }


@router.get("/digital-employees/{employee_id}")
async def get_employee(employee_id: int):
    """获取单个数字员工详情"""
    for emp in EMPLOYEES_DATA:
        if emp["id"] == employee_id:
            return {
                "success": True,
                "data": emp
            }
    raise HTTPException(status_code=404, detail="员工未找到")
