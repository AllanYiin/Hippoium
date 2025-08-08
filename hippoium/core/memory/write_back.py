from __future__ import annotations
"""Write-back implementation for storing large artifacts.

This module provides a simple :class:`LocalWriteBack` that persists
`Artifact` instances into a shared :class:`ColdStore`. Artifacts are
identified by a checksum computed from their payload. The checksum is
also used as default ID if the artifact lacks one.
"""
from hippoium.ports.protocols import WriteBackAPI
from hippoium.ports.port_types import Artifact
from hippoium.core.memory.stores import ColdStore
from hippoium.core.utils.hasher import hash_text


class LocalWriteBack(WriteBackAPI):
    """Persist artifacts into an in-memory cold store.

    This basic implementation is intended for local development and
    testing. It computes a SHA-1 checksum of the artifact's data,
    stores the raw payload into :class:`ColdStore`, and returns the
    artifact's identifier as a reference string.
    """

    def __init__(self, store: ColdStore | None = None) -> None:
        self.store = store or ColdStore()

    def write(self, artifact: Artifact) -> str:
        """Persist ``artifact`` and return its reference ID.

        The artifact's checksum is computed from ``artifact.data`` using
        :func:`hash_text`. If the artifact does not already have an ID,
        the checksum is assigned as its ID. The raw data is then saved
        into the underlying :class:`ColdStore` and the artifact ID is
        returned so callers can retrieve it later.
        """
        # Compute checksum from the string representation of the data.
        art_str = str(artifact.data)
        artifact.checksum = hash_text(art_str)

        # Use checksum as ID if not already provided.
        if not getattr(artifact, "id", None):
            artifact.id = artifact.checksum

        # Persist the raw data in the cold store.
        self.store.put(artifact.id, artifact.data)
        return artifact.id
