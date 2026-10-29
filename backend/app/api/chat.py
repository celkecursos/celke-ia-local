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
        "Resposta em Server-Sent Events. Eventos: `sources` (lista de trechos recuperados), "
        "`thinking` (o modelo está raciocinando; enviado uma vez), `token` (`{text}`, pedaço da resposta), `done` (fim) e `error` (`{codigo, mensagem}`)."
    ),
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
def chat(request: ChatRequest, c: ContainerDep) -> StreamingResponse:
    c.rag.validate(request)
    return StreamingResponse(
        c.rag.stream_answer(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
