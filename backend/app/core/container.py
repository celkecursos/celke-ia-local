from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from app.core.config import Settings
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.database import Database
from app.repositories.document_repository import DocumentRepository
from app.repositories.vector_store import ChromaVectorStore, VectorStore
from app.services.conversation_service import ConversationService
from app.services.document_service import DocumentService
from app.services.ollama_service import OllamaService
from app.services.rag_service import RagService


@dataclass
class Container:
    """Objetos compartilhados pela aplicação (criados uma vez, na inicialização)."""

    settings: Settings
    database: Database
    repository: DocumentRepository
    vector_store: VectorStore
    ollama: OllamaService
    documents: DocumentService
    conversations: ConversationService
    rag: RagService
    executor: ThreadPoolExecutor


def build_container(settings: Settings) -> Container:
    database = Database(settings.database_conninfo)
    repository = DocumentRepository(database)
    conversation_repository = ConversationRepository(database)
    vector_store = ChromaVectorStore(settings.chroma_host, settings.chroma_port, settings.embedding_model)
    ollama = OllamaService(
        host=settings.ollama_url,
        timeout=settings.ollama_timeout_seconds,
        chat_model=settings.chat_model,
        embedding_model=settings.embedding_model,
        num_ctx=settings.chat_num_ctx,
        temperature=settings.chat_temperature,
        think=settings.chat_think,
    )
    # Um documento por vez: o Ollama processa os embeddings de forma sequencial de qualquer jeito.
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="indexer")
    documents = DocumentService(settings, repository, vector_store, ollama, executor)
    conversations = ConversationService(conversation_repository)
    rag = RagService(settings, repository, conversation_repository, vector_store, ollama)
    return Container(settings, database, repository, vector_store, ollama, documents, conversations, rag, executor)
