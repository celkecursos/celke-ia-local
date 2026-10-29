from app.core.errors import OllamaUnavailableError, VectorStoreError
from tests.fakes import make_pdf


def upload(client, path, name=None, content_type="application/pdf"):
    with path.open("rb") as f:
        return client.post("/api/documents", files={"file": (name or path.name, f, content_type)})


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_upload_indexes_document(client, sample_pdf, vectors):
    response = upload(client, sample_pdf)

    assert response.status_code == 202
    document_id = response.json()["id"]
    document = client.get(f"/api/documents/{document_id}").json()
    assert document["status"] == "pronto"
    assert document["page_count"] == 2
    assert document["chunk_count"] > 0
    assert document["embedding_model"] == "nomic-embed-text"
    assert {c.page for c in vectors.chunks.values()} == {1, 2}


def test_upload_stores_file_with_internal_name(client, sample_pdf, settings):
    response = upload(client, sample_pdf, name="../../etc/passwd.pdf")

    body = response.json()
    assert body["filename"] == "passwd.pdf"
    assert [p.name for p in settings.documents_dir.iterdir()] == [f"{body['id']}.pdf"]


def test_upload_rejects_duplicate(client, sample_pdf):
    upload(client, sample_pdf)

    response = upload(client, sample_pdf, name="copia.pdf")

    assert response.status_code == 409
    assert response.json()["erro"]["codigo"] == "conflito"


def test_upload_rejects_non_pdf(client, tmp_path):
    fake = tmp_path / "planilha.pdf"
    fake.write_bytes(b"col1,col2\n1,2\n")

    response = upload(client, fake)

    assert response.status_code == 422
    assert "PDF" in response.json()["erro"]["mensagem"]


def test_upload_rejects_wrong_extension(client, sample_pdf):
    assert upload(client, sample_pdf, name="manual.txt").status_code == 422


def test_upload_rejects_large_file(client, tmp_path, settings):
    big = tmp_path / "grande.pdf"
    big.write_bytes(b"%PDF-" + b"0" * settings.max_upload_bytes)

    response = upload(client, big)

    assert response.status_code == 413
    assert list(settings.documents_dir.iterdir()) == []


def test_pdf_without_text_ends_with_error(client, tmp_path):
    response = upload(client, make_pdf(tmp_path / "escaneado.pdf", ["", ""]))

    document = client.get(f"/api/documents/{response.json()['id']}").json()
    assert document["status"] == "erro"
    assert "OCR" in document["error_message"]


def test_embedding_failure_marks_error_and_reprocess_recovers(client, sample_pdf, model):
    model.embed_error = OllamaUnavailableError("Ollama fora do ar")
    document_id = upload(client, sample_pdf).json()["id"]
    assert client.get(f"/api/documents/{document_id}").json()["error_message"] == "Ollama fora do ar"

    model.embed_error = None
    response = client.post(f"/api/documents/{document_id}/reprocess")

    assert response.status_code == 202
    assert client.get(f"/api/documents/{document_id}").json()["status"] == "pronto"


def test_delete_removes_only_that_document(client, sample_pdf, tmp_path, vectors, settings):
    keep = upload(client, make_pdf(tmp_path / "outro.pdf", ["Outro documento sobre Docker."])).json()["id"]
    remove = upload(client, sample_pdf).json()["id"]

    response = client.delete(f"/api/documents/{remove}")

    assert response.status_code == 204
    assert client.get(f"/api/documents/{remove}").status_code == 404
    assert {c.document_id for c in vectors.chunks.values()} == {keep}
    assert [p.name for p in settings.documents_dir.iterdir()] == [f"{keep}.pdf"]


def test_delete_keeps_document_when_vector_store_fails(client, sample_pdf, vectors):
    document_id = upload(client, sample_pdf).json()["id"]
    vectors.fail = VectorStoreError("ChromaDB indisponível")

    response = client.delete(f"/api/documents/{document_id}")

    assert response.status_code == 503
    assert client.get(f"/api/documents/{document_id}").status_code == 200


def test_list_and_stats(client, sample_pdf, tmp_path):
    upload(client, sample_pdf)
    upload(client, make_pdf(tmp_path / "vazio.pdf", [""]))

    assert len(client.get("/api/documents").json()["items"]) == 2
    assert client.get("/api/documents/stats").json() == {"total": 2, "ready": 1, "processing": 0, "error": 1}


def test_get_unknown_document(client):
    response = client.get("/api/documents/nao-existe")

    assert response.status_code == 404
    assert response.json()["erro"]["mensagem"] == "Documento não encontrado."


def test_interrupted_processing_is_marked_on_startup(settings, container):
    from fastapi.testclient import TestClient

    from app.main import create_app

    doc = container.repository.create(document_id="abc", filename="a.pdf", size_bytes=1, sha256="x")
    container.repository.update(doc.id, status="processando")

    with TestClient(create_app(settings, container)) as client:
        document = client.get("/api/documents/abc").json()

    assert document["status"] == "erro"
    assert "reprocessar" in document["error_message"]


def test_status_reports_services(client, container):
    body = client.get("/api/status").json()

    assert body["backend"]["online"] is True
    assert body["vector_store"]["online"] is True
    assert body["ollama"]["online"] is True
    assert body["ollama"]["embedding_model"] == {"name": "nomic-embed-text", "installed": True}


def test_status_reports_ollama_offline_and_missing_models(client, container):
    container.ollama.error = OllamaUnavailableError("Não foi possível conectar ao Ollama.")
    body = client.get("/api/status/ollama").json()
    assert body["online"] is False
    assert body["error"] == "Não foi possível conectar ao Ollama."

    container.ollama.error = None
    container.ollama.installed = ["nomic-embed-text:latest"]
    body = client.get("/api/status/ollama").json()
    assert body["chat_model"] == {"name": "qwen3:4b", "installed": False}


def test_models_endpoint(client):
    names = [m["name"] for m in client.get("/api/models").json()["items"]]

    assert names == ["qwen3:4b", "nomic-embed-text:latest"]
