import logging
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from azure.core.exceptions import ClientAuthenticationError
from fastapi import APIRouter, File, UploadFile, status
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse, Response, StreamingResponse

from .adls_client import ADLSClient, ADLSClientError
from .document_service import (
    DocumentNotFoundError,
    DocumentService,
    DocumentStorageError,
)

logger = logging.getLogger(__name__)

api_router = APIRouter()

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def _storage_http_error(exc: Exception) -> HTTPException:
    """Map storage-layer exceptions onto meaningful status codes."""
    if isinstance(exc, ClientAuthenticationError):
        logger.critical("ADLS authentication failure.", exc_info=exc)
        return HTTPException(
            status_code=503,
            detail="Storage backend authentication failed.",
        )
    if isinstance(exc, ADLSClientError):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


@api_router.get(path="/health-check", status_code=status.HTTP_200_OK)
async def health_check() -> JSONResponse:
    """Liveness + storage connectivity."""
    healthy = await ADLSClient().health_check()
    return JSONResponse(
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"message": "OK" if healthy else "storage unavailable"},
    )


@api_router.put(path="/upload-document", status_code=status.HTTP_200_OK)
async def upload_document(
    file: Annotated[UploadFile, File()],
) -> JSONResponse:
    """Accept a PDF, store it under a generated filename, return metadata."""
    errors: list[dict] = []

    if file.content_type != "application/pdf" and not (
        file.filename or ""
    ).lower().endswith(".pdf"):
        errors.append(
            {"message": "Uploaded file must be a PDF.", "code": "invalid_media_type"}
        )

    if errors:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "metadata": None, "errors": errors},
        )

    body = await file.read()

    if len(body) > MAX_UPLOAD_BYTES:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={
                "success": False,
                "metadata": None,
                "errors": [
                    {"message": "File exceeds size limit.", "code": "file_too_large"}
                ],
            },
        )

    file_id = uuid4().hex
    safe_name = Path(file.filename or "upload.pdf").name
    generated_filename = f"{file_id}-{safe_name}"

    metadata = {
        "original_filename": safe_name,
        "generated_filename": generated_filename,
        "file_id": file_id,
    }

    try:
        # Upload under the *generated* name — this is what /status queries.
        await DocumentService.upload_pdf(generated_filename, body)
    except (ClientAuthenticationError, ADLSClientError, DocumentStorageError) as exc:
        raise _storage_http_error(exc) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "metadata": metadata, "errors": None},
    )


@api_router.get(
    path="/status/{generated_filename}", status_code=status.HTTP_200_OK
)
async def check_status(generated_filename: str) -> JSONResponse:
    """Return whether processing has produced a report for this filename."""
    try:
        exists = await DocumentService.exists(generated_filename)
    except (ClientAuthenticationError, ADLSClientError, DocumentStorageError) as exc:
        raise _storage_http_error(exc) from exc

    return JSONResponse(
        {"filename": generated_filename, "completed": exists}
    )


@api_router.get(path="/download-report/{filename}")
async def download_report(filename: str) -> Response:
    """Stream the report. Tries the exact name, then the .xlsx variant."""
    requested = Path(filename).name  # strip any path traversal
    stem = Path(requested)

    candidates: list[str] = [requested]
    if stem.suffix != ".xlsx":
        candidates.append(str(stem.with_suffix(".xlsx")))

    try:
        for cand in candidates:
            if not await DocumentService.exists(cand):
                continue

            data = await DocumentService.download(cand)
            xlsx_name = str(Path(cand).with_suffix(".xlsx"))

            return StreamingResponse(
                iter([data]),
                media_type=XLSX_MEDIA_TYPE,
                headers={
                    "Content-Disposition": f'attachment; filename="{xlsx_name}"'
                },
            )
    except DocumentNotFoundError:
        pass  # fall through to 404
    except (ClientAuthenticationError, ADLSClientError, DocumentStorageError) as exc:
        raise _storage_http_error(exc) from exc

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "errors": [{"message": "Report not found.", "code": "not_found"}]
        },
    )
