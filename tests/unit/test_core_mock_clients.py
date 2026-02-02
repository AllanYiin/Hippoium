import os

import pytest

from hippoium.adapters.openai import OpenAIAdapter
from hippoium.core.retriever.scorer import HybridScorer
from hippoium.ports.domain import Message


def test_hybrid_scorer_with_mock_embeddings():
    pytest.importorskip("openai")
    api_key = os.getenv("OPENAI-API-KEY")
    if not api_key:
        pytest.skip("環境未設定 OPENAI-API-KEY")
    embedder = OpenAIAdapter(api_key=api_key)
    scorer = HybridScorer(embedding_client=embedder)
    docs = [
        Message(role="user", content="alpha"),
        Message(role="assistant", content="beta gamma"),
    ]

    scores = scorer.score("query", docs)

    assert len(scores) == len(docs)
