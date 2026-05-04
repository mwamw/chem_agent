from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.observability import generate_trace_id
from app.core.exceptions import NotFoundError
from app.db.models import AgentRun, AgentStep
from app.modules.activities.service import BioactivityService
from app.modules.audit.service import AuditService
from app.modules.compounds.service import CompoundService
from app.modules.literature.service import LiteratureService
from app.modules.reports.service import ReportService
from app.modules.targets.service import TargetService
from app.modules.tools.base import ToolContext
from app.modules.tools.executor import ToolExecutor
from app.modules.tools.registry import build_tool_registry


class AgentRunService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.compounds = CompoundService(session)
        self.targets = TargetService(session)
        self.bioactivities = BioactivityService(session)
        self.literature = LiteratureService(session)
        self.reports = ReportService()
        self.audit = AuditService(session)
        self.registry = build_tool_registry()
        self.executor = ToolExecutor(session)

    async def run(self, agent_id: str, tenant_id: str, user_id: str, user_input: str) -> AgentRun:
        trace_id = generate_trace_id()
        run = AgentRun(trace_id=trace_id, tenant_id=tenant_id, user_id=user_id, agent_id=agent_id, input_text=user_input)
        self.session.add(run)
        await self.session.flush()
        context = ToolContext(
            tenant_id=tenant_id,
            user_id=user_id,
            run_id=run.id,
            services={
                "compound": self.compounds,
                "target": self.targets,
                "bioactivity": self.bioactivities,
                "literature": self.literature,
                "report": self.reports,
            },
        )
        if agent_id == "compound_research_agent":
            actions, citations, answer = await self._run_compound_agent(user_input, context, run.id)
        elif agent_id == "target_intel_agent":
            actions, citations, answer = await self._run_target_agent(user_input, context, run.id)
        else:
            actions, citations, answer = await self._run_literature_agent(user_input, context, run.id)
        run.actions_json = actions
        run.citations_json = citations
        run.final_answer = answer
        await self.audit.log(tenant_id, user_id, "agent.run", "agent_run", run.id, {"agent_id": agent_id, "trace_id": trace_id})
        await self.session.flush()
        return run

    async def _step(self, run_id: str, index: int, step_type: str, thought_summary: str, tool_name: str | None = None, tool_input: dict | None = None, tool_output: dict | None = None) -> None:
        self.session.add(
            AgentStep(
                agent_run_id=run_id,
                step_index=index,
                step_type=step_type,
                thought_summary=thought_summary,
                tool_name=tool_name,
                tool_input=tool_input or {},
                tool_output=tool_output or {},
            )
        )
        await self.session.flush()

    async def _run_compound_agent(self, user_input: str, context: ToolContext, run_id: str) -> tuple[list[dict], list[dict], str]:
        query = await self._resolve_compound_query(user_input, context)
        await self._step(run_id, 1, "plan", f"Resolve compound entity from input: {query}")
        resolved = await self.executor.execute(self.registry.get("compound.resolve"), {"query": query}, context)
        compound_id = resolved.structured_data["compound_id"]
        await self._step(run_id, 2, "tool", "Resolved compound entity.", "compound.resolve", {"query": query}, resolved.structured_data)
        profile = await self.executor.execute(self.registry.get("compound.get_profile"), {"compound_id": compound_id}, context)
        await self._step(run_id, 3, "tool", "Loaded compound profile.", "compound.get_profile", {"compound_id": compound_id}, profile.structured_data)
        literature = await self.executor.execute(self.registry.get("literature.search"), {"query": user_input, "profile": "high_recall", "k": 4}, context)
        await self._step(run_id, 4, "tool", "Retrieved literature evidence.", "literature.search", {"query": user_input}, literature.structured_data)
        report = await self.executor.execute(
            self.registry.get("report.generate_brief"),
            {"prompt": user_input, "context": {"compound": profile.structured_data, "literature": literature.structured_data}},
            context,
        )
        await self._step(run_id, 5, "tool", "Generated final brief.", "report.generate_brief", {"prompt": user_input}, {"text": report.content})
        actions = [
            {"tool": "compound.resolve", "status": resolved.status},
            {"tool": "compound.get_profile", "status": profile.status},
            {"tool": "literature.search", "status": literature.status},
            {"tool": "report.generate_brief", "status": report.status},
        ]
        citations = literature.structured_data["citations"]
        return actions, citations, report.content

    async def _run_target_agent(self, user_input: str, context: ToolContext, run_id: str) -> tuple[list[dict], list[dict], str]:
        query = await self._resolve_target_query(user_input, context)
        await self._step(run_id, 1, "plan", f"Resolve target entity from input: {query}")
        targets = await self.executor.execute(self.registry.get("target.search"), {"query": query}, context)
        target = (targets.structured_data or [{}])[0]
        await self._step(run_id, 2, "tool", "Resolved target candidates.", "target.search", {"query": query}, {"count": len(targets.structured_data)})
        bio = await self.executor.execute(self.registry.get("bioactivity.search"), {"target_query": target.get("symbol", query), "limit": 5}, context)
        await self._step(run_id, 3, "tool", "Loaded related bioactivity evidence.", "bioactivity.search", {"target_query": target.get("symbol", query)}, {"count": len(bio.structured_data)})
        literature = await self.executor.execute(self.registry.get("literature.search"), {"query": user_input, "profile": "high_recall", "k": 4}, context)
        await self._step(run_id, 4, "tool", "Retrieved target literature evidence.", "literature.search", {"query": user_input}, literature.structured_data)
        report = await self.executor.execute(
            self.registry.get("report.generate_brief"),
            {"prompt": user_input, "context": {"target": target, "bioactivity": bio.structured_data, "literature": literature.structured_data}},
            context,
        )
        await self._step(run_id, 5, "tool", "Generated final target brief.", "report.generate_brief", {"prompt": user_input}, {"text": report.content})
        actions = [
            {"tool": "target.search", "status": targets.status},
            {"tool": "bioactivity.search", "status": bio.status},
            {"tool": "literature.search", "status": literature.status},
            {"tool": "report.generate_brief", "status": report.status},
        ]
        citations = literature.structured_data["citations"]
        return actions, citations, report.content

    async def _run_literature_agent(self, user_input: str, context: ToolContext, run_id: str) -> tuple[list[dict], list[dict], str]:
        literature = await self.executor.execute(self.registry.get("literature.search"), {"query": user_input, "profile": "high_recall", "k": 5}, context)
        await self._step(run_id, 1, "tool", "Retrieved literature evidence.", "literature.search", {"query": user_input}, literature.structured_data)
        report = await self.executor.execute(
            self.registry.get("report.generate_brief"),
            {"prompt": user_input, "context": {"literature": literature.structured_data}},
            context,
        )
        await self._step(run_id, 2, "tool", "Generated literature brief.", "report.generate_brief", {"prompt": user_input}, {"text": report.content})
        actions = [
            {"tool": "literature.search", "status": literature.status},
            {"tool": "report.generate_brief", "status": report.status},
        ]
        citations = literature.structured_data["citations"]
        return actions, citations, report.content

    @staticmethod
    def _extract_entity_candidates(text: str) -> list[str]:
        stopwords = {
            "give", "short", "research", "brief", "cite", "evidence", "summarize", "summary",
            "what", "which", "with", "about", "there", "for", "and", "the", "agent", "query",
        }
        matches = re.findall(r"[A-Za-z][A-Za-z0-9\-\+]{2,}", text)
        ranked: list[str] = []
        for token in matches:
            lowered = token.lower()
            if lowered in stopwords:
                continue
            ranked.append(token)
        return ranked or [text.strip()]

    async def _resolve_compound_query(self, text: str, context: ToolContext) -> str:
        candidates = self._extract_entity_candidates(text)
        for candidate in candidates:
            try:
                await context.services["compound"].resolve(context.tenant_id, candidate)
                return candidate
            except NotFoundError:
                continue
        return candidates[0]

    async def _resolve_target_query(self, text: str, context: ToolContext) -> str:
        candidates = self._extract_entity_candidates(text)
        for candidate in candidates:
            rows = await context.services["target"].search(context.tenant_id, candidate)
            if rows:
                return candidate
        return candidates[0]
