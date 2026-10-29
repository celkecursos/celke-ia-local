import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)


def _as_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        return datetime.now(UTC)
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def import_legacy_sqlite(path: Path, repository: DocumentRepository) -> int:
    """Leva os documentos do SQLite das versões anteriores para o PostgreSQL, uma vez só.

    Os vetores no ChromaDB usam o mesmo id, então os documentos continuam prontos para o chat.
    Depois da importação o arquivo é renomeado para `app.db.importado` (fica como cópia de segurança).
    """
    if not path.is_file():
        return 0
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in conn.execute("SELECT * FROM documents").fetchall()]
    except sqlite3.DatabaseError:
        logger.warning("%s não tem a tabela de documentos esperada; nada foi importado", path)
        return 0
    finally:
        conn.close()
    for row in rows:
        row["created_at"] = _as_datetime(row.get("created_at"))
        row["updated_at"] = _as_datetime(row.get("updated_at"))
    imported = repository.import_rows(rows)
    path.rename(path.with_name(path.name + ".importado"))
    logger.info("%d documento(s) importado(s) do SQLite para o PostgreSQL", imported)
    return imported
