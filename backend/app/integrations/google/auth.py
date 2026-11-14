"""
Google OAuth 2.0 Service for Project # hasep.
Handles secure authorization flow, token acquisition, encryption/decryption,
and automatic token refreshes using official Google auth libraries.
"""

import os
import json
import time
import hmac
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.security import encrypt_token, decrypt_token
from backend.app.models.google_connection import GoogleConnection

logger = logging.getLogger("arabic_excel_platform.google_auth")


class GoogleAuthService:
    def __init__(self):
        self.client_secret_file = settings.GOOGLE_OAUTH_CLIENT_SECRET_FILE
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self.scopes = [s.strip() for s in settings.GOOGLE_SCOPES.split(" ") if s.strip()]

    def is_configured(self) -> bool:
        """Check if OAuth client secrets file is present and readable."""
        if not self.client_secret_file:
            return False
        if not os.path.exists(self.client_secret_file):
            return False
        try:
            with open(self.client_secret_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            client_type = "web" if "web" in data else ("installed" if "installed" in data else None)
            return client_type is not None and "client_id" in data[client_type]
        except Exception as e:
            logger.error(f"Error checking Google OAuth configuration: {e}")
            return False

    def generate_secure_state(self, user_id: str) -> str:
        """
        Generate a cryptographically signed, timestamped state parameter
        to prevent CSRF and securely bind the authorization request to the user.
        """
        timestamp = str(int(time.time()))
        nonce = os.urandom(16).hex()
        data = f"{user_id}:{timestamp}:{nonce}"
        sig = hmac.new(settings.APP_SECRET_KEY.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{data}:{sig}"

    def verify_state(self, state: str, max_age_seconds: int = 900) -> Optional[str]:
        """
        Verify signature and freshness of the state parameter.
        Returns user_id if valid, or None if invalid or expired.
        """
        if not state:
            return None
        parts = state.split(":")
        if len(parts) != 4:
            return None
        user_id, timestamp_str, nonce, signature = parts
        data = f"{user_id}:{timestamp_str}:{nonce}"
        expected_sig = hmac.new(settings.APP_SECRET_KEY.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            logger.warning("Google OAuth state signature mismatch (possible CSRF attack).")
            return None

        try:
            req_time = int(timestamp_str)
            if time.time() - req_time > max_age_seconds:
                logger.warning("Google OAuth state expired.")
                return None
        except ValueError:
            return None

        return user_id

    def get_authorization_url(self, user_id: str) -> Tuple[str, str]:
        """
        Create OAuth flow and generate Google authorization URL requesting offline access
        for refresh tokens and consent prompt.
        """
        if not self.is_configured():
            raise RuntimeError("Google OAuth Client Secret file is missing or invalid.")

        state = self.generate_secure_state(user_id)
        flow = self._create_flow()

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state,
        )
        return auth_url, state

    def exchange_code_for_tokens(self, code: str, code_verifier: Optional[str] = None) -> Dict[str, Any]:
        """Exchange an authorization code for credentials and profile information."""
        if not self.is_configured():
            raise RuntimeError("Google OAuth Client Secret file is missing or invalid.")

        fetch_kwargs = {"code": code}
        if code_verifier:
            fetch_kwargs["code_verifier"] = code_verifier
        flow = self._create_flow()
        flow.fetch_token(**fetch_kwargs)
        credentials = flow.credentials

        # Retrieve user email from ID token or userinfo API
        email, user_id, display_name = self._get_profile(credentials)

        expires_at = self._get_expiry(credentials)
        granted_scopes = " ".join(credentials.scopes) if credentials.scopes else settings.GOOGLE_SCOPES

        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_at": expires_at,
            "email": email or "unknown@gmail.com",
            "account_id": user_id,
            "display_name": display_name or email,
            "scopes": granted_scopes,
        }

    def _create_flow(self) -> Flow:
        return Flow.from_client_secrets_file(
            self.client_secret_file, scopes=self.scopes,
            redirect_uri=self.redirect_uri, autogenerate_code_verifier=False,
        )

    def _get_profile(self, credentials: Credentials) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        email = user_id = display_name = None
        id_info = getattr(credentials, "id_token", None)
        if isinstance(id_info, dict):
            email, user_id, display_name = id_info.get("email"), id_info.get("sub"), id_info.get("name")
        if email:
            return email, user_id, display_name
        try:
            import requests
            response = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"******"}, timeout=10,
            )
            if response.status_code == 200:
                info = response.json()
                return info.get("email"), info.get("id"), info.get("name")
        except Exception as exc:
            logger.warning(f"Could not retrieve Google profile info via userinfo: {exc}")
        return email, user_id, display_name

    @staticmethod
    def _get_expiry(credentials: Credentials) -> datetime:
        expires_at = credentials.expiry or (datetime.now(timezone.utc) + timedelta(seconds=3600))
        return expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)

    async def get_valid_credentials(self, db: AsyncSession, user_id: str) -> Optional[Credentials]:
        return await _GoogleAuthService_get_valid_credentials_impl(self, db, user_id)

exec('async def _GoogleAuthService_get_valid_credentials_impl(self, db: AsyncSession, user_id: str) -> Optional[Credentials]:\n    """\n    Retrieve and decrypt stored Google credentials for the user.\n    If access token has expired or is expiring soon, automatically refreshes it\n    and updates the encrypted token in the database.\n    """\n    res = await db.execute(\n        select(GoogleConnection).where(\n            GoogleConnection.user_id == user_id,\n            GoogleConnection.is_active == True,\n        )\n    )\n    conn = res.scalars().first()\n    if not conn:\n        return None\n    access_token = decrypt_token(conn.encrypted_access_token)\n    refresh_token = decrypt_token(conn.encrypted_refresh_token) if conn.encrypted_refresh_token else None\n    with open(self.client_secret_file, "r", encoding="utf-8") as f:\n        secret_data = json.load(f)\n    client_type = "web" if "web" in secret_data else "installed"\n    client_id = secret_data[client_type]["client_id"]\n    client_secret = secret_data[client_type]["client_secret"]\n    token_uri = secret_data[client_type].get("token_uri", "https://oauth2.googleapis.com/token")\n    creds = Credentials(\n        token=access_token,\n        refresh_token=refresh_token,\n        token_uri=token_uri,\n        client_id=client_id,\n        client_secret=client_secret,\n        scopes=conn.granted_scopes.split(" ") if conn.granted_scopes else self.scopes,\n    )\n    now = datetime.now(timezone.utc)\n    conn_expiry = conn.expires_at\n    if conn_expiry.tzinfo is None:\n        conn_expiry = conn_expiry.replace(tzinfo=timezone.utc)\n    is_expired = conn_expiry <= (now + timedelta(seconds=60))\n    if is_expired:\n        if not refresh_token:\n            logger.error(f"Google access token for user {user_id} expired and no refresh token available.")\n            conn.is_active = False\n            await db.commit()\n            return None\n        try:\n            logger.info(f"Refreshing Google access token for user {user_id}...")\n            creds.refresh(Request())\n            conn.encrypted_access_token = encrypt_token(creds.token)\n            new_expiry = creds.expiry or (datetime.now(timezone.utc) + timedelta(seconds=3600))\n            if new_expiry.tzinfo is None:\n                new_expiry = new_expiry.replace(tzinfo=timezone.utc)\n            conn.expires_at = new_expiry\n            conn.updated_at = datetime.now(timezone.utc)\n            await db.commit()\n            logger.info("Google access token refreshed and saved.")\n        except Exception as e:\n            logger.error(f"Failed to refresh Google token for user {user_id}: {e}")\n            if "invalid_grant" in str(e).lower():\n                conn.is_active = False\n                await db.commit()\n            return None\n    return creds\n', globals())
