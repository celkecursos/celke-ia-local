from psycopg import sql

from app.repositories.database import Database
from app.schemas.documents import Document, DocumentStatus

_COLUMNS = (
    "id",
    "filename",
    "size_bytes",
    "sha256",
    "page_count",
    "chunk_count",
    "status",
    "error_message",
    "embedding_model",
    "created_at",
    "updated_at",
)


class DocumentRepository:
    """Metadados dos documentos no PostgreSQL (o ChromaDB guarda só os trechos e vetores)."""

    def __init__(self, database: Database):
        self._db = database

    def create(self, *, document_id: str, filename: str, size_bytes: int, sha256: str) -> Document:
        with self._db.connection() as conn:
            row = conn.execute(
                "INSERT INTO documents (id, filename, size_bytes, sha256, status)"
                " VALUES (%s, %s, %s, %s, %s) RETURNING *",
                (document_id, filename, size_bytes, sha256, DocumentStatus.PENDING),
            ).fetchone()
        return Document(**row)

    def get(self, document_id: str) -> Document | None:
        with self._db.connection() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = %s", (document_id,)).fetchone()
        return Document(**row) if row else None

    def get_by_sha256(self, sha256: str) -> Document | None:
        with self._db.connection() as conn:
            row = conn.execute("SELECT * FROM documents WHERE sha256 = %s", (sha256,)).fetchone()
        return Document(**row) if row else None

    def list_all(self) -> list[Document]:
        with self._db.connection() as conn:
            rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
        return [Document(**r) for r in rows]

    def list_by_ids(self, ids: list[str]) -> list[Document]:
        if not ids:
            return []
        with self._db.connection() as conn:
            rows = conn.execute("SELECT * FROM documents WHERE id = ANY(%s)", (ids,)).fetchall()
        return [Document(**r) for r in rows]

    def update(self, document_id: str, **fields: object) -> None:
        unknown = set(fields) - set(_COLUMNS)
        if unknown:
            raise ValueError(f"Colunas desconhecidas: {', '.join(sorted(unknown))}")
        assignments = [sql.SQL("{} = %s").format(sql.Identifier(name)) for name in fields]
        assignments.append(sql.SQL("updated_at = now()"))
        query = sql.SQL("UPDATE documents SET {} WHERE id = %s").format(sql.SQL(", ").join(assignments))
        with self._db.connection() as conn:
            conn.execute(query, (*fields.values(), document_id))

    def delete(self, document_id: str) -> None:
        with self._db.connection() as conn:
            conn.execute("DELETE FROM documents WHERE id = %s", (document_id,))

    def import_rows(self, rows: list[dict[str, object]]) -> int:
        """Grava documentos vindos de outro banco, mantendo id e datas. Os que já existem ficam como estão."""
        query = sql.SQL("INSERT INTO documents ({}) VALUES ({}) ON CONFLICT DO NOTHING").format(
            sql.SQL(", ").join(map(sql.Identifier, _COLUMNS)),
            sql.SQL(", ").join(sql.Placeholder() * len(_COLUMNS)),
        )
        imported = 0
        with self._db.connection() as conn:
            for row in rows:
                imported += conn.execute(query, [row.get(c) for c in _COLUMNS]).rowcount
        return imported

    def mark_interrupted(self) -> int:
        """Documentos que estavam na fila ou processando quando o backend parou viram erro."""
        with self._db.connection() as conn:
            cur = conn.execute(
                "UPDATE documents SET status = %s, error_message = %s, updated_at = now() WHERE status IN (%s, %s)",
                (
                    DocumentStatus.ERROR,
                    "O processamento foi interrompido porque o serviço reiniciou. Clique em reprocessar.",
                    DocumentStatus.PENDING,
                    DocumentStatus.PROCESSING,
                ),
            )
            return cur.rowcount
