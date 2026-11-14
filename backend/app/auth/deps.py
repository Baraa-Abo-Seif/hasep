from typing import Optional
from fastapi import Depends, HTTPException, status, Header, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.core.security import decode_access_token

DEFAULT_DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_DEMO_EMAIL = "demo@arabic-excel-ai.local"


async def get_or_create_demo_user(db: AsyncSession) -> User:
    """Ensures a default system user exists for frictionless development & testing."""
    res = await db.execute(select(User).where(User.id == DEFAULT_DEMO_USER_ID))
    user = res.scalars().first()
    if not user:
        user = User(
            id=DEFAULT_DEMO_USER_ID,
            email=DEFAULT_DEMO_EMAIL,
            full_name="المستخدم التجريبي (Demo User)",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def get_current_user(
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract authenticated user from JWT token or fallback to demo user in dev."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    elif session_token:
        token = session_token
    if token:
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            user_id = payload["sub"]
            res = await db.execute(select(User).where(User.id == user_id))
            user = res.scalars().first()
            if user and user.is_active:
                return user
    from backend.app.core.config import settings
    if settings.APP_ENV == "development":
        return await get_or_create_demo_user(db)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="جلسة العمل غير صالحة أو منتهية. يرجى تسجيل الدخول مجدداً.",
        headers={"WWW-Authenticate": "Bearer"},
    )
