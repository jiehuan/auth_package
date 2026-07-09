import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.adls_client import ADLSClient
from app.api.logging_handler import setup_async_logging
from app.api.routes import api_router
from app.api.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan of FastAPI application."""
    listener = setup_async_logging()
    logger.info("Async logging initialized.")

    adls_client = ADLSClient()
    logger.info("Initializing ADLS client..")
    # Fail fast: ADLSClientError carries tenant/client_id for diagnosis.
    await adls_client.initialize()
    logger.info("ADLS client initialized successfully.")

    logger.info("Application startup complete.")
    try:
        yield
    finally:
        logger.info("Shutting down application..")
        await adls_client.close()
        logger.info("ADLS client closed.")
        if listener:
            listener.stop()
            logger.info("Log listener stopped.")
        logger.info("Application shutdown complete.")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,  # explicit list, not ["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
logger.info("API router mounted at /api")
