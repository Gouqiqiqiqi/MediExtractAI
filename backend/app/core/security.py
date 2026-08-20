"""Authentication & authorization — demo mode, or OIDC token validation."""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import Settings, get_settings
from app.models.schemas import UserClaims

logger = logging.getLogger("mediextract.security")

_bearer_scheme = HTTPBearer(auto_error=False)

# Cached JWKS
_jwks_cache: dict[str, Any] = {}


class Role(StrEnum):
    ADMIN = "Admin"
    CLINICIAN = "Clinician"
    READONLY = "ReadOnly"


async def _get_signing_keys(authority: str) -> dict[str, Any]:
    """Fetch and cache OIDC signing keys from Azure AD."""
    if _jwks_cache:
        return _jwks_cache

    async with httpx.AsyncClient() as client:
        oidc_config = (
            await client.get(f"{authority}/v2.0/.well-known/openid-configuration")
        ).json()
        jwks_uri = oidc_config["jwks_uri"]
        jwks = (await client.get(jwks_uri)).json()

    for key in jwks.get("keys", []):
        _jwks_cache[key["kid"]] = key

    return _jwks_cache


async def validate_token(
    token: str,
    settings: Settings,
) -> dict[str, Any]:
    """Validate a JWT access token against Azure AD OIDC."""
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header",
        ) from e

    kid = unverified_header.get("kid")
    keys = await _get_signing_keys(settings.azure_authority)
    key = keys.get(kid)

    if key is None:
        # Refresh cache once and retry
        _jwks_cache.clear()
        keys = await _get_signing_keys(settings.azure_authority)
        key = keys.get(kid)
        if key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token signing key not found",
            )

    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.azure_client_id,
            issuer=f"{settings.azure_authority}/v2.0",
            options={"verify_at_hash": False},
        )
    except JWTError as e:
        logger.warning("Token validation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
        ) from e

    return payload


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> UserClaims:
    """Extract and validate the current user from the Authorization header.

    In demo mode (DEMO_MODE=true) authentication is disabled entirely and a
    demo user with full permissions is returned. Demo deployments must only
    ever contain synthetic data.
    """
    if settings.demo_mode:
        return UserClaims(
            sub="demo-user-001",
            name="Demo User",
            email="demo@example.com",
            roles=[Role.ADMIN],
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # In development mode, allow a bypass token for testing
    if settings.app_env == "development" and credentials.credentials == "dev-bypass":
        return UserClaims(
            sub="dev-user-001",
            name="Dev User",
            email="dev@example.com",
            roles=[Role.ADMIN],
        )

    payload = await validate_token(credentials.credentials, settings)

    return UserClaims(
        sub=payload.get("sub", ""),
        name=payload.get("name", ""),
        email=payload.get("preferred_username", payload.get("email", "")),
        roles=payload.get("roles", [Role.READONLY]),
    )


def require_role(*roles: Role):
    """Dependency that enforces the user has at least one of the given roles."""

    async def _check(user: UserClaims = Depends(get_current_user)) -> UserClaims:
        if not any(r in user.roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _check
