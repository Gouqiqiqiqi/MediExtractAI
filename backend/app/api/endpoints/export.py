"""Export endpoints — a reviewed run leaves the system here.

Exports are addressed by run, not by a payload the client posts. That is the
whole point: if the browser could hand over its own rows, "only approved data
leaves" would be a claim the client is trusted to honour, and the audit entry
would record something nobody could verify.
"""

from __future__ import annotations

import logging
from typing import Any, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.core.security import Role, require_role
from app.dependencies import DbSession
from app.models.schemas import ColumnDefinition, RunStatus, UserClaims
from app.services import audit_service, run_service
from app.services.export_service import STATUS_COLUMN, ExportService

router = APIRouter()
logger = logging.getLogger("mediextract.api.export")

Scope = Literal["approved", "all"]

EXCEL_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def _content_disposition(filename: str) -> dict[str, str]:
    # A source label can be a filename with a comma or a non-ASCII character in
    # it, and an unquoted one truncates the download name at the comma.
    return {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
    }


async def _prepare(
    session: DbSession,
    user: UserClaims,
    run_id: str,
    scope: Scope,
    fmt: str,
) -> tuple[list[ColumnDefinition], list[dict[str, Any]], list[str], str, list[tuple[str, str]]]:
    """Everything an export needs, with the approval rules already applied."""
    detail = await run_service.get_run_detail(session, run_id)
    approved_only = scope == "approved"
    rows_orm = await run_service.rows_for_export(
        session, run_id, approved_only=approved_only
    )

    if not rows_orm:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No approved rows in this run yet. Approve the rows you want to "
            "export, or export the draft explicitly."
            if approved_only
            else "This run has no rows to export.",
        )

    is_signed_off = detail.status == RunStatus.APPROVED

    # Two independent questions, and conflating them was a bug: whether the run
    # is signed off, and whether this file holds rows that are not all approved.
    # The status column is dropped only when both answers are reassuring — a
    # signed-off run exported as approved rows. Approved rows pulled out of an
    # unsigned run carry it (the run is not reviewed), and so does a signed-off
    # run exported wholesale (it contains the rejected rows too).
    label_rows = not is_signed_off or not approved_only
    rows: list[dict[str, Any]] = []
    for orm_row in rows_orm:
        values = run_service.row_values(orm_row)
        if label_rows:
            values[STATUS_COLUMN] = f"{orm_row.status} (run not signed off)"
        rows.append(values)

    extra = [STATUS_COLUMN] if label_rows else []

    stamp = (detail.created_at or "")[:16].replace(":", "").replace("-", "")
    if not is_signed_off:
        marker = "DRAFT"
    elif approved_only:
        marker = "approved"
    else:
        # Signed off, but the reader is getting the rows a reviewer threw out
        # as well. The filename says so rather than implying they were kept.
        marker = "including-rejected"
    filename = f"extraction-{detail.source_kind}-{stamp}-{marker}.{fmt}"

    about: list[tuple[str, str]] = [
        ("Extraction run", detail.id),
        ("Run at", detail.created_at),
        ("Run by", detail.created_by),
        ("Source", f"{detail.source_kind} · {detail.source_label}"),
        ("Notes / documents", str(detail.note_count)),
        ("Model(s)", detail.models_used or "unrecorded"),
        ("Rows in this file", str(len(rows))),
        ("Rows corrected by a person", str(detail.corrected_rows)),
    ]
    if is_signed_off:
        about += [
            ("Review status", "Signed off"),
            ("Signed off by", detail.approved_by),
            ("Signed off at", detail.approved_at or ""),
            ("Sign-off note", detail.sign_off_note or "—"),
        ]
    else:
        about += [
            ("Review status", "DRAFT — not clinically approved"),
            (
                "Warning",
                "These values were produced by an AI model and have not been "
                "signed off by a clinician. Do not use them as a clinical "
                "record or in a published analysis.",
            ),
            ("Rows still awaiting a decision", str(detail.pending_rows)),
        ]

    await audit_service.record(
        session,
        user,
        f"export.{fmt}",
        run_id,
        f"scope={scope} · {len(rows)} rows · {'signed off' if is_signed_off else 'draft'}",
    )
    return detail.columns, rows, extra, filename, about


@router.get("/runs/{run_id}/csv")
async def export_run_csv(
    run_id: str,
    session: DbSession,
    scope: Scope = Query("approved", description="approved rows only, or the draft"),
    user: UserClaims = Depends(require_role(Role.ADMIN, Role.CLINICIAN, Role.READONLY)),
):
    """Download a run as CSV. Draft rows carry a review-status column."""
    columns, rows, extra, filename, _ = await _prepare(session, user, run_id, scope, "csv")
    buffer = ExportService.to_csv(columns, rows, extra)
    return StreamingResponse(
        buffer, media_type="text/csv", headers=_content_disposition(filename)
    )


@router.get("/runs/{run_id}/excel")
async def export_run_excel(
    run_id: str,
    session: DbSession,
    scope: Scope = Query("approved", description="approved rows only, or the draft"),
    user: UserClaims = Depends(require_role(Role.ADMIN, Role.CLINICIAN, Role.READONLY)),
):
    """Download a run as .xlsx, with a sheet recording what it is and who signed it."""
    columns, rows, extra, filename, about = await _prepare(
        session, user, run_id, scope, "xlsx"
    )
    buffer = ExportService.to_excel(columns, rows, extra, about)
    return StreamingResponse(
        buffer, media_type=EXCEL_MEDIA_TYPE, headers=_content_disposition(filename)
    )
