"""
SESSION ENDPOINTS
─────────────────
POST /sessions/                   → Trainer creates a session
GET  /sessions/{id}/attendance    → Trainer views full attendance list
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from src.database import get_db
from src.models import (
    User, Batch, BatchTrainer,
    Session as SessionModel,
    Attendance
)
from src.schemas import (
    SessionCreate, SessionResponse,
    SessionAttendanceResponse, AttendanceDetail
)
from src.auth import require_role

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    request: SessionCreate,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(require_role("trainer"))
):
    """Trainer creates a session for a batch they are assigned to."""
    batch = db.query(Batch).filter(Batch.id == request.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {request.batch_id} not found")

    is_trainer = db.query(BatchTrainer).filter(
        BatchTrainer.batch_id == request.batch_id,
        BatchTrainer.trainer_id == current_user.id
    ).first()
    if not is_trainer:
        raise HTTPException(status_code=403, detail="You are not assigned as trainer for this batch")

    new_session = SessionModel(
        batch_id=request.batch_id,
        trainer_id=current_user.id,
        title=request.title,
        date=request.date,
        start_time=request.start_time,
        end_time=request.end_time
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return new_session


@router.get("/{session_id}/attendance", response_model=SessionAttendanceResponse)
def get_session_attendance(
    session_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(require_role("trainer", "institution", "programme_manager"))
):
    """Full attendance list for a session."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    attendances = db.query(Attendance).filter(Attendance.session_id == session_id).all()

    records = []
    present = absent = late = 0

    for att in attendances:
        student = db.query(User).filter(User.id == att.student_id).first()
        records.append(AttendanceDetail(
            student_id=att.student_id,
            student_name=student.name if student else "Unknown",
            status=att.status.value,
            marked_at=att.marked_at
        ))
        if att.status.value == "present":
            present += 1
        elif att.status.value == "absent":
            absent += 1
        else:
            late += 1

    return SessionAttendanceResponse(
        session_id=session.id,
        session_title=session.title,
        total_students=len(records),
        present_count=present,
        absent_count=absent,
        late_count=late,
        records=records
    )