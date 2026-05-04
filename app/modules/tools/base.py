from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from pydantic import BaseModel


@dataclass
class ToolContext:
    tenant_id: str
    user_id: str
    run_id: str | None
    services: dict[str, Any]
    permissions: frozenset[str] = field(default_factory=frozenset)


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
    input_model: type[BaseModel] | None = None
    timeout_seconds: int = 15
