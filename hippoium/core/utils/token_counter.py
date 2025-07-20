import re
from typing import Sequence
from hippoium.ports.port_types import TokenCount

_TOKENIZER_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def count_tokens(text: str | Sequence[str]) -> TokenCount:
    """Rough heuristic token counter (word + punctuation)."""
    if isinstance(text, str):
        return len(_TOKENIZER_RE.findall(text))
    return sum(count_tokens(t) for t in text)  # type: ignore[recursion]
