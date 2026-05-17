# 合规增值模块 — Compliance Add-on

> **状态**：增值模块（非主产品核心）
> **定位**：作为"中韩出海数智港"的差异化壁垒在定价页提及，不作为首页主推功能。

## 说明

合规能力（AI合规自检、法规监控、知识图谱、PDF报告）已从核心产品中移除，
归档至 `_archive/compliance/` 目录。

如需重新启用合规模块：

```bash
# 1. 恢复模块文件
cp _archive/compliance/*.py backend/compliance/

# 2. 恢复Router
cp _archive/compliance/compliance_v1.py backend/routers/
cp _archive/compliance/compliance_knowledge.py backend/routers/
cp _archive/compliance/compliance_baseline.py backend/routers/

# 3. 恢复main.py中的导入和路由注册
# 参照 _archive/compliance/main_compliance_ref.txt
```

## 原模块文件清单

| 文件 | 原路径 | 说明 |
|------|--------|------|
| `questions_data.py` | `backend/compliance/` | 8道合规自检题数据 |
| `report_score.py` | `backend/compliance/` | 评分算法引擎 |
| `report_pdf.py` | `backend/compliance/` | PDF报告生成 |
| `knowledge_graph.py` | `backend/compliance/` | 合规知识图谱 |
| `regulatory_monitor.py` | `backend/compliance/` | 法规变化追踪 |
| `compliance_baseline.py` | `backend/` | 合规基准API |
| `compliance_v1.py` | `backend/routers/` | 合规自检Router v1 |
| `compliance_knowledge.py` | `backend/routers/` | 知识图谱Router |
| `compliance_baseline.py` | `backend/routers/` | 合规基准Router |

## 前端页面

合规相关HTML页面已移入 `_archive/compliance/`：
- `compliance_report.html`
- `合规自检.html`
- `compliance-check.html`

## 数据文件

合规数据文件保留在 `backend/compliance/`：
- `_kg_articles.json`
- `_kg_dims.json`
- `_kg_qref.json`
- `_kg_rels.json`
- `PRD_DESIGN_SPEC.md`
- `frontend_design.md`
