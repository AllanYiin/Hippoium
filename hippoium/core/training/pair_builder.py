"""
PairBuilder – align messages into (prompt, completion) pairs.
"""
from __future__ import annotations
from typing import List, Tuple
from hippoium.ports.domain import Message


class PairBuilder:
    def build(self, history: List[Message]) -> List[Tuple[str, str]]:
        pairs: List[Tuple[str, str]] = []
        for i in range(0, len(history) - 1, 2):
            user_msg, assistant_msg = history[i], history[i + 1]
            if user_msg.role == "user" and assistant_msg.role == "assistant":
                pairs.append((user_msg.content, assistant_msg.content))
        return pairs
