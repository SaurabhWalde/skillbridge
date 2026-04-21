"""
PYDANTIC SCHEMAS
────────────────
Request/response validation for every endpoint.
FastAPI auto-returns 422 with descriptive errors if validation fails.
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import date, time, datetime
from src.models import UserRole, AttendanceStatus


# ──────────── GENERIC ────────────

class MessageResponse(BaseModel):
    message: str
    batch_id: Optional[int] = None
    student_id: Optional[int] = None


# ──────────── AUTH ────────────

class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole
    institution_id: Optional[int] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MonitoringTokenRequest(BaseModel):
    """Monitoring Officer provides their valid JWT + API key to get scoped token"""
    key: str = Field(..., description="Monitoring API key")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int


class MonitoringTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int = 60
    scope: str = "monitoring:read"


# ──────────── BATCHES ────────────

class BatchCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    institution_id: int = Field(..., gt=0)


class BatchResponse(BaseModel):
    id: int
    name: str
    institution_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)    # ✅ FIXED


class InviteResponse(BaseModel):
    invite_token: str
    batch_id: int
    expires_at: datetime


class JoinBatchRequest(BaseModel):
    token: str = Field(..., description="Invite token received from trainer")


# ──────────── SESSIONS ────────────

class SessionCreate(BaseModel):
    batch_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=1, max_length=200)
    date: date
    start_time: time
    end_time: time


class SessionResponse(BaseModel):
    id: int
    batch_id: int
    trainer_id: int
    title: str
    date: date
    start_time: time
    end_time: time
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)    # ✅ FIXED


# ──────────── ATTENDANCE ────────────

class AttendanceMark(BaseModel):
    session_id: int = Field(..., gt=0)
    status: AttendanceStatus = AttendanceStatus.present


class AttendanceResponse(BaseModel):
    id: int
    session_id: int
    student_id: int
    status: AttendanceStatus
    marked_at: datetime

    model_config = ConfigDict(from_attributes=True)    # ✅ FIXED


class AttendanceDetail(BaseModel):
    student_id: int
    student_name: str
    status: str
    marked_at: Optional[datetime]


class SessionAttendanceResponse(BaseModel):
    session_id: int
    session_title: str
    total_students: int
    present_count: int
    absent_count: int
    late_count: int
    records: List[AttendanceDetail]


# ──────────── SUMMARIES ────────────

class BatchSummary(BaseModel):
    batch_id: int
    batch_name: str
    institution_id: int
    total_students: int
    total_sessions: int
    average_attendance_percent: float
    trainers: List[str]


class InstitutionSummary(BaseModel):
    institution_id: int
    institution_name: str
    total_batches: int
    total_trainers: int
    total_students: int
    total_sessions: int
    overall_attendance_percent: float
    batches: List[BatchSummary]


class ProgrammeSummary(BaseModel):
    total_institutions: int
    total_batches: int
    total_trainers: int
    total_students: int
    total_sessions: int
    overall_attendance_percent: float
    institutions: List[InstitutionSummary]


class MonitoringAttendanceRecord(BaseModel):
    attendance_id: int
    session_id: int
    session_title: str
    session_date: date
    batch_id: int
    batch_name: str
    student_id: int
    student_name: str
    status: str
    marked_at: Optional[datetime]