import hashlib
from typing import Iterable


def hash_text(text: str) -> str:
    """Return SHA-1 hash of given text."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def rolling_hash(tokens: Iterable[str]) -> str:
    """Very light rolling hash (for sliding window dedupe)."""
    # TODO: optimised rolling hash; placeholder concat-hash for now
    return hash_text("".join(tokens))
