import json
import pickle
from typing import Any


def to_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def from_json(payload: str) -> Any:
    return json.loads(payload)


def to_pickle(data: Any) -> bytes:
    return pickle.dumps(data)


def from_pickle(blob: bytes) -> Any:
    return pickle.loads(blob)
