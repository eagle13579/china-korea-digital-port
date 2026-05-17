"""Cortex 大脑皮层引擎 API路由
将 10 个原子模块的接口暴露给前端和管理后台
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
import importlib

router = APIRouter(prefix="/api/v1/cortex", tags=["cortex"])

CORTEX_MODULES = {
    "event_bus": "cortex.event_bus",
    "process_modes": "cortex.process_modes",
    "flow_engine": "cortex.flow_engine",
    "conditional_task": "cortex.conditional_task",
    "evaluation": "cortex.evaluation",
    "agent_adapter": "cortex.agent_adapter",
    "security": "cortex.security",
    "unified_memory": "cortex.unified_memory",
    "rag_knowledge": "cortex.rag_knowledge",
    "visualizer": "cortex.visualizer",
}


def _load(mod_name: str):
    """动态加载cortex模块（捕获导入错误）"""
    full = CORTEX_MODULES.get(mod_name)
    if not full:
        raise HTTPException(404, f"未知模块: {mod_name}")
    try:
        return importlib.import_module(full)
    except ImportError as e:
        raise HTTPException(500, f"模块 {mod_name} 加载失败: {e}")


@router.get("/modules")
async def list_modules():
    """列出所有cortex模块"""
    return {
        "success": True,
        "modules": [
            {"name": k, "available": True}
            for k in CORTEX_MODULES
        ],
        "total": len(CORTEX_MODULES),
    }


@router.get("/modules/{mod_name}/info")
async def module_info(mod_name: str):
    """获取模块信息"""
    mod = _load(mod_name)
    doc = (mod.__doc__ or "").strip()[:500]
    members = [name for name in dir(mod) if not name.startswith("_")]
    return {"success": True, "name": mod_name, "doc": doc, "members": members[:30]}


# ── 流程执行 ──

class FlowExecuteRequest(BaseModel):
    mode: str = "sequential"
    steps: list[dict] = []
    context: dict = {}


@router.post("/flow/execute")
async def execute_flow(req: FlowExecuteRequest):
    """执行一个多步骤流程"""
    mod = _load("process_modes")
    engine = mod.ProcessEngine(mod.ProcessMode(req.mode))
    for step in req.steps:
        engine.add_step(step.get("name",""), step.get("agent",""), step.get("task",""),
                       step.get("depends_on"))
    import asyncio
    result = await engine.execute(req.context)
    return {"success": True, "mode": req.mode, "result": result}


# ── 评估 ──

class EvalRequest(BaseModel):
    task: str
    output: str
    expected: str = ""


@router.post("/evaluate")
async def evaluate(req: EvalRequest):
    """评估任务输出质量"""
    mod = _load("evaluation")
    report = mod.evaluate(req.task, req.output, req.expected)
    return {"success": True, "report": report.to_dict()}


# ── Guardrail ──

class GuardrailRequest(BaseModel):
    output: str
    rules: dict = {}


@router.post("/guardrail/check")
async def guardrail_check(req: GuardrailRequest):
    """检查输出是否符合Guardrail规则"""
    mod = _load("conditional_task")
    guardrail = mod.LLMGuardrail()
    banned = req.rules.get("banned", [])
    for b in banned:
        guardrail = guardrail.with_banned(b)
    if req.rules.get("min_length"):
        guardrail = guardrail.with_min_length(req.rules["min_length"])
    result = guardrail.check(req.output)
    return {"success": True, "passed": result.passed, "score": result.score, "issues": result.issues}


# ── 事件总线 ──

@router.get("/events/history")
async def event_history(event_type: str = "", limit: int = 20):
    """获取事件历史"""
    mod = _load("event_bus")
    bus = mod.EventBus()
    events = bus.get_history(event_type or None, limit)
    return {"success": True, "events": [{"type": e.type, "source": e.source, "data": e.data} for e in events]}


# ── 记忆 ──

class MemoryStoreRequest(BaseModel):
    content: str
    type: str = "short_term"
    tags: list = []
    source: str = ""
    importance: float = 0.5


@router.post("/memory/store")
async def memory_store(req: MemoryStoreRequest):
    """存储记忆"""
    mod = _load("unified_memory")
    mem = mod.UnifiedMemory()
    mem_id = mem.store(req.content, req.type, req.tags, req.source, req.importance)
    return {"success": True, "memory_id": mem_id}


@router.get("/memory/recall")
async def memory_recall(query: str, limit: int = 5):
    """召回记忆"""
    mod = _load("unified_memory")
    mem = mod.UnifiedMemory()
    results = mem.recall(query, limit)
    return {"success": True, "results": [r.to_dict() for r in results]}


# ── 知识库 ──

class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/knowledge/query")
async def knowledge_query(req: RAGQueryRequest):
    """查询知识库"""
    mod = _load("rag_knowledge")
    kb = mod.KnowledgeBase()
    results = kb.query(req.query, req.top_k)
    return {"success": True, "results": [{"text": r[0][:200], "score": round(r[1], 3)} for r in results]}


# ── 安全指纹 ──

class FingerprintRequest(BaseModel):
    agent: str
    action: str


@router.post("/security/fingerprint")
async def create_fingerprint(req: FingerprintRequest):
    """创建执行指纹"""
    mod = _load("security")
    fp = mod.create_fingerprint(req.agent, req.action)
    return {"success": True, "fingerprint": fp.to_dict()}


# ── Flow装饰器可视化 ──

@router.get("/visualizer/flow/{flow_id}")
async def visualize_flow(flow_id: str):
    """获取Flow执行状态的可视化数据"""
    mod_flow = _load("flow_engine")
    ctx = mod_flow.FlowRegistry.get(flow_id)
    if not ctx:
        raise HTTPException(404, f"Flow {flow_id} 不存在")
    return {"success": True, "flow": ctx.to_dict()}


# ── 北极星数据引擎 ──

@router.get("/polaris")
async def polaris_status():
    """获取六维北极星实时数据"""
    import sys
    sys.path.insert(0, "/mnt/d/向海容的知识库/wiki/wiki/记忆宫殿")
    from cortex.polaris_engine import get_polaris, update_dimension
    return {"success": True, "polaris": get_polaris()}


class PolarisUpdateRequest(BaseModel):
    dimension: str
    score: int
    event: str = ""


@router.post("/polaris/update")
async def polaris_update(req: PolarisUpdateRequest):
    """更新某个维度的北极星评分"""
    import sys
    sys.path.insert(0, "/mnt/d/向海容的知识库/wiki/wiki/记忆宫殿")
    from cortex.polaris_engine import update_dimension
    result = update_dimension(req.dimension, req.score, req.event or "手动更新")
    return {"success": True, "result": result}
