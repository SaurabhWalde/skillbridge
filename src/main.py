"""
MAIN APPLICATION — entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src.database import engine, Base, SessionLocal
from src.config import settings
from src.routers import (
    auth_router, batches, sessions,
    attendance, institutions, programme, monitoring
)

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="REST API for SkillBridge attendance management with RBAC and dual JWT system.",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router.router)
app.include_router(batches.router)
app.include_router(sessions.router)
app.include_router(attendance.router)
app.include_router(institutions.router)
app.include_router(programme.router)
app.include_router(monitoring.router)


# ── Root Endpoint (supports GET + HEAD for Render health check) ──
@app.api_route("/", methods=["GET", "HEAD"], tags=["Health"])
def root():
    return {
        "message": f"{settings.APP_NAME} is running",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


# ── Health Check (supports GET + HEAD) ──
@app.api_route("/health", methods=["GET", "HEAD"], tags=["Health"])
def health_check():
    db_status = "unknown"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status
    }