from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.core.container import Container
from app.core.errors import AppError
from app.schemas.status import Health, InstalledModel, ModelList, ModelStatus, OllamaStatus, ServiceStatus, SystemStatus

router = APIRouter(tags=["Estado"])

ContainerDep = Annotated[Container, Depends(get_container)]


@router.get("/health", response_model=Health, summary="Saúde da API")
def health() -> Health:
    return Health(status="ok")


def _ollama_status(c: ContainerDep) -> OllamaStatus:
    chat, embed = c.settings.chat_model, c.settings.embedding_model
    try:
        names = [name for name, _ in c.ollama.installed_models()]
    except AppError as exc:
        return OllamaStatus(
            online=False,
            chat_model=ModelStatus(name=chat, installed=False),
            embedding_model=ModelStatus(name=embed, installed=False),
            error=exc.message,
        )
    return OllamaStatus(
        online=True,
        chat_model=ModelStatus(name=chat, installed=c.ollama.is_installed(chat, names)),
        embedding_model=ModelStatus(name=embed, installed=c.ollama.is_installed(embed, names)),
    )


@router.get("/status/ollama", response_model=OllamaStatus, summary="Estado do Ollama e dos modelos configurados")
def ollama_status(c: ContainerDep) -> OllamaStatus:
    return _ollama_status(c)


@router.get("/status", response_model=SystemStatus, summary="Estado de todos os serviços")
def system_status(c: ContainerDep) -> SystemStatus:
    try:
        c.vector_store.ping()
        vector = ServiceStatus(online=True)
    except AppError as exc:
        vector = ServiceStatus(online=False, error=exc.message)
    return SystemStatus(backend=ServiceStatus(online=True), ollama=_ollama_status(c), vector_store=vector)


@router.get("/models", response_model=ModelList, summary="Modelos instalados no Ollama")
def models(c: ContainerDep) -> ModelList:
    return ModelList(items=[InstalledModel(name=n, size_bytes=s) for n, s in c.ollama.installed_models()])
