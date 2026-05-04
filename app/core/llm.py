from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def _ensure_easyagent_importable() -> None:
    settings = get_settings()
    easyagent_path = Path(settings.easyagent_path).resolve()
    if str(easyagent_path) not in sys.path:
        sys.path.insert(0, str(easyagent_path))


def build_easyllm() -> Any:
    settings = get_settings()
    if not settings.llm_enabled:
        return None
    _ensure_easyagent_importable()
    from easyagent import EasyLLM

    return EasyLLM(
        provider=settings.llm_provider,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        temperature=settings.llm_temperature,
        timeout=settings.llm_timeout,
    )
