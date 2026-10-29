import sqlite3

from app.core.errors import ModelNotInstalledError
from app.repositories.legacy_sqlite import import_legacy_sqlite
from app.schemas.chat import ChatRequest
from app.services.rag_service import INTERRUPTED_ANSWER
from tests.fakes import make_pdf
from tests.unit.test_chat import ask, parse_sse, upload


def start_conversation(client, document_id, question="Qual é a porta do ChromaDB?"):
    events = parse_sse(ask(client, question, [document_id]).text)
    return events[0][1]["id"], events


def test_chat_creates_conversation_and_saves_messages(client, sample_pdf):
    document_id = upload(client, sample_pdf)

    conversation_id, events = start_conversation(client, document_id)

    assert events[0] == ("conversation", {"id": conversation_id, "title": "Qual é a porta do ChromaDB?"})
    body = client.get(f"/api/conversations/{conversation_id}").json()
    assert body["document_ids"] == [document_id]
    question, answer = body["messages"]
    assert (question["role"], question["content"], question["state"]) == (
        "user",
        "Qual é a porta do ChromaDB?",
        "concluida",
    )
    assert answer["role"] == "assistant"
    assert answer["state"] == "concluida"
    assert answer["content"] == "".join(d["text"] for name, d in events if name == "token")
    assert answer["sources"] == events[1][1]
    assert [c["id"] for c in client.get("/api/conversations").json()["items"]] == [conversation_id]


def test_long_question_becomes_short_title(client, sample_pdf):
    document_id = upload(client, sample_pdf)

    _, events = start_conversation(client, document_id, "Qual   é a porta " + "muito " * 30)

    title = events[0][1]["title"]
    assert len(title) == 80
    assert title.startswith("Qual é a porta muito")
    assert title.endswith("…")


def test_next_question_stays_in_the_same_conversation(client, sample_pdf, tmp_path):
    first = upload(client, sample_pdf)
    second = upload(client, make_pdf(tmp_path / "outro.pdf", ["Outro documento sobre Docker."]))
    conversation_id, _ = start_conversation(client, first)

    events = parse_sse(ask(client, "E o Docker?", [first, second], conversation_id=conversation_id).text)

    assert events[0][1]["id"] == conversation_id
    body = client.get(f"/api/conversations/{conversation_id}").json()
    assert [m["role"] for m in body["messages"]] == ["user", "assistant", "user", "assistant"]
    assert body["document_ids"] == [first, second]
    assert len(client.get("/api/conversations").json()["items"]) == 1


def test_error_is_saved_and_retry_replaces_it(client, sample_pdf, model):
    document_id = upload(client, sample_pdf)
    model.chat_error = ModelNotInstalledError("O modelo qwen3:4b não está instalado no Ollama.")
    conversation_id, events = start_conversation(client, document_id)
    assert events[-1][0] == "error"
    failed = client.get(f"/api/conversations/{conversation_id}").json()["messages"][-1]
    assert failed["state"] == "erro"
    assert failed["error_message"] == "O modelo qwen3:4b não está instalado no Ollama."

    model.chat_error = None
    events = parse_sse(
        ask(client, "Qual é a porta do ChromaDB?", [document_id], conversation_id=conversation_id, retry=True).text
    )

    assert events[-1] == ("done", {})
    messages = client.get(f"/api/conversations/{conversation_id}").json()["messages"]
    assert [(m["role"], m["state"]) for m in messages] == [("user", "concluida"), ("assistant", "concluida")]
    # a pergunta não entra duas vezes no histórico enviado ao modelo
    assert [m["role"] for m in model.chat_calls[-1]] == ["system", "user"]


def test_retry_only_after_an_error(client, sample_pdf):
    document_id = upload(client, sample_pdf)
    conversation_id, _ = start_conversation(client, document_id)

    response = ask(client, "Outra?", [document_id], conversation_id=conversation_id, retry=True)

    assert response.status_code == 409
    assert len(client.get(f"/api/conversations/{conversation_id}").json()["messages"]) == 2


def test_retry_needs_a_conversation(client, sample_pdf):
    document_id = upload(client, sample_pdf)

    assert ask(client, "Pergunta?", [document_id], retry=True).status_code == 422
    assert client.get("/api/conversations").json()["items"] == []


def test_unknown_conversation(client, sample_pdf):
    document_id = upload(client, sample_pdf)

    response = ask(client, "Pergunta?", [document_id], conversation_id="nao-existe")

    assert response.status_code == 404
    assert response.json()["erro"]["mensagem"] == "Conversa não encontrada."
    assert client.get("/api/conversations/nao-existe").status_code == 404
    assert client.delete("/api/conversations/nao-existe").status_code == 404


def test_rejected_question_is_not_saved(client, tmp_path):
    document_id = upload(client, make_pdf(tmp_path / "vazio.pdf", [""]))

    assert ask(client, "Pergunta?", [document_id]).status_code == 422
    assert client.get("/api/conversations").json()["items"] == []


def test_delete_conversation_keeps_documents(client, sample_pdf):
    document_id = upload(client, sample_pdf)
    conversation_id, _ = start_conversation(client, document_id)

    assert client.delete(f"/api/conversations/{conversation_id}").status_code == 204

    assert client.get(f"/api/conversations/{conversation_id}").status_code == 404
    assert client.get("/api/conversations").json()["items"] == []
    assert client.get(f"/api/documents/{document_id}").json()["status"] == "pronto"


def test_conversation_survives_document_deletion(client, sample_pdf):
    document_id = upload(client, sample_pdf)
    conversation_id, _ = start_conversation(client, document_id)

    client.delete(f"/api/documents/{document_id}")

    body = client.get(f"/api/conversations/{conversation_id}").json()
    assert body["messages"][-1]["sources"][0]["filename"] == "manual.pdf"


def test_stopped_answer_keeps_what_arrived(client, sample_pdf, container):
    document_id = upload(client, sample_pdf)
    turn = container.rag.start(ChatRequest(question="Qual modelo é usado?", document_ids=[document_id]))
    stream = container.rag.stream_answer(turn)
    while '"text"' not in next(stream):  # até o primeiro pedaço da resposta
        pass

    stream.close()  # o navegador fechou a conexão

    answer = container.conversations.get(turn.conversation.id).messages[-1]
    assert (answer.role, answer.state, answer.content) == ("assistant", "concluida", "Resposta")


def test_stopped_before_any_text(client, sample_pdf, container):
    document_id = upload(client, sample_pdf)
    turn = container.rag.start(ChatRequest(question="Qual modelo é usado?", document_ids=[document_id]))
    stream = container.rag.stream_answer(turn)
    next(stream)

    stream.close()

    assert container.conversations.get(turn.conversation.id).messages[-1].content == INTERRUPTED_ANSWER


def test_imports_documents_from_old_sqlite_once(settings, container):
    path = settings.legacy_sqlite_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE documents (id TEXT PRIMARY KEY, filename TEXT, size_bytes INTEGER, sha256 TEXT,"
            " page_count INTEGER, chunk_count INTEGER, status TEXT, error_message TEXT, embedding_model TEXT,"
            " created_at TEXT, updated_at TEXT)"
        )
        conn.execute(
            "INSERT INTO documents VALUES ('abc', 'antigo.pdf', 10, 'hash', 3, 7, 'pronto', NULL,"
            " 'nomic-embed-text', '2026-01-02T03:04:05+00:00', '2026-01-02T03:04:05+00:00')"
        )
    conn.close()

    assert import_legacy_sqlite(path, container.repository) == 1

    document = container.repository.get("abc")
    assert (document.filename, document.status, document.chunk_count) == ("antigo.pdf", "pronto", 7)
    assert document.created_at.year == 2026
    assert not path.exists()
    assert path.with_name("app.db.importado").exists()
    assert import_legacy_sqlite(path, container.repository) == 0
