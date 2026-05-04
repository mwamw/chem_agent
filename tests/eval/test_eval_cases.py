import json
from pathlib import Path


def test_eval_cases_cover_all_agents():
    cases = json.loads(Path("data/seeds/eval_cases/agent_eval.json").read_text(encoding="utf-8"))
    agent_ids = {case["agent_id"] for case in cases}
    assert {"compound_research_agent", "target_intel_agent", "literature_brief_agent"} <= agent_ids


def test_rag_eval_cases_have_expected_papers():
    cases = json.loads(Path("data/seeds/eval_cases/rag_eval.json").read_text(encoding="utf-8"))
    assert cases
    for case in cases:
        assert case["expected_paper_ids"]
