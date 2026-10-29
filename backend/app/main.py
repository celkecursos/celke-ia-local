import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, documents, status
from app.core.config import Settings, get_settings
from app.core.container import Container, build_container
from app.core.errors import register_error_handlers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("celke-ia-local")


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = container or build_container(settings)
        interrupted = app.state.container.repository.mark_interrupted()
        if interrupted:
            logger.warning("%d documento(s) com processamento interrompido marcados como erro", interrupted)
        yield
        app.state.container.executor.shutdown(wait=False, cancel_futures=True)

    app = FastAPI(
        title="Celke IA Local",
        description="API do chatbot com RAG sobre PDFs, executado localmente com Ollama e ChromaDB.",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Content-Type"],
        )
    register_error_handlers(app)

    api = APIRouter(prefix="/api")
    api.include_router(status.router)
    api.include_router(documents.router)
    api.include_router(chat.router)
    app.include_router(api)
    return app


app = create_app()
