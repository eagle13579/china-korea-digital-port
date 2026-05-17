"""
合规自检工具 API路由 (P0任务1版)
- POST /api/compliance/check 接收答案，返回评分+风险等级
- POST /api/compliance/check/pdf 接收答案，返回PDF报告
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime
import secrets

from backend.compliance.questions_data import get_questions
from backend.compliance.report_score import calculate_score, generate_report_data
from backend.compliance.report_pdf import generate_report_pdf

router = APIRouter(prefix="/api/compliance", tags=["compliance-check-v1"])


class CheckRequest(BaseModel):
    answers: Dict[int, int]
    language: str = "zh"
    company_name: Optional[str] = ""
    contact_name: Optional[str] = ""
    email: Optional[str] = ""


@router.get("/questions")
async def api_get_questions(language: str = "zh"):
    """获取合规自检题目列表"""
    questions = get_questions(language)
    return {
        "success": True,
        "questions": questions,
        "total": len(questions)
    }


@router.post("/check")
async def api_compliance_check(data: CheckRequest):
    """提交合规自检答案，返回评分+风险等级

    Args:
        answers: {question_id: option_value} 格式
        language: "zh" 或 "ko"

    Returns:
        {
            "success": bool,
            "report": {
                "total_score": float,
                "risk_level": str,
                "risk_label": str,
                "summary": str,
                "dimensions": [...],
                "priorities": [...],
                "disclaimer": str
            }
        }
    """
    if not data.answers or len(data.answers) == 0:
        raise HTTPException(
            status_code=400,
            detail="请至少回答一道题" if data.language == "zh" else "최소 한 문제 이상 답변해 주세요"
        )

    # 验证所有答案在有效范围内 (0-3)
    for qid, val in data.answers.items():
        if val not in (0, 1, 2, 3):
            raise HTTPException(
                status_code=400,
                detail=f"题目 {qid} 的选项值无效: {val}" if data.language == "zh"
                       else f"질문 {qid}의 옵션 값이 유효하지 않습니다: {val}"
            )

    try:
        company_info = {
            "company_name": data.company_name or "",
            "contact_name": data.contact_name or "",
            "email": data.email or "",
            "report_token": secrets.token_hex(6).upper(),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        result = calculate_score(data.answers, data.language)
        return {
            "success": True,
            "report": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报告生成失败: {str(e)}")


@router.post("/check/pdf")
async def api_compliance_check_pdf(data: CheckRequest):
    """提交合规自检答案，返回PDF报告文件

    Args:
        answers: {question_id: option_value} 格式
        language: "zh" 或 "ko"
        company_name: 企业名称（可选）

    Returns:
        PDF文件（application/pdf）
    """
    if not data.answers or len(data.answers) == 0:
        raise HTTPException(
            status_code=400,
            detail="请至少回答一道题" if data.language == "zh" else "최소 한 문제 이상 답변해 주세요"
        )

    for qid, val in data.answers.items():
        if val not in (0, 1, 2, 3):
            raise HTTPException(
                status_code=400,
                detail=f"题目 {qid} 的选项值无效: {val}"
            )

    try:
        company_info = {
            "company_name": data.company_name or "",
            "contact_name": data.contact_name or "",
            "email": data.email or "",
            "report_token": secrets.token_hex(6).upper(),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        report_data = generate_report_data(data.answers, company_info, data.language)
        pdf_bytes = generate_report_pdf(report_data)

        filename = f"compliance_report_{company_info['report_token']}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF生成失败: {str(e)}")
