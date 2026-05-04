from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("tenant"))
    name: Mapped[str] = mapped_column(String(120), unique=True)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("user"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"))
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tenant: Mapped["Tenant"] = relationship()


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("role"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(String(80))


class UserRole(Base, TimestampMixin):
    __tablename__ = "user_roles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("urole"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"))


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("perm"))
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"))
    key: Mapped[str] = mapped_column(String(120))


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("rtok"))
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    jwt_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    replaced_by_token_id: Mapped[str | None] = mapped_column(String(32), nullable=True)


class Compound(Base, TimestampMixin):
    __tablename__ = "compounds"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("cmp"))
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    primary_name: Mapped[str] = mapped_column(String(255), index=True)
    smiles: Mapped[str | None] = mapped_column(Text, nullable=True)
    inchi: Mapped[str | None] = mapped_column(Text, nullable=True)
    molecular_formula: Mapped[str | None] = mapped_column(String(80), nullable=True)
    molecular_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    properties_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_name: Mapped[str] = mapped_column(String(80), default="seed")
    source_id: Mapped[str | None] = mapped_column(String(120), nullable=True)


class CompoundSynonym(Base, TimestampMixin):
    __tablename__ = "compound_synonyms"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("syn"))
    compound_id: Mapped[str] = mapped_column(ForeignKey("compounds.id"), index=True)
    synonym: Mapped[str] = mapped_column(String(255), index=True)


class Target(Base, TimestampMixin):
    __tablename__ = "targets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("tgt"))
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    organism: Mapped[str] = mapped_column(String(120), default="Homo sapiens")
    summary: Mapped[str] = mapped_column(Text, default="")
    source_name: Mapped[str] = mapped_column(String(80), default="seed")
    source_id: Mapped[str | None] = mapped_column(String(120), nullable=True)


class Assay(Base, TimestampMixin):
    __tablename__ = "assays"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("asy"))
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    target_id: Mapped[str] = mapped_column(ForeignKey("targets.id"))
    name: Mapped[str] = mapped_column(String(255))
    assay_type: Mapped[str] = mapped_column(String(64), default="binding")
    source_name: Mapped[str] = mapped_column(String(80), default="seed")


class Bioactivity(Base, TimestampMixin):
    __tablename__ = "bioactivities"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("bio"))
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    compound_id: Mapped[str] = mapped_column(ForeignKey("compounds.id"), index=True)
    target_id: Mapped[str] = mapped_column(ForeignKey("targets.id"), index=True)
    assay_id: Mapped[str | None] = mapped_column(ForeignKey("assays.id"), nullable=True)
    activity_type: Mapped[str] = mapped_column(String(32), default="IC50")
    activity_value: Mapped[float] = mapped_column(Float)
    activity_unit: Mapped[str] = mapped_column(String(32), default="nM")
    relation: Mapped[str] = mapped_column(String(8), default="=")
    evidence_summary: Mapped[str] = mapped_column(Text, default="")


class Paper(Base, TimestampMixin):
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("pap"))
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(500), index=True)
    abstract: Mapped[str] = mapped_column(Text, default="")
    doi: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pmid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pmcid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class PaperChunk(Base, TimestampMixin):
    __tablename__ = "paper_chunks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("chk"))
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    section_title: Mapped[str] = mapped_column(String(255), default="abstract")
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ToolPolicy(Base, TimestampMixin):
    __tablename__ = "tools"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("toolpol"))
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    permission_key: Mapped[str] = mapped_column(String(120), index=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=15)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    is_side_effect: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AgentTool(Base, TimestampMixin):
    __tablename__ = "agent_tools"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("atool"))
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    tool_name: Mapped[str] = mapped_column(String(120), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ToolPermission(Base, TimestampMixin):
    __tablename__ = "tool_permissions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("tperm"))
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), index=True)
    tool_name: Mapped[str] = mapped_column(String(120), index=True)
    can_execute: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("run"))
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    input_text: Mapped[str] = mapped_column(Text)
    final_answer: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="completed")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    citations_json: Mapped[list] = mapped_column(JSON, default=list)
    actions_json: Mapped[list] = mapped_column(JSON, default=list)


class AgentStep(Base, TimestampMixin):
    __tablename__ = "agent_steps"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("step"))
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    step_index: Mapped[int] = mapped_column(Integer)
    step_type: Mapped[str] = mapped_column(String(32))
    thought_summary: Mapped[str] = mapped_column(Text, default="")
    tool_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tool_input: Mapped[dict] = mapped_column(JSON, default=dict)
    tool_output: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="success")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ToolInvocation(Base, TimestampMixin):
    __tablename__ = "tool_invocations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("tool"))
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    agent_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id"), nullable=True)
    tool_name: Mapped[str] = mapped_column(String(120), index=True)
    input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="success")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("audit"))
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail_json: Mapped[dict] = mapped_column(JSON, default=dict)


class SourceSyncJob(Base, TimestampMixin):
    __tablename__ = "source_sync_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: _id("sync"))
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    source_name: Mapped[str] = mapped_column(String(64), index=True)
    scope: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    counters_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
