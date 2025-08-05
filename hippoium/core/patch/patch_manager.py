"""
PatchManager – MVCC-style artifact version control.
"""
from __future__ import annotations
from typing import Dict
from hippoium.ports.types import Artifact
from hippoium.core.utils.hasher import hash_text
from .diff_generator import generate_delta


class PatchManager:
    def __init__(self):
        self.versions: Dict[str, list[Artifact]] = {}

    def commit(self, artifact: Artifact):
        self.versions.setdefault(artifact.id, []).append(artifact)

    def delta_commit(self, prev: Artifact, next_artifact: Artifact):
        delta = generate_delta(prev.data, next_artifact.data)
        next_artifact.data = delta
        self.commit(next_artifact)

    def latest(self, aid: str) -> Artifact | None:
        lst = self.versions.get(aid)
        return lst[-1] if lst else None

    def checksum(self, artifact: Artifact) -> str:
        return hash_text(str(artifact.data))
