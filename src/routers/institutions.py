"""
INSTITUTION ENDPOINTS
─────────────────────
GET /institutions/{id}/summary → Programme Manager views institution-level summary
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from src.database import get_db
from src.models import (
    User, Batch, BatchTrainer, BatchStudent,
    Session as SessionModel, Attendance, AttendanceStatus, UserRole
)
from src.schemas import InstitutionSummary, BatchSummary
from src.auth import require_role

router = APIRouter(prefix="/institutions", tags=["Institutions"])


@router.get("/{institution_id}/summary", response_model=InstitutionSummary)
def get_institution_summary(
    institution_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(require_role("programme_manager", "institution"))
):
    """
    Attendance summary across all batches in an institution.
    Programme Manager or the Institution itself can access this.
    """
    # Verify institution exists and has the correct role
    institution = db.query(User).filter(
        User.id == institution_id,
        User.role == UserRole.institution
    ).first()
    if not institution:
        raise HTTPException(status_code=404, detail=f"Institution {institution_id} not found")

    # If current user is an institution, they can only see their own summary
    if current_user.role.value == "institution" and current_user.id != institution_id:
        raise HTTPException(status_code=403, detail="You can only view your own institution summary")

    # Get all batches for this institution
    batches = db.query(Batch).filter(Batch.institution_id == institution_id).all()

    batch_summaries = []
    total_trainers_set = set()
    total_students_set = set()
    total_sessions_count = 0
    total_present = 0
    total_possible = 0

    for batch in batches:
        # Students in this batch
        batch_students = db.query(BatchStudent).filter(BatchStudent.batch_id == batch.id).all()
        student_count = len(batch_students)
        for bs in batch_students:
            total_students_set.add(bs.student_id)

        # Trainers in this batch
        batch_trainers = db.query(BatchTrainer).filter(BatchTrainer.batch_id == batch.id).all()
        trainer_names = []
        for bt in batch_trainers:
            total_trainers_set.add(bt.trainer_id)
            trainer = db.query(User).filter(User.id == bt.trainer_id).first()
            if trainer:
                trainer_names.append(trainer.name)

        # Sessions in this batch
        sessions = db.query(SessionModel).filter(SessionModel.batch_id == batch.id).all()
        session_count = len(sessions)
        total_sessions_count += session_count

        # Attendance for this batch
        batch_present = 0
        batch_possible = student_count * session_count
        if batch_possible > 0:
            batch_present = db.query(Attendance).join(SessionModel).filter(
                SessionModel.batch_id == batch.id,
                Attendance.status == AttendanceStatus.present
            ).count()
            total_present += batch_present
            total_possible += batch_possible

        avg_att = round((batch_present / batch_possible) * 100, 2) if batch_possible > 0 else 0.0

        batch_summaries.append(BatchSummary(
            batch_id=batch.id,
            batch_name=batch.name,
            institution_id=batch.institution_id,
            total_students=student_count,
            total_sessions=session_count,
            average_attendance_percent=avg_att,
            trainers=trainer_names
        ))

    overall_att = round((total_present / total_possible) * 100, 2) if total_possible > 0 else 0.0

    return InstitutionSummary(
        institution_id=institution.id,
        institution_name=institution.name,
        total_batches=len(batches),
        total_trainers=len(total_trainers_set),
        total_students=len(total_students_set),
        total_sessions=total_sessions_count,
        overall_attendance_percent=overall_att,
        batches=batch_summaries
    )