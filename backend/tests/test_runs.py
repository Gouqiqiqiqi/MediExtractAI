"""The review lifecycle: draft → correction → sign-off → export.

These are the tests that matter for the governance story, so they assert the
refusals as much as the happy path: an unapproved run must not export as
though it were reviewed, a signed-off run must not be quietly edited, and every
step has to be in the audit trail afterwards.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.security import Role, get_current_user
from app.main import app
from app.models.database import AuditLog, ExtractionRowRevision
from app.models.schemas import ColumnDefinition, UserClaims
from app.services import app_database, run_service

NOTE_COL = "Source Note"
PATIENT_COL = "Patient ID"

COLUMNS = [
    ColumnDefinition(name=NOTE_COL, data_type="text", description="Source note"),
    ColumnDefinition(name=PATIENT_COL, data_type="text", description="Patient"),
    ColumnDefinition(name="Diagnosis", data_type="text", description="Primary diagnosis"),
    ColumnDefinition(name="Medications", data_type="text[]", description="Drugs"),
]

ROWS = [
    {
        NOTE_COL: "NOTE-0001",
        PATIENT_COL: "SYN-0001",
        "Diagnosis": "Community acquired pneumonia",
        "Medications": ["Amoxicillin 500mg TDS"],
    },
    {
        NOTE_COL: "NOTE-0002",
        PATIENT_COL: "SYN-0002",
        "Diagnosis": "Multifactorial falls",
        "Medications": ["Amlodipine 2.5mg OD"],
    },
]

AUTHOR = UserClaims(
    sub="dev-user-001", name="Dev User", email="dev@example.com", roles=[Role.ADMIN]
)


async def _make_run(source_kind: str = "database") -> str:
    """Persist a run the way the extraction endpoint does, without calling a model."""
    async with app_database.session_factory()() as session:
        run = await run_service.create_run(
            session,
            AUTHOR,
            source_kind=source_kind,
            source_id="src-1",
            source_label="Synthetic EPR",
            columns=COLUMNS,
            provenance_columns=[NOTE_COL, PATIENT_COL],
            rows=ROWS,
            note_count=2,
            models_used={"gemini:gemini-3.5-flash"},
            note_key=NOTE_COL,
            patient_key=PATIENT_COL,
        )
        await session.commit()
        return run.id


@pytest.fixture
async def run_id():
    return await _make_run()


async def _audit_actions(run_id: str) -> list[str]:
    async with app_database.session_factory()() as session:
        result = await session.execute(
            select(AuditLog.action).where(AuditLog.resource.startswith(run_id))
        )
        return list(result.scalars())


@pytest.mark.anyio
async def test_a_run_is_persisted_as_a_draft(client: AsyncClient, run_id: str):
    """An extraction is saved before anyone reviews it — but saved is not blessed."""
    resp = await client.get(f"/api/v1/runs/{run_id}")
    assert resp.status_code == 200
    detail = resp.json()

    assert detail["status"] == "draft"
    assert detail["pending_rows"] == 2
    assert detail["approved_rows"] == 0
    assert detail["row_count"] == 2
    assert detail["models_used"] == "gemini:gemini-3.5-flash"
    assert [r["note_id"] for r in detail["rows"]] == ["NOTE-0001", "NOTE-0002"]
    assert "run.created" in await _audit_actions(run_id)


@pytest.mark.anyio
async def test_runs_are_listed_newest_first_with_review_progress(
    client: AsyncClient, run_id: str
):
    resp = await client.get("/api/v1/runs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    listed = next(r for r in body["items"] if r["id"] == run_id)
    assert listed["pending_rows"] == 2
    assert listed["source_label"] == "Synthetic EPR"


@pytest.mark.anyio
async def test_a_correction_keeps_the_model_answer_beside_it(
    client: AsyncClient, run_id: str
):
    """The pair (what the model said, what the right answer was) is the asset."""
    detail = (await client.get(f"/api/v1/runs/{run_id}")).json()
    row = detail["rows"][0]

    resp = await client.patch(
        f"/api/v1/runs/{run_id}/rows/{row['id']}",
        json={"values": {"Diagnosis": "Hospital acquired pneumonia"}},
    )
    assert resp.status_code == 200
    edited = resp.json()

    assert edited["data"]["Diagnosis"] == "Hospital acquired pneumonia"
    assert edited["ai_data"]["Diagnosis"] == "Community acquired pneumonia"
    assert edited["corrected_columns"] == ["Diagnosis"]
    assert edited["edited_by"] == "Dev User"

    # A correction moves the run out of draft: work has started on it.
    assert (await client.get(f"/api/v1/runs/{run_id}")).json()["status"] == "in_review"

    async with app_database.session_factory()() as session:
        revisions = await session.scalar(
            select(func.count())
            .select_from(ExtractionRowRevision)
            .where(ExtractionRowRevision.row_id == row["id"])
        )
    assert revisions == 1
    assert "row.edited" in await _audit_actions(run_id)


@pytest.mark.anyio
async def test_provenance_cannot_be_edited(client: AsyncClient, run_id: str):
    """Which note a row came from is a fact about the extraction, not a value."""
    row = (await client.get(f"/api/v1/runs/{run_id}")).json()["rows"][0]
    resp = await client.patch(
        f"/api/v1/runs/{run_id}/rows/{row['id']}",
        json={"values": {NOTE_COL: "NOTE-9999"}},
    )
    assert resp.status_code == 400
    assert "provenance" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_unknown_columns_are_refused(client: AsyncClient, run_id: str):
    row = (await client.get(f"/api/v1/runs/{run_id}")).json()["rows"][0]
    resp = await client.patch(
        f"/api/v1/runs/{run_id}/rows/{row['id']}",
        json={"values": {"Invented": "x"}},
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_a_correction_can_be_reverted(client: AsyncClient, run_id: str):
    row = (await client.get(f"/api/v1/runs/{run_id}")).json()["rows"][0]
    await client.patch(
        f"/api/v1/runs/{run_id}/rows/{row['id']}", json={"values": {"Diagnosis": "wrong"}}
    )

    resp = await client.post(
        f"/api/v1/runs/{run_id}/rows/{row['id']}/revert", json={"column": "Diagnosis"}
    )
    assert resp.status_code == 200
    reverted = resp.json()
    assert reverted["data"]["Diagnosis"] == "Community acquired pneumonia"
    assert reverted["corrected_columns"] == []


@pytest.mark.anyio
async def test_export_of_approved_rows_refuses_while_none_are(
    client: AsyncClient, run_id: str
):
    """The gate that makes approval mean something."""
    resp = await client.get(f"/api/v1/export/runs/{run_id}/csv?scope=approved")
    assert resp.status_code == 409
    assert "approve" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_a_draft_export_is_labelled_as_one(client: AsyncClient, run_id: str):
    """Draft data may leave — but never disguised as reviewed data."""
    resp = await client.get(f"/api/v1/export/runs/{run_id}/csv?scope=all")
    assert resp.status_code == 200
    assert "DRAFT" in resp.headers["content-disposition"]

    body = resp.content.decode("utf-8-sig")
    header, first_row = body.splitlines()[0], body.splitlines()[1]
    assert "Review status" in header
    assert "pending" in first_row
    assert "export.csv" in await _audit_actions(run_id)


@pytest.mark.anyio
async def test_sign_off_will_not_skip_undecided_rows_silently(
    client: AsyncClient, run_id: str
):
    resp = await client.post(
        f"/api/v1/runs/{run_id}/approve", json={"approve_pending": False}
    )
    assert resp.status_code == 409
    assert "2 rows still need a decision" in resp.json()["detail"]


@pytest.mark.anyio
async def test_sign_off_then_export_and_lock(client: AsyncClient, run_id: str):
    rows = (await client.get(f"/api/v1/runs/{run_id}")).json()["rows"]

    decided = await client.patch(
        f"/api/v1/runs/{run_id}/rows/{rows[0]['id']}/status",
        json={"status": "approved", "note": "checked against the note"},
    )
    assert decided.status_code == 200
    assert decided.json()["decided_by"] == "Dev User"

    approved = await client.post(
        f"/api/v1/runs/{run_id}/approve",
        json={"approve_pending": True, "note": "Reviewed 2/2"},
    )
    assert approved.status_code == 200
    detail = approved.json()
    assert detail["status"] == "approved"
    assert detail["approved_rows"] == 2
    assert detail["approved_by"] == "Dev User"

    # Approved data exports clean: no draft marker, no status column.
    export = await client.get(f"/api/v1/export/runs/{run_id}/csv?scope=approved")
    assert export.status_code == 200
    assert "approved" in export.headers["content-disposition"]
    assert "DRAFT" not in export.headers["content-disposition"]
    assert "Review status" not in export.content.decode("utf-8-sig").splitlines()[0]

    # And is read-only until someone reopens it, on the record.
    edit = await client.patch(
        f"/api/v1/runs/{run_id}/rows/{rows[0]['id']}",
        json={"values": {"Diagnosis": "changed after sign-off"}},
    )
    assert edit.status_code == 409

    assert (await client.delete(f"/api/v1/runs/{run_id}")).status_code == 409

    reopened = await client.post(f"/api/v1/runs/{run_id}/reopen", json={"note": "typo"})
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "in_review"

    actions = await _audit_actions(run_id)
    assert {"run.created", "run.approved", "run.reopened"} <= set(actions)


@pytest.mark.anyio
async def test_an_approved_row_is_read_only_until_reopened(
    client: AsyncClient, run_id: str
):
    row = (await client.get(f"/api/v1/runs/{run_id}")).json()["rows"][0]
    await client.patch(
        f"/api/v1/runs/{run_id}/rows/{row['id']}/status", json={"status": "approved"}
    )

    blocked = await client.patch(
        f"/api/v1/runs/{run_id}/rows/{row['id']}", json={"values": {"Diagnosis": "x"}}
    )
    assert blocked.status_code == 409

    await client.patch(
        f"/api/v1/runs/{run_id}/rows/{row['id']}/status", json={"status": "pending"}
    )
    allowed = await client.patch(
        f"/api/v1/runs/{run_id}/rows/{row['id']}", json={"values": {"Diagnosis": "x"}}
    )
    assert allowed.status_code == 200


@pytest.mark.anyio
async def test_a_draft_can_be_discarded(client: AsyncClient, run_id: str):
    assert (await client.delete(f"/api/v1/runs/{run_id}")).status_code == 204
    assert (await client.get(f"/api/v1/runs/{run_id}")).status_code == 404


@pytest.mark.anyio
async def test_a_reader_may_look_but_not_approve(run_id: str):
    """Reading a run is not a clinical act; signing one off is."""
    app.dependency_overrides[get_current_user] = lambda: UserClaims(
        sub="reader-1", name="Demo Auditor", email="audit@example.nhs.uk",
        roles=[Role.READONLY],
    )
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as reader:
            assert (await reader.get(f"/api/v1/runs/{run_id}")).status_code == 200
            assert (
                await reader.post(f"/api/v1/runs/{run_id}/approve", json={})
            ).status_code == 403
            row = (await reader.get(f"/api/v1/runs/{run_id}")).json()["rows"][0]
            assert (
                await reader.patch(
                    f"/api/v1/runs/{run_id}/rows/{row['id']}",
                    json={"values": {"Diagnosis": "x"}},
                )
            ).status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.anyio
async def test_four_eyes_blocks_signing_off_your_own_run(
    client: AsyncClient, run_id: str, monkeypatch: pytest.MonkeyPatch
):
    """The rule a governed deployment turns on, and the demo does not."""
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "require_separate_approver", True, raising=False)

    resp = await client.post(f"/api/v1/runs/{run_id}/approve", json={})
    assert resp.status_code == 403
    assert "second reviewer" in resp.json()["detail"]


@pytest.mark.anyio
async def test_stats_report_outstanding_review_work(client: AsyncClient, run_id: str):
    resp = await client.get("/api/v1/runs/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["awaiting_review"] >= 1
    assert stats["pending_rows"] >= 2


@pytest.mark.anyio
async def test_multi_value_columns_export_as_readable_cells(
    client: AsyncClient, run_id: str
):
    """A list has to arrive as a cell someone can read, not as a Python repr."""
    resp = await client.get(f"/api/v1/export/runs/{run_id}/csv?scope=all")
    body = resp.content.decode("utf-8-sig")
    assert "Amoxicillin 500mg TDS" in body
    assert "['" not in body

    # And Excel at all: openpyxl refuses a list outright, so this path used to
    # fail for every schema with a text[] column in it.
    xlsx = await client.get(f"/api/v1/export/runs/{run_id}/excel?scope=all")
    assert xlsx.status_code == 200
    assert len(xlsx.content) > 0


@pytest.mark.anyio
async def test_awaiting_review_is_a_filter_the_server_understands(
    client: AsyncClient, run_id: str
):
    """Filtering one page in the client hid the oldest run still waiting."""
    resp = await client.get("/api/v1/runs?status=awaiting_review")
    assert resp.status_code == 200
    assert run_id in [r["id"] for r in resp.json()["items"]]

    await client.post(
        f"/api/v1/runs/{run_id}/approve", json={"approve_pending": True}
    )
    after = await client.get("/api/v1/runs?status=awaiting_review")
    assert run_id not in [r["id"] for r in after.json()["items"]]


@pytest.mark.anyio
async def test_a_signed_off_run_exported_whole_says_it_carries_rejected_rows(
    client: AsyncClient, run_id: str
):
    """Signed off is not the same as "every row in this file was kept"."""
    rows = (await client.get(f"/api/v1/runs/{run_id}")).json()["rows"]
    await client.patch(
        f"/api/v1/runs/{run_id}/rows/{rows[1]['id']}/status",
        json={"status": "rejected", "note": "hallucinated dose"},
    )
    await client.post(
        f"/api/v1/runs/{run_id}/approve", json={"approve_pending": True}
    )

    whole = await client.get(f"/api/v1/export/runs/{run_id}/csv?scope=all")
    assert whole.status_code == 200
    assert "including-rejected" in whole.headers["content-disposition"]
    body = whole.content.decode("utf-8-sig")
    assert "Review status" in body.splitlines()[0]
    assert "rejected" in body

    clean = await client.get(f"/api/v1/export/runs/{run_id}/csv?scope=approved")
    assert "approved" in clean.headers["content-disposition"]
    assert "Review status" not in clean.content.decode("utf-8-sig").splitlines()[0]
