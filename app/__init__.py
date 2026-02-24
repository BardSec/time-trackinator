import logging
import os
from logging.handlers import RotatingFileHandler

from authlib.integrations.flask_client import OAuth
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per minute"])
oauth = OAuth()

_WEAK_KEYS = {"dev-secret-change-me", "change-me", "secret"}


def create_app():
    app = Flask(__name__)

    from app.config import Config
    app.config.from_object(Config)

    secret = app.config.get("SECRET_KEY", "")
    if len(secret) < 16 or secret in _WEAK_KEYS:
        import warnings
        warnings.warn(
            "SECRET_KEY is weak or default — set a strong SECRET_KEY in production.",
            stacklevel=1,
        )

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    oauth.init_app(app)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to access this page."
    login_manager.login_message_category = "info"

    # OAuth providers
    if app.config.get("MICROSOFT_CLIENT_ID"):
        oauth.register(
            name="microsoft",
            client_id=app.config["MICROSOFT_CLIENT_ID"],
            client_secret=app.config["MICROSOFT_CLIENT_SECRET"],
            server_metadata_url=(
                f"https://login.microsoftonline.com/"
                f"{app.config['MICROSOFT_TENANT_ID']}/v2.0/.well-known/openid-configuration"
            ),
            client_kwargs={"scope": "openid email profile"},
        )

    if app.config.get("GOOGLE_CLIENT_ID"):
        oauth.register(
            name="google",
            client_id=app.config["GOOGLE_CLIENT_ID"],
            client_secret=app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    # Blueprints
    from app.auth import auth_bp
    from app.timeclock import timeclock_bp
    from app.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(timeclock_bp)
    app.register_blueprint(admin_bp)

    # Template filters
    @app.template_filter("fmt_hours")
    def fmt_hours(h):
        h = h or 0
        hours = int(h)
        minutes = int(round((h % 1) * 60))
        return f"{hours}h {minutes:02d}m"

    @app.template_filter("fmt_dt")
    def fmt_dt(dt):
        if dt is None:
            return "—"
        return dt.strftime("%-m/%-d/%y %-I:%M %p")

    @app.template_filter("fmt_time")
    def fmt_time(dt):
        if dt is None:
            return "—"
        return dt.strftime("%-I:%M %p")

    @app.template_filter("fmt_date")
    def fmt_date(dt):
        if dt is None:
            return "—"
        return dt.strftime("%-m/%-d/%y")

    # Security headers
    @app.after_request
    def set_security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'"
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        if not app.debug:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    # Logging
    if not app.debug:
        os.makedirs("logs", exist_ok=True)
        handler = RotatingFileHandler(
            "logs/timeclock.log", maxBytes=10_000_000, backupCount=10
        )
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)

    with app.app_context():
        db.create_all()

    return app
