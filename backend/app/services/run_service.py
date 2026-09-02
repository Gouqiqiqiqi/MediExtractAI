"""Extraction runs — persistence, correction, and clinical sign-off.

The shape of this module follows one decision: an extraction is a *draft*, and
the reviewed dataset is the product. So every run is recorded the moment the
model answers — nothing depends on a browser tab staying open — but recording
it is not the same as blessing it. Rows arrive ``pending`` and only a clinician
moves them to ``approved``; the export layer is what enforces the difference.

Corrections are edits, not re-runs. Asking the model again for a value a person
has already read and fixed spends money and time to produce a *different*
uncertainty, and would throw away the one thing worth keeping: the pair of
(what the model said, what the right answer was).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status as http_status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import ExtractionRow, ExtractionRowRevision, ExtractionRun
from app.models.schemas import (
    ColumnDefinition,
    RowStatus,
    RunDetail,
    RunRow,
    RunStatus,
    RunSummary,
    UserClaims,
)
from app.services import audit_service

logger = logging.getLogger("mediextract.services.runs")

# Not a stored status: the two states that mean "a person still has to look".
AWAITING_REVIEW = "awaiting_review"


# ── JSON helpers ──
# sort_keys everywhere: "has this row been corrected?" is answered by comparing
# the stored value with the stored model output, and two dicts that differ only
# in key order must not read as a correction.


def _dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def _loads(raw: str, fallback: Any) -> Any:
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return fallback


def _iso(value: datetime | None) -> str | None:
    """UTC ISO-8601, including for the naive datetimes SQLite hands back."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Reading ──


async def _get_run(session: AsyncSession, run_id: str) -> ExtractionRun:
    run = await session.get(ExtractionRun, run_id)
    if run is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "No such extraction run")
    return run


async def _get_row(session: AsyncSession, run_id: str, row_id: str) -> ExtractionRow:
    row = await session.get(ExtractionRow, row_id)
    # Checking the run as well as the row: a row id from another run must not
    # be editable by pointing a request at a run the caller can reach.
    if row is None or row.run_id != run_id:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "No such row in this run")
    return row


def _row_out(row: ExtractionRow) -> RunRow:
    data = _loads(row.data_json, {})
    ai_data = _loads(row.ai_data_json, {})
    corrected = [k for k, v in data.items() if k in ai_data and ai_data[k] != v]
    return RunRow(
        id=row.id,
        row_index=row.row_index,
        note_id=row.note_id,
        patient_id=row.patient_id,
        data=data,
        ai_data=ai_data,
        corrected_columns=sorted(corrected),
        status=RowStatus(row.status),
        review_note=row.review_note,
        edited_by=row.edited_by_name,
        edited_at=_iso(row.edited_at),
        decided_by=row.decided_by_name,
        decided_at=_iso(row.decided_at),
    )


def _summary(run: ExtractionRun, counts: dict[str, int]) -> RunSummary:
    return RunSummary(
        id=run.id,
        created_at=_iso(run.created_at) or "",
        created_by=run.created_by_name,
        source_kind=run.source_kind,
        source_label=run.source_label,
        note_count=run.note_count,
        row_count=run.row_count,
        status=RunStatus(run.status),
        models_used=run.models_used,
        approved_by=run.approved_by_name,
        approved_at=_iso(run.approved_at),
        pending_rows=counts.get(RowStatus.PENDING, 0),
        approved_rows=counts.get(RowStatus.APPROVED, 0),
        rejected_rows=counts.get(RowStatus.REJECTED, 0),
        corrected_rows=counts.get("corrected", 0),
    )


async def _counts_for(session: AsyncSession, run_ids: list[str]) -> dict[str, dict[str, int]]:
    """Row tallies per run, in two queries rather than per run.

    A list of twenty runs was otherwise forty round trips, and the counts are
    the whole point of the list: how much review is left.
    """
    if not run_ids:
        return {}

    tallies: dict[str, dict[str, int]] = {rid: {} for rid in run_ids}

    by_status = await session.execute(
        select(ExtractionRow.run_id, ExtractionRow.status, func.count())
        .where(ExtractionRow.run_id.in_(run_ids))
        .group_by(ExtractionRow.run_id, ExtractionRow.status)
    )
    for run_id, row_status, count in by_status:
        tallies[run_id][row_status] = count

    corrected = await session.execute(
        select(ExtractionRow.run_id, func.count())
        .where(
            ExtractionRow.run_id.in_(run_ids),
            ExtractionRow.data_json != ExtractionRow.ai_data_json,
        )
        .group_by(ExtractionRow.run_id)
    )
    for run_id, count in corrected:
        tallies[run_id]["corrected"] = count

    return tallies


async def list_runs(
    session: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 25,
    status_filter: str | None = None,
    created_by_sub: str | None = None,
) -> tuple[list[RunSummary], int]:
    conditions = []
    if status_filter == AWAITING_REVIEW:
        # The state anyone actually filters on. Doing this in the client meant
        # filtering one page of results, so a deployment with more runs than a
        # page would hide the oldest thing still waiting — exactly the one that
        # matters most.
        conditions.append(
            ExtractionRun.status.in_([RunStatus.DRAFT, RunStatus.IN_REVIEW])
        )
    elif status_filter:
        conditions.append(ExtractionRun.status == status_filter)
    if created_by_sub:
        conditions.append(ExtractionRun.created_by_sub == created_by_sub)

    total = await session.scalar(
        select(func.count()).select_from(ExtractionRun).where(*conditions)
    )

    result = await session.execute(
        select(ExtractionRun)
        .where(*conditions)
        # id as tiebreaker: SQLite timestamps are second-granular, and two runs
        # in the same second must still come back in a stable order or paging
        # can show one twice and skip another.
        .order_by(ExtractionRun.created_at.desc(), ExtractionRun.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    runs = list(result.scalars())
    tallies = await _counts_for(session, [r.id for r in runs])
    return [_summary(r, tallies.get(r.id, {})) for r in runs], int(total or 0)


async def run_stats(session: AsyncSession) -> dict[str, int]:
    """How much work is outstanding — one query, because the sidebar asks often."""
    result = await session.execute(
        select(ExtractionRun.status, func.count()).group_by(ExtractionRun.status)
    )
    by_status = {row_status: count for row_status, count in result}
    pending_rows = await session.scalar(
        select(func.count())
        .select_from(ExtractionRow)
        .where(ExtractionRow.status == RowStatus.PENDING)
    )
    return {
        "total": sum(by_status.values()),
        "draft": by_status.get(RunStatus.DRAFT, 0),
        "in_review": by_status.get(RunStatus.IN_REVIEW, 0),
        "approved": by_status.get(RunStatus.APPROVED, 0),
        "rejected": by_status.get(RunStatus.REJECTED, 0),
        # What the badge counts: runs that still need a person.
        "awaiting_review": by_status.get(RunStatus.DRAFT, 0)
        + by_status.get(RunStatus.IN_REVIEW, 0),
        "pending_rows": int(pending_rows or 0),
    }


async def get_run_detail(session: AsyncSession, run_id: str) -> RunDetail:
    run = await _get_run(session, run_id)
    result = await session.execute(
        select(ExtractionRow)
        .where(ExtractionRow.run_id == run_id)
        .order_by(ExtractionRow.row_index)
    )
    rows = list(result.scalars())
    tallies = await _counts_for(session, [run_id])
    summary = _summary(run, tallies.get(run_id, {}))

    return RunDetail(
        **summary.model_dump(),
        columns=[ColumnDefinition(**c) for c in _loads(run.schema_json, [])],
        provenance_columns=_loads(run.provenance_columns_json, []),
        rows=[_row_out(r) for r in rows],
        sign_off_note=run.sign_off_note,
    )


# ── Creating ──


async def create_run(
    session: AsyncSession,
    user: UserClaims,
    *,
    source_kind: str,
    source_id: str,
    source_label: str,
    columns: list[ColumnDefinition],
    provenance_columns: list[str],
    rows: list[dict[str, Any]],
    note_count: int,
    models_used: Iterable[str],
    note_key: str = "",
    patient_key: str = "",
) -> ExtractionRun:
    """Record a finished extraction as a draft run.

    Called before the result is returned to the caller: if persisting fails,
    the user should find out now rather than after spending an afternoon
    correcting rows that were never going to be saved.
    """
    run = ExtractionRun(
        created_by_sub=user.sub,
        created_by_name=user.name,
        source_kind=source_kind,
        source_id=source_id,
        source_label=source_label[:500],
        schema_json=_dumps([c.model_dump(mode="json") for c in columns]),
        provenance_columns_json=_dumps(provenance_columns),
        models_used=", ".join(sorted(models_used))[:500],
        note_count=note_count,
        row_count=len(rows),
        status=RunStatus.DRAFT,
    )
    session.add(run)
    await session.flush()

    for index, row in enumerate(rows):
        payload = _dumps(row)
        session.add(
            ExtractionRow(
                run_id=run.id,
                row_index=index,
                note_id=str(row.get(note_key) or "")[:255] if note_key else "",
                patient_id=str(row.get(patient_key) or "")[:255] if patient_key else "",
                data_json=payload,
                # Identical today, and never written again: this is the model's
                # answer, kept so a correction can be seen as one.
                ai_data_json=payload,
            )
        )

    await audit_service.record(
        session,
        user,
        "run.created",
        run.id,
        f"{source_kind} · {note_count} notes · {len(rows)} rows · {run.models_used}",
    )
    await session.flush()
    await session.refresh(run)
    return run


# ── Editing and review ──


def _assert_open(run: ExtractionRun) -> None:
    if run.status == RunStatus.APPROVED:
        raise HTTPException(
            http_status.HTTP_409_CONFLICT,
            "This run is signed off and read-only. Reopen it to make changes — "
            "the reopening is recorded.",
        )
    if run.status == RunStatus.REJECTED:
        raise HTTPException(
            http_status.HTTP_409_CONFLICT,
            "This run was rejected. Run the extraction again rather than editing it.",
        )


async def edit_row(
    session: AsyncSession,
    user: UserClaims,
    run_id: str,
    row_id: str,
    values: dict[str, Any],
) -> RunRow:
    run = await _get_run(session, run_id)
    _assert_open(run)
    row = await _get_row(session, run_id, row_id)

    if row.status == RowStatus.APPROVED:
        raise HTTPException(
            http_status.HTTP_409_CONFLICT,
            "This row is approved and read-only. Reopen the row to correct it.",
        )

    provenance = set(_loads(run.provenance_columns_json, []))
    schema_names = {c["name"] for c in _loads(run.schema_json, [])}

    unknown = [k for k in values if k not in schema_names]
    if unknown:
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            f"Not a column of this run: {', '.join(sorted(unknown))}",
        )
    blocked = [k for k in values if k in provenance]
    if blocked:
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            # One note can produce several rows, so which note a row came from
            # is a fact about the extraction, not a value to correct.
            f"Provenance columns record where a row came from and cannot be "
            f"edited: {', '.join(sorted(blocked))}",
        )

    data = _loads(row.data_json, {})
    changed: list[str] = []
    for column, new_value in values.items():
        old_value = data.get(column)
        if old_value == new_value:
            continue
        data[column] = new_value
        changed.append(column)
        session.add(
            ExtractionRowRevision(
                run_id=run_id,
                row_id=row.id,
                column_name=column,
                old_value_json=_dumps(old_value),
                new_value_json=_dumps(new_value),
                kind="edit",
                changed_by_sub=user.sub,
                changed_by_name=user.name,
            )
        )

    if not changed:
        return _row_out(row)

    row.data_json = _dumps(data)
    row.edited_by_sub = user.sub
    row.edited_by_name = user.name
    row.edited_at = _now()
    if run.status == RunStatus.DRAFT:
        run.status = RunStatus.IN_REVIEW

    await audit_service.record(
        session, user, "row.edited", f"{run_id}/{row.id}", ", ".join(sorted(changed))
    )
    await session.flush()
    return _row_out(row)


async def revert_row(
    session: AsyncSession,
    user: UserClaims,
    run_id: str,
    row_id: str,
    column: str | None,
) -> RunRow:
    """Put the model's original answer back, for one column or the whole row."""
    run = await _get_run(session, run_id)
    _assert_open(run)
    row = await _get_row(session, run_id, row_id)

    if row.status == RowStatus.APPROVED:
        raise HTTPException(
            http_status.HTTP_409_CONFLICT,
            "This row is approved and read-only. Reopen the row to change it.",
        )

    data = _loads(row.data_json, {})
    ai_data = _loads(row.ai_data_json, {})
    targets = [column] if column else list(ai_data)

    changed: list[str] = []
    for name in targets:
        if name not in ai_data:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST, f"Not a column of this run: {name}"
            )
        if data.get(name) == ai_data[name]:
            continue
        session.add(
            ExtractionRowRevision(
                run_id=run_id,
                row_id=row.id,
                column_name=name,
                old_value_json=_dumps(data.get(name)),
                new_value_json=_dumps(ai_data[name]),
                kind="revert",
                changed_by_sub=user.sub,
                changed_by_name=user.name,
            )
        )
        data[name] = ai_data[name]
        changed.append(name)

    if not changed:
        return _row_out(row)

    row.data_json = _dumps(data)
    row.edited_by_sub = user.sub
    row.edited_by_name = user.name
    row.edited_at = _now()

    await audit_service.record(
        session, user, "row.reverted", f"{run_id}/{row.id}", ", ".join(sorted(changed))
    )
    await session.flush()
    return _row_out(row)


async def decide_row(
    session: AsyncSession,
    user: UserClaims,
    run_id: str,
    row_id: str,
    new_status: RowStatus,
    note: str,
) -> RunRow:
    """Approve, reject, or reopen one row."""
    run = await _get_run(session, run_id)
    _assert_open(run)
    row = await _get_row(session, run_id, row_id)

    row.status = new_status
    row.review_note = note
    if new_status == RowStatus.PENDING:
        # Reopening clears the decision rather than leaving a name against a
        # verdict that no longer stands.
        row.decided_by_sub = ""
        row.decided_by_name = ""
        row.decided_at = None
    else:
        row.decided_by_sub = user.sub
        row.decided_by_name = user.name
        row.decided_at = _now()

    if run.status == RunStatus.DRAFT:
        run.status = RunStatus.IN_REVIEW

    await audit_service.record(
        session, user, f"row.{new_status}", f"{run_id}/{row.id}", note[:200]
    )
    await session.flush()
    return _row_out(row)


# ── Sign-off ──


async def approve_run(
    session: AsyncSession,
    user: UserClaims,
    run_id: str,
    *,
    approve_pending: bool,
    note: str,
    require_separate_approver: bool = False,
) -> RunDetail:
    run = await _get_run(session, run_id)
    if run.status == RunStatus.APPROVED:
        raise HTTPException(http_status.HTTP_409_CONFLICT, "This run is already signed off")
    if run.status == RunStatus.REJECTED:
        raise HTTPException(
            http_status.HTTP_409_CONFLICT, "This run was rejected and cannot be signed off"
        )
    if run.row_count == 0:
        raise HTTPException(
            http_status.HTTP_409_CONFLICT, "This run produced no rows to sign off"
        )
    if require_separate_approver and run.created_by_sub == user.sub:
        raise HTTPException(
            http_status.HTTP_403_FORBIDDEN,
            "This deployment requires a second reviewer: the person who ran an "
            "extraction cannot sign it off.",
        )

    result = await session.execute(
        select(ExtractionRow).where(
            ExtractionRow.run_id == run_id, ExtractionRow.status == RowStatus.PENDING
        )
    )
    pending = list(result.scalars())

    if pending and not approve_pending:
        raise HTTPException(
            http_status.HTTP_409_CONFLICT,
            f"{len(pending)} row{'' if len(pending) == 1 else 's'} still need a "
            "decision. Review them, or sign off the remainder in one action.",
        )

    now = _now()
    for row in pending:
        row.status = RowStatus.APPROVED
        row.decided_by_sub = user.sub
        row.decided_by_name = user.name
        row.decided_at = now

    approved_total = await session.scalar(
        select(func.count())
        .select_from(ExtractionRow)
        .where(ExtractionRow.run_id == run_id, ExtractionRow.status == RowStatus.APPROVED)
    )
    if not approved_total:
        raise HTTPException(
            http_status.HTTP_409_CONFLICT,
            "Every row was rejected — reject the run rather than signing it off.",
        )

    run.status = RunStatus.APPROVED
    run.approved_by_sub = user.sub
    run.approved_by_name = user.name
    run.approved_at = now
    run.sign_off_note = note

    # The detail records *how* it was signed. A batch sign-off that claims each
    # row was read individually would be a false record, and at a few thousand
    # rows it is the common case, not the exception.
    await audit_service.record(
        session,
        user,
        "run.approved",
        run_id,
        f"{approved_total} rows approved"
        + (f", {len(pending)} in one batch action" if pending else ", row by row"),
    )
    await session.flush()
    return await get_run_detail(session, run_id)


async def reject_run(
    session: AsyncSession, user: UserClaims, run_id: str, note: str
) -> RunDetail:
    run = await _get_run(session, run_id)
    if run.status == RunStatus.APPROVED:
        raise HTTPException(
            http_status.HTTP_409_CONFLICT,
            "This run is signed off. Reopen it before rejecting it.",
        )
    run.status = RunStatus.REJECTED
    run.sign_off_note = note
    await audit_service.record(session, user, "run.rejected", run_id, note[:200])
    await session.flush()
    return await get_run_detail(session, run_id)


async def reopen_run(
    session: AsyncSession, user: UserClaims, run_id: str, note: str
) -> RunDetail:
    """Take a run back out of sign-off so it can be corrected again.

    Not an undo: the approval that stood is in the audit trail, and so is this.
    Approved rows stay approved — reopening the run unlocks the run, and each
    row a reviewer wants to change is reopened on its own.
    """
    run = await _get_run(session, run_id)
    if run.status not in (RunStatus.APPROVED, RunStatus.REJECTED):
        raise HTTPException(
            http_status.HTTP_409_CONFLICT, "This run is already open for review"
        )
    run.status = RunStatus.IN_REVIEW
    run.approved_by_sub = ""
    run.approved_by_name = ""
    run.approved_at = None
    await audit_service.record(session, user, "run.reopened", run_id, note[:200])
    await session.flush()
    return await get_run_detail(session, run_id)


async def delete_run(
    session: AsyncSession, user: UserClaims, run_id: str, *, is_admin: bool
) -> None:
    run = await _get_run(session, run_id)
    if run.status == RunStatus.APPROVED:
        raise HTTPException(
            http_status.HTTP_409_CONFLICT,
            "A signed-off run is a clinical record and cannot be deleted.",
        )
    if run.created_by_sub != user.sub and not is_admin:
        raise HTTPException(
            http_status.HTTP_403_FORBIDDEN,
            "Only the person who ran this extraction, or an administrator, can discard it.",
        )

    # Children first, explicitly: SQLite does not enforce foreign keys unless
    # asked to, so relying on a cascade here would leave orphans on the demo
    # database and not on Postgres — the worst kind of difference.
    for model in (ExtractionRowRevision, ExtractionRow):
        result = await session.execute(select(model).where(model.run_id == run_id))
        for child in result.scalars():
            await session.delete(child)
    await session.delete(run)

    await audit_service.record(
        session, user, "run.deleted", run_id, f"{run.row_count} rows discarded"
    )
    await session.flush()


def row_values(row: ExtractionRow) -> dict[str, Any]:
    """The current values of a stored row, provenance included."""
    return _loads(row.data_json, {})


async def rows_for_export(
    session: AsyncSession, run_id: str, *, approved_only: bool
) -> list[ExtractionRow]:
    conditions = [ExtractionRow.run_id == run_id]
    if approved_only:
        conditions.append(ExtractionRow.status == RowStatus.APPROVED)
    result = await session.execute(
        select(ExtractionRow).where(*conditions).order_by(ExtractionRow.row_index)
    )
    return list(result.scalars())
