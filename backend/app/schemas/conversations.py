from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.chat import Source

MessageRole = Literal["user", "assistant"]
MessageState = Literal["concluida", "erro"]


class Message(BaseModel):
    id: str
    role: MessageRole
    content: str
    state: MessageState
    error_message: str | None = None
    sources: list[Source] = []
    created_at: datetime


class Conversation(BaseModel):
    id: str
    title: str
    document_ids: list[str]
    created_at: datetime
    updated_at: datetime


class ConversationDetail(Conversation):
    messages: list[Message]


class ConversationList(BaseModel):
    items: list[Conversation]
