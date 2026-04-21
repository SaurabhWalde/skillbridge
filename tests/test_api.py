"""
API TESTS — 5 required by assignment + 1 bonus
───────────────────────────────────────────────
1. Student signup+login → valid JWT returned        (REAL DB ✅)
2. Trainer creates session with all required fields  (REAL DB ✅)
3. Student marks own attendance                      (REAL DB ✅)
4. POST /monitoring/attendance → 405                 (no DB needed)
5. Protected endpoint without token → 401            (no DB needed)
6. BONUS: Role mismatch → 403                        (REAL DB ✅)

Run: pytest tests/test_api.py -v -s
"""

import uuid
from datetime import date


# ══════════════════════════════════════════════════
# TEST 1: Student signup and login → valid JWT
# REAL DB ✅
# ══════════════════════════════════════════════════

def test_student_signup_and_login_returns_jwt(client, institution_id):
    """
    Assignment requirement: 'Successful student signup and login,
    asserting a valid JWT is returned.'
    """
    uid = uuid.uuid4().hex[:8]
    student_data = {
        "name": f"Signup Login Test {uid}",
        "email": f"signlogin_{uid}@test.com",
        "password": "securepass123",
        "role": "student",
        "institution_id": institution_id
    }

    # ── SIGNUP ──
    signup_resp = client.post("/auth/signup", json=student_data)
    assert signup_resp.status_code == 201, f"Signup failed: {signup_resp.json()}"

    signup_data = signup_resp.json()
    assert "access_token" in signup_data, "Signup response must have access_token"
    assert signup_data["token_type"] == "bearer"
    assert signup_data["role"] == "student"
    assert isinstance(signup_data["user_id"], int)

    # JWT format: xxx.yyy.zzz
    token = signup_data["access_token"]
    assert token.count(".") == 2, "JWT must have 3 parts separated by dots"

    # ── LOGIN ──
    login_resp = client.post("/auth/login", json={
        "email": student_data["email"],
        "password": student_data["password"]
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.json()}"

    login_data = login_resp.json()
    assert "access_token" in login_data, "Login response must have access_token"
    assert login_data["role"] == "student"
    assert login_data["access_token"].count(".") == 2

    print(f"✅ TEST 1 PASSED: Student signup + login returned valid JWTs")


# ══════════════════════════════════════════════════
# TEST 2: Trainer creates session with all required fields
# REAL DB ✅
# ══════════════════════════════════════════════════

def test_trainer_creates_session(client, trainer_token, institution_id):
    """
    Assignment requirement: 'A trainer creating a session with
    all required fields.'
    """
    headers = {"Authorization": f"Bearer {trainer_token}"}

    # Step 1: Create a batch (trainer needs a batch first)
    batch_resp = client.post("/batches/", json={
        "name": "Session Test Batch",
        "institution_id": institution_id
    }, headers=headers)
    assert batch_resp.status_code == 201, f"Batch creation failed: {batch_resp.json()}"
    batch_id = batch_resp.json()["id"]

    # Step 2: Create a session with ALL required fields
    session_data = {
        "batch_id": batch_id,
        "title": "Test Session - Python Basics",
        "date": str(date.today()),
        "start_time": "09:00:00",
        "end_time": "11:00:00"
    }
    session_resp = client.post("/sessions/", json=session_data, headers=headers)

    assert session_resp.status_code == 201, f"Session creation failed: {session_resp.json()}"

    data = session_resp.json()
    assert data["batch_id"] == batch_id
    assert data["title"] == "Test Session - Python Basics"
    assert data["date"] == str(date.today())
    assert data["start_time"] == "09:00:00"
    assert data["end_time"] == "11:00:00"
    assert "id" in data
    assert "trainer_id" in data
    assert "created_at" in data

    print(f"✅ TEST 2 PASSED: Trainer created session id={data['id']} with all fields")


# ══════════════════════════════════════════════════
# TEST 3: Student marks own attendance
# REAL DB ✅
# ══════════════════════════════════════════════════

def test_student_marks_attendance(client, student_token, trainer_token, institution_id):
    """
    Assignment requirement: 'A student successfully marking their
    own attendance.'
    Full flow: batch → session → invite → join → mark attendance
    """
    trainer_h = {"Authorization": f"Bearer {trainer_token}"}
    student_h = {"Authorization": f"Bearer {student_token}"}

    # 1. Trainer creates batch
    batch_resp = client.post("/batches/", json={
        "name": "Attendance Flow Test Batch",
        "institution_id": institution_id
    }, headers=trainer_h)
    assert batch_resp.status_code == 201
    batch_id = batch_resp.json()["id"]

    # 2. Trainer creates session
    session_resp = client.post("/sessions/", json={
        "batch_id": batch_id,
        "title": "Attendance Test Session",
        "date": str(date.today()),
        "start_time": "10:00:00",
        "end_time": "12:00:00"
    }, headers=trainer_h)
    assert session_resp.status_code == 201
    session_id = session_resp.json()["id"]

    # 3. Trainer generates invite
    invite_resp = client.post(f"/batches/{batch_id}/invite", headers=trainer_h)
    assert invite_resp.status_code == 200
    invite_token = invite_resp.json()["invite_token"]

    # 4. Student joins batch
    join_resp = client.post("/batches/join", json={
        "token": invite_token
    }, headers=student_h)
    assert join_resp.status_code == 200, f"Join failed: {join_resp.json()}"

    # 5. Student marks attendance
    att_resp = client.post("/attendance/mark", json={
        "session_id": session_id,
        "status": "present"
    }, headers=student_h)

    assert att_resp.status_code == 201, f"Attendance marking failed: {att_resp.json()}"

    data = att_resp.json()
    assert data["session_id"] == session_id
    assert data["status"] == "present"
    assert "id" in data
    assert "student_id" in data
    assert "marked_at" in data

    print(f"✅ TEST 3 PASSED: Student marked attendance id={data['id']}")


# ══════════════════════════════════════════════════
# TEST 4: POST /monitoring/attendance → 405
# ══════════════════════════════════════════════════

def test_monitoring_post_returns_405(client):
    """
    Assignment requirement: 'A POST to /monitoring/attendance
    returning 405.'
    Monitoring is read-only.
    """
    resp = client.post("/monitoring/attendance")

    assert resp.status_code == 405, f"Expected 405, got {resp.status_code}: {resp.json()}"
    assert "detail" in resp.json()

    print(f"✅ TEST 4 PASSED: POST /monitoring/attendance returned 405")


# ══════════════════════════════════════════════════
# TEST 5: No token → 401 Unauthorized
# ══════════════════════════════════════════════════

def test_no_token_returns_401(client):
    """
    Assignment requirement: 'A request to a protected endpoint
    with no token returning 401.'
    """
    protected_endpoints = [
        ("POST", "/batches/", {}),
        ("POST", "/sessions/", {}),
        ("POST", "/attendance/mark", {}),
        ("GET", "/batches/1/summary", None),
        ("GET", "/sessions/1/attendance", None),
        ("GET", "/institutions/1/summary", None),
        ("GET", "/programme/summary", None),
        ("GET", "/monitoring/attendance", None),
    ]

    for method, url, body in protected_endpoints:
        if method == "POST":
            resp = client.post(url, json=body)
        else:
            resp = client.get(url)

        assert resp.status_code == 401, (
            f"Expected 401 for {method} {url} without token, "
            f"got {resp.status_code}: {resp.json()}"
        )

    print(f"✅ TEST 5 PASSED: All {len(protected_endpoints)} protected endpoints returned 401 without token")


# ══════════════════════════════════════════════════
# BONUS TEST 6: Wrong role → 403 Forbidden
# REAL DB ✅
# ══════════════════════════════════════════════════

def test_wrong_role_returns_403(client, student_token, institution_id):
    """
    Student tries to create a batch (trainer-only) → 403.
    Student tries to view programme summary (PM-only) → 403.
    """
    student_h = {"Authorization": f"Bearer {student_token}"}

    # Student cannot create batch
    resp = client.post("/batches/", json={
        "name": "Illegal Batch",
        "institution_id": institution_id
    }, headers=student_h)
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    # Student cannot view programme summary
    resp2 = client.get("/programme/summary", headers=student_h)
    assert resp2.status_code == 403, f"Expected 403, got {resp2.status_code}"

    print(f"✅ BONUS TEST 6 PASSED: Wrong role correctly returns 403")