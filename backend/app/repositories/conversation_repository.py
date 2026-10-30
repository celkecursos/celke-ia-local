import uuid

from psycopg.types.json import Jsonb

from app.repositories.database import Database
from app.schemas.chat import Source
from app.schemas.conversations import AnswerKind, Conversation, Message, MessageRole, MessageState

_MESSAGE_COLUMNS = "id, role, content, state, error_message, sources, answer_kind, created_at"


class ConversationRepository:
    """Conversas e mensagens do chat no PostgreSQL."""

    def __init__(self, database: Database):
        self._db = database

    def create(self, *, title: str, document_ids: list[str]) -> Conversation:
        with self._db.connection() as conn:
            row = conn.execute(
                "INSERT INTO conversations (id, title, document_ids) VALUES (%s, %s, %s) RETURNING *",
                (uuid.uuid4().hex, title, document_ids),
            ).fetchone()
        return Conversation(**row)

    def get(self, conversation_id: str) -> Conversation | None:
        with self._db.connection() as conn:
            row = conn.execute("SELECT * FROM conversations WHERE id = %s", (conversation_id,)).fetchone()
        return Conversation(**row) if row else None

    def list_all(self) -> list[Conversation]:
        with self._db.connection() as conn:
            rows = conn.execute("SELECT * FROM conversations ORDER BY updated_at DESC").fetchall()
        return [Conversation(**r) for r in rows]

    def update_documents(self, conversation_id: str, document_ids: list[str]) -> None:
        """Guarda os documentos da última pergunta e leva a conversa para o topo da lista."""
        with self._db.connection() as conn:
            conn.execute(
                "UPDATE conversations SET document_ids = %s, updated_at = now() WHERE id = %s",
                (document_ids, conversation_id),
            )

    def delete(self, conversation_id: str) -> bool:
        with self._db.connection() as conn:
            return conn.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,)).rowcount > 0

    def messages(self, conversation_id: str) -> list[Message]:
        with self._db.connection() as conn:
            rows = conn.execute(
                f"SELECT {_MESSAGE_COLUMNS} FROM messages WHERE conversation_id = %s ORDER BY seq",
                (conversation_id,),
            ).fetchall()
        return [Message(**r) for r in rows]

    def add_message(
        self,
        conversation_id: str,
        *,
        role: MessageRole,
        content: str,
        state: MessageState = "concluida",
        error_message: str | None = None,
        sources: list[Source] | None = None,
        answer_kind: AnswerKind = "documents",
    ) -> Message:
        with self._db.connection() as conn:
            row = conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, state, error_message, sources, answer_kind)"
                f" VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING {_MESSAGE_COLUMNS}",
                (
                    uuid.uuid4().hex,
                    conversation_id,
                    role,
                    content,
                    state,
                    error_message,
                    Jsonb([s.model_dump() for s in sources or []]),
                    answer_kind,
                ),
            ).fetchone()
            conn.execute("UPDATE conversations SET updated_at = now() WHERE id = %s", (conversation_id,))
        return Message(**row)

    def delete_message(self, message_id: str) -> None:
        with self._db.connection() as conn:
            conn.execute("DELETE FROM messages WHERE id = %s", (message_id,))
