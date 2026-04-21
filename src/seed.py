"""
SEED SCRIPT
───────────
Creates: 2 institutions, 4 trainers, 15 students, 1 PM, 1 MO,
         3 batches, 8 sessions, attendance records.

Run: python -m src.seed
"""

import sys
import os
import random
from datetime import date, time, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import engine, SessionLocal, Base
from src.models import (
    User, UserRole, Batch, BatchTrainer, BatchStudent,
    Session, Attendance, AttendanceStatus, BatchInvite
)
from src.auth import hash_password


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Clear existing data
        existing = db.query(User).count()
        if existing > 0:
            print("⚠️  Clearing existing data...")
            db.query(Attendance).delete()
            db.query(BatchInvite).delete()
            db.query(Session).delete()
            db.query(BatchStudent).delete()
            db.query(BatchTrainer).delete()
            db.query(Batch).delete()
            db.query(User).delete()
            db.commit()

        print("🌱 Seeding database...\n")
        pw = hash_password("password123")

        # ═══════════════════════════════════
        #  1. INSTITUTIONS (2)
        # ═══════════════════════════════════
        inst1 = User(
            name="National Skills Institute",
            email="institution1@test.com",
            hashed_password=pw,
            role=UserRole.institution
        )
        inst2 = User(
            name="Regional Training Centre",
            email="institution2@test.com",
            hashed_password=pw,
            role=UserRole.institution
        )
        db.add_all([inst1, inst2])
        db.commit()
        for u in [inst1, inst2]:
            db.refresh(u)
        print(f"  ✅ 2 institutions created (IDs: {inst1.id}, {inst2.id})")

        # ═══════════════════════════════════
        #  2. TRAINERS (4) — linked to institutions
        # ═══════════════════════════════════
        trainer_info = [
            ("Rahul Sharma", "trainer1@test.com", inst1.id),
            ("Priya Patel", "trainer2@test.com", inst1.id),
            ("Amit Kumar", "trainer3@test.com", inst2.id),
            ("Sneha Gupta", "trainer4@test.com", inst2.id),
        ]
        trainers = []
        for name, email, inst_id in trainer_info:
            t = User(
                name=name,
                email=email,
                hashed_password=pw,
                role=UserRole.trainer,
                institution_id=inst_id
            )
            db.add(t)
            trainers.append(t)
        db.commit()
        for t in trainers:
            db.refresh(t)
        print(f"  ✅ 4 trainers created")

        # ═══════════════════════════════════
        #  3. STUDENTS (15) — linked to institutions
        # ═══════════════════════════════════
        student_names = [
            "Aarav Singh", "Diya Sharma", "Vihaan Patel", "Ananya Gupta",
            "Arjun Kumar", "Isha Reddy", "Reyansh Joshi", "Kavya Nair",
            "Aditya Verma", "Saanvi Iyer", "Krishna Das", "Meera Kapoor",
            "Rohan Malhotra", "Tara Bose", "Siddharth Rao"
        ]
        students = []
        for i, name in enumerate(student_names, 1):
            # First 8 students under inst1, rest under inst2
            inst_id = inst1.id if i <= 8 else inst2.id
            s = User(
                name=name,
                email=f"student{i}@test.com",
                hashed_password=pw,
                role=UserRole.student,
                institution_id=inst_id
            )
            db.add(s)
            students.append(s)
        db.commit()
        for s in students:
            db.refresh(s)
        print(f"  ✅ 15 students created")

        # ═══════════════════════════════════
        #  4. PROGRAMME MANAGER (1)
        # ═══════════════════════════════════
        pm = User(
            name="Rajesh Mehta",
            email="pm@test.com",
            hashed_password=pw,
            role=UserRole.programme_manager
        )
        db.add(pm)

        # ═══════════════════════════════════
        #  5. MONITORING OFFICER (1)
        # ═══════════════════════════════════
        mo = User(
            name="Vijay Krishnan",
            email="monitor@test.com",
            hashed_password=pw,
            role=UserRole.monitoring_officer
        )
        db.add(mo)
        db.commit()
        db.refresh(pm)
        db.refresh(mo)
        print(f"  ✅ 1 programme manager + 1 monitoring officer created")

        # ═══════════════════════════════════
        #  6. BATCHES (3)
        # ═══════════════════════════════════
        batch1 = Batch(name="Python Full Stack - Batch A", institution_id=inst1.id)
        batch2 = Batch(name="Data Science - Batch B", institution_id=inst1.id)
        batch3 = Batch(name="Web Development - Batch C", institution_id=inst2.id)
        db.add_all([batch1, batch2, batch3])
        db.commit()
        for b in [batch1, batch2, batch3]:
            db.refresh(b)
        batches = [batch1, batch2, batch3]
        print(f"  ✅ 3 batches created")

        # ═══════════════════════════════════
        #  7. ASSIGN TRAINERS TO BATCHES
        # ═══════════════════════════════════
        # Batch A: Trainer 1 + Trainer 2
        # Batch B: Trainer 2
        # Batch C: Trainer 3 + Trainer 4
        assignments = [
            (batch1.id, trainers[0].id),
            (batch1.id, trainers[1].id),
            (batch2.id, trainers[1].id),
            (batch3.id, trainers[2].id),
            (batch3.id, trainers[3].id),
        ]
        for bid, tid in assignments:
            db.add(BatchTrainer(batch_id=bid, trainer_id=tid))
        db.commit()
        print(f"  ✅ Trainers assigned to batches")

        # ═══════════════════════════════════
        #  8. ENROLL STUDENTS IN BATCHES
        # ═══════════════════════════════════
        # Batch A: students 1-5
        for i in range(0, 5):
            db.add(BatchStudent(batch_id=batch1.id, student_id=students[i].id))
        # Batch B: students 6-10
        for i in range(5, 10):
            db.add(BatchStudent(batch_id=batch2.id, student_id=students[i].id))
        # Batch C: students 11-15
        for i in range(10, 15):
            db.add(BatchStudent(batch_id=batch3.id, student_id=students[i].id))
        db.commit()
        print(f"  ✅ Students enrolled in batches")

        # ═══════════════════════════════════
        #  9. CREATE SESSIONS (8)
        # ═══════════════════════════════════
        base_date = date.today() - timedelta(days=14)

        session_defs = [
            # (batch, trainer_index, title, day_offset, start_h, end_h)
            (batch1, 0, "Introduction to Python", 0, 9, 11),
            (batch1, 0, "Variables & Data Types", 2, 9, 11),
            (batch1, 1, "Control Flow & Loops", 4, 14, 16),
            (batch2, 1, "Pandas Basics", 1, 10, 12),
            (batch2, 1, "Data Visualization", 3, 10, 12),
            (batch2, 1, "ML Introduction", 5, 10, 12),
            (batch3, 2, "HTML/CSS Fundamentals", 1, 9, 11),
            (batch3, 3, "JavaScript Basics", 3, 9, 11),
        ]

        sessions_list = []
        for batch, t_idx, title, day_off, sh, eh in session_defs:
            sess = Session(
                batch_id=batch.id,
                trainer_id=trainers[t_idx].id,
                title=title,
                date=base_date + timedelta(days=day_off),
                start_time=time(sh, 0),
                end_time=time(eh, 0),
            )
            db.add(sess)
            sessions_list.append(sess)
        db.commit()
        for s in sessions_list:
            db.refresh(s)
        print(f"  ✅ 8 sessions created")

        # ═══════════════════════════════════
        #  10. CREATE ATTENDANCE RECORDS
        # ═══════════════════════════════════
        statuses = [AttendanceStatus.present, AttendanceStatus.absent, AttendanceStatus.late]
        weights = [0.70, 0.15, 0.15]
        att_count = 0

        # Map: batch → student indices
        batch_student_map = {
            batch1.id: list(range(0, 5)),
            batch2.id: list(range(5, 10)),
            batch3.id: list(range(10, 15)),
        }

        for sess in sessions_list:
            student_indices = batch_student_map.get(sess.batch_id, [])
            for si in student_indices:
                chosen_status = random.choices(statuses, weights=weights, k=1)[0]
                att = Attendance(
                    session_id=sess.id,
                    student_id=students[si].id,
                    status=chosen_status,
                    marked_at=datetime.utcnow() - timedelta(
                        days=random.randint(0, 10),
                        hours=random.randint(0, 5)
                    )
                )
                db.add(att)
                att_count += 1

        db.commit()
        print(f"  ✅ {att_count} attendance records created")

        # ═══════════════════════════════════
        #  SUMMARY
        # ═══════════════════════════════════
        print("\n" + "=" * 55)
        print("🎉 SEEDING COMPLETE!")
        print("=" * 55)
        print("\n📋 Test Accounts (all passwords: password123)")
        print("-" * 55)
        print("  Role                  | Email")
        print("-" * 55)
        print(f"  Institution 1         | institution1@test.com")
        print(f"  Institution 2         | institution2@test.com")
        print(f"  Trainer 1             | trainer1@test.com")
        print(f"  Trainer 2             | trainer2@test.com")
        print(f"  Trainer 3             | trainer3@test.com")
        print(f"  Trainer 4             | trainer4@test.com")
        print(f"  Student 1-15          | student1@test.com ... student15@test.com")
        print(f"  Programme Manager     | pm@test.com")
        print(f"  Monitoring Officer    | monitor@test.com")
        print("-" * 55)
        print(f"  Monitoring API Key    | {os.getenv('MONITORING_API_KEY', 'monitor_secret_key_2024')}")
        print("-" * 55)
        print(f"\n  Total users: {db.query(User).count()}")
        print(f"  Total batches: {db.query(Batch).count()}")
        print(f"  Total sessions: {db.query(Session).count()}")
        print(f"  Total attendance: {db.query(Attendance).count()}")

    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed()