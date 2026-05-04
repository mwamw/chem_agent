from __future__ import annotations

import asyncio
import argparse
import json
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from statistics import mean
from time import perf_counter

from app.db.session import SessionFactory
from app.modules.agents.service import AgentRunService
from app.modules.literature.service import LiteratureService


@dataclass
class EvalSummary:
    cases: int
    successes: int
    average_citations: float


class EvalRunner:
    async def run_agent_suite(self, suite_path: str, tenant_id: str, user_id: str) -> dict:
        cases = json.loads(Path(suite_path).read_text(encoding="utf-8"))
        results = []
        async with SessionFactory() as session:
            service = AgentRunService(session)
            for case in cases:
                run = await service.run(case["agent_id"], tenant_id, user_id, case["query"])
                ok = all(fragment.lower() in run.final_answer.lower() for fragment in case.get("expected_contains", []))
                results.append(
                    {
                        "case_id": case["case_id"],
                        "success": ok,
                        "citations": len(run.citations_json),
                        "actions": run.actions_json,
                    }
                )
            await session.rollback()
        successes = sum(1 for row in results if row["success"])
        avg_citations = sum(row["citations"] for row in results) / max(len(results), 1)
        return {
            "suite": "agent",
            "summary": EvalSummary(
                cases=len(results),
                successes=successes,
                average_citations=avg_citations,
            ).__dict__,
            "results": results,
        }

    async def run_rag_suite(self, suite_path: str, tenant_id: str, k: int = 3, profile: str = "high_recall") -> dict:
        cases = json.loads(Path(suite_path).read_text(encoding="utf-8"))
        results = []
        latencies_ms: list[float] = []
        async with SessionFactory() as session:
            service = LiteratureService(session)
            for case in cases:
                started = perf_counter()
                retrieval = await service.search(tenant_id, case["query"], k=k, profile=profile)
                latency_ms = (perf_counter() - started) * 1000
                latencies_ms.append(latency_ms)
                citations = retrieval["citations"]
                expected_ids = set(case["expected_paper_ids"])
                paper_ids = [row["paper_id"] for row in citations]
                reciprocal_rank = 0.0
                for index, paper_id in enumerate(paper_ids, start=1):
                    if paper_id in expected_ids:
                        reciprocal_rank = 1.0 / index
                        break
                hit_at_1 = 1 if any(paper_id in expected_ids for paper_id in paper_ids[:1]) else 0
                hit_at_k = 1 if any(paper_id in expected_ids for paper_id in paper_ids[:k]) else 0
                precision_at_k = sum(1 for paper_id in paper_ids[:k] if paper_id in expected_ids) / max(min(k, len(paper_ids)), 1)
                precision_at_1 = 1.0 if paper_ids and paper_ids[0] in expected_ids else 0.0
                results.append(
                    {
                        "case_id": case["case_id"],
                        "query": case["query"],
                        "expected_paper_ids": case["expected_paper_ids"],
                        "returned_paper_ids": paper_ids,
                        "hit_at_1": hit_at_1,
                        "hit_at_k": hit_at_k,
                        "reciprocal_rank": reciprocal_rank,
                        "citation_precision_at_1": precision_at_1,
                        "citation_precision_at_k": round(precision_at_k, 4),
                        "latency_ms": round(latency_ms, 2),
                    }
                )
        sorted_latencies = sorted(latencies_ms)
        p95_index = max(ceil(len(sorted_latencies) * 0.95) - 1, 0)
        return {
            "suite": "rag",
            "summary": {
                "cases": len(results),
                "hit_at_1": round(mean(row["hit_at_1"] for row in results), 4),
                "hit_at_k": round(mean(row["hit_at_k"] for row in results), 4),
                "mrr": round(mean(row["reciprocal_rank"] for row in results), 4),
                "citation_precision_at_1": round(mean(row["citation_precision_at_1"] for row in results), 4),
                "citation_precision_at_k": round(mean(row["citation_precision_at_k"] for row in results), 4),
                "avg_latency_ms": round(mean(latencies_ms), 2),
                "p95_latency_ms": round(sorted_latencies[p95_index], 2),
                "profile": profile,
                "k": k,
            },
            "results": results,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ChemIntel evaluation suites.")
    parser.add_argument("--suite", choices=["agent", "rag", "all"], default="all")
    parser.add_argument("--tenant-id", default="tenant_demo")
    parser.add_argument("--user-id", default="user_eval")
    parser.add_argument("--profile", default="high_recall")
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()

    runner = EvalRunner()
    output: dict[str, object]
    if args.suite == "agent":
        output = asyncio.run(
            runner.run_agent_suite(
                "data/seeds/eval_cases/agent_eval.json",
                tenant_id=args.tenant_id,
                user_id=args.user_id,
            )
        )
    elif args.suite == "rag":
        output = asyncio.run(
            runner.run_rag_suite(
                "data/seeds/eval_cases/rag_eval.json",
                tenant_id=args.tenant_id,
                k=args.k,
                profile=args.profile,
            )
        )
    else:
        async def run_all() -> dict[str, object]:
            return {
                "agent": await runner.run_agent_suite(
                    "data/seeds/eval_cases/agent_eval.json",
                    tenant_id=args.tenant_id,
                    user_id=args.user_id,
                ),
                "rag": await runner.run_rag_suite(
                    "data/seeds/eval_cases/rag_eval.json",
                    tenant_id=args.tenant_id,
                    k=args.k,
                    profile=args.profile,
                ),
            }

        output = asyncio.run(run_all())
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
