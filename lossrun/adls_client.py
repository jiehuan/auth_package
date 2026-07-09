import asyncio
import logging

from aiohttp import ClientSession, TCPConnector
from azure.core.exceptions import (
    ClientAuthenticationError,
    ResourceNotFoundError,
)
from azure.identity.aio import ClientSecretCredential
from azure.storage.filedatalake.aio import FileSystemClient

from .settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ADLSClientError(RuntimeError):
    """Raised when the ADLS client cannot be initialized or used."""


class ADLSClient:
    """Singleton wrapper around an async FileSystemClient.

    Initialize once at application startup, close once at shutdown.
    """

    _instance: "ADLSClient | None" = None
    _lock: asyncio.Lock = asyncio.Lock()

    _fs_client: FileSystemClient | None = None
    _credential: ClientSecretCredential | None = None
    _http_session: ClientSession | None = None
    _is_initialized: bool = False

    def __new__(cls) -> "ADLSClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self) -> None:
        """Build the credential, session and FileSystemClient.

        Idempotent. Safe under concurrency. Cleans up on failure so a
        later retry starts from a clean slate.
        """
        if type(self)._is_initialized:
            return

        async with type(self)._lock:
            if type(self)._is_initialized:
                return

            cls = type(self)
            logger.info(
                "Initializing ADLS client (tenant=%s, client=%s, account=%s, container=%s)",
                settings.ADLS_TENANT_ID,
                settings.ADLS_CLIENT_ID,
                settings.ADLS_ACCOUNT_URL,
                settings.ADLS_CONTAINER_NAME,
            )

            try:
                connector = TCPConnector(
                    limit=1000,
                    limit_per_host=1000,
                    ttl_dns_cache=300,
                )
                cls._http_session = ClientSession(connector=connector)

                cls._credential = ClientSecretCredential(
                    settings.ADLS_TENANT_ID,
                    settings.ADLS_CLIENT_ID,
                    settings.ADLS_CLIENT_SECRET,
                )

                cls._fs_client = FileSystemClient(
                    account_url=settings.ADLS_ACCOUNT_URL,
                    file_system_name=settings.ADLS_CONTAINER_NAME,
                    credential=cls._credential,
                    session=cls._http_session,
                )

                await self._verify_connectivity()

            except Exception:
                logger.exception("ADLS client initialization failed; cleaning up.")
                await self._teardown()
                raise

            cls._is_initialized = True
            logger.info("ADLS client initialized successfully.")

    async def _verify_connectivity(self) -> None:
        """Force a real round-trip to Entra ID and the storage account.

        `get_paths()` returns a lazy async iterator, so it must be consumed
        for anything to hit the network.
        """
        cls = type(self)
        assert cls._fs_client is not None

        try:
            paths = cls._fs_client.get_paths(max_results=1)
            async for _ in paths:
                break
        except ClientAuthenticationError as exc:
            raise ADLSClientError(
                f"ADLS authentication failed for client_id="
                f"{settings.ADLS_CLIENT_ID} in tenant={settings.ADLS_TENANT_ID}: {exc}"
            ) from exc
        except ResourceNotFoundError as exc:
            raise ADLSClientError(
                f"ADLS container not found: {settings.ADLS_CONTAINER_NAME}: {exc}"
            ) from exc

    async def _teardown(self) -> None:
        """Best-effort release of every resource. Never raises."""
        cls = type(self)

        for name, closer in (
            ("fs_client", cls._fs_client),
            ("credential", cls._credential),
            ("http_session", cls._http_session),
        ):
            if closer is None:
                continue
            try:
                await closer.close()
            except Exception:
                logger.warning("Error closing %s.", name, exc_info=True)

        cls._fs_client = None
        cls._credential = None
        cls._http_session = None
        cls._is_initialized = False

    async def close(self) -> None:
        """Release all resources. Call once at application shutdown."""
        async with type(self)._lock:
            await self._teardown()
        logger.info("ADLS client closed.")

    def get_client(self) -> FileSystemClient:
        cls = type(self)
        if not cls._is_initialized or cls._fs_client is None:
            raise ADLSClientError(
                "ADLS client is not initialized. Call initialize() at startup."
            )
        return cls._fs_client

    async def health_check(self) -> bool:
        """Liveness probe. Returns False rather than raising."""
        if not type(self)._is_initialized:
            logger.warning("Health check failed: client not initialized.")
            return False
        try:
            await self._verify_connectivity()
        except Exception:
            logger.exception("ADLS health check failed.")
            return False
        return True
