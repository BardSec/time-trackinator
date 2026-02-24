import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:////app/instance/timeclock.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Microsoft OAuth
    MICROSOFT_CLIENT_ID = os.environ.get("MICROSOFT_CLIENT_ID", "")
    MICROSOFT_CLIENT_SECRET = os.environ.get("MICROSOFT_CLIENT_SECRET", "")
    MICROSOFT_TENANT_ID = os.environ.get("MICROSOFT_TENANT_ID", "common")

    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # Access control
    ADMIN_EMAILS = [
        e.strip().lower()
        for e in os.environ.get("ADMIN_EMAILS", "").split(",")
        if e.strip()
    ]
    ALLOWED_DOMAINS = [
        d.strip().lower()
        for d in os.environ.get("ALLOWED_DOMAINS", "").split(",")
        if d.strip()
    ]

    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    _weak = {"dev-secret-change-me", "change-me", "secret"}
    SESSION_COOKIE_SECURE = bool(
        SECRET_KEY and len(SECRET_KEY) >= 16 and SECRET_KEY not in _weak
    )
