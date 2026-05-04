from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


@dataclass
class ToolContext:
    tenant_id: str
    user_id: str
    run_id: str | None
    services: dict[str, Any]


@dataclass
class ToolResult:
    status: str
    content: str = ""
    structured_data: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


ToolHandler = Callable[[dict[str, Any], ToolContext], Awaitable[ToolResult]]


@dataclass
class ToolDefinition:
    name: str
    description: str
    permission_key: str
    handler: ToolHandler
