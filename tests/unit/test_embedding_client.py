from app.integrations.embedding_client import EmbeddingClient, to_pgvector_literal


def test_deterministic_embedding_has_configured_dimension():
    client = EmbeddingClient()
    embedding = client._deterministic_embedding("Gefitinib EGFR inhibitor")
    assert len(embedding) == client.settings.embedding_dimension
    assert any(value != 0 for value in embedding)


def test_pgvector_literal_format():
    literal = to_pgvector_literal([0.1, -0.2])
    assert literal == "[0.10000000,-0.20000000]"
