"""
中韩出海数智港 - FastAPI应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
import os
from dotenv import load_dotenv

# ⚠️ 必须在import所有模块之前加载.env
# 因为admin.py/database.py的模块级代码会在import时读取环境变量
load_dotenv()

from backend.database import init_db
from backend.routers import contact, demo, pricing, admin, employees

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="中韩出海数智港 API",
    description="China-Korea Digital Port Backend API",
    version="1.1.0",
)

# CORS配置 — 从环境变量读取允许的来源
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*")
if ALLOWED_ORIGINS == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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


# 静态文件路由（手动处理，避免 mount 抢占 API 路由）
@app.get("/")
async def root():
    return FileResponse(os.path.join(ROOT_DIR, "index.html"))


@app.get("/index.html")
async def index_html():
    return FileResponse(os.path.join(ROOT_DIR, "index.html"))


@app.get("/pricing.html")
async def pricing_html():
    return FileResponse(os.path.join(ROOT_DIR, "pricing.html"))


@app.get("/team.html")
async def team_html():
    return FileResponse(os.path.join(ROOT_DIR, "team.html"))


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(os.path.join(ROOT_DIR, "favicon.ico"))


@app.get("/css/{path:path}")
async def css_files(path: str):
    return FileResponse(os.path.join(ROOT_DIR, "css", path))


@app.get("/js/{path:path}")
async def js_files(path: str):
    return FileResponse(os.path.join(ROOT_DIR, "js", path))


@app.get("/admin")
async def admin_root():
    return FileResponse(os.path.join(ROOT_DIR, "admin", "index.html"))

@app.get("/admin/{path:path}")
async def admin_files(path: str):
    if not path or path.endswith("/"):
        # 直接访问 /admin/ 或 /admin 时返回 index.html
        return FileResponse(os.path.join(ROOT_DIR, "admin", "index.html"))
    file_path = os.path.join(ROOT_DIR, "admin", path)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        # SPA fallback: 如果文件不存在，返回 admin/index.html
        file_path = os.path.join(ROOT_DIR, "admin", "index.html")
    return FileResponse(file_path)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    """启动时初始化数据库"""
    init_db()
