"""
预约演示API路由
"""
from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.models import DemoRequest, APIResponse

router = APIRouter(tags=["demo"])


@router.post("/api/v1/demo", response_model=APIResponse)
async def submit_demo(form: DemoRequest):
    """提交预约演示"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO demo_requests (name, company, email, phone, preferred_date, notes, status)
               VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
            (form.name, form.company, form.email, form.phone,
             form.preferred_date, form.notes),
        )
        conn.commit()
        conn.close()

        # 发送新线索通知
        try:
            from backend.services.email_service import send_new_lead_notification
            send_new_lead_notification({
                "_label": "预约演示",
                "name": form.name,
                "company": form.company,
                "email": form.email,
                "phone": form.phone,
                "message": form.notes,
                "notes": f"期望日期: {form.preferred_date or '未指定'}",
            })
        except ImportError:
            pass
        except Exception:
            pass

        return APIResponse(
            success=True,
            message="演示预约已提交！我们的团队将尽快与您确认具体时间。"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")


