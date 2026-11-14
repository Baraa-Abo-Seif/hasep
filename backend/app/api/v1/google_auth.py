"""
Google OAuth 2.0 API Endpoints for Project # hasep.
Provides routes for initiating Google OAuth, processing callback, checking connection status,
and disconnecting the Google account.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.models.google_connection import GoogleConnection
from backend.app.auth.deps import get_current_user
from backend.app.core.config import settings
from backend.app.core.security import encrypt_token
from backend.app.integrations.google.auth import GoogleAuthService
from backend.app.schemas.common import APIResponse

logger = logging.getLogger("arabic_excel_platform.google_auth_api")

router = APIRouter(prefix="/auth/google", tags=["Google Authentication"])


@router.get("/status", response_model=APIResponse[dict])
async def get_google_auth_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check Google account connection status for the current user."""
    auth_service = GoogleAuthService()
    is_configured = auth_service.is_configured()
    res = await db.execute(
        select(GoogleConnection).where(
            GoogleConnection.user_id == current_user.id,
            GoogleConnection.is_active == True,
        )
    )
    conn = res.scalars().first()
    conn_expiry = conn.expires_at if conn else None
    if conn_expiry and conn_expiry.tzinfo is None:
        conn_expiry = conn_expiry.replace(tzinfo=timezone.utc)
    conn_info = {
        "is_configured": is_configured,
        "is_connected": conn is not None,
        "email": conn.google_email if conn else None,
        "display_name": conn.display_name if conn else None,
        "expires_at": conn.expires_at.isoformat() if conn else None,
        "is_expired": (conn_expiry <= datetime.now(timezone.utc)) if conn_expiry else False,
        "granted_scopes": conn.granted_scopes if conn else None,
    }
    return APIResponse(
        success=True,
        data=conn_info,
    )


@router.get("/login")
async def google_login(
    current_user: User = Depends(get_current_user),
):
    """Initiate Google OAuth 2.0 authorization code flow."""
    auth_service = GoogleAuthService()
    if not auth_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth client secret file is not configured or missing on the server.",
        )

    auth_url, _ = auth_service.get_authorization_url(user_id=current_user.id)
    return {"authorization_url": auth_url}


@router.get("/callback")
async def google_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await _google_callback_impl(code, state, error, error_description, db)
exec('async def _google_callback_impl(\n    code: Optional[str] = Query(None),\n    state: Optional[str] = Query(None),\n    error: Optional[str] = Query(None),\n    error_description: Optional[str] = Query(None),\n    db: AsyncSession = Depends(get_db),\n):\n    """OAuth callback endpoint handling Google authorization response."""\n    if error:\n        logger.warning(f"Google OAuth denied or returned error: {error} - {error_description}")\n        error_url = f"{settings.GOOGLE_FRONTEND_REDIRECT}?google_error={error}"\n        return RedirectResponse(url=error_url)\n    if not code or not state:\n        raise HTTPException(\n            status_code=status.HTTP_400_BAD_REQUEST,\n            detail="Missing authorization code or state.",\n        )\n    auth_service = GoogleAuthService()\n    user_id = auth_service.verify_state(state)\n    if not user_id:\n        raise HTTPException(\n            status_code=status.HTTP_400_BAD_REQUEST,\n            detail="Invalid or expired OAuth state parameter (CSRF protection).",\n        )\n    res = await db.execute(select(User).where(User.id == user_id))\n    user = res.scalars().first()\n    if not user:\n        raise HTTPException(\n            status_code=status.HTTP_404_NOT_FOUND,\n            detail="User associated with OAuth session not found.",\n        )\n    try:\n        token_data = auth_service.exchange_code_for_tokens(code)\n    except Exception as e:\n        logger.error(f"Failed to exchange Google OAuth code: {e}")\n        raise HTTPException(\n            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,\n            detail=f"Failed to exchange Google OAuth code: {str(e)}",\n        )\n    existing_conn = await db.execute(\n        select(GoogleConnection).where(GoogleConnection.user_id == user.id)\n    )\n    conn = existing_conn.scalars().first()\n    enc_access = encrypt_token(token_data["access_token"])\n    enc_refresh = encrypt_token(token_data.get("refresh_token") or "")\n    if conn:\n        conn.google_account_id = token_data.get("account_id")\n        conn.google_email = token_data.get("email")\n        conn.display_name = token_data.get("display_name")\n        conn.encrypted_access_token = enc_access\n        if token_data.get("refresh_token"):\n            conn.encrypted_refresh_token = enc_refresh\n        conn.expires_at = token_data["expires_at"]\n        conn.granted_scopes = token_data["scopes"]\n        conn.is_active = True\n        conn.updated_at = datetime.now(timezone.utc)\n    else:\n        conn = GoogleConnection(\n            user_id=user.id,\n            google_account_id=token_data.get("account_id"),\n            google_email=token_data.get("email"),\n            display_name=token_data.get("display_name"),\n            encrypted_access_token=enc_access,\n            encrypted_refresh_token=enc_refresh,\n            expires_at=token_data["expires_at"],\n            granted_scopes=token_data["scopes"],\n            is_active=True,\n        )\n        db.add(conn)\n    await db.commit()\n    frontend_redirect = f"{settings.GOOGLE_FRONTEND_REDIRECT}?google=connected&email={token_data.get(\'email\', \'\')}"\n    return RedirectResponse(url=frontend_redirect)\n', globals())


@router.delete("/disconnect", response_model=APIResponse[bool])
async def disconnect_google(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect active Google account connection."""
    res = await db.execute(
        select(GoogleConnection).where(GoogleConnection.user_id == current_user.id)
    )
    conns = res.scalars().all()
    for c in conns:
        c.is_active = False
        c.encrypted_access_token = ""
        c.encrypted_refresh_token = ""
        c.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return APIResponse(success=True, message="تم فصل حساب Google بنجاح.", data=True)
