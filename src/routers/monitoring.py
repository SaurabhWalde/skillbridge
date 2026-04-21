"""
MONITORING ENDPOINTS
────────────────────
GET /monitoring/attendance → Read-only attendance data (scoped token required)
ALL other methods          → 405 Method Not Allowed
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session as DBSession
from typing import Optional, List
from datetime import date

from src.database import get_db
from src.models import (
    User, Session as SessionModel,
    Attendance, Batch
)
from src.schemas import MonitoringAttendanceRecord
from src.auth import get_monitoring_user

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/attendance", response_model=List[MonitoringAttendanceRecord])
def get_monitoring_attendance(
    batch_id: Optional[int] = Query(None),
    session_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_monitoring_user)
):
    """
    Read-only attendance data across the entire programme.
    Requires SCOPED monitoring token (not standard JWT).
    
    Obtain scoped token via: POST /auth/monitoring-token
    """
    query = db.query(Attendance).join(SessionModel)

    if batch_id:
        query = query.filter(SessionModel.batch_id == batch_id)
    if session_date:
        query = query.filter(SessionModel.date == session_date)

    records = query.offset(offset).limit(limit).all()

    result = []
    for record in records:
        session = db.query(SessionModel).filter(SessionModel.id == record.session_id).first()
        batch = db.query(Batch).filter(Batch.id == session.batch_id).first() if session else None
        student = db.query(User).filter(User.id == record.student_id).first()

        result.append(MonitoringAttendanceRecord(
            attendance_id=record.id,
            session_id=record.session_id,
            session_title=session.title if session else "Unknown",
            session_date=session.date if session else date.today(),
            batch_id=session.batch_id if session else 0,
            batch_name=batch.name if batch else "Unknown",
            student_id=record.student_id,
            student_name=student.name if student else "Unknown",
            status=record.status.value,
            marked_at=record.marked_at
        ))

    return result


# ──── Reject ALL non-GET methods with 405 ────

@router.api_route(
    "/attendance",
    methods=["POST", "PUT", "PATCH", "DELETE"],
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
    include_in_schema=True
)
def monitoring_method_not_allowed(request: Request):
    """Monitoring is read-only. Only GET is permitted."""
    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content={"detail": f"Method {request.method} not allowed. Monitoring endpoint is read-only (GET only)."}
    )