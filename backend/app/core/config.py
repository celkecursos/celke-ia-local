from functools import lru_cache
from pathlib import Path
from typing import Literal

from psycopg.conninfo import make_conninfo
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração lida das variáveis de ambiente (ver `.env.example`)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_url: str = "http://ollama:11434"
    ollama_timeout_seconds: float = 300.0
    chat_model: str = "qwen3:4b"
    embedding_model: str = "nomic-embed-text"
    # Janela de contexto do modelo de chat. O padrão do Ollama corta o contexto do RAG sem avisar.
    chat_num_ctx: int = 8192
    chat_temperature: float = 0.2
    # auto = usa o raciocínio separado se o modelo tiver a capacidade "thinking"; true/false força.
    chat_think: Literal["auto", "true", "false"] = "auto"
    # Prefixos recomendados pelo nomic-embed-text; deixe vazio para outros modelos.
    embedding_document_prefix: str = "search_document: "
    embedding_query_prefix: str = "search_query: "
    embedding_batch_size: int = 16

    chroma_host: str = "chroma"
    chroma_port: int = 8000

    # PostgreSQL: metadados dos documentos, conversas e mensagens.
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "celke_ia_local"
    postgres_user: str = "celke"
    postgres_password: str = ""

    data_dir: Path = Path("/data")
    max_upload_mb: int = 25
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_top_k: int = 5
    history_max_messages: int = 6

    # Busca na internet: só acontece quando a pessoa clica em "Pesquisar na internet".
    searxng_url: str = "http://searxng:8080"
    web_search_timeout_seconds: float = 15.0
    web_search_max_results: int = 3
    web_page_max_chars: int = 2000

    # Vazio = sem CORS (o navegador acessa a API pelo proxy do frontend, na mesma origem).
    cors_origins: str = ""

    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"

    @property
    def database_conninfo(self) -> str:
        return make_conninfo(
            host=self.postgres_host,
            port=self.postgres_port,
            dbname=self.postgres_db,
            user=self.postgres_user,
            password=self.postgres_password,
            application_name="celke-ia-local",
        )

    @property
    def legacy_sqlite_path(self) -> Path:
        """Banco SQLite das versões anteriores: importado uma vez para o PostgreSQL."""
        return self.data_dir / "app.db"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
