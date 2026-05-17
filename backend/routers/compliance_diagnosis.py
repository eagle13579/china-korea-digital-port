"""
合规诊断引擎 — 从单轮问答升级为"问->测->诊->报"四步流程
POST /api/v1/compliance/diagnosis/start — 启动诊断会话
POST /api/v1/compliance/diagnosis/answer — 提交答案
GET  /api/v1/compliance/diagnosis/result/{session_id} — 获取诊断报告
"""
import json, sqlite3, os, uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/v1/compliance/diagnosis", tags=["compliance-diagnosis"])
DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "compliance_diagnosis.db")

def _db():
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, company_type TEXT, industry TEXT, stage TEXT, status TEXT, score REAL, created_at TEXT, completed_at TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS answers (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, question_id TEXT, dimension TEXT, answer TEXT, score REAL)")
    return conn

# 诊断问卷（基于合规维度）
DIAG_QUESTIONS = [
    {"id": "d1", "dimension": "industry_access", "question_zh": "您的企业是否已完成中国市场的行业准入评估？",
     "options_zh": ["已完成全面评估", "正在评估中", "尚未评估"]},
    {"id": "d2", "dimension": "data_security", "question_zh": "您的企业是否涉及个人信息或数据的跨境传输？",
     "options_zh": ["不涉及", "少量涉及", "大量涉及"]},
    {"id": "d3", "dimension": "intellectual_property", "question_zh": "您的企业在中国是否已完成商标/专利布局？",
     "options_zh": ["已完成注册", "正在申请", "尚未启动"]},
    {"id": "d4", "dimension": "cross_border_tax", "question_zh": "您的企业是否了解中韩税收协定及跨境税务合规要求？",
     "options_zh": ["已聘请税务顾问", "了解基本政策", "完全不了解"]},
    {"id": "d5", "dimension": "labor_employment", "question_zh": "您的企业是否有中国境内员工或计划派遣韩籍员工？",
     "options_zh": ["已有中国团队", "计划招聘", "暂无计划"]},
    {"id": "d6", "dimension": "visa_immigration", "question_zh": "您的企业是否了解韩籍员工在华工作签证要求？",
     "options_zh": ["已办妥签证", "了解流程", "完全不清楚"]},
    {"id": "d7", "dimension": "company_formation", "question_zh": "您的企业是否已确立进入中国市场的投资架构？",
     "options_zh": ["已确定WFOE/JV", "正在比较方案", "尚未考虑"]},
    {"id": "d8", "dimension": "import_export", "question_zh": "您的企业是否有中韩进出口业务？",
     "options_zh": ["有稳定进出口", "计划开展", "暂无"]},
]

class StartRequest(BaseModel):
    company_type: Optional[str] = None
    industry: Optional[str] = None

class AnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: str

@router.post("/start")
def start_diagnosis(req: StartRequest):
    sid = uuid.uuid4().hex[:12]
    c = _db()
    c.execute("INSERT INTO sessions (id, company_type, industry, status, created_at) VALUES (?,?,?,?,?)",
              (sid, req.company_type, req.industry, "in_progress", datetime.now().isoformat()))
    c.commit()
    return {"session_id": sid, "questions": DIAG_QUESTIONS, "total": len(DIAG_QUESTIONS)}

@router.post("/answer")
def submit_answer(req: AnswerRequest):
    c = _db()
    session = c.execute("SELECT * FROM sessions WHERE id=?", (req.session_id,)).fetchone()
    if not session or session["status"] != "in_progress":
        raise HTTPException(404, "会话不存在或已完成")
    
    # Find question
    q = None
    for qq in DIAG_QUESTIONS:
        if qq["id"] == req.question_id:
            q = qq
            break
    if not q:
        raise HTTPException(404, "问题不存在")
    
    score = {"已完成全面评估": 0, "正在评估中": 1, "尚未评估": 2,
             "不涉及": 0, "少量涉及": 1, "大量涉及": 2,
             "已完成注册": 0, "正在申请": 1, "尚未启动": 2,
             "已聘请税务顾问": 0, "了解基本政策": 1, "完全不了解": 2,
             "已有中国团队": 0, "计划招聘": 1, "暂无计划": 2,
             "已办妥签证": 0, "了解流程": 1, "完全不清楚": 2,
             "已确定WFOE/JV": 0, "正在比较方案": 1, "尚未考虑": 2,
             "有稳定进出口": 0, "计划开展": 1, "暂无": 2}.get(req.answer, 1)
    
    c.execute("INSERT INTO answers (session_id, question_id, dimension, answer, score) VALUES (?,?,?,?,?)",
              (req.session_id, q["id"], q["dimension"], req.answer, score))
    c.commit()
    
    return {"status": "ok", "question_id": req.question_id, "score": score}

@router.get("/result/{session_id}")
def get_result(session_id: str):
    c = _db()
    session = c.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not session:
        raise HTTPException(404, "会话不存在")
    
    answers = c.execute("SELECT * FROM answers WHERE session_id=?", (session_id,)).fetchall()
    answered = len(answers)
    total = len(DIAG_QUESTIONS)
    
    dim_scores = {}
    for a in answers:
        dim = a["dimension"]
        if dim not in dim_scores:
            dim_scores[dim] = []
        dim_scores[dim].append(a["score"])
    
    avg_per_dim = {dim: round(sum(s)/len(s), 1) for dim, s in dim_scores.items()}
    overall = round(sum(avg_per_dim.values()) / max(len(avg_per_dim), 1), 1)
    
    # Normalize to 0-100
    health = max(0, min(100, round((1 - overall / 2) * 100)))
    
    risk_level = "低" if health >= 70 else ("中" if health >= 40 else "高")
    
    return {
        "session_id": session_id,
        "status": "completed" if answered >= total else "in_progress",
        "progress": f"{answered}/{total}",
        "health_score": health,
        "risk_level": risk_level,
        "by_dimension": avg_per_dim,
        "details": [{"question": d["question_zh"], "answer": a["answer"], "dimension": d["dimension"]}
                    for d, a in zip(DIAG_QUESTIONS, answers)],
    }
