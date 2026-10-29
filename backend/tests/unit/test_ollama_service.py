from types import SimpleNamespace

import httpx
import ollama
import pytest

from app.core.errors import ModelNotInstalledError, OllamaUnavailableError
from app.repositories.vector_store import collection_name_for
from app.services.ollama_service import ChatChunk, OllamaService


class FakeClient:
    def __init__(self, error: Exception | None = None, models=None, capabilities=None):
        self.error = error
        self.models = models or []
        self.capabilities = capabilities if capabilities is not None else ["completion", "thinking"]
        self.show_calls = 0

    def show(self, model):
        self.show_calls += 1
        if self.error:
            raise self.error
        return SimpleNamespace(capabilities=self.capabilities)

    def list(self):
        if self.error:
            raise self.error
        return SimpleNamespace(models=[SimpleNamespace(model=m, size=10) for m in self.models])

    def embed(self, **_):
        if self.error:
            raise self.error
        return SimpleNamespace(embeddings=[[0.1, 0.2]])

    def chat(self, **kwargs):
        if self.error:
            raise self.error
        self.chat_kwargs = kwargs
        parts = [("Pensando", ""), ("", "Olá"), ("", ""), ("", " mundo")]
        return iter([SimpleNamespace(message=SimpleNamespace(thinking=t, content=c)) for t, c in parts])


def service(client: FakeClient, think: str = "auto") -> OllamaService:
    s = OllamaService("http://ollama:11434", 30, "qwen3:4b", "nomic-embed-text", 8192, 0.2, think)
    s._client = client
    s._quick = client
    return s


def test_model_not_found_has_clear_message():
    s = service(FakeClient(ollama.ResponseError("model not found", 404)))

    with pytest.raises(ModelNotInstalledError, match="ollama pull nomic-embed-text"):
        s.embed(["texto"])


def test_connection_error_becomes_unavailable():
    s = service(FakeClient(httpx.ConnectError("recusada")))

    with pytest.raises(OllamaUnavailableError, match="Não foi possível conectar"):
        s.installed_models()
    with pytest.raises(OllamaUnavailableError):
        list(s.chat_stream([{"role": "user", "content": "oi"}]))


def test_timeout_has_clear_message():
    s = service(FakeClient(httpx.ReadTimeout("lento")))

    with pytest.raises(OllamaUnavailableError, match="demorou demais"):
        s.embed(["texto"])


def test_out_of_memory_has_clear_message():
    s = service(FakeClient(ollama.ResponseError("model requires more system memory than is available", 500)))

    with pytest.raises(OllamaUnavailableError, match="memória suficiente"):
        list(s.chat_stream([{"role": "user", "content": "oi"}]))


def test_chat_stream_separates_thinking_from_answer():
    client = FakeClient()
    s = service(client)

    chunks = list(s.chat_stream([{"role": "user", "content": "oi"}]))

    assert chunks == [ChatChunk("thinking", "Pensando"), ChatChunk("content", "Olá"), ChatChunk("content", " mundo")]
    assert client.chat_kwargs["think"] is True
    assert client.chat_kwargs["options"]["num_ctx"] == 8192


def test_thinking_auto_follows_model_capabilities_and_is_cached():
    client = FakeClient(capabilities=["completion"])
    s = service(client)

    list(s.chat_stream([{"role": "user", "content": "oi"}]))
    list(s.chat_stream([{"role": "user", "content": "oi"}]))

    assert client.chat_kwargs["think"] is False
    assert client.show_calls == 1


def test_thinking_can_be_forced():
    client = FakeClient(capabilities=["completion", "thinking"])

    list(service(client, think="false").chat_stream([{"role": "user", "content": "oi"}]))

    assert client.chat_kwargs["think"] is False
    assert client.show_calls == 0


def test_is_installed_accepts_latest_tag():
    s = service(FakeClient(models=["nomic-embed-text:latest", "qwen3:4b"]))

    assert s.is_installed("nomic-embed-text")
    assert s.is_installed("qwen3:4b")
    assert not s.is_installed("qwen3:8b")


def test_collection_name_depends_on_model():
    assert collection_name_for("nomic-embed-text") == "chunks-nomic-embed-text"
    assert collection_name_for("mxbai-embed-large:335m") == "chunks-mxbai-embed-large-335m"
