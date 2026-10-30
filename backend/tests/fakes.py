"""Dublês do Ollama, do ChromaDB e do executor: os testes unitários não baixam modelos."""

import hashlib
import math
import re
from collections.abc import Iterator
from concurrent.futures import Executor, Future
from pathlib import Path

import pymupdf

from app.core.errors import AppError
from app.repositories.vector_store import ChunkRecord, SearchHit
from app.services.ollama_service import ChatChunk
from app.services.web_search import WebResult

DIMENSION = 64


def _vector(text: str) -> list[float]:
    vec = [0.0] * DIMENSION
    for word in re.findall(r"\w+", text.lower()):
        vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIMENSION] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class FakeModel:
    def __init__(self, answer: str = "Resposta de teste [1]."):
        self.answer = answer
        self.embed_calls: list[list[str]] = []
        self.chat_calls: list[list[dict[str, str]]] = []
        self.embed_error: AppError | None = None
        self.chat_error: AppError | None = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.embed_error:
            raise self.embed_error
        self.embed_calls.append(texts)
        # sem o prefixo do nomic, para a busca por palavras funcionar
        return [_vector(t.split(": ", 1)[-1]) for t in texts]

    def chat_stream(self, messages: list[dict[str, str]]) -> Iterator[ChatChunk]:
        self.chat_calls.append(messages)
        if self.chat_error:
            raise self.chat_error
        yield ChatChunk("thinking", "Vou procurar ")
        yield ChatChunk("thinking", "nos trechos.")
        for word in re.findall(r"\S+\s*", self.answer):
            yield ChatChunk("content", word)


class InMemoryVectorStore:
    def __init__(self):
        self.chunks: dict[str, ChunkRecord] = {}
        self.fail: AppError | None = None

    def ping(self) -> None:
        if self.fail:
            raise self.fail

    def add(self, chunks: list[ChunkRecord]) -> None:
        for c in chunks:
            self.chunks[c.id] = c

    def search(self, embedding: list[float], document_ids: list[str], top_k: int) -> list[SearchHit]:
        scored = []
        for c in self.chunks.values():
            if c.document_id in document_ids:
                similarity = sum(a * b for a, b in zip(embedding, c.embedding, strict=True))
                if similarity > 0:
                    scored.append((1 - similarity, c))
        scored.sort(key=lambda item: item[0])
        return [
            SearchHit(document_id=c.document_id, filename=c.filename, page=c.page, text=c.text, distance=d)
            for d, c in scored[:top_k]
        ]

    def delete_document(self, document_id: str) -> None:
        if self.fail:
            raise self.fail
        self.chunks = {k: v for k, v in self.chunks.items() if v.document_id != document_id}


class FakeWebSearch:
    def __init__(self):
        self.results = [WebResult("Página de teste", "https://exemplo.com.br/pagina", "A capital da França é Paris.")]
        self.queries: list[str] = []
        self.error: AppError | None = None

    def ping(self) -> None:
        if self.error:
            raise self.error

    def search(self, query: str) -> list[WebResult]:
        self.queries.append(query)
        if self.error:
            raise self.error
        return self.results


class ImmediateExecutor(Executor):
    """Executa a tarefa na hora, para o teste ver o resultado do processamento."""

    def submit(self, fn, /, *args, **kwargs):
        future: Future = Future()
        future.set_result(fn(*args, **kwargs))
        return future


def make_pdf(path: Path, pages: list[str]) -> Path:
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        if text:
            page.insert_textbox(pymupdf.Rect(50, 50, 550, 800), text, fontsize=11)
    doc.save(path)
    doc.close()
    return path
