import base64
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from cryptography.fernet import Fernet
from jose import jwt, JWTError
from passlib.context import CryptContext
from backend.app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_cipher() -> Fernet:
    """Return Fernet cipher using configured 32-byte url-safe base64 key."""
    key = settings.ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode("utf-8")
    # If key is not valid 32 bytes base64, ensure proper padding/format
    try:
        return Fernet(key)
    except Exception:
        # Fallback to deterministic key derived from APP_SECRET_KEY
        import hashlib
        derived = base64.urlsafe_b64encode(hashlib.sha256(settings.APP_SECRET_KEY.encode()).digest())
        return Fernet(derived)


def encrypt_token(plain_token: str) -> str:
    """Encrypt a sensitive token string (e.g. OAuth access/refresh token)."""
    if not plain_token:
        return ""
    cipher = get_cipher()
    return cipher.encrypt(plain_token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt an encrypted token string."""
    if not encrypted_token:
        return ""
    cipher = get_cipher()
    return cipher.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate signed JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.APP_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and verify JWT token."""
    try:
        payload = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
