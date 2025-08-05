"""
Auto-label incoming/outgoing messages as OK/WARN/ERR.
"""
from __future__ import annotations
import re
from hippoium.ports.types import Message
from hippoium.ports.port_types import MsgLabel


_ERR_PATTERNS = [
    re.compile(r"^\s*Error:", re.I),
    re.compile(r"exception", re.I),
]


def label(msg: Message) -> MsgLabel:
    for pat in _ERR_PATTERNS:
        if pat.search(msg.content):
            return MsgLabel.ERR
    if "todo" in msg.content.lower():
        return MsgLabel.TODO
    return MsgLabel.OK
