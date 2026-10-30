from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_container
from app.core.container import Container
from app.schemas.chat import ChatDocument, ChatDocumentList, ChatRequest

router = APIRouter(prefix="/chat", tags=["Chat"])

ContainerDep = Annotated[Container, Depends(get_container)]


@router.get("/documents", response_model=ChatDocumentList, summary="Documentos prontos para o chat")
def chat_documents(c: ContainerDep) -> ChatDocumentList:
    return ChatDocumentList(
        items=[
            ChatDocument(id=d.id, filename=d.filename, page_count=d.page_count)
            for d in c.documents.available_for_chat()
        ]
    )


@router.post(
    "",
    summary="Pergunta sobre os documentos (streaming)",
    description=(
        "Resposta em Server-Sent Events. Eventos: `conversation` (`{id, title}`, a conversa em que a pergunta "
        "foi gravada), `searching` (busca na internet em andamento, com `web_search`), `sources` (lista de trechos "
        "recuperados), `thinking` (o modelo está raciocinando; enviado uma vez), `token` (`{text}`, pedaço da "
        "resposta), `not_found` (os documentos não tinham a resposta), `done` (fim) e `error` "
        "(`{codigo, mensagem}`). A pergunta e a resposta ficam gravadas na conversa."
    ),
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
def chat(request: ChatRequest, c: ContainerDep) -> StreamingResponse:
    turn = c.rag.start(request)
    return StreamingResponse(
        c.rag.stream_answer(turn),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
