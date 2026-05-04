from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

TOKEN_RE = re.compile(r"[A-Za-z0-9\-\+]+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "brief",
    "by",
    "cite",
    "evidence",
    "for",
    "from",
    "give",
    "how",
    "in",
    "is",
    "me",
    "of",
    "on",
    "or",
    "short",
    "summarize",
    "summary",
    "the",
    "there",
    "to",
    "what",
    "with",
}


@dataclass
class RetrievedChunk:
    chunk_id: str
    paper_id: str
    paper_title: str
    section_title: str
    content: str
    metadata: dict[str, Any]
    score: float


def _tokenize(text: str) -> list[str]:
    lowered = text.lower()
    tokens = TOKEN_RE.findall(lowered)
    if tokens:
        return tokens
    return lowered.split()


def _tfidf_score(
    query_tokens: list[str], doc_tokens: list[str], document_frequency: Counter, total_docs: int
) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    doc_counter = Counter(doc_tokens)
    score = 0.0
    for token in query_tokens:
        tf = doc_counter[token] / max(len(doc_tokens), 1)
        df = max(document_frequency[token], 1)
        idf = math.log((1 + total_docs) / df) + 1
        score += tf * idf
    return score


def _dense_overlap(query_tokens: list[str], doc_tokens: list[str]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    query_set = set(query_tokens)
    doc_set = set(doc_tokens)
    intersection = len(query_set & doc_set)
    union = len(query_set | doc_set)
    return intersection / max(union, 1)


def _extract_salient_terms(text: str) -> list[str]:
    raw_tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-\+]{2,}", text)
    terms: list[str] = []
    seen: set[str] = set()
    for token in raw_tokens:
        lowered = token.lower()
        if lowered in STOPWORDS:
            continue
        if token.isupper() or token[0].isupper() or len(token) >= 5:
            if lowered not in seen:
                terms.append(lowered)
                seen.add(lowered)
    return terms


def _query_phrases(query_tokens: list[str]) -> list[str]:
    filtered = [token for token in query_tokens if token not in STOPWORDS]
    phrases: list[str] = []
    for size in (3, 2):
        for index in range(0, max(len(filtered) - size + 1, 0)):
            phrase = " ".join(filtered[index : index + size])
            if phrase not in phrases:
                phrases.append(phrase)
    return phrases


def _heuristic_boost(query: str, paper_title: str, content: str) -> float:
    title_lower = paper_title.lower()
    content_lower = content.lower()
    title_tokens = set(_tokenize(paper_title))
    content_tokens = set(_tokenize(content))
    boost = 0.0

    terms = _extract_salient_terms(query)
    for term in terms:
        if term in title_tokens:
            boost += 1.2
        if term in content_tokens:
            boost += 0.6

    query_tokens = _tokenize(query)
    for phrase in _query_phrases(query_tokens):
        if phrase in title_lower:
            boost += 0.9
        if phrase in content_lower:
            boost += 0.4

    query_lower = query.lower().strip()
    if query_lower and query_lower in title_lower:
        boost += 1.0
    if query_lower and query_lower in content_lower:
        boost += 0.5
    return boost


class HybridRetriever:
    def __init__(self, llm: Any | None = None, multi_query_count: int = 3):
        self.llm = llm
        self.multi_query_count = multi_query_count

    def retrieve(
        self, query: str, chunks: list[dict[str, Any]], k: int = 4, profile: str = "balanced"
    ) -> list[RetrievedChunk]:
        expanded_queries = [query]
        if profile in {"high_recall", "multi_query"}:
            expanded_queries = self._expand_queries(query)
        scored: dict[str, RetrievedChunk] = {}
        for subquery in expanded_queries:
            batch = self._retrieve_once(subquery, chunks, k=max(k * 2, 6))
            for item in batch:
                previous = scored.get(item.chunk_id)
                if previous is None or item.score > previous.score:
                    scored[item.chunk_id] = item
        merged = sorted(scored.values(), key=lambda item: item.score, reverse=True)
        if profile in {"high_recall", "rerank"}:
            merged = self._rerank(query, merged, top_k=k)
        return merged[:k]

    def _retrieve_once(
        self, query: str, chunks: list[dict[str, Any]], k: int
    ) -> list[RetrievedChunk]:
        docs_tokens = [_tokenize(chunk["content"]) for chunk in chunks]
        title_tokens_list = [_tokenize(chunk["paper_title"]) for chunk in chunks]
        document_frequency: Counter = Counter()
        title_document_frequency: Counter = Counter()
        for tokens in docs_tokens:
            document_frequency.update(set(tokens))
        for tokens in title_tokens_list:
            title_document_frequency.update(set(tokens))
        query_tokens = _tokenize(query)
        ranked: list[RetrievedChunk] = []
        for raw, doc_tokens, title_tokens in zip(chunks, docs_tokens, title_tokens_list):
            bm25_like = _tfidf_score(query_tokens, doc_tokens, document_frequency, len(chunks))
            title_bm25 = _tfidf_score(
                query_tokens, title_tokens, title_document_frequency, len(chunks)
            )
            dense_like = _dense_overlap(query_tokens, doc_tokens)
            title_dense = _dense_overlap(query_tokens, title_tokens)
            heuristic = _heuristic_boost(query, raw["paper_title"], raw["content"])
            score = (
                0.35 * bm25_like
                + 0.20 * title_bm25
                + 0.15 * dense_like
                + 0.10 * title_dense
                + 0.20 * heuristic
            )
            ranked.append(
                RetrievedChunk(
                    chunk_id=raw["chunk_id"],
                    paper_id=raw["paper_id"],
                    paper_title=raw["paper_title"],
                    section_title=raw["section_title"],
                    content=raw["content"],
                    metadata=raw["metadata"],
                    score=score,
                )
            )
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:k]

    def _expand_queries(self, query: str) -> list[str]:
        if self.llm is None:
            return [query]
        prompt = (
            f"Generate {self.multi_query_count} alternative chemistry literature search queries for the user query.\n"
            "Return one query per line with no numbering.\n\n"
            f"User query: {query}"
        )
        try:
            response = self.llm.invoke([{"role": "user", "content": prompt}])
            generated = [
                line.strip(" -0123456789.") for line in str(response).splitlines() if line.strip()
            ]
            return [query] + generated[: self.multi_query_count]
        except Exception:
            return [query]

    def _rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        if not candidates:
            return []
        heuristic_scores = {
            item.chunk_id: _heuristic_boost(query, item.paper_title, item.content) + item.score
            for item in candidates[: max(top_k * 2, 6)]
        }
        if self.llm is None:
            return sorted(
                candidates,
                key=lambda item: (heuristic_scores.get(item.chunk_id, item.score), item.score),
                reverse=True,
            )[:top_k]
        prompt_lines = [
            "Score the relevance of each chunk to the chemistry query from 0 to 10.",
            "Return JSON list with chunk_id and score.",
            f"Query: {query}",
            "Chunks:",
        ]
        for item in candidates[: max(top_k * 2, 6)]:
            prompt_lines.append(
                f"- chunk_id={item.chunk_id}; title={item.paper_title}; text={item.content[:400]}"
            )
        try:
            response = str(self.llm.invoke([{"role": "user", "content": "\n".join(prompt_lines)}]))
            scores = {}
            for chunk_id in [item.chunk_id for item in candidates]:
                match = re.search(rf"{re.escape(chunk_id)}[^0-9]*(\d+)", response)
                if match:
                    scores[chunk_id] = float(match.group(1))
            reranked = sorted(
                candidates,
                key=lambda item: (
                    scores.get(item.chunk_id, 0.0)
                    + heuristic_scores.get(item.chunk_id, item.score),
                    item.score,
                ),
                reverse=True,
            )
            return reranked[:top_k]
        except Exception:
            return sorted(
                candidates,
                key=lambda item: (heuristic_scores.get(item.chunk_id, item.score), item.score),
                reverse=True,
            )[:top_k]
