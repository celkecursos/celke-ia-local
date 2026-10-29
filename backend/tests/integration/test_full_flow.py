"""Fluxo completo com o Ollama e o ChromaDB de verdade.

Rode com a stack no ar e os modelos baixados:
    docker compose --profile test run --rm backend-tests pytest -m integration
"""

import json
import os
import time

import httpx
import pytest

from tests.fakes import make_pdf

pytestmark = pytest.mark.integration

API = os.environ.get("INTEGRATION_API_URL", "http://backend:8000/api")


@pytest.fixture
def api():
    with httpx.Client(base_url=API, timeout=600) as client:
        status = client.get("/status").json()
        if not (status["ollama"]["chat_model"]["installed"] and status["ollama"]["embedding_model"]["installed"]):
            pytest.skip("Modelos ainda não instalados no Ollama")
        yield client


def test_upload_ask_and_delete(api, tmp_path):
    marker = f"zebra-{int(time.time())}"
    pdf = make_pdf(
        tmp_path / f"{marker}.pdf",
        [
            "Introdução ao manual de testes de integração.",
            f"A senha da sala de reuniões do projeto {marker} é girassol azul.",
        ],
    )
    with pdf.open("rb") as f:
        response = api.post("/documents", files={"file": (pdf.name, f, "application/pdf")})
    assert response.status_code == 202, response.text
    document_id = response.json()["id"]

    try:
        for _ in range(120):
            document = api.get(f"/documents/{document_id}").json()
            if document["status"] in ("pronto", "erro"):
                break
            time.sleep(1)
        assert document["status"] == "pronto", document

        body = {"question": f"Qual é a senha da sala de reuniões do projeto {marker}?", "document_ids": [document_id]}
        events = []
        with api.stream("POST", "/chat", json=body) as stream:
            for block in stream.read().decode().strip().split("\n\n"):
                lines = dict(line.split(": ", 1) for line in block.splitlines())
                events.append((lines["event"], json.loads(lines["data"])))

        assert events[-1][0] == "done", events[-1]
        sources = events[0][1]
        assert any(s["page"] == 2 for s in sources)
        answer = "".join(d["text"] for name, d in events if name == "token").lower()
        assert "girassol" in answer
    finally:
        assert api.delete(f"/documents/{document_id}").status_code == 204
    assert api.get(f"/documents/{document_id}").status_code == 404
