"""
TEST FIXTURES
─────────────
Shared across all test files. pytest auto-discovers conftest.py.
"""

import os
import sys
import uuid
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app
from src.database import SessionLocal


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient — no real server needed."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def db_session():
    """Real DB session for tests that must hit database."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def unique_id():
    """Unique suffix to prevent email collisions between test runs."""
    return uuid.uuid4().hex[:8]


@pytest.fixture(scope="session")
def test_student_data(unique_id):
    return {
        "name": f"Test Student {unique_id}",
        "email": f"teststudent_{unique_id}@test.com",
        "password": "testpass123",
        "role": "student"
    }


@pytest.fixture(scope="session")
def test_trainer_data(unique_id):
    return {
        "name": f"Test Trainer {unique_id}",
        "email": f"testtrainer_{unique_id}@test.com",
        "password": "testpass123",
        "role": "trainer"
    }


@pytest.fixture(scope="session")
def test_institution_data(unique_id):
    return {
        "name": f"Test Institution {unique_id}",
        "email": f"testinst_{unique_id}@test.com",
        "password": "testpass123",
        "role": "institution"
    }


@pytest.fixture(scope="session")
def institution_id(client, test_institution_data):
    """Create a test institution and return its user ID. HITS REAL DB."""
    resp = client.post("/auth/signup", json=test_institution_data)
    assert resp.status_code == 201, f"Institution signup failed: {resp.json()}"
    return resp.json()["user_id"]


@pytest.fixture(scope="session")
def student_token(client, test_student_data, institution_id):
    """Register test student → return JWT. HITS REAL DB."""
    data = {**test_student_data, "institution_id": institution_id}
    resp = client.post("/auth/signup", json=data)
    assert resp.status_code == 201, f"Student signup failed: {resp.json()}"
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def trainer_token(client, test_trainer_data, institution_id):
    """Register test trainer → return JWT. HITS REAL DB."""
    data = {**test_trainer_data, "institution_id": institution_id}
    resp = client.post("/auth/signup", json=data)
    assert resp.status_code == 201, f"Trainer signup failed: {resp.json()}"
    return resp.json()["access_token"]