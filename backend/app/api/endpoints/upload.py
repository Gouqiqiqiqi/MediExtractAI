"""File upload endpoint — accepts .txt, .doc/.docx, .pdf and returns extracted text."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.config import Settings, get_settings
from app.core.security import Role, require_role
from app.models.schemas import UploadResponse, UserClaims
from app.services.file_service import FileService

router = APIRouter()
logger = logging.getLogger("mediextract.api.upload")

ALLOWED_CONTENT_TYPES = {
    "text/plain",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".doc", ".docx"}


@router.post("/", response_model=UploadResponse)
async def upload_file(
    file: UploadFile,
    user: UserClaims = Depends(require_role(Role.ADMIN, Role.CLINICIAN)),
    settings: Settings = Depends(get_settings),
):
    """Upload a medical document and extract its plain text content.

    Accepted formats: .txt, .doc, .docx, .pdf
    Max size: configured via MAX_UPLOAD_SIZE_MB (default 10 MB).
    """
    # ── Validate filename & extension ──
    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Filename is required")

    import pathlib
    ext = pathlib.Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # ── Read & size check ──
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds {settings.max_upload_size_mb} MB limit",
        )

    logger.info(
        "User %s uploaded '%s' (%d bytes)",
        user.sub,
        file.filename,
        len(content),
    )

    # ── Parse ──
    file_service = FileService(
        render_dpi=settings.pdf_render_dpi,
        max_render_pages=settings.pdf_render_max_pages,
        jpeg_quality=settings.pdf_render_jpeg_quality,
    )
    try:
        parsed = file_service.parse_document(content, ext)
    except Exception as exc:
        logger.exception("Failed to parse uploaded file '%s'", file.filename)
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Could not parse file: {exc}",
        ) from exc

    # A file that yielded neither text nor pages is a failure, and saying so
    # here is the point: it used to come back as a 200 with an empty string,
    # which looked like a successful upload of an empty document all the way
    # up to the model.
    if not parsed.has_content:
        logger.warning("Extracted nothing from '%s'", file.filename)
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"No text could be extracted from '{file.filename}'. If it is a "
            "scan, the pages could not be rendered either — try re-exporting "
            "it, or upload the original document.",
        )

    return UploadResponse(
        filename=file.filename,
        size_bytes=len(content),
        extracted_text=parsed.text,
        char_count=len(parsed.text),
        page_images=parsed.images,
        page_count=parsed.page_count,
        warning=parsed.warning,
    )
