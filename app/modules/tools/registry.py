from __future__ import annotations

from pydantic import BaseModel, Field

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

    class CompoundResolveInput(BaseModel):
        query: str = Field(min_length=1, max_length=255)

    class CompoundProfileInput(BaseModel):
        compound_id: str = Field(min_length=1, max_length=64)

    class TargetSearchInput(BaseModel):
        query: str = Field(min_length=1, max_length=255)

    class TargetProfileInput(BaseModel):
        target_id: str = Field(min_length=1, max_length=64)

    class BioactivitySearchInput(BaseModel):
        target_query: str | None = Field(default=None, max_length=255)
        compound_query: str | None = Field(default=None, max_length=255)
        limit: int = Field(default=10, ge=1, le=50)

    class LiteratureSearchInput(BaseModel):
        query: str = Field(min_length=1, max_length=1000)
        profile: str = "balanced"
        k: int = Field(default=4, ge=1, le=20)

    class ReportGenerateInput(BaseModel):
        prompt: str = Field(min_length=1, max_length=2000)
        context: dict

    async def compound_resolve(payload: dict, ctx: ToolContext) -> ToolResult:
        compound = await ctx.services["compound"].resolve(ctx.tenant_id, payload["query"])
        return ToolResult(
            status="success",
            structured_data={"compound_id": compound.id, "primary_name": compound.primary_name},
        )

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
            structured_data=[
                {"target_id": row.id, "symbol": row.symbol, "summary": row.summary}
                for row in targets
            ],
        )

    async def target_profile(payload: dict, ctx: ToolContext) -> ToolResult:
        target = await ctx.services["target"].get(ctx.tenant_id, payload["target_id"])
        return ToolResult(
            status="success",
            structured_data={
                "target_id": target.id,
                "symbol": target.symbol,
                "summary": target.summary,
            },
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

    for name, description, permission_key, input_model, handler in [
        (
            "compound.resolve",
            "Resolve a compound from a chemistry query.",
            "tool:compound:resolve",
            CompoundResolveInput,
            compound_resolve,
        ),
        (
            "compound.get_profile",
            "Get a compound profile.",
            "tool:compound:get",
            CompoundProfileInput,
            compound_profile,
        ),
        (
            "target.search",
            "Search targets.",
            "tool:target:search",
            TargetSearchInput,
            target_search,
        ),
        (
            "target.get_profile",
            "Get target profile.",
            "tool:target:get",
            TargetProfileInput,
            target_profile,
        ),
        (
            "bioactivity.search",
            "Search bioactivity facts.",
            "tool:bioactivity:search",
            BioactivitySearchInput,
            bioactivity_search,
        ),
        (
            "literature.search",
            "Search literature evidence.",
            "tool:literature:search",
            LiteratureSearchInput,
            literature_search,
        ),
        (
            "report.generate_brief",
            "Generate a grounded brief.",
            "tool:report:generate",
            ReportGenerateInput,
            report_generate,
        ),
    ]:
        registry.register(
            ToolDefinition(
                name=name,
                description=description,
                permission_key=permission_key,
                input_model=input_model,
                handler=handler,
            )
        )

    return registry
