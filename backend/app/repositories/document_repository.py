import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.schemas.documents import Document, DocumentStatus

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    page_count INTEGER,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    error_message TEXT,
    embedding_model TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


class DocumentRepository:
    """Metadados dos documentos em SQLite (o ChromaDB guarda só os trechos e vetores)."""

    def __init__(self, database_path: Path):
        self._path = database_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        # Uma conexão por operação: o processamento roda em outra thread.
        conn = sqlite3.connect(self._path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _to_document(row: sqlite3.Row) -> Document:
        return Document(**dict(row))

    def create(self, *, document_id: str, filename: str, size_bytes: int, sha256: str) -> Document:
        now = _now()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO documents (id, filename, size_bytes, sha256, status, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (document_id, filename, size_bytes, sha256, DocumentStatus.PENDING, now, now),
            )
        document = self.get(document_id)
        assert document is not None
        return document

    def get(self, document_id: str) -> Document | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        return self._to_document(row) if row else None

    def get_by_sha256(self, sha256: str) -> Document | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE sha256 = ?", (sha256,)).fetchone()
        return self._to_document(row) if row else None

    def list_all(self) -> list[Document]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
        return [self._to_document(r) for r in rows]

    def list_by_ids(self, ids: list[str]) -> list[Document]:
        if not ids:
            return []
        marks = ",".join("?" for _ in ids)
        with self._connect() as conn:
            rows = conn.execute(f"SELECT * FROM documents WHERE id IN ({marks})", ids).fetchall()
        return [self._to_document(r) for r in rows]

    def update(self, document_id: str, **fields: object) -> None:
        fields["updated_at"] = _now()
        columns = ", ".join(f"{name} = ?" for name in fields)
        with self._connect() as conn:
            conn.execute(f"UPDATE documents SET {columns} WHERE id = ?", (*fields.values(), document_id))

    def delete(self, document_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))

    def mark_interrupted(self) -> int:
        """Documentos que estavam na fila ou processando quando o backend parou viram erro."""
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE documents SET status = ?, error_message = ?, updated_at = ? WHERE status IN (?, ?)",
                (
                    DocumentStatus.ERROR,
                    "O processamento foi interrompido porque o serviço reiniciou. Clique em reprocessar.",
                    _now(),
                    DocumentStatus.PENDING,
                    DocumentStatus.PROCESSING,
                ),
            )
            return cur.rowcount
