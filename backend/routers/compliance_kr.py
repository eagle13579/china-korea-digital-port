"""
한국 기업 중국 진입 규정 준수 API 라우터
Korean Enterprise China Entry Compliance API Router

POST /api/compliance/kr/check → 산업별 규정 준수 데이터 반환
GET  /compliance/kr          → 한글 규정 준수 페이지
"""

import json
import os
import sys
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# 상대 임포트를 위한 경로 설정
_script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_project_root = os.path.dirname(_script_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.compliance_kr_data import (
    get_compliance_data,
    get_checklist_summary,
    get_faq,
    INDUSTRIES,
)

router = APIRouter(tags=["compliance_kr"])


# ─── 요청/응답 모델 ───

class KRComplianceRequest(BaseModel):
    industry: Optional[str] = "all"  # "cosmetics", "food", "health_supplements", "all"
    language: str = "ko"  # "ko", "zh"


class KRComplianceResponse(BaseModel):
    success: bool = True
    industries: Optional[dict] = None
    data: Optional[dict] = None
    summary: Optional[dict] = None
    summaries: Optional[dict] = None
    faq: Optional[list] = None
    industry_info: Optional[dict] = None
    error: Optional[str] = None


# ─── API 엔드포인트 ───

@router.post("/api/compliance/kr/check", response_model=KRComplianceResponse)
async def compliance_kr_check(req: KRComplianceRequest):
    """
    한국 기업 중국 진입 규정 준수 데이터 조회
    산업별(화장품/식품/건강기능식품) 체크리스트, 관련 법규, FAQ 반환
    """
    lang = req.language if req.language in ("ko", "zh") else "ko"

    try:
        if req.industry and req.industry != "all":
            # 특정 산업만 조회
            if req.industry not in ("cosmetics", "food", "health_supplements"):
                return KRComplianceResponse(
                    success=False,
                    error=f"알 수 없는 산업: {req.industry}. 'cosmetics', 'food', 'health_supplements', 'all' 중 선택하세요."
                )

            data = get_compliance_data(req.industry)
            summary = get_checklist_summary(req.industry, lang)

            # 산업 정보 포함
            industry_info = INDUSTRIES.get(req.industry)

            return KRComplianceResponse(
                success=True,
                data=data,
                summary=summary,
                industry_info=industry_info,
                faq=get_faq(lang),
            )

        else:
            # 모든 산업 조회
            all_data = get_compliance_data(None)

            # 각 산업별 요약
            summaries = {}
            for ind_id in ("cosmetics", "food", "health_supplements"):
                summaries[ind_id] = get_checklist_summary(ind_id, lang)

            return KRComplianceResponse(
                success=True,
                industries=INDUSTRIES,
                data=all_data.get("data", all_data),
                summaries=summaries,
                faq=get_faq(lang),
            )

    except Exception as e:
        return KRComplianceResponse(
            success=False,
            error=f"서버 오류: {str(e)}"
        )


@router.post("/api/compliance/kr/summary")
async def compliance_kr_summary(req: KRComplianceRequest):
    """한국 기업 중국 진입 규정 준수 요약 데이터"""
    lang = req.language if req.language in ("ko", "zh") else "ko"

    if req.industry and req.industry != "all":
        summary = get_checklist_summary(req.industry, lang)
        return {"success": True, "summary": summary}

    summaries = {}
    for ind_id in ("cosmetics", "food", "health_supplements"):
        summaries[ind_id] = get_checklist_summary(ind_id, lang)
    return {"success": True, "summaries": summaries}


@router.get("/api/compliance/kr/industries")
async def compliance_kr_industries():
    """산업 목록 반환"""
    return {"success": True, "industries": INDUSTRIES}


@router.get("/api/compliance/kr/faq")
async def compliance_kr_faq(language: str = "ko"):
    """FAQ 데이터 반환"""
    lang = language if language in ("ko", "zh") else "ko"
    return {"success": True, "faq": get_faq(lang)}
