"""合规反馈收集器"""
import sqlite3, os, uuid
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/compliance/feedback", tags=["compliance-feedback"])
DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "compliance_feedback.db")

def _db():
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS feedback (id TEXT PRIMARY KEY, query TEXT, reply TEXT, helpful INTEGER, dimension TEXT, language TEXT, comment TEXT, created_at TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS accuracy_log (id TEXT PRIMARY KEY, query TEXT, ai_reply TEXT, expert_reply TEXT, expert_rating INTEGER, corrected BOOLEAN, created_at TEXT)")
    conn.commit()
    return conn

class FB(BaseModel):
    query: str; reply: str; helpful: bool
    dimension: Optional[str] = None; language: Optional[str] = "zh"; comment: Optional[str] = ""

@router.post("")
def submit(fb: FB):
    c = _db()
    c.execute("INSERT INTO feedback VALUES (?,?,?,?,?,?,?,?)",
              (uuid.uuid4().hex[:8], fb.query[:200], fb.reply[:500], 1 if fb.helpful else 0,
               fb.dimension, fb.language, fb.comment[:200], datetime.now().isoformat()))
    c.commit()
    return {"status": "ok"}

@router.get("/stats")
def stats():
    c = _db()
    t = c.execute("SELECT COUNT(*) as c FROM feedback").fetchone()[0]
    h = c.execute("SELECT COUNT(*) as c FROM feedback WHERE helpful=1").fetchone()[0]
    return {"total": t, "helpful": h, "accuracy": round(h/t*100,1) if t>0 else 0}
