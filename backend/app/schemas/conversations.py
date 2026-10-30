from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.chat import Source

MessageRole = Literal["user", "assistant"]
MessageState = Literal["concluida", "erro"]
# documents = veio dos PDFs; not_found = os PDFs não tinham a resposta; web = veio da busca na internet
AnswerKind = Literal["documents", "not_found", "web"]


class Message(BaseModel):
    id: str
    role: MessageRole
    content: str
    state: MessageState
    error_message: str | None = None
    sources: list[Source] = []
    answer_kind: AnswerKind = "documents"
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
