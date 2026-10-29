from typing import Annotated

from fastapi import APIRouter, Depends, File, Response, UploadFile, status

from app.api.deps import get_container
from app.core.container import Container
from app.schemas.documents import DocumentList, DocumentOut, DocumentStats

router = APIRouter(prefix="/documents", tags=["Documentos"])

ContainerDep = Annotated[Container, Depends(get_container)]


@router.get("", response_model=DocumentList, summary="Lista os documentos")
def list_documents(c: ContainerDep) -> DocumentList:
    return DocumentList(items=c.documents.list_all())


@router.get("/stats", response_model=DocumentStats, summary="Contagem de documentos por situação")
def document_stats(c: ContainerDep) -> DocumentStats:
    return c.documents.stats()


@router.post(
    "",
    response_model=DocumentOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Envia um PDF",
    description="Grava o arquivo e agenda o processamento. Acompanhe pelo campo `status`.",
)
def upload_document(c: ContainerDep, file: Annotated[UploadFile, File(description="Arquivo PDF")]) -> DocumentOut:
    return c.documents.upload(file.filename, file.content_type, file.file)


@router.get("/{document_id}", response_model=DocumentOut, summary="Consulta um documento e o status do processamento")
def get_document(document_id: str, c: ContainerDep) -> DocumentOut:
    return c.documents.get(document_id)


@router.post(
    "/{document_id}/reprocess",
    response_model=DocumentOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Processa o documento de novo",
)
def reprocess_document(document_id: str, c: ContainerDep) -> DocumentOut:
    return c.documents.reprocess(document_id)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui o documento, o arquivo e os trechos indexados",
)
def delete_document(document_id: str, c: ContainerDep) -> Response:
    c.documents.delete(document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
