from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Any
from .port_types import MsgLabel, ArtifactType


class Message(BaseModel):
    id: str
    role: str  # user / assistant / system
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    label: MsgLabel | None = None


class Artifact(BaseModel):
    id: str
    type: ArtifactType
    data: Any
    checksum: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RetrievalRequest(BaseModel):
    query: str
    top_k: int = 5
