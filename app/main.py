from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import init_db
from app.modules.activities.router import router as bioactivity_router
from app.modules.agents.router import router as agent_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.compounds.router import router as compound_router
from app.modules.literature.router import router as literature_router
from app.modules.rag.router import router as rag_router
from app.modules.targets.router import router as target_router


settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title=settings.project_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = settings.api_v1_prefix
app.include_router(auth_router, prefix=api_prefix)
app.include_router(compound_router, prefix=api_prefix)
app.include_router(target_router, prefix=api_prefix)
app.include_router(bioactivity_router, prefix=api_prefix)
app.include_router(literature_router, prefix=api_prefix)
app.include_router(rag_router, prefix=api_prefix)
app.include_router(agent_router, prefix=api_prefix)
app.include_router(audit_router, prefix=api_prefix)


@app.get("/")
async def root() -> dict:
    return {"name": settings.project_name, "status": "ok"}
