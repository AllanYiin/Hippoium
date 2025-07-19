"""
Generate binary/textual deltas for large artifacts.
"""
import difflib
from typing import Tuple


def generate_delta(old: str, new: str) -> str:
    diff = difflib.unified_diff(
        old.splitlines(), new.splitlines(), lineterm=""
    )
    return "\n".join(diff)


def apply_delta(old: str, delta: str) -> str:
    patched = difflib.restore(delta.splitlines(), which=2)
    return "\n".join(patched)


def binary_diff(a: bytes, b: bytes) -> Tuple[bytes, bytes]:
    # TODO: use xdelta; placeholder returns originals
    return a, b
