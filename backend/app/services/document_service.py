import hashlib
import logging
import shutil
import tempfile
import uuid
from concurrent.futures import Executor
from pathlib import Path
from typing import BinaryIO

from app.core.config import Settings
from app.core.errors import AppError, ConflictError, FileTooLargeError, InvalidFileError, NotFoundError
from app.repositories.document_repository import DocumentRepository
from app.repositories.vector_store import ChunkRecord, VectorStore
from app.schemas.documents import Document, DocumentOut, DocumentStats, DocumentStatus
from app.services.chunker import split_pages
from app.services.ollama_service import LanguageModel
from app.services.pdf_extractor import extract_pdf, page_count

logger = logging.getLogger(__name__)

_COPY_BLOCK = 1024 * 1024


def safe_display_name(filename: str | None) -> str:
    """Só o nome, sem caminho: o arquivo é gravado com o id, nunca com o nome enviado."""
    name = Path((filename or "").replace("\\", "/")).name.strip()
    name = "".join(ch for ch in name if ch.isprintable())
    return name[:200] or "documento.pdf"


class DocumentService:
    def __init__(
        self,
        settings: Settings,
        repository: DocumentRepository,
        vector_store: VectorStore,
        model: LanguageModel,
        executor: Executor,
    ):
        self._settings = settings
        self._repo = repository
        self._vectors = vector_store
        self._model = model
        self._executor = executor
        settings.documents_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self, document_id: str) -> Path:
        # id = uuid4 hex: sem barras nem "..", não há como sair da pasta
        return self._settings.documents_dir / f"{document_id}.pdf"

    def _to_out(self, document: Document) -> DocumentOut:
        needs_reindex = (
            document.status == DocumentStatus.READY and document.embedding_model != self._settings.embedding_model
        )
        return DocumentOut(**document.model_dump(), needs_reindex=needs_reindex)

    def list_all(self) -> list[DocumentOut]:
        return [self._to_out(d) for d in self._repo.list_all()]

    def get(self, document_id: str) -> DocumentOut:
        document = self._repo.get(document_id)
        if document is None:
            raise NotFoundError("Documento não encontrado.")
        return self._to_out(document)

    def stats(self) -> DocumentStats:
        docs = self._repo.list_all()
        return DocumentStats(
            total=len(docs),
            ready=sum(d.status == DocumentStatus.READY for d in docs),
            processing=sum(d.status in (DocumentStatus.PENDING, DocumentStatus.PROCESSING) for d in docs),
            error=sum(d.status == DocumentStatus.ERROR for d in docs),
        )

    def available_for_chat(self) -> list[Document]:
        return [
            d
            for d in self._repo.list_all()
            if d.status == DocumentStatus.READY and d.embedding_model == self._settings.embedding_model
        ]

    def upload(self, filename: str | None, content_type: str | None, stream: BinaryIO) -> DocumentOut:
        name = safe_display_name(filename)
        if not name.lower().endswith(".pdf"):
            raise InvalidFileError("Envie um arquivo com a extensão .pdf.")
        if content_type and content_type not in ("application/pdf", "application/x-pdf", "application/octet-stream"):
            raise InvalidFileError("O arquivo enviado não é um PDF.")

        limit = self._settings.max_upload_bytes
        digest = hashlib.sha256()
        size = 0
        with tempfile.NamedTemporaryFile(dir=self._settings.documents_dir, suffix=".part", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            try:
                header = b""
                while block := stream.read(_COPY_BLOCK):
                    if not header:
                        header = block[:5]
                    size += len(block)
                    if size > limit:
                        raise FileTooLargeError(f"O arquivo passa do limite de {self._settings.max_upload_mb} MB.")
                    digest.update(block)
                    tmp.write(block)
                if size == 0:
                    raise InvalidFileError("O arquivo está vazio.")
                if header != b"%PDF-":
                    raise InvalidFileError("O conteúdo do arquivo não é de um PDF.")
            except Exception:
                tmp.close()
                tmp_path.unlink(missing_ok=True)
                raise

        try:
            sha256 = digest.hexdigest()
            existing = self._repo.get_by_sha256(sha256)
            if existing:
                raise ConflictError(f'Este PDF já foi enviado como "{existing.filename}".')
            pages = page_count(tmp_path)
            if pages == 0:
                raise InvalidFileError("O PDF não tem páginas.")
            document_id = uuid.uuid4().hex
            target = self._file_path(document_id)
            shutil.move(tmp_path, target)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise

        self._repo.create(document_id=document_id, filename=name, size_bytes=size, sha256=sha256)
        self._repo.update(document_id, page_count=pages)
        self._executor.submit(self.process, document_id)
        return self.get(document_id)

    def reprocess(self, document_id: str) -> DocumentOut:
        document = self.get(document_id)
        if document.status in (DocumentStatus.PENDING, DocumentStatus.PROCESSING):
            raise ConflictError("O documento já está sendo processado.")
        self._repo.update(document_id, status=DocumentStatus.PENDING, error_message=None)
        self._executor.submit(self.process, document_id)
        return self.get(document_id)

    def delete(self, document_id: str) -> None:
        document = self.get(document_id)
        if document.status == DocumentStatus.PROCESSING:
            raise ConflictError("Aguarde o fim do processamento para excluir o documento.")
        # Primeiro os vetores: se o ChromaDB falhar, o documento continua listado e a exclusão pode ser repetida.
        self._vectors.delete_document(document_id)
        self._file_path(document_id).unlink(missing_ok=True)
        self._repo.delete(document_id)

    def process(self, document_id: str) -> None:
        """Extrai, divide, gera os embeddings e grava no banco vetorial. Roda fora da requisição."""
        document = self._repo.get(document_id)
        if document is None:  # excluído enquanto aguardava na fila
            return
        self._repo.update(document_id, status=DocumentStatus.PROCESSING, error_message=None)
        try:
            extracted = extract_pdf(self._file_path(document_id))
            if not extracted.has_text:
                raise InvalidFileError(
                    "O PDF não tem texto selecionável (pode ser digitalizado como imagem). Esta versão não faz OCR."
                )
            chunks = split_pages(extracted.pages, self._settings.chunk_size, self._settings.chunk_overlap)
            self._vectors.delete_document(document_id)
            batch_size = self._settings.embedding_batch_size
            prefix = self._settings.embedding_document_prefix
            for start in range(0, len(chunks), batch_size):
                batch = chunks[start : start + batch_size]
                embeddings = self._model.embed([prefix + c.text for c in batch])
                self._vectors.add(
                    [
                        ChunkRecord(
                            id=f"{document_id}:{c.index}",
                            document_id=document_id,
                            filename=document.filename,
                            page=c.page,
                            text=c.text,
                            embedding=e,
                        )
                        for c, e in zip(batch, embeddings, strict=True)
                    ]
                )
            self._repo.update(
                document_id,
                status=DocumentStatus.READY,
                page_count=extracted.page_count,
                chunk_count=len(chunks),
                embedding_model=self._settings.embedding_model,
                error_message=None,
            )
            logger.info("Documento %s indexado: %d trechos", document_id, len(chunks))
        except AppError as exc:
            logger.warning("Falha ao processar %s: %s", document_id, exc.message)
            self._repo.update(document_id, status=DocumentStatus.ERROR, error_message=exc.message)
        except Exception:
            logger.exception("Erro inesperado ao processar %s", document_id)
            self._repo.update(
                document_id,
                status=DocumentStatus.ERROR,
                error_message="Erro inesperado ao processar o documento. Veja os logs do backend.",
            )
