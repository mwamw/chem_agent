from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import get_current_user
from app.db.session import get_db_session
from app.modules.compounds.schemas import CompoundResolveRequest, CompoundResponse
from app.modules.compounds.service import CompoundService

router = APIRouter(prefix="/compounds", tags=["compounds"])


def _to_response(compound, synonyms: list[str]) -> CompoundResponse:
    return CompoundResponse(
        id=compound.id,
        primary_name=compound.primary_name,
        smiles=compound.smiles,
        inchi=compound.inchi,
        molecular_formula=compound.molecular_formula,
        molecular_weight=compound.molecular_weight,
        summary=compound.summary,
        properties=compound.properties_json,
        synonyms=synonyms,
    )


@router.post("/resolve", response_model=CompoundResponse)
async def resolve_compound(
    payload: CompoundResolveRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CompoundResponse:
    service = CompoundService(session)
    try:
        compound = await service.resolve(current_user.tenant_id, payload.query)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    synonyms = await service.get_synonyms(compound.id)
    return _to_response(compound, synonyms)


@router.get("/{compound_id}", response_model=CompoundResponse)
async def get_compound(
    compound_id: str,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CompoundResponse:
    service = CompoundService(session)
    compound = await service.get(current_user.tenant_id, compound_id)
    synonyms = await service.get_synonyms(compound.id)
    return _to_response(compound, synonyms)
