from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.container import Container
from app.main import create_app
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.database import Database
from app.repositories.document_repository import DocumentRepository
from app.services.conversation_service import ConversationService
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


@pytest.fixture(scope="session")
def database():
    """PostgreSQL de teste (serviço postgres-test do compose, em memória). Uma conexão para a sessão toda."""
    db = Database(Settings().database_conninfo)
    db.create_schema()
    yield db
    db.close()


@pytest.fixture(autouse=True)
def clean_database(database):
    with database.connection() as conn:
        conn.execute("TRUNCATE documents, conversations, messages")


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
def container(settings, database, model, vectors) -> Container:
    repository = DocumentRepository(database)
    conversations = ConversationRepository(database)
    executor = ImmediateExecutor()
    return Container(
        settings=settings,
        database=database,
        repository=repository,
        vector_store=vectors,
        ollama=FakeOllamaStatus(),  # type: ignore[arg-type]
        documents=DocumentService(settings, repository, vectors, model, executor),
        conversations=ConversationService(conversations),
        rag=RagService(settings, repository, conversations, vectors, model),
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
