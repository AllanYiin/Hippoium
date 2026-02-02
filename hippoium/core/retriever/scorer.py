"""Hybrid retrieval scorer based on vector similarities.

This module implements the positive/negative cosine similarity scoring
described in the project README. A positive similarity between the
query and document is computed and penalised by ``β`` times the
similarity between a *negative* query and the document.
"""
from __future__ import annotations

from typing import Sequence, List

import numpy as np

from hippoium.ports.domain import Message
from hippoium.ports.port_types import ScoreFn
from hippoium.ports.constants import DEFAULT_BETA
from hippoium.ports.protocols import EmbeddingClient


class HybridScorer:
    """Score documents using hybrid positive/negative cosine similarity."""

    def __init__(self, embedding_client: EmbeddingClient, beta: float = DEFAULT_BETA, mode: ScoreFn = ScoreFn.HYBRID):
        self.beta = beta
        self.mode = mode
        self.embedding_client = embedding_client

    def _cos_sim(self, vec1: List[float], vec2: List[float]) -> float:
        """Return cosine similarity between two vectors."""
        a = np.array(vec1)
        b = np.array(vec2)
        denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)

    def score(self, query: str, docs: Sequence[Message]) -> List[float]:
        """Compute hybrid scores for ``docs`` given ``query``."""

        # Obtain embeddings for the query and a simple negative query.
        q_vec = self._embed_one(query)
        neg_query = query[::-1]  # Placeholder negative example.
        neg_vec = self._embed_one(neg_query)

        scores: List[float] = []
        for d in docs:
            doc_vec = self._embed_one(d.content)

            pos = self._cos_sim(q_vec, doc_vec)
            neg = self._cos_sim(neg_vec, doc_vec)

            if self.mode is ScoreFn.POS_COS:
                s = pos
            elif self.mode is ScoreFn.NEG_COS:
                s = 1 - neg
            else:
                s = pos - self.beta * neg
            scores.append(s)
        return scores

    def _embed_one(self, text: str) -> List[float]:
        vectors = list(self.embedding_client.embed([text]))
        if not vectors:
            return []
        return list(vectors[0])
