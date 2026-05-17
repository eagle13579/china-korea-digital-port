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

        # 发送新线索通知
        try:
            from backend.services.email_service import send_new_lead_notification
            send_new_lead_notification({
                "_label": "联系咨询",
                "name": form.name,
                "company": form.company,
                "email": form.email,
                "phone": form.phone,
                "message": form.message,
            })
        except ImportError:
            pass
        except Exception:
            pass
        
        # 追踪转化漏斗事件
        try:
            from backend.analytics.event_tracker import track_event
            track_event(
                user_id=form.email,
                event_type="lead_contact",
                event_data={"name": form.name, "company": form.company},
                page_url="/api/v1/contact",
            )
        except Exception:
            pass

        return APIResponse(
            success=True,
            message="感谢您的咨询！我们将在24小时内与您联系。"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")
