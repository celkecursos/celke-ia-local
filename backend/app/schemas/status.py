from pydantic import BaseModel


class Health(BaseModel):
    status: str


class ModelStatus(BaseModel):
    name: str
    installed: bool


class OllamaStatus(BaseModel):
    online: bool
    chat_model: ModelStatus
    embedding_model: ModelStatus
    error: str | None = None


class ServiceStatus(BaseModel):
    online: bool
    error: str | None = None


class SystemStatus(BaseModel):
    backend: ServiceStatus
    ollama: OllamaStatus
    vector_store: ServiceStatus


class InstalledModel(BaseModel):
    name: str
    size_bytes: int | None = None


class ModelList(BaseModel):
    items: list[InstalledModel]
