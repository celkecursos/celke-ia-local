from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_ids: list[str] = Field(min_length=1, max_length=50)
    conversation_id: str | None = Field(
        default=None,
        max_length=64,
        description="Conversa em que a pergunta entra. Vazio = cria uma conversa nova (evento `conversation`).",
    )
    retry: bool = Field(
        default=False,
        description="Gera de novo a última resposta da conversa, que terminou em erro, sem repetir a pergunta.",
    )
    web_search: bool = Field(
        default=False,
        description="Responde com a busca na internet, e não com os documentos. Só a pergunta sai do computador.",
    )


class Source(BaseModel):
    """Trecho usado na resposta. Na web, `filename` é o título da página e não há documento nem número de página."""

    kind: Literal["document", "web"] = "document"
    document_id: str | None = None
    filename: str
    page: int | None = None
    url: str | None = None
    excerpt: str
    score: float | None = None


class ChatDocument(BaseModel):
    id: str
    filename: str
    page_count: int | None


class ChatDocumentList(BaseModel):
    items: list[ChatDocument]
