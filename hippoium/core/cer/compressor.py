"""
Context Trimmer – dedupe & diff-patch compression for conversation context.
"""
from __future__ import annotations

import difflib
from typing import List
from hippoium.ports.types import DedupStrategy, TrimPolicy
from hippoium.core.utils.hasher import hash_text
from hippoium.core.utils.token_counter import count_tokens


class Compressor:
    def __init__(
        self,
        dedup_strategy: DedupStrategy = DedupStrategy.HASH,
        trim_policy: TrimPolicy = TrimPolicy.DIFF_PATCH,
    ):
        self.dedup_strategy = dedup_strategy
        self.trim_policy = trim_policy

    # ---------- public API ---------- #
    def compress(self, chunks: List[str]) -> List[str]:
        if self.dedup_strategy == DedupStrategy.HASH:
            chunks = self._hash_dedupe(chunks)
        # Future: MINHASH support

        if self.trim_policy == TrimPolicy.DIFF_PATCH:
            return self._diff_patch(chunks)
        elif self.trim_policy == TrimPolicy.KEEP_HEAD:
            return self._keep_head(chunks)
        return self._keep_tail(chunks)

    # ---------- internal helpers ---------- #
    def _hash_dedupe(self, chunks: List[str]) -> List[str]:
        seen: set[str] = set()
        deduped: List[str] = []
        for c in chunks:
            h = hash_text(c)
            if h not in seen:
                deduped.append(c)
                seen.add(h)
        return deduped

    def _diff_patch(self, chunks: List[str]) -> List[str]:
        if not chunks:
            return []
        base = chunks[0]
        patches = [base]
        for c in chunks[1:]:
            diff = difflib.unified_diff(base.splitlines(), c.splitlines(), lineterm="")
            patches.append("\n".join(diff))
            base = c
        return patches

    def _keep_head(self, chunks: List[str], budget: int | None = None) -> List[str]:
        if budget is None:
            return chunks
        acc, out = 0, []
        for c in chunks:
            acc += count_tokens(c)
            if acc > budget:
                break
            out.append(c)
        return out

    def _keep_tail(self, chunks: List[str], budget: int | None = None) -> List[str]:
        if budget is None:
            return chunks
        out, acc = [], 0
        for c in reversed(chunks):
            acc += count_tokens(c)
            if acc > budget:
                break
            out.insert(0, c)
        return out
