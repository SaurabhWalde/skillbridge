"""
AUTH ENDPOINTS
──────────────
POST /auth/signup              → Register new user → standard JWT
POST /auth/login               → Login → standard JWT (24hr)
POST /auth/monitoring-token    → MO's standard JWT + API key → scoped token (1hr)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from src.database import get_db
from src.models import User, UserRole
from src.schemas import (
    SignupRequest, LoginRequest, MonitoringTokenRequest,
    TokenResponse, MonitoringTokenResponse
)
from src.auth import (
    hash_password, verify_password, create_access_token,
    create_monitoring_token, get_current_user
)
from src.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(request: SignupRequest, db: DBSession = Depends(get_db)):
    """
    Register a new user.
    - Validates email uniqueness
    - Hashes password with bcrypt
    - Returns a standard JWT (24hr)
    """
    # Check if institution_id references a valid institution user
    if request.institution_id is not None:
        inst = db.query(User).filter(
            User.id == request.institution_id,
            User.role == UserRole.institution
        ).first()
        if not inst:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Institution with id {request.institution_id} not found"
            )

    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    new_user = User(
        name=request.name,
        email=request.email,
        hashed_password=hash_password(request.password),
        role=request.role,
        institution_id=request.institution_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({
        "user_id": new_user.id,
        "role": new_user.role.value,
        "token_type": "standard"
    })

    return TokenResponse(
        access_token=token,
        role=new_user.role.value,
        user_id=new_user.id
    )


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: DBSession = Depends(get_db)):
    """
    Validate credentials → return standard JWT.
    Token payload: { user_id, role, token_type: "standard", iat, exp }
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token({
        "user_id": user.id,
        "role": user.role.value,
        "token_type": "standard"
    })

    return TokenResponse(
        access_token=token,
        role=user.role.value,
        user_id=user.id
    )


@router.post("/monitoring-token", response_model=MonitoringTokenResponse)
def get_monitoring_token(
    request: MonitoringTokenRequest,
    current_user: User = Depends(get_current_user)
):
    """
    DUAL TOKEN FLOW for Monitoring Officer:
    
    Step 1: MO logs in via /auth/login → gets standard JWT
    Step 2: MO calls this endpoint with:
        - Standard JWT in Authorization header (automatically extracted)
        - {"key": "<api_key>"} in request body
    Step 3: If both are valid → returns a SHORT-LIVED scoped token (1hr)
    
    The scoped token is the ONLY token accepted by GET /monitoring/attendance.
    """
    # Verify the user is a monitoring officer
    if current_user.role != UserRole.monitoring_officer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only monitoring officers can request a monitoring token"
        )

    # Verify the API key
    if request.key != settings.MONITORING_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid monitoring API key"
        )

    # Issue scoped short-lived token
    scoped_token = create_monitoring_token(current_user.id)

    return MonitoringTokenResponse(
        access_token=scoped_token,
        expires_in_minutes=settings.MONITORING_TOKEN_EXPIRE_MINUTES,
        scope="monitoring:read"
    )