from __future__ import annotations

from app.modules.tools.base import ToolContext, ToolDefinition, ToolResult


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition:
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools.keys())


def build_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()

    async def compound_resolve(payload: dict, ctx: ToolContext) -> ToolResult:
        compound = await ctx.services["compound"].resolve(ctx.tenant_id, payload["query"])
        return ToolResult(status="success", structured_data={"compound_id": compound.id, "primary_name": compound.primary_name})

    async def compound_profile(payload: dict, ctx: ToolContext) -> ToolResult:
        compound = await ctx.services["compound"].get(ctx.tenant_id, payload["compound_id"])
        synonyms = await ctx.services["compound"].get_synonyms(compound.id)
        return ToolResult(
            status="success",
            structured_data={
                "compound_id": compound.id,
                "primary_name": compound.primary_name,
                "summary": compound.summary,
                "synonyms": synonyms,
                "properties": compound.properties_json,
            },
        )

    async def target_search(payload: dict, ctx: ToolContext) -> ToolResult:
        targets = await ctx.services["target"].search(ctx.tenant_id, payload["query"])
        return ToolResult(
            status="success",
            structured_data=[{"target_id": row.id, "symbol": row.symbol, "summary": row.summary} for row in targets],
        )

    async def target_profile(payload: dict, ctx: ToolContext) -> ToolResult:
        target = await ctx.services["target"].get(ctx.tenant_id, payload["target_id"])
        return ToolResult(
            status="success",
            structured_data={"target_id": target.id, "symbol": target.symbol, "summary": target.summary},
        )

    async def bioactivity_search(payload: dict, ctx: ToolContext) -> ToolResult:
        rows = await ctx.services["bioactivity"].search(
            ctx.tenant_id,
            target_query=payload.get("target_query"),
            compound_query=payload.get("compound_query"),
            limit=payload.get("limit", 10),
        )
        return ToolResult(status="success", structured_data=rows)

    async def literature_search(payload: dict, ctx: ToolContext) -> ToolResult:
        rows = await ctx.services["literature"].search(
            ctx.tenant_id,
            payload["query"],
            k=payload.get("k", 4),
            profile=payload.get("profile", "balanced"),
        )
        return ToolResult(status="success", structured_data=rows)

    async def report_generate(payload: dict, ctx: ToolContext) -> ToolResult:
        text = await ctx.services["report"].generate_brief(payload["prompt"], payload["context"])
        return ToolResult(status="success", content=text, structured_data={"text": text})

    for name, description, permission_key, handler in [
        ("compound.resolve", "Resolve a compound from a chemistry query.", "tool:compound:resolve", compound_resolve),
        ("compound.get_profile", "Get a compound profile.", "tool:compound:get", compound_profile),
        ("target.search", "Search targets.", "tool:target:search", target_search),
        ("target.get_profile", "Get target profile.", "tool:target:get", target_profile),
        ("bioactivity.search", "Search bioactivity facts.", "tool:bioactivity:search", bioactivity_search),
        ("literature.search", "Search literature evidence.", "tool:literature:search", literature_search),
        ("report.generate_brief", "Generate a grounded brief.", "tool:report:generate", report_generate),
    ]:
        registry.register(ToolDefinition(name=name, description=description, permission_key=permission_key, handler=handler))

    return registry
