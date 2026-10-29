from functools import lru_cache
from pathlib import Path
from typing import Literal

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

    data_dir: Path = Path("/data")
    max_upload_mb: int = 25
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_top_k: int = 5
    history_max_messages: int = 6

    # Vazio = sem CORS (o navegador acessa a API pelo proxy do frontend, na mesma origem).
    cors_origins: str = ""

    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"

    @property
    def database_path(self) -> Path:
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
