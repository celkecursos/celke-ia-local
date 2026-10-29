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
