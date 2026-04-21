"""
AUTHENTICATION
──────────────
Two token types:

1. STANDARD JWT (24hr expiry):
   Payload: { "user_id": int, "role": str, "token_type": "standard", "iat": ..., "exp": ... }

2. MONITORING SCOPED TOKEN (1hr expiry):
   Payload: { "user_id": int, "role": "monitoring_officer", "token_type": "monitoring",
              "scope": "monitoring:read", "iat": ..., "exp": ... }

Flow for Monitoring Officer:
   Step 1: POST /auth/login → get standard JWT (like everyone else)
   Step 2: POST /auth/monitoring-token with standard JWT in header + {"key": "api_key"} in body
           → get short-lived scoped monitoring token
   Step 3: GET /monitoring/attendance with scoped token in header
"""

from datetime import datetime, timedelta
from typing import Optional
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session as DBSession

from src.config import settings
from src.database import get_db
from src.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token.
    data should contain: user_id, role, token_type
    Automatically adds: iat (issued at), exp (expiry)
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"iat": now, "exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_monitoring_token(user_id: int) -> str:
    """
    Create a SHORT-LIVED scoped token specifically for monitoring endpoints.
    1 hour expiry, scope=monitoring:read, token_type=monitoring.
    """
    data = {
        "user_id": user_id,
        "role": "monitoring_officer",
        "token_type": "monitoring",
        "scope": "monitoring:read"
    }
    return create_access_token(
        data,
        expires_delta=timedelta(minutes=settings.MONITORING_TOKEN_EXPIRE_MINUTES)
    )


def decode_token(token: str) -> dict:
    """Decode and return JWT payload. Raises JWTError if invalid/expired."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: DBSession = Depends(get_db)
) -> User:
    """
    Extract user from standard JWT.
    Used by all endpoints EXCEPT /monitoring/attendance.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


def get_monitoring_user(
    token: str = Depends(oauth2_scheme),
    db: DBSession = Depends(get_db)
) -> User:
    """
    Validate the SCOPED monitoring token (not standard JWT).
    Checks:
    1. Token is valid and not expired
    2. token_type == "monitoring"
    3. role == "monitoring_officer"
    4. User exists in DB
    """
    auth_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired monitoring token. Use POST /auth/monitoring-token to get one.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id = payload.get("user_id")
        token_type = payload.get("token_type")
        role = payload.get("role")

        # Must be a scoped monitoring token, not a standard JWT
        if token_type != "monitoring":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="This endpoint requires a scoped monitoring token, not a standard JWT. "
                       "Use POST /auth/monitoring-token to obtain one."
            )
        if role != "monitoring_officer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only monitoring officers can access this endpoint."
            )
        if user_id is None:
            raise auth_exception
    except JWTError:
        raise auth_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise auth_exception
    return user


def require_role(*allowed_roles):
    """
    Role-based access control factory.
    Returns a dependency that checks if current user's role is in allowed_roles.
    403 if not.
    """
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role.value not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(allowed_roles)}. "
                       f"Your role: {current_user.role.value}"
            )
        return current_user
    return role_checker