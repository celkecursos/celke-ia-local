from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.container import Container
from app.main import create_app
from app.repositories.document_repository import DocumentRepository
from app.services.document_service import DocumentService
from app.services.rag_service import RagService
from tests.fakes import FakeModel, ImmediateExecutor, InMemoryVectorStore, make_pdf


class FakeOllamaStatus:
    """Só o que as rotas de estado usam do OllamaService."""

    def __init__(self, installed: list[str] | None = None, error=None):
        self.installed = installed if installed is not None else ["qwen3:4b", "nomic-embed-text:latest"]
        self.error = error

    def installed_models(self):
        if self.error:
            raise self.error
        return [(name, 1000) for name in self.installed]

    def is_installed(self, model, installed=None):
        names = installed if installed is not None else self.installed
        return any(n == model or n == f"{model}:latest" for n in names)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", chunk_size=200, chunk_overlap=40, retrieval_top_k=3, max_upload_mb=1)


@pytest.fixture
def model() -> FakeModel:
    return FakeModel()


@pytest.fixture
def vectors() -> InMemoryVectorStore:
    return InMemoryVectorStore()


@pytest.fixture
def container(settings, model, vectors) -> Container:
    repository = DocumentRepository(settings.database_path)
    executor = ImmediateExecutor()
    return Container(
        settings=settings,
        repository=repository,
        vector_store=vectors,
        ollama=FakeOllamaStatus(),  # type: ignore[arg-type]
        documents=DocumentService(settings, repository, vectors, model, executor),
        rag=RagService(settings, repository, vectors, model),
        executor=executor,  # type: ignore[arg-type]
    )


@pytest.fixture
def client(settings, container):
    with TestClient(create_app(settings, container)) as test_client:
        yield test_client


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    return make_pdf(
        tmp_path / "manual.pdf",
        [
            "O Celke IA Local usa o Ollama para gerar respostas. O modelo padrão é o qwen3.",
            "O ChromaDB guarda os vetores dos trechos. A porta interna do ChromaDB é 8000.",
        ],
    )
