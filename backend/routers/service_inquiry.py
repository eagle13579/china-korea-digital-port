"""
服务邀请（数字员工邀请）API路由
"""
from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.models import ServiceInquiry, APIResponse
from datetime import datetime

router = APIRouter(tags=["service_inquiry"])


@router.post("/api/v1/service-inquiry", response_model=APIResponse)
async def submit_service_inquiry(form: ServiceInquiry):
    """提交数字员工服务邀请"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO service_inquiries (name, company, email, phone, employee_id, employee_name, message, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'new')""",
            (form.name, form.company, form.email, form.phone,
             form.employee_id, form.employee_name, form.message),
        )
        conn.commit()
        conn.close()
        return APIResponse(
            success=True,
            message="邀请已提交！销售团队将主动联系您。"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")
