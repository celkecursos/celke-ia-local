import logging
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

from app.core.errors import DatabaseUnavailableError

logger = logging.getLogger(__name__)

UNAVAILABLE_MESSAGE = "O banco de dados (PostgreSQL) não está respondendo. Verifique: docker compose logs postgres"

# Idempotente: roda a cada inicialização do backend.
SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    size_bytes BIGINT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    page_count INTEGER,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    error_message TEXT,
    embedding_model TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    -- sem chave estrangeira: a conversa continua legível depois que um documento é excluído
    document_ids TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS conversations_updated_at_idx ON conversations (updated_at DESC);

CREATE TABLE IF NOT EXISTS messages (
    -- ordem das mensagens na conversa
    seq BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id TEXT NOT NULL UNIQUE,
    conversation_id TEXT NOT NULL REFERENCES conversations (id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('concluida', 'erro')),
    error_message TEXT,
    sources JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS messages_conversation_idx ON messages (conversation_id, seq);
"""


class Database:
    """Pool de conexões com o PostgreSQL, compartilhado pelos repositórios."""

    def __init__(self, conninfo: str, *, max_size: int = 10, connect_timeout: float = 30):
        # Abre já esperando a primeira conexão: sem banco, o backend nem sobe.
        self._pool = ConnectionPool(
            conninfo,
            min_size=1,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
            timeout=connect_timeout,
            open=False,
            name="celke-ia-local",
        )
        try:
            self._pool.open(wait=True, timeout=connect_timeout)
        except PoolTimeout as exc:
            self._pool.close()
            raise DatabaseUnavailableError(UNAVAILABLE_MESSAGE) from exc

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        """Uma transação: commit no fim do bloco, rollback se der erro."""
        try:
            with self._pool.connection() as conn:
                yield conn
        except (PoolTimeout, psycopg.OperationalError) as exc:
            logger.warning("Falha de conexão com o PostgreSQL: %s", exc)
            raise DatabaseUnavailableError(UNAVAILABLE_MESSAGE) from exc

    def create_schema(self) -> None:
        with self.connection() as conn:
            conn.execute(SCHEMA)

    def ping(self) -> None:
        with self.connection() as conn:
            conn.execute("SELECT 1")

    def close(self) -> None:
        self._pool.close()
