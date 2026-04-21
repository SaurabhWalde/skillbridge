"""
PROGRAMME ENDPOINTS
───────────────────
GET /programme/summary → Programme Manager views programme-wide summary
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from src.database import get_db
from src.models import (
    User, Batch, BatchTrainer, BatchStudent,
    Session as SessionModel, Attendance, AttendanceStatus, UserRole
)
from src.schemas import ProgrammeSummary, InstitutionSummary, BatchSummary
from src.auth import require_role

router = APIRouter(prefix="/programme", tags=["Programme"])


@router.get("/summary", response_model=ProgrammeSummary)
def get_programme_summary(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(require_role("programme_manager"))
):
    """
    Programme-wide summary across ALL institutions.
    Only Programme Manager can access this.
    Shows: total institutions, batches, trainers, students, sessions, attendance.
    """
    # Get all institution users
    institutions = db.query(User).filter(User.role == UserRole.institution).all()

    institution_summaries = []
    grand_total_batches = 0
    grand_trainers_set = set()
    grand_students_set = set()
    grand_total_sessions = 0
    grand_total_present = 0
    grand_total_possible = 0

    for inst in institutions:
        batches = db.query(Batch).filter(Batch.institution_id == inst.id).all()

        batch_summaries = []
        inst_trainers_set = set()
        inst_students_set = set()
        inst_sessions = 0
        inst_present = 0
        inst_possible = 0

        for batch in batches:
            # Students
            batch_students = db.query(BatchStudent).filter(BatchStudent.batch_id == batch.id).all()
            student_count = len(batch_students)
            for bs in batch_students:
                inst_students_set.add(bs.student_id)
                grand_students_set.add(bs.student_id)

            # Trainers
            batch_trainers = db.query(BatchTrainer).filter(BatchTrainer.batch_id == batch.id).all()
            trainer_names = []
            for bt in batch_trainers:
                inst_trainers_set.add(bt.trainer_id)
                grand_trainers_set.add(bt.trainer_id)
                trainer = db.query(User).filter(User.id == bt.trainer_id).first()
                if trainer:
                    trainer_names.append(trainer.name)

            # Sessions
            sessions = db.query(SessionModel).filter(SessionModel.batch_id == batch.id).all()
            session_count = len(sessions)
            inst_sessions += session_count

            # Attendance
            batch_possible = student_count * session_count
            batch_present = 0
            if batch_possible > 0:
                batch_present = db.query(Attendance).join(SessionModel).filter(
                    SessionModel.batch_id == batch.id,
                    Attendance.status == AttendanceStatus.present
                ).count()
                inst_present += batch_present
                inst_possible += batch_possible

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

        grand_total_batches += len(batches)
        grand_total_sessions += inst_sessions
        grand_total_present += inst_present
        grand_total_possible += inst_possible

        inst_att = round((inst_present / inst_possible) * 100, 2) if inst_possible > 0 else 0.0

        institution_summaries.append(InstitutionSummary(
            institution_id=inst.id,
            institution_name=inst.name,
            total_batches=len(batches),
            total_trainers=len(inst_trainers_set),
            total_students=len(inst_students_set),
            total_sessions=inst_sessions,
            overall_attendance_percent=inst_att,
            batches=batch_summaries
        ))

    grand_att = round((grand_total_present / grand_total_possible) * 100, 2) if grand_total_possible > 0 else 0.0

    return ProgrammeSummary(
        total_institutions=len(institutions),
        total_batches=grand_total_batches,
        total_trainers=len(grand_trainers_set),
        total_students=len(grand_students_set),
        total_sessions=grand_total_sessions,
        overall_attendance_percent=grand_att,
        institutions=institution_summaries
    )