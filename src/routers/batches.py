"""
BATCH ENDPOINTS
───────────────
POST /batches              → Trainer / Institution creates a batch
POST /batches/{id}/invite  → Trainer generates invite token
POST /batches/join         → Student joins batch using invite token
GET  /batches/{id}/summary → Institution views batch summary
"""

import uuid
from datetime import datetime, timedelta
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from src.database import get_db
from src.config import settings
from src.models import (
    User, Batch, BatchTrainer, BatchStudent, BatchInvite,
    Session as SessionModel, Attendance, AttendanceStatus
)
from src.schemas import (
    BatchCreate, BatchResponse, InviteResponse,
    JoinBatchRequest, BatchSummary, MessageResponse
)
from src.auth import require_role

router = APIRouter(prefix="/batches", tags=["Batches"])


@router.post("/", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
def create_batch(
    request: BatchCreate,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(require_role("trainer", "institution"))
):
    """Trainer or Institution creates a batch."""
    # Verify institution_id references a valid institution
    inst = db.query(User).filter(
        User.id == request.institution_id,
        User.role == "institution"
    ).first()
    if not inst:
        raise HTTPException(status_code=404, detail=f"Institution {request.institution_id} not found")

    new_batch = Batch(
        name=request.name,
        institution_id=request.institution_id
    )
    db.add(new_batch)
    db.commit()
    db.refresh(new_batch)

    # If creator is a trainer, auto-assign them to this batch
    if current_user.role.value == "trainer":
        db.add(BatchTrainer(batch_id=new_batch.id, trainer_id=current_user.id))
        db.commit()

    return new_batch


@router.post("/{batch_id}/invite", response_model=InviteResponse)
def generate_invite(
    batch_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(require_role("trainer"))
):
    """Trainer generates a unique invite token for a batch. Token valid for 7 days."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Verify trainer is assigned to this batch
    is_trainer = db.query(BatchTrainer).filter(
        BatchTrainer.batch_id == batch_id,
        BatchTrainer.trainer_id == current_user.id
    ).first()
    if not is_trainer:
        raise HTTPException(status_code=403, detail="You are not a trainer of this batch")

    invite_token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.INVITE_EXPIRY_DAYS)

    invite = BatchInvite(
        batch_id=batch_id,
        token=invite_token,
        created_by=current_user.id,
        expires_at=expires_at
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    return InviteResponse(
        invite_token=invite.token,
        batch_id=invite.batch_id,
        expires_at=invite.expires_at
    )


@router.post("/join", response_model=MessageResponse)
def join_batch(
    request: JoinBatchRequest,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(require_role("student"))
):
    """Student uses invite token to join a batch."""
    invite = db.query(BatchInvite).filter(BatchInvite.token == request.token).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invalid invite token")

    if invite.used:
        raise HTTPException(status_code=400, detail="Invite token already used")

    if invite.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invite token has expired")

    # Check if already enrolled
    already = db.query(BatchStudent).filter(
        BatchStudent.batch_id == invite.batch_id,
        BatchStudent.student_id == current_user.id
    ).first()
    if already:
        raise HTTPException(status_code=400, detail="Already enrolled in this batch")

    db.add(BatchStudent(batch_id=invite.batch_id, student_id=current_user.id))
    invite.used = True
    db.commit()

    return MessageResponse(
        message="Successfully joined batch",
        batch_id=invite.batch_id,
        student_id=current_user.id
    )


@router.get("/{batch_id}/summary", response_model=BatchSummary)
def get_batch_summary(
    batch_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(require_role("institution", "programme_manager", "trainer"))
):
    """Batch attendance summary — total students, sessions, avg attendance."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    total_students = db.query(BatchStudent).filter(BatchStudent.batch_id == batch_id).count()
    total_sessions = db.query(SessionModel).filter(SessionModel.batch_id == batch_id).count()

    avg_attendance = 0.0
    if total_sessions > 0 and total_students > 0:
        present_count = db.query(Attendance).join(SessionModel).filter(
            SessionModel.batch_id == batch_id,
            Attendance.status == AttendanceStatus.present
        ).count()
        total_possible = total_sessions * total_students
        avg_attendance = round((present_count / total_possible) * 100, 2) if total_possible > 0 else 0.0

    trainer_records = db.query(BatchTrainer).filter(BatchTrainer.batch_id == batch_id).all()
    trainer_names = []
    for bt in trainer_records:
        t = db.query(User).filter(User.id == bt.trainer_id).first()
        if t:
            trainer_names.append(t.name)

    return BatchSummary(
        batch_id=batch.id,
        batch_name=batch.name,
        institution_id=batch.institution_id,
        total_students=total_students,
        total_sessions=total_sessions,
        average_attendance_percent=avg_attendance,
        trainers=trainer_names
    )