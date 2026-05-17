# -*- coding: utf-8 -*-
"""
合规知识图谱 API路由 — 中韩出海数智港

注册到 main.py:
    from backend.routers.compliance_knowledge import router as compliance_knowledge_router
    app.include_router(compliance_knowledge_router)

端点:
    GET /api/compliance/knowledge/dimensions
    GET /api/compliance/knowledge/articles?dimension=xxx
    GET /api/compliance/knowledge/search?keyword=xxx
    GET /api/compliance/knowledge/compare?topic=data_retention
    GET /api/compliance/knowledge/statistics
    GET /api/compliance/knowledge/obligations
    GET /api/compliance/knowledge/recommendations?q1=2&q2=3
"""

from backend.compliance.knowledge_graph import (
    router as knowledge_graph_router,
    get_dimensions,
    get_articles_by_dimension,
    compare_across_regulations,
    get_recommendations,
    search_articles,
    list_all_obligations,
    get_knowledge_statistics,
    ALL_ARTICLES,
    ARTICLE_MAP,
    COMPARE_TOPICS,
)

# The router is already defined in knowledge_graph.py
# This file re-exports it for clean import in main.py
router = knowledge_graph_router
