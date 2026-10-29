import re
from dataclasses import dataclass
from typing import Protocol

from app.core.errors import EmbeddingMismatchError, VectorStoreError


@dataclass(frozen=True)
class ChunkRecord:
    id: str
    document_id: str
    filename: str
    page: int
    text: str
    embedding: list[float]


@dataclass(frozen=True)
class SearchHit:
    document_id: str
    filename: str
    page: int
    text: str
    distance: float


class VectorStore(Protocol):
    def ping(self) -> None: ...

    def add(self, chunks: list[ChunkRecord]) -> None: ...

    def search(self, embedding: list[float], document_ids: list[str], top_k: int) -> list[SearchHit]: ...

    def delete_document(self, document_id: str) -> None: ...


def collection_name_for(model: str) -> str:
    """Uma coleção por modelo de embeddings: vetores de modelos diferentes não se misturam."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", model).strip("-").lower()
    return f"chunks-{slug}"[:63]


class ChromaVectorStore:
    """Trechos e vetores no ChromaDB, com o documento e a página nos metadados."""

    def __init__(self, host: str, port: int, embedding_model: str):
        self._host = host
        self._port = port
        self._embedding_model = embedding_model
        self._client = None
        self._collection = None
        self._dimension: int | None = None

    def _get_client(self):
        if self._client is None:
            import chromadb

            try:
                self._client = chromadb.HttpClient(host=self._host, port=self._port)
            except Exception as exc:  # o cliente já testa a conexão ao ser criado
                raise VectorStoreError(f"Não foi possível conectar ao ChromaDB: {exc}") from exc
        return self._client

    def ping(self) -> None:
        try:
            self._get_client().heartbeat()
        except VectorStoreError:
            raise
        except Exception as exc:
            self._client = None
            raise VectorStoreError(f"ChromaDB indisponível: {exc}") from exc

    def _get_collection(self, dimension: int | None = None):
        if self._collection is None:
            try:
                self._collection = self._get_client().get_or_create_collection(
                    name=collection_name_for(self._embedding_model),
                    # Vetores calculados pelo backend (Ollama); o ChromaDB não gera embeddings.
                    embedding_function=None,
                    metadata={"hnsw:space": "cosine", "embedding_model": self._embedding_model},
                )
            except VectorStoreError:
                raise
            except Exception as exc:
                raise VectorStoreError(f"Erro ao abrir a coleção no ChromaDB: {exc}") from exc
            meta = self._collection.metadata or {}
            stored = meta.get("embedding_model")
            if stored and stored != self._embedding_model:
                raise EmbeddingMismatchError(
                    f"A coleção foi criada com o modelo {stored}, mas o configurado é {self._embedding_model}."
                )
            self._dimension = meta.get("dimension")
        if dimension is not None:
            self._check_dimension(dimension)
        return self._collection

    def _check_dimension(self, dimension: int) -> None:
        if self._dimension is None:
            meta = dict(self._collection.metadata or {})
            meta.pop("hnsw:space", None)  # o espaço de distância não pode ser alterado depois
            meta["dimension"] = dimension
            self._collection.modify(metadata=meta)
            self._dimension = dimension
        elif self._dimension != dimension:
            raise EmbeddingMismatchError(
                f"O modelo de embeddings gerou vetores de dimensão {dimension}, "
                f"mas a coleção usa {self._dimension}. Apague os dados ou volte ao modelo anterior."
            )

    def add(self, chunks: list[ChunkRecord]) -> None:
        if not chunks:
            return
        collection = self._get_collection(len(chunks[0].embedding))
        try:
            collection.upsert(
                ids=[c.id for c in chunks],
                embeddings=[c.embedding for c in chunks],
                documents=[c.text for c in chunks],
                metadatas=[{"document_id": c.document_id, "filename": c.filename, "page": c.page} for c in chunks],
            )
        except Exception as exc:
            raise VectorStoreError(f"Erro ao gravar os trechos no ChromaDB: {exc}") from exc

    def search(self, embedding: list[float], document_ids: list[str], top_k: int) -> list[SearchHit]:
        collection = self._get_collection(len(embedding))
        where = {"document_id": document_ids[0]} if len(document_ids) == 1 else {"document_id": {"$in": document_ids}}
        try:
            result = collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorStoreError(f"Erro ao consultar o ChromaDB: {exc}") from exc
        hits = []
        for text, meta, distance in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0], strict=True
        ):
            hits.append(
                SearchHit(
                    document_id=str(meta["document_id"]),
                    filename=str(meta["filename"]),
                    page=int(meta["page"]),
                    text=text,
                    distance=float(distance),
                )
            )
        return hits

    def delete_document(self, document_id: str) -> None:
        try:
            self._get_collection().delete(where={"document_id": document_id})
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(f"Erro ao remover os trechos do ChromaDB: {exc}") from exc
