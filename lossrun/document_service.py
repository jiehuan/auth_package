import logging

from azure.core.exceptions import (
    ClientAuthenticationError,
    ResourceNotFoundError,
)
from azure.storage.filedatalake import ContentSettings
from azure.storage.filedatalake.aio import FileSystemClient

from .adls_client import ADLSClient, ADLSClientError
from .settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# e.g. "loss_runs/demo" — no leading or trailing slash
PREFIX = settings.ADLS_PATH_PREFIX.strip("/")


class DocumentNotFoundError(Exception):
    """The requested blob does not exist."""


class DocumentStorageError(Exception):
    """A transient or unexpected storage failure."""


class DocumentService:
    """Document operations against a single ADLS Gen2 container."""

    @staticmethod
    def _path(file_name: str) -> str:
        return f"{PREFIX}/{file_name.lstrip('/')}"

    @staticmethod
    def _fs() -> FileSystemClient:
        return ADLSClient().get_client()

    @classmethod
    async def exists(cls, file_name: str) -> bool:
        path = cls._path(file_name)
        try:
            return await cls._fs().get_file_client(file_path=path).exists()
        except ClientAuthenticationError:
            # Do not swallow: this is a config problem, not a missing file.
            raise
        except ADLSClientError:
            raise
        except Exception as exc:
            logger.exception("Error checking existence of %s.", path)
            raise DocumentStorageError(f"Error checking {path}: {exc}") from exc

    @classmethod
    async def download(cls, file_name: str) -> bytes:
        path = cls._path(file_name)
        try:
            logger.info("Downloading %s", path)
            stream = await cls._fs().get_file_client(file_path=path).download_file()
            data = await stream.readall()
        except ResourceNotFoundError as exc:
            logger.warning("File not found: %s", path)
            raise DocumentNotFoundError(path) from exc
        except ClientAuthenticationError:
            raise
        except Exception as exc:
            logger.exception("Error downloading %s.", path)
            raise DocumentStorageError(f"Error downloading {path}: {exc}") from exc

        logger.info("Downloaded %s (%d bytes)", path, len(data))
        return data

    @classmethod
    async def upload_pdf(
        cls,
        file_name: str,
        data: bytes,
        overwrite: bool = True,
    ) -> None:
        path = cls._path(file_name)
        try:
            logger.info("Uploading %s (%d bytes)", path, len(data))
            file_client = await cls._fs().create_file(
                file=path,
                content_settings=ContentSettings(content_type="application/pdf"),
            )
            await file_client.upload_data(
                data,
                overwrite=overwrite,
                length=len(data),
            )
        except ClientAuthenticationError:
            raise
        except Exception as exc:
            logger.exception("Error uploading %s.", path)
            raise DocumentStorageError(f"Error uploading {path}: {exc}") from exc

        logger.info("Uploaded %s", path)
