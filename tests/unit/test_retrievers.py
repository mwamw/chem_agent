from app.adapters.easyagent.retrievers import HybridRetriever


def test_hybrid_retriever_returns_ranked_chunks():
    retriever = HybridRetriever(llm=None, multi_query_count=2)
    chunks = [
        {
            "chunk_id": "a",
            "paper_id": "p1",
            "paper_title": "Gefitinib profile",
            "section_title": "abstract",
            "content": "Gefitinib is an EGFR inhibitor used in lung cancer.",
            "metadata": {},
        },
        {
            "chunk_id": "b",
            "paper_id": "p2",
            "paper_title": "PARP review",
            "section_title": "abstract",
            "content": "Olaparib is a PARP inhibitor.",
            "metadata": {},
        },
    ]
    results = retriever.retrieve("EGFR inhibitor", chunks, k=1, profile="balanced")
    assert len(results) == 1
    assert results[0].chunk_id == "a"


def test_hybrid_retriever_boosts_exact_compound_match():
    retriever = HybridRetriever(llm=None, multi_query_count=2)
    chunks = [
        {
            "chunk_id": "gefitinib",
            "paper_id": "p1",
            "paper_title": "Clinical and pharmacologic profile of gefitinib",
            "section_title": "abstract",
            "content": "Gefitinib is an orally available EGFR inhibitor used as a reference targeted therapy.",
            "metadata": {},
        },
        {
            "chunk_id": "parp",
            "paper_id": "p2",
            "paper_title": "PARP inhibition and synthetic lethality",
            "section_title": "abstract",
            "content": "Olaparib is a clinically important PARP inhibitor used in oncology practice.",
            "metadata": {},
        },
    ]
    results = retriever.retrieve(
        "Give me a short research brief on Gefitinib and cite evidence.",
        chunks,
        k=2,
        profile="high_recall",
    )
    assert results[0].chunk_id == "gefitinib"
