"""Auth endpoints — login redirect, token exchange, user info."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.models.schemas import UserClaims

router = APIRouter()


@router.get("/me", response_model=UserClaims)
async def get_me(user: UserClaims = Depends(get_current_user)):
    """Return the authenticated user's claims."""
    return user
