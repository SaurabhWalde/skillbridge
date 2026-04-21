```markdown
# SkillBridge Attendance API

REST API for a state-level skilling programme attendance system with role-based access control and dual JWT authentication. Built with FastAPI + PostgreSQL (Neon) + JWT.

## 1. Live API Base URL

```
https://skillbridge-api.onrender.com
```

- Swagger Docs: https://skillbridge-api.onrender.com/docs
- Health Check: https://skillbridge-api.onrender.com/health
- Hosted on **Render** (free tier, cold start ~30s). Database on **Neon** (free PostgreSQL). No credentials in repo.

```bash
# Working curl against live deployment
curl -X POST https://skillbridge-api.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"trainer1@test.com","password":"password123"}'
```

## 2. Local Setup

Requires: Python 3.9+, pip

```bash
git clone https://github.com/SaurabhWalde/skillbridge.git
cd skillbridge
python -m venv venv
venv\Scripts\activate              # Windows
# source venv/bin/activate         # Mac/Linux
pip install -r requirements.txt
cp .env.example .env               # Edit .env with your Neon DB URL + secrets
python run.py seed                 # Seed database (23 users, 8 sessions, 40 attendance)
python run.py test                 # Run tests (6 passed, 0 warnings)
python run.py                      # Start server → http://localhost:8000/docs
```

Get a free Neon DB at [neon.tech](https://neon.tech) → Create Project → Connection Details → **Pooled connection** → paste into `.env`.

## 3. Test Accounts

All passwords: `password123`

| Role | Email | Access |
|------|-------|--------|
| Institution 1 | `institution1@test.com` | Batch summaries, create batches |
| Institution 2 | `institution2@test.com` | Batch summaries, create batches |
| Trainer 1 | `trainer1@test.com` | Sessions, invites (Batch A) |
| Trainer 2 | `trainer2@test.com` | Sessions, invites (Batch A, B) |
| Trainer 3 | `trainer3@test.com` | Sessions, invites (Batch C) |
| Trainer 4 | `trainer4@test.com` | Sessions, invites (Batch C) |
| Student 1-5 | `student1@test.com` … `student5@test.com` | Attendance (Batch A) |
| Student 6-10 | `student6@test.com` … `student10@test.com` | Attendance (Batch B) |
| Student 11-15 | `student11@test.com` … `student15@test.com` | Attendance (Batch C) |
| Programme Manager | `pm@test.com` | All summaries |
| Monitoring Officer | `monitor@test.com` | Read-only (dual token) |

**Monitoring API Key**: `monitor_secret_key_2024` (or check seed output for actual value)

## 4. Curl Commands for Every Endpoint

Replace `$TOKEN` with the `access_token` from login response.

```bash
# ── AUTH ──

# Signup
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"name":"New User","email":"new@test.com","password":"pass123","role":"student","institution_id":1}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"trainer1@test.com","password":"password123"}'

# Monitoring token (requires standard JWT in header + API key in body)
curl -X POST http://localhost:8000/auth/monitoring-token \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MO_STANDARD_JWT" \
  -d '{"key":"monitor_secret_key_2024"}'

# ── BATCHES ──

# Create batch (Trainer/Institution)
curl -X POST http://localhost:8000/batches/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"New Batch","institution_id":1}'

# Generate invite (Trainer)
curl -X POST http://localhost:8000/batches/1/invite \
  -H "Authorization: Bearer $TOKEN"

# Join batch (Student)
curl -X POST http://localhost:8000/batches/join \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -d '{"token":"invite-uuid-here"}'

# Batch summary (Institution/PM/Trainer)
curl -X GET http://localhost:8000/batches/1/summary \
  -H "Authorization: Bearer $TOKEN"

# ── SESSIONS ──

# Create session (Trainer)
curl -X POST http://localhost:8000/sessions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"batch_id":1,"title":"Python Basics","date":"2025-01-15","start_time":"09:00:00","end_time":"11:00:00"}'

# Session attendance (Trainer/Institution/PM)
curl -X GET http://localhost:8000/sessions/1/attendance \
  -H "Authorization: Bearer $TOKEN"

# ── ATTENDANCE ──

# Mark attendance (Student)
curl -X POST http://localhost:8000/attendance/mark \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -d '{"session_id":1,"status":"present"}'

# ── SUMMARIES ──

# Institution summary (PM/Institution)
curl -X GET http://localhost:8000/institutions/1/summary \
  -H "Authorization: Bearer $PM_TOKEN"

# Programme summary (PM only)
curl -X GET http://localhost:8000/programme/summary \
  -H "Authorization: Bearer $PM_TOKEN"

# ── MONITORING (dual token flow) ──

# Step 1: Login as MO → get standard JWT
# Step 2: POST /auth/monitoring-token with JWT + API key → get scoped token
# Step 3: Use scoped token below
curl -X GET "http://localhost:8000/monitoring/attendance?batch_id=1&limit=10" \
  -H "Authorization: Bearer $SCOPED_TOKEN"

# POST returns 405 (read-only)
curl -X POST http://localhost:8000/monitoring/attendance
```

## 5. Schema Decisions

**`batch_trainers`** — Composite PK `(batch_id, trainer_id)` instead of surrogate ID. A trainer can teach multiple batches and a batch can have co-trainers. Composite PK enforces uniqueness at DB level.

**`batch_invites`** — UUID4 tokens, single-use (`used` boolean), 7-day expiry. `created_by` FK tracks which trainer generated the invite for audit. Single-use prevents token sharing abuse.

**`users.institution_id`** — Self-referential FK. Institutions are users (they log in), trainers/students link to their institution. Nullable for PM and MO who don't belong to any institution.

**Dual-token for Monitoring Officer** — Standard login gives a 24hr JWT (like everyone). To access `/monitoring/attendance`, MO must exchange that JWT + API key for a short-lived 1hr scoped token. The monitoring endpoint rejects standard JWTs — only scoped tokens with `token_type: "monitoring"` are accepted. This provides defense-in-depth: stolen JWT alone cannot access sensitive data.

### JWT Payload Structures

**Standard JWT (24hr):**
```json
{"user_id": 1, "role": "trainer", "token_type": "standard", "iat": 1704067200, "exp": 1704153600}
```

**Monitoring Scoped Token (1hr):**
```json
{"user_id": 5, "role": "monitoring_officer", "token_type": "monitoring", "scope": "monitoring:read", "iat": 1704067200, "exp": 1704070800}
```

### Token Rotation/Revocation (Production)

Current tokens are stateless — cannot revoke individually. In production: store `token_version` per user in DB, include in JWT, reject mismatched versions. Use Redis blacklist with TTL for immediate revocation. Implement refresh tokens (7-day) + short access tokens (15-min) with `POST /auth/refresh` and `POST /auth/logout`.

### Known Security Issue

The monitoring API key is a single static string in env vars. If leaked, anyone with an MO account can generate scoped tokens indefinitely. **Fix**: Store hashed keys in DB with expiry, support key rotation, add rate limiting (5 req/hr) on `/auth/monitoring-token`, require MFA before issuing scoped tokens.

## 6. What's Working / Partial / Skipped

**✅ Fully Working:** Signup/login with JWT, RBAC on all endpoints (401/403), batch CRUD + invite/join, session creation, student self-marking attendance, duplicate attendance prevention, FK violations → 404 (not 500), validation → 422, session/batch/institution/programme summaries, dual-token monitoring system, 405 for non-GET on monitoring, seed script (23 users, 40 attendance), 6 passing tests (4 hit real DB), deployed on Render.

**⚠️ Partial:** Pagination on monitoring endpoint only (not all list endpoints).

**❌ Skipped:** Rate limiting, email verification, password reset, refresh token rotation, audit logging, WebSocket updates.

## 7. What I'd Do Differently

**Refresh token flow.** Currently the 24hr JWT can't be revoked. I'd implement: short-lived access tokens (15 min) + DB-stored refresh tokens (7 days) + `POST /auth/refresh` + `POST /auth/logout` + per-user `token_version` for password-change invalidation. Reduces exposure window from 24 hours to 15 minutes.

## Tests

```bash
pytest tests/test_api.py -v -s
```

| # | Test | Real DB | Verifies |
|---|------|---------|----------|
| 1 | Student signup + login | ✅ | Valid JWT returned with correct structure |
| 2 | Trainer creates session | ✅ | Batch + session with all required fields |
| 3 | Student marks attendance | ✅ | Full flow: batch → session → invite → join → mark |
| 4 | POST /monitoring/attendance | ❌ | Returns 405 Method Not Allowed |
| 5 | No token on protected endpoints | ❌ | All 8 endpoints return 401 |
| 6 | Wrong role | ✅ | Student blocked from trainer/PM endpoints (403) |

## Project Structure

```
skillbridge/
├── CONTACT.txt              # Contact info
├── README.md                # This file
├── requirements.txt         # Dependencies
├── .env.example             # Env var template
├── .gitignore               # .env excluded
├── Procfile                 # Render start command
├── pytest.ini               # Test config
├── run.py                   # CLI runner (server/seed/test)
├── src/
│   ├── config.py            # Centralized env vars
│   ├── database.py          # SQLAlchemy engine + session
│   ├── models.py            # 7 tables (users, batches, batch_trainers, batch_students, batch_invites, sessions, attendance)
│   ├── schemas.py           # Pydantic validation schemas
│   ├── auth.py              # JWT + bcrypt + RBAC
│   ├── main.py              # FastAPI app + router registration
│   ├── seed.py              # Test data seeder
│   └── routers/
│       ├── auth_router.py   # /auth/signup, /login, /monitoring-token
│       ├── batches.py       # /batches CRUD + invite + join + summary
│       ├── sessions.py      # /sessions create + attendance view
│       ├── attendance.py    # /attendance/mark
│       ├── institutions.py  # /institutions/{id}/summary
│       ├── programme.py     # /programme/summary
│       └── monitoring.py    # /monitoring/attendance (GET only)
└── tests/
    ├── conftest.py          # Shared fixtures
    └── test_api.py          # 6 tests (5 required + 1 bonus)
```

## Tech Stack

| Layer | Tool |
|-------|------|
| Framework | FastAPI |
| Database | PostgreSQL (Neon) |
| ORM | SQLAlchemy 2.0 |
| Auth | python-jose + bcrypt |
| Validation | Pydantic V2 |
| Testing | pytest + httpx |
| Deployment | Render |
```

This covers all 7 required sections from Task 5 + JWT docs + security analysis — concise and complete! 🚀