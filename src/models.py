"""
DATABASE MODELS — 7 tables
──────────────────────────
Matches the assignment schema EXACTLY:
- users:          id, name, email, hashed_password, role, institution_id, created_at
- batches:        id, name, institution_id, created_at
- batch_trainers: batch_id, trainer_id
- batch_students: batch_id, student_id
- batch_invites:  id, batch_id, token, created_by, expires_at, used
- sessions:       id, batch_id, trainer_id, title, date, start_time, end_time, created_at
- attendance:     id, session_id, student_id, status, marked_at
"""

from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey,
    Enum, Boolean, Date, Time, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from src.database import Base


# ──────────── HELPER FUNCTION ────────────
# ✅ FIX 1: Define utc_now BEFORE using it in models

def utc_now():
    """Returns current UTC time — used as default for DateTime columns."""
    return datetime.now(timezone.utc)


# ──────────── ENUMS ────────────

class UserRole(str, enum.Enum):
    student = "student"
    trainer = "trainer"
    institution = "institution"
    programme_manager = "programme_manager"
    monitoring_officer = "monitoring_officer"


class AttendanceStatus(str, enum.Enum):
    present = "present"
    absent = "absent"
    late = "late"


# ──────────── TABLE 1: USERS ────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    institution_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now)    # ✅ FIX 2: ccreated_at → created_at

    # Self-referential: institution user can have trainers/students under it
    institution = relationship("User", remote_side=[id], backref="members")
    trained_batches = relationship("BatchTrainer", back_populates="trainer")
    enrolled_batches = relationship("BatchStudent", back_populates="student")
    attendances = relationship("Attendance", back_populates="student")

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', role='{self.role.value}')>"


# ──────────── TABLE 2: BATCHES ────────────

class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    institution_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    institution = relationship("User", foreign_keys=[institution_id])
    trainers = relationship("BatchTrainer", back_populates="batch", cascade="all, delete-orphan")
    students = relationship("BatchStudent", back_populates="batch", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="batch", cascade="all, delete-orphan")
    invites = relationship("BatchInvite", back_populates="batch", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Batch(id={self.id}, name='{self.name}')>"


# ──────────── TABLE 3: BATCH_TRAINERS ────────────

class BatchTrainer(Base):
    __tablename__ = "batch_trainers"

    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), primary_key=True)
    trainer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    batch = relationship("Batch", back_populates="trainers")
    trainer = relationship("User", back_populates="trained_batches")


# ──────────── TABLE 4: BATCH_STUDENTS ────────────

class BatchStudent(Base):
    __tablename__ = "batch_students"

    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), primary_key=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    batch = relationship("Batch", back_populates="students")
    student = relationship("User", back_populates="enrolled_batches")


# ──────────── TABLE 5: BATCH_INVITES ────────────

class BatchInvite(Base):
    __tablename__ = "batch_invites"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)

    batch = relationship("Batch", back_populates="invites")
    creator = relationship("User", foreign_keys=[created_by])


# ──────────── TABLE 6: SESSIONS ────────────

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    trainer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    batch = relationship("Batch", back_populates="sessions")
    trainer = relationship("User", foreign_keys=[trainer_id])
    attendances = relationship("Attendance", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session(id={self.id}, title='{self.title}')>"


# ──────────── TABLE 7: ATTENDANCE ────────────

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(AttendanceStatus), nullable=False, default=AttendanceStatus.present)
    marked_at = Column(DateTime, default=utc_now)    # ✅ FIX 3: datetime.datetime.utcnow → utc_now

    __table_args__ = (
        UniqueConstraint('session_id', 'student_id', name='uq_session_student'),
    )

    session = relationship("Session", back_populates="attendances")
    student = relationship("User", back_populates="attendances")

    def __repr__(self):
        return f"<Attendance(session={self.session_id}, student={self.student_id}, status='{self.status.value}')>"