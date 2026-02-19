"""
Inject negative prompts / system guards into prompt template.
"""
from __future__ import annotations

from hippoium.ports.port_types import GuardAction


def inject_negatives(prompt: str, stop_phrases: list[str], action: GuardAction) -> str:
    if action == GuardAction.ALLOW:
        return prompt
    guard_block = "\n".join(f"[FORBIDDEN]: {p}" for p in stop_phrases)
    if action == GuardAction.SOFT_BLOCK:
        return guard_block + "\n\n" + prompt
    # HARD_BLOCK – override entire prompt
    return guard_block
