"""中韩出海数智港 - FastAPI应用入口"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
from dotenv import load_dotenv

# 必须在import所有模块之前加载.env
load_dotenv()

import sys
# 将项目根目录加入 path（无论 main.py 在何处执行）
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.database import init_db
from backend.analytics.event_tracker import init_analytics_db, track_event
from backend.knowledge_graph import router as knowledge_graph_router
from backend.routers.compliance_feedback import router as compliance_feedback_router
from backend.routers.compliance_diagnosis import router as compliance_diagnosis_router
from backend.routers.compliance_scoring import router as compliance_scoring_router
from backend.routers.compliance_report import router as compliance_report_router
from backend.routers import contact, demo, pricing, admin, employees, service_inquiry, payment, members, compliance, cortex_api, ai_dialogue
from backend.routers import products
import backend.channel_tracker as channel_tracker

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="中韩出海数智港 API",
    description="China-Korea Digital Trade Gateway Backend API",
    version="1.2.0",
)

# CORS配置
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*")
if ALLOWED_ORIGINS == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    origins = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 注册API路由（必须先注册，静态文件后注册）
app.include_router(contact.router)
app.include_router(demo.router)
app.include_router(pricing.router)
app.include_router(admin.router)
app.include_router(employees.router)
app.include_router(service_inquiry.router)
app.include_router(payment.router)
app.include_router(members.router)
app.include_router(compliance.router)
app.include_router(cortex_api.router)
app.include_router(ai_dialogue.router)
app.include_router(knowledge_graph_router)
app.include_router(compliance_feedback_router)
app.include_router(compliance_diagnosis_router)
app.include_router(compliance_scoring_router)
app.include_router(compliance_report_router)
app.include_router(products.router)

# ── 渠道/KOI追踪中间件 ────────────────────────────────
# @app.middleware("http")
# async def channel_middleware(request: Request, call_next):
#     return await channel_tracker.channel_tracking_middleware(request, call_next)

# ── 用户行为追踪中间件 ─────────────────────────────────
@app.middleware("http")
async def analytics_middleware(request: Request, call_next):
    """自动追踪页面访问事件"""
    import time
    start_time = time.time()
    response = await call_next(request)

    # 仅追踪 HTML 页面请求（非 API、非静态资源）
    path = request.url.path
    if (
        response.status_code == 200
        and not path.startswith("/api/")
        and not path.startswith("/css/")
        and not path.startswith("/js/")
        and not path.startswith("/uploads/")
        and not path.startswith("/admin")
        and path != "/health"
        and not path.startswith("/analytics")
    ):
        try:
            user_id = request.client.host if request.client else "unknown"
            session_id = request.headers.get("x-session-id", None)
            if not session_id:
                session_id = request.headers.get("cookie", "")
            track_event(
                user_id=user_id,
                event_type="page_view",
                page_url=str(request.url.path),
                session_id=session_id[:128] if session_id else None,
                ip_address=user_id,
                user_agent=request.headers.get("user-agent", None),
            )
        except Exception:
            pass

    response.headers["X-Process-Time"] = str(time.time() - start_time)
    return response

# ── 分析 API 端点 ──────────────────────────────────────
@app.get("/analytics/dashboard")
async def analytics_dashboard_api():
    """获取分析仪表盘数据（JSON格式）"""
    from backend.analytics.event_tracker import (
        get_today_active_users, get_today_events_count,
        get_popular_pages, get_conversion_funnel, get_event_type_breakdown,
    )
    return {
        "today": {
            "active_users": get_today_active_users(),
            "total_events": get_today_events_count(),
            "event_breakdown": get_event_type_breakdown(),
        },
        "popular_pages": get_popular_pages(),
        "conversion_funnel": get_conversion_funnel(),
    }

@app.get("/analytics/funnel")
async def analytics_funnel_api():
    """获取转化漏斗数据"""
    from backend.analytics.event_tracker import get_conversion_funnel
    return {"funnel": get_conversion_funnel()}

@app.get("/analytics/track")
async def analytics_track_event(
    request: Request,
    event_type: str = "click",
    page_url: str = None,
    data: str = None,
):
    """手动追踪事件（供前端JS调用）"""
    import json
    user_id = request.client.host if request.client else "unknown"
    event_data = json.loads(data) if data else {}
    track_event(
        user_id=user_id,
        event_type=event_type,
        event_data=event_data,
        page_url=page_url,
        session_id=request.headers.get("x-session-id", None),
        ip_address=user_id,
        user_agent=request.headers.get("user-agent", None),
    )
    return {"success": True}

# ── 静态文件路由 ───────────────────────────────────────
@app.get("/")
async def root():
    return FileResponse(os.path.join(ROOT_DIR, "index.html"))

@app.get("/index.html")
async def index_html():
    return FileResponse(os.path.join(ROOT_DIR, "index.html"))

@app.get("/chat.html")
async def chat_html():
    return FileResponse(os.path.join(ROOT_DIR, "chat.html"))

@app.get("/pricing.html")
async def pricing_html():
    return FileResponse(os.path.join(ROOT_DIR, "pricing-v2.html"))

@app.get("/pricing-v2.html")
async def pricing_v2_html():
    return FileResponse(os.path.join(ROOT_DIR, "pricing-v2.html"))

@app.get("/order.html")
async def order_html():
    return FileResponse(os.path.join(ROOT_DIR, "order.html"))

@app.get("/payment.html")
async def payment_html():
    return FileResponse(os.path.join(ROOT_DIR, "payment.html"))

@app.get("/checkout.html")
async def checkout_html():
    return FileResponse(os.path.join(ROOT_DIR, "checkout.html"))

@app.get("/payment-success.html")
async def payment_success_html():
    return FileResponse(os.path.join(ROOT_DIR, "payment-success.html"))

@app.get("/team.html")
async def team_html():
    return FileResponse(os.path.join(ROOT_DIR, "team.html"))

@app.get("/privacy.html")
async def privacy_html():
    return FileResponse(os.path.join(ROOT_DIR, "privacy.html"))

@app.get("/terms.html")
async def terms_html():
    return FileResponse(os.path.join(ROOT_DIR, "terms.html"))

@app.get("/channel-dashboard.html")
async def channel_dashboard_html():
    return FileResponse(os.path.join(ROOT_DIR, "channel_dashboard.html"))

@app.get("/robots.txt")
async def robots_txt():
    return FileResponse(os.path.join(ROOT_DIR, "robots.txt"))

@app.get("/sitemap.xml")
async def sitemap_xml():
    return FileResponse(os.path.join(ROOT_DIR, "sitemap.xml"))

@app.get("/favicon.ico")
async def favicon():
    return FileResponse(os.path.join(ROOT_DIR, "favicon.ico"))

@app.get("/css/{path:path}")
async def css_files(path: str):
    return FileResponse(os.path.join(ROOT_DIR, "css", path))

@app.get("/js/{path:path}")
async def js_files(path: str):
    return FileResponse(os.path.join(ROOT_DIR, "js", path))

@app.get("/uploads/{path:path}")
async def upload_files(path: str):
    return FileResponse(os.path.join(ROOT_DIR, "uploads", path))

@app.get("/admin")
async def admin_root():
    return FileResponse(os.path.join(ROOT_DIR, "admin", "index.html"))

@app.get("/admin/{path:path}")
async def admin_files(path: str):
    if not path or path.endswith("/"):
        return FileResponse(os.path.join(ROOT_DIR, "admin", "index.html"))
    file_path = os.path.join(ROOT_DIR, "admin", path)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        file_path = os.path.join(ROOT_DIR, "admin", "index.html")
    return FileResponse(file_path)

@app.get("/health")
async def health():
    return {"status": "ok"}

# ── 启动事件 ───────────────────────────────────────────
@app.on_event("startup")
async def startup():
    """启动时初始化数据库"""
    init_db()
    init_analytics_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5031)
