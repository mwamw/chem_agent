from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    display_name: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    tenant_id: str
