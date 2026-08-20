"""Export endpoints — download extraction results as CSV, Excel, or JSON."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.security import Role, require_role
from app.models.schemas import ExportRequest, UserClaims
from app.services.export_service import ExportService

router = APIRouter()
logger = logging.getLogger("mediextract.api.export")


@router.post("/csv")
async def export_csv(
    body: ExportRequest,
    user: UserClaims = Depends(require_role(Role.ADMIN, Role.CLINICIAN, Role.READONLY)),
):
    """Export extraction results as a CSV file."""
    logger.info("User %s exporting CSV (%d rows)", user.sub, len(body.rows))
    buffer = ExportService.to_csv(body.columns, body.rows)
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=extraction.csv"},
    )


@router.post("/excel")
async def export_excel(
    body: ExportRequest,
    user: UserClaims = Depends(require_role(Role.ADMIN, Role.CLINICIAN, Role.READONLY)),
):
    """Export extraction results as an Excel (.xlsx) file."""
    logger.info("User %s exporting Excel (%d rows)", user.sub, len(body.rows))
    buffer = ExportService.to_excel(body.columns, body.rows)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=extraction.xlsx"},
    )


@router.post("/json")
async def export_json(
    body: ExportRequest,
    user: UserClaims = Depends(require_role(Role.ADMIN, Role.CLINICIAN, Role.READONLY)),
):
    """Export extraction results as JSON."""
    logger.info("User %s exporting JSON (%d rows)", user.sub, len(body.rows))
    return {"columns": [c.model_dump() for c in body.columns], "rows": body.rows}
