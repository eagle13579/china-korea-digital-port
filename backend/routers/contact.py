"""
联系表单API路由
"""
from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.models import ContactForm, APIResponse
from datetime import datetime

router = APIRouter(tags=["contact"])


@router.post("/api/v1/contact", response_model=APIResponse)
async def submit_contact(form: ContactForm):
    """提交联系表单"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO contacts (name, company, email, phone, message, status)
               VALUES (?, ?, ?, ?, ?, 'new')""",
            (form.name, form.company, form.email, form.phone, form.message),
        )
        conn.commit()
        conn.close()
        return APIResponse(
            success=True,
            message="感谢您的咨询！我们将在24小时内与您联系。"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")
