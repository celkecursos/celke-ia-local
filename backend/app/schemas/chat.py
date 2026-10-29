from typing import Literal

from pydantic import BaseModel, Field


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_ids: list[str] = Field(min_length=1, max_length=50)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=20)


class Source(BaseModel):
    document_id: str
    filename: str
    page: int
    excerpt: str
    score: float


class ChatDocument(BaseModel):
    id: str
    filename: str
    page_count: int | None


class ChatDocumentList(BaseModel):
    items: list[ChatDocument]
