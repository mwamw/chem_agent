from __future__ import annotations

import hashlib
import math
import re

import httpx

from app.core.config import get_settings

TOKEN_RE = re.compile(r"[A-Za-z0-9\-\+]+")


class EmbeddingClient:
    def __init__(self):
        self.settings = get_settings()

    async def embed_text(self, text: str) -> list[float]:
        if self.settings.embedding_api_key and self.settings.embedding_api_key != "test":
            try:
                return await self._remote_embedding(text)
            except Exception:
                pass
        return self._deterministic_embedding(text)

    async def _remote_embedding(self, text: str) -> list[float]:
        url = f"{self.settings.embedding_base_url.rstrip('/')}/embeddings"
        async with httpx.AsyncClient(timeout=self.settings.llm_timeout) as client:
            response = await client.post(
                url,
                headers={"authorization": f"Bearer {self.settings.embedding_api_key}"},
                json={"model": self.settings.embedding_model, "input": text},
            )
            response.raise_for_status()
            payload = response.json()
            embedding = payload["data"][0]["embedding"]
            return self._normalize([float(value) for value in embedding])

    def _deterministic_embedding(self, text: str) -> list[float]:
        dimension = self.settings.embedding_dimension
        vector = [0.0] * dimension
        for token in TOKEN_RE.findall(text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        return self._normalize(vector)

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def to_pgvector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"
