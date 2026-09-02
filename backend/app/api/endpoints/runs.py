"""Extraction runs — list, review, correct and sign off.

The review surface. Everything an extraction produced lives here as a draft
until a clinician approves it; the export endpoints are what turn that
distinction into something enforced rather than advisory.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from app.core.security import Role, require_role
from app.dependencies import DbSession, SettingsDep
from app.models.schemas import (
    RowDecisionRequest,
    RowEditRequest,
    RowRevertRequest,
    RunApprovalRequest,
    RunDetail,
    RunListResponse,
    RunRow,
    RunStats,
    UserClaims,
)
from app.services import run_service

router = APIRouter()
logger = logging.getLogger("mediextract.api.runs")

# Reading a run is not a clinical action; correcting or approving one is.
AnyRole = require_role(Role.ADMIN, Role.CLINICIAN, Role.READONLY)
Reviewer = require_role(Role.ADMIN, Role.CLINICIAN)


@router.get("", response_model=RunListResponse)
async def list_runs(
    session: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status: str | None = Query(
        None,
        description=(
            "draft | in_review | approved | rejected, or awaiting_review for "
            "the two states that still need a person"
        ),
    ),
    mine: bool = Query(False, description="Only runs this user started"),
    user: UserClaims = Depends(AnyRole),
):
    """The extraction history, newest first."""
    items, total = await run_service.list_runs(
        session,
        page=page,
        page_size=page_size,
        status_filter=status,
        created_by_sub=user.sub if mine else None,
    )
    return RunListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/stats", response_model=RunStats)
async def run_stats(
    session: DbSession,
    user: UserClaims = Depends(AnyRole),
):
    """How many runs are waiting for a person. Declared before /{run_id} so the
    path is not read as the id of a run called "stats"."""
    return RunStats(**await run_service.run_stats(session))


@router.get("/{run_id}", response_model=RunDetail)
async def get_run(
    run_id: str,
    session: DbSession,
    user: UserClaims = Depends(AnyRole),
):
    """One run: its schema, its rows, and where each row is in review."""
    return await run_service.get_run_detail(session, run_id)


@router.patch("/{run_id}/rows/{row_id}", response_model=RunRow)
async def edit_row(
    run_id: str,
    row_id: str,
    body: RowEditRequest,
    session: DbSession,
    user: UserClaims = Depends(Reviewer),
):
    """Correct extracted values on one row.

    A correction, not a re-run: the model's original answer is kept beside the
    new value, and every change is recorded against the person who made it.
    """
    return await run_service.edit_row(session, user, run_id, row_id, body.values)


@router.post("/{run_id}/rows/{row_id}/revert", response_model=RunRow)
async def revert_row(
    run_id: str,
    row_id: str,
    body: RowRevertRequest,
    session: DbSession,
    user: UserClaims = Depends(Reviewer),
):
    """Put the model's original answer back, for one column or the whole row."""
    return await run_service.revert_row(session, user, run_id, row_id, body.column)


@router.patch("/{run_id}/rows/{row_id}/status", response_model=RunRow)
async def decide_row(
    run_id: str,
    row_id: str,
    body: RowDecisionRequest,
    session: DbSession,
    user: UserClaims = Depends(Reviewer),
):
    """Approve, reject, or reopen a single row."""
    return await run_service.decide_row(
        session, user, run_id, row_id, body.status, body.note
    )


@router.post("/{run_id}/approve", response_model=RunDetail)
async def approve_run(
    run_id: str,
    body: RunApprovalRequest,
    session: DbSession,
    settings: SettingsDep,
    user: UserClaims = Depends(Reviewer),
):
    """Sign off a run. Only after this may its rows leave as reviewed data."""
    return await run_service.approve_run(
        session,
        user,
        run_id,
        approve_pending=body.approve_pending,
        note=body.note,
        require_separate_approver=settings.require_separate_approver,
    )


@router.post("/{run_id}/reject", response_model=RunDetail)
async def reject_run(
    run_id: str,
    body: RunApprovalRequest,
    session: DbSession,
    user: UserClaims = Depends(Reviewer),
):
    """Mark a whole run unusable. Kept, not deleted — a bad run is a finding."""
    return await run_service.reject_run(session, user, run_id, body.note)


@router.post("/{run_id}/reopen", response_model=RunDetail)
async def reopen_run(
    run_id: str,
    body: RunApprovalRequest,
    session: DbSession,
    user: UserClaims = Depends(Reviewer),
):
    """Take a signed-off run back into review. Both approvals stay in the trail."""
    return await run_service.reopen_run(session, user, run_id, body.note)


@router.delete("/{run_id}", status_code=204)
async def delete_run(
    run_id: str,
    session: DbSession,
    user: UserClaims = Depends(Reviewer),
):
    """Discard a draft. Signed-off runs cannot be deleted."""
    await run_service.delete_run(
        session, user, run_id, is_admin=Role.ADMIN in user.roles
    )
