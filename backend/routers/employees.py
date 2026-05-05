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
        "title_zh": "首席合规官",
        "title_ko": "수석 규정준수 책임자",
        "level": "P9",
        "price": 999,
        "cost_comparison_zh": "资深合规经理 ¥30,000+",
        "cost_comparison_ko": "선임 규정준수 매니저 ¥30,000+",
        "capabilities_zh": [
            "中国市场准入全链路诊断（12年经验）",
            "跨境投资政策合规解读",
            "WFOE/JV/代表处设立架构"
        ],
        "capabilities_ko": [
            "중국 시장 진입 전 과정 진단(12년 경험)",
            "해외 투자 정책 규정 해석",
            "WFOE/JV/대표처 설립 구조"
        ],
        "experience_zh": "服务过30+韩企完成中国子公司设立",
        "experience_ko": "30+ 한국 기업의 중국 자회사 설립 지원",
        "avatar_color": "#8B5CF6"
    },
    {
        "id": 2,
        "name_zh": "朴泰俊",
        "name_ko": "박태준",
        "title_zh": "合规战略官",
        "title_ko": "규정준수 전략 책임자",
        "level": "P10",
        "price": 1499,
        "cost_comparison_zh": "合规总监 ¥50,000+",
        "cost_comparison_ko": "규정준수 디렉터 ¥50,000+",
        "capabilities_zh": [
            "企业合规体系搭建",
            "跨境投资架构设计",
            "风险评估与应对策略"
        ],
        "capabilities_ko": [
            "기업 규정준수 체계 구축",
            "해외 투자 구조 설계",
            "위험 평가 및 대응 전략"
        ],
        "experience_zh": "主导过50+跨境合规项目",
        "experience_ko": "50+ 해외 규정준수 프로젝트 주도",
        "avatar_color": "#06B6D4"
    },
    {
        "id": 3,
        "name_zh": "丹书",
        "name_ko": "단서",
        "title_zh": "数据合规官",
        "title_ko": "데이터 규정준수 책임자",
        "level": "P8",
        "price": 799,
        "cost_comparison_zh": "数据隐私律师 ¥25,000+",
        "cost_comparison_ko": "데이터 프라이버시 변호사 ¥25,000+",
        "capabilities_zh": [
            "个人信息保护合规",
            "数据跨境传输方案",
            "算法备案与安全评估"
        ],
        "capabilities_ko": [
            "개인정보 보호 규정 준수",
            "데이터 해외 전송 솔루션",
            "알고리즘 등록 및 보안 평가"
        ],
        "experience_zh": "处理过20+企业数据合规整改",
        "experience_ko": "20+ 기업 데이터 규정준수 개선 처리",
        "avatar_color": "#10B981"
    },
    {
        "id": 4,
        "name_zh": "李朴",
        "name_ko": "이박",
        "title_zh": "劳动合规官",
        "title_ko": "노무 규정준수 책임자",
        "level": "P8",
        "price": 699,
        "cost_comparison_zh": "劳动法律师 ¥22,000+",
        "cost_comparison_ko": "노동법 변호사 ¥22,000+",
        "capabilities_zh": [
            "中国劳动法合规诊断",
            "薪酬社保体系搭建",
            "外籍员工派遣合规"
        ],
        "capabilities_ko": [
            "중국 노동법 규정 준수 진단",
            "급여 및 사회보험 체계 구축",
            "외국인 직원 파견 규정 준수"
        ],
        "experience_zh": "服务过15+韩企在华用工合规",
        "experience_ko": "15+ 한국 기업 중국 고용 규정준수 지원",
        "avatar_color": "#F59E0B"
    },
    {
        "id": 5,
        "name_zh": "金镇宇",
        "name_ko": "김진우",
        "title_zh": "法律合规官",
        "title_ko": "법률 규정준수 책임자",
        "level": "P8",
        "price": 899,
        "cost_comparison_zh": "企业法律顾问 ¥28,000+",
        "cost_comparison_ko": "기업 법률 고문 ¥28,000+",
        "capabilities_zh": [
            "合同审核与法律审查",
            "争议解决策略",
            "外商投资法律咨询"
        ],
        "capabilities_ko": [
            "계약 검토 및 법률 검사",
            "분쟁 해결 전략",
            "외국인 투자 법률 자문"
        ],
        "experience_zh": "审核过200+跨境商务合同",
        "experience_ko": "200+ 해외 상업 계약 검토",
        "avatar_color": "#EF4444"
    },
    {
        "id": 6,
        "name_zh": "崔敏智",
        "name_ko": "최민지",
        "title_zh": "公司设立官",
        "title_ko": "회사 설립 책임자",
        "level": "P7",
        "price": 599,
        "cost_comparison_zh": "注册代理 ¥18,000+",
        "cost_comparison_ko": "등록 대리인 ¥18,000+",
        "capabilities_zh": [
            "外商投资企业设立",
            "资质许可办理",
            "公司架构设计"
        ],
        "capabilities_ko": [
            "외국인 투자 기업 설립",
            "자격증 및 허가 처리",
            "회사 구조 설계"
        ],
        "experience_zh": "完成过50+外资企业注册",
        "experience_ko": "50+ 외국인 기업 등록 완료",
        "avatar_color": "#EC4899"
    }
]


@router.get("/digital-employees")
@router.get("/employees")
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
