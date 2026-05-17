"""
中韩出海数智港 — K-DPA / GDPR / PIPL 合规基线 API路由

提供合规基线检查清单和状态摘要
- GET /api/compliance/baseline — 返回合规基线状态
"""
from fastapi import APIRouter, Query
from backend.compliance_baseline import build_baseline_response

router = APIRouter(prefix="/api/compliance", tags=["compliance-baseline"])


@router.get("/baseline")
async def get_compliance_baseline(language: str = Query("zh", description="语言: zh 中文 / en 英文")):
    """
    获取K-DPA / GDPR / PIPL合规基线状态

    返回三个法规的检查清单及合规摘要，包含：
    - summary: 各法规的合规分数和统计
    - regulations: 详细检查清单
    """
    return build_baseline_response(language)
