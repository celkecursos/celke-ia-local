from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal, Protocol

import httpx
import ollama

from app.core.errors import ModelNotInstalledError, OllamaUnavailableError


@dataclass(frozen=True)
class ChatChunk:
    """Pedaço da resposta: `content` vai para o usuário; `thinking` é o raciocínio do modelo."""

    kind: Literal["content", "thinking"]
    text: str


class LanguageModel(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def chat_stream(self, messages: list[dict[str, str]]) -> Iterator[ChatChunk]: ...


def _same_model(installed: str, wanted: str) -> bool:
    # "nomic-embed-text" é instalado como "nomic-embed-text:latest"
    if ":" not in wanted:
        wanted = f"{wanted}:latest"
    return installed == wanted


class OllamaService:
    """Acesso ao Ollama: estado, modelos instalados, embeddings e chat com streaming."""

    def __init__(
        self,
        host: str,
        timeout: float,
        chat_model: str,
        embedding_model: str,
        num_ctx: int,
        temperature: float,
        think: str = "auto",
    ):
        self._client = ollama.Client(host=host, timeout=timeout)
        self._quick = ollama.Client(host=host, timeout=5)
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self._num_ctx = num_ctx
        self._temperature = temperature
        self._think = think
        self._thinks: bool | None = None

    def installed_models(self) -> list[tuple[str, int | None]]:
        try:
            response = self._quick.list()
        except (httpx.HTTPError, ConnectionError) as exc:
            raise OllamaUnavailableError(
                "Não foi possível conectar ao Ollama. Verifique se o container está rodando."
            ) from exc
        return [(m.model, m.size) for m in response.models if m.model]

    def is_installed(self, model: str, installed: list[str] | None = None) -> bool:
        names = installed if installed is not None else [name for name, _ in self.installed_models()]
        return any(_same_model(name, model) for name in names)

    def _translate(self, exc: Exception, model: str) -> Exception:
        if isinstance(exc, ollama.ResponseError):
            if exc.status_code == 404:
                return ModelNotInstalledError(
                    f"O modelo {model} não está instalado no Ollama. Aguarde o download inicial "
                    f"(serviço ollama-init) ou execute: docker compose exec ollama ollama pull {model}"
                )
            if "memory" in str(exc.error).lower():
                return OllamaUnavailableError(
                    f"O Ollama não tem memória suficiente para carregar o modelo {model}. "
                    "Feche outros programas ou configure um modelo menor."
                )
            return OllamaUnavailableError(f"O Ollama retornou um erro: {exc.error}")
        if isinstance(exc, httpx.TimeoutException):
            return OllamaUnavailableError(
                "O Ollama demorou demais para responder. Na primeira pergunta o modelo é carregado na memória; tente de novo."
            )
        if isinstance(exc, (httpx.HTTPError, ConnectionError)):
            return OllamaUnavailableError("Não foi possível conectar ao Ollama. Verifique se o container está rodando.")
        return exc

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = self._client.embed(model=self.embedding_model, input=texts)
        except Exception as exc:
            raise self._translate(exc, self.embedding_model) from exc
        return [list(v) for v in response.embeddings]

    def _use_thinking(self) -> bool:
        """Liga o raciocínio separado quando o modelo tem essa capacidade.

        Alguns modelos (como o qwen3:4b atual) sempre raciocinam: com `think=False` o
        raciocínio vem misturado na resposta. Com `think=True` o Ollama o devolve à parte.
        """
        if self._think in ("true", "false"):
            return self._think == "true"
        if self._thinks is None:
            try:
                capabilities = self._quick.show(self.chat_model).capabilities or []
            except Exception as exc:
                raise self._translate(exc, self.chat_model) from exc
            self._thinks = "thinking" in capabilities
        return self._thinks

    def chat_stream(self, messages: list[dict[str, str]]) -> Iterator[ChatChunk]:
        try:
            stream = self._client.chat(
                model=self.chat_model,
                messages=messages,
                stream=True,
                think=self._use_thinking(),
                options={"num_ctx": self._num_ctx, "temperature": self._temperature},
            )
            for part in stream:
                if part.message.thinking:
                    yield ChatChunk("thinking", part.message.thinking)
                if part.message.content:
                    yield ChatChunk("content", part.message.content)
        except Exception as exc:
            raise self._translate(exc, self.chat_model) from exc
