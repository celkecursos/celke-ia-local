from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DocumentStatus(StrEnum):
    PENDING = "pendente"
    PROCESSING = "processando"
    READY = "pronto"
    ERROR = "erro"


class Document(BaseModel):
    id: str
    filename: str
    size_bytes: int
    sha256: str
    page_count: int | None = None
    chunk_count: int = 0
    status: DocumentStatus
    error_message: str | None = None
    embedding_model: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentOut(Document):
    needs_reindex: bool = Field(
        default=False,
        description="O documento foi indexado com outro modelo de embeddings e precisa ser reprocessado.",
    )


class DocumentList(BaseModel):
    items: list[DocumentOut]


class DocumentStats(BaseModel):
    total: int
    ready: int
    processing: int
    error: int
