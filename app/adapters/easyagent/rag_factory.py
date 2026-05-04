from __future__ import annotations

from app.adapters.easyagent.llm_factory import build_easyllm
from app.adapters.easyagent.retrievers import HybridRetriever
from app.core.config import get_settings


def build_hybrid_retriever() -> HybridRetriever:
    settings = get_settings()
    llm = None
    try:
        llm = build_easyllm()
    except Exception:
        llm = None
    return HybridRetriever(llm=llm, multi_query_count=settings.rag_multi_query_count)
