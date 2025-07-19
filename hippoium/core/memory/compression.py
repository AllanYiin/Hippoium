"""
Optional memory compression (gzip placeholder).
"""
import gzip
import pickle
from typing import Any


def compress(obj: Any) -> bytes:
    return gzip.compress(pickle.dumps(obj))


def decompress(blob: bytes) -> Any:
    return pickle.loads(gzip.decompress(blob))
