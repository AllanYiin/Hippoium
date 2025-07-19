"""
PromptBuilder – assemble trimmed chunks into final prompt.
"""
from __future__ import annotations
from typing import List
from hippoium.ports.types import TrimPolicy
from hippoium.core.cer.compressor import Compressor
from hippoium.core.utils.token_counter import count_tokens
from hippoium.ports.constants import MAX_TOKENS_PROMPT


class PromptBuilder:
    def __init__(self, policy: TrimPolicy = TrimPolicy.DIFF_PATCH):
        self.compressor = Compressor(trim_policy=policy)

    def build(self, chunks: List[str]) -> str:
        compressed = self.compressor.compress(chunks)
        prompt = "\n\n".join(compressed)
        # final guard
        if count_tokens(prompt) > MAX_TOKENS_PROMPT:
            prompt = prompt[-MAX_TOKENS_PROMPT:]  # naive cut
        return prompt
