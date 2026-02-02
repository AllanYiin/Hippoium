"""
Negative Vault engine – persists & retrieves negative samples.
"""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
from typing import List
from hippoium.ports.domain import Message
from hippoium.core.utils.serializer import to_json, from_json


class NegVaultStore:
    def __init__(self, path: str | Path = "neg_vault.jsonl"):
        self.path = Path(path)

    def add(self, msg: Message):
        with self.path.open("a", encoding="utf-8") as fp:
            fp.write(to_json(asdict(msg)) + "\n")

    def load(self) -> List[Message]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as fp:
            messages: List[Message] = []
            for line in fp:
                data = from_json(line)
                messages.append(
                    Message(
                        role=data.get("role", ""),
                        content=data.get("content", ""),
                        metadata=data.get("metadata") or {},
                    )
                )
            return messages
