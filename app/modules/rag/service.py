from __future__ import annotations

import asyncio

from app.adapters.easyagent.llm_factory import build_easyllm
from app.modules.literature.service import LiteratureService


class RAGService:
    def __init__(self, literature_service: LiteratureService):
        self.literature_service = literature_service
        try:
            self.llm = build_easyllm()
        except Exception:
            self.llm = None

    async def query(self, tenant_id: str, query: str, k: int, profile: str) -> dict:
        retrieval = await self.literature_service.search(tenant_id, query, k=k, profile=profile)
        citations = retrieval["citations"]
        if not citations:
            return {"answer": "No relevant literature found.", "citations": [], "profile": profile}
        context = "\n\n".join(
            [
                f"[{item['paper_title']} | {item['section_title']}]\n{item['snippet']}"
                for item in citations
            ]
        )
        if self.llm is not None:
            prompt = (
                "You are a chemistry literature assistant. Answer using only the cited evidence.\n\n"
                f"Question: {query}\n\nEvidence:\n{context}"
            )
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(self.llm.invoke, [{"role": "user", "content": prompt}]),
                    timeout=10,
                )
                answer = str(result)
            except Exception:
                answer = self._fallback_answer(query, citations)
        else:
            answer = self._fallback_answer(query, citations)
        return {"answer": answer, "citations": citations, "profile": profile}

    @staticmethod
    def _fallback_answer(query: str, citations: list[dict]) -> str:
        snippets = [item.get("snippet", "") for item in citations[:2] if item.get("snippet")]
        if not snippets:
            answer = f"Retrieved {len(citations)} relevant chunks for: {query}"
        else:
            answer = f"Evidence summary for '{query}': " + " ".join(snippets)
        return answer
