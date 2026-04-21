"""
ATTENDANCE ENDPOINT
───────────────────
POST /attendance/mark → Student self-marks attendance
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from src.database import get_db
from src.models import (
    User, Session as SessionModel,
    Attendance, BatchStudent
)
from src.schemas import AttendanceMark, AttendanceResponse
from src.auth import require_role

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("/mark", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
def mark_attendance(
    request: AttendanceMark,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(require_role("student"))
):
    """
    Student self-marks attendance for an active session.
    - 404 if session doesn't exist
    - 403 if student is not enrolled in the session's batch
    - 400 if attendance already marked
    """
    session = db.query(SessionModel).filter(SessionModel.id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {request.session_id} not found")

    # Check student is enrolled in this session's batch
    is_enrolled = db.query(BatchStudent).filter(
        BatchStudent.batch_id == session.batch_id,
        BatchStudent.student_id == current_user.id
    ).first()
    if not is_enrolled:
        raise HTTPException(
            status_code=403,
            detail="You are not enrolled in this session's batch"
        )

    # Check duplicate
    existing = db.query(Attendance).filter(
        Attendance.session_id == request.session_id,
        Attendance.student_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Attendance already marked for this session")

    attendance = Attendance(
        session_id=request.session_id,
        student_id=current_user.id,
        status=request.status
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)

    return attendance