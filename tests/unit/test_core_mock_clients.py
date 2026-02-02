from hippoium.core.retriever.scorer import HybridScorer
from hippoium.ports.domain import Message


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.calls = []

    def embed(self, texts, **opts):
        values = []
        for text in texts:
            self.calls.append(text)
            values.append([float(len(text)), float(len(text) % 3)])
        return values


def test_hybrid_scorer_with_mock_embeddings():
    embedder = FakeEmbeddingClient()
    scorer = HybridScorer(embedding_client=embedder)
    docs = [
        Message(role="user", content="alpha"),
        Message(role="assistant", content="beta gamma"),
    ]

    scores = scorer.score("query", docs)

    assert len(scores) == len(docs)
    assert embedder.calls[0] == "query"
