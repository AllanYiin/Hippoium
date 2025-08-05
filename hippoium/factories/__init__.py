# hippoium/factories/__init__.py
"""
Factory namespace: re-export high-level helpers
"""

from .cer_factory import create_cer   # re-export

__all__ = ["create_cer"]