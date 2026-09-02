"""Audit trail — who did what, to which run, when.

Deliberately not best-effort. An audit write happens in the same transaction as
the thing it records, so a failure to record an approval also fails the
approval. A trail with silent holes in it is worse than none, because people
trust it.

What never goes in here: note text, extracted values, patient identifiers. The
trail says *that* row 4 of run X was corrected and by whom; the values live in
the run itself, under the same access control.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AuditLog
from app.models.schemas import UserClaims

logger = logging.getLogger("mediextract.services.audit")


async def record(
    session: AsyncSession,
    user: UserClaims,
    action: str,
    resource: str = "",
    detail: str = "",
) -> None:
    """Append one entry. Flushed, not committed — the caller owns the transaction."""
    entry = AuditLog(
        user_sub=user.sub,
        user_email=user.email,
        action=action,
        resource=resource,
        detail=detail,
    )
    session.add(entry)
    await session.flush()
    logger.info("audit %s %s %s by %s", action, resource, detail, user.sub)
