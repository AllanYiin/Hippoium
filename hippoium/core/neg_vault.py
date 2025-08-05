# hippoium/core/neg_vault.py  (New module for Negative Prompt Vault)
from typing import List

class NegativeVault:
    """Global repository for negative prompt examples."""
    _vault: List[str] = []

    @classmethod
    def add_example(cls, prompt: str) -> None:
        """Add a negative prompt example to the vault (if not duplicate)."""
        if prompt not in cls._vault:
            cls._vault.append(prompt)

    @classmethod
    def remove_example(cls, prompt: str) -> None:
        """Remove a prompt from the vault if it exists."""
        try:
            cls._vault.remove(prompt)
        except ValueError:
            pass  # ignore if not present

    @classmethod
    def list_examples(cls) -> List[str]:
        """List all negative prompt examples in the vault."""
        return list(cls._vault)