"""
CENTRALIZED CONFIGURATION
──────────────────────────
All environment variables managed from one place.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://localhost/skillbridge")

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback_secret_change_in_prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24          # 24 hours for standard roles
    MONITORING_TOKEN_EXPIRE_MINUTES: int = 60            # 1 hour for monitoring scoped token

    # Monitoring
    MONITORING_API_KEY: str = os.getenv("MONITORING_API_KEY", "monitor_secret_key_2024")

    # App
    APP_NAME: str = "SkillBridge Attendance API"
    APP_VERSION: str = "1.0.0"
    INVITE_EXPIRY_DAYS: int = 7


settings = Settings()