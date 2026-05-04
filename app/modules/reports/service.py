from __future__ import annotations

import asyncio

from app.adapters.easyagent.llm_factory import build_easyllm


class ReportService:
    def __init__(self):
        try:
            self.llm = build_easyllm()
        except Exception:
            self.llm = None

    async def generate_brief(self, prompt: str, context: dict) -> str:
        if self.llm is None:
            return self._fallback_summary(prompt, context)
        llm_prompt = (
            "Produce a concise chemistry intelligence brief grounded in the provided structured context.\n"
            f"User prompt: {prompt}\nContext: {context}"
        )
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self.llm.invoke, [{"role": "user", "content": llm_prompt}]),
                timeout=10,
            )
            return str(result)
        except Exception:
            return self._fallback_summary(prompt, context)

    @staticmethod
    def _fallback_summary(prompt: str, context: dict) -> str:
        parts: list[str] = [f"Brief for: {prompt}"]
        compound = context.get("compound")
        if isinstance(compound, dict) and compound.get("primary_name"):
            parts.append(
                f"Compound: {compound['primary_name']}. {compound.get('summary', '')}".strip()
            )
        target = context.get("target")
        if isinstance(target, dict) and target.get("symbol"):
            parts.append(f"Target: {target['symbol']}. {target.get('summary', '')}".strip())
        bioactivity = context.get("bioactivity")
        if isinstance(bioactivity, list) and bioactivity:
            first = bioactivity[0]
            parts.append(
                f"Bioactivity example: {first.get('compound_name', 'compound')} vs {first.get('target_symbol', 'target')} "
                f"{first.get('activity_type', '')} {first.get('activity_value', '')} {first.get('activity_unit', '')}".strip()
            )
        literature = context.get("literature", {})
        citations = literature.get("citations") if isinstance(literature, dict) else None
        if citations:
            parts.append(f"Evidence: {citations[0].get('paper_title', 'literature result')}")
        return " ".join(part for part in parts if part)
