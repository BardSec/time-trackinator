from datetime import datetime

from flask import current_app, flash, redirect, render_template, session, url_for
from flask_login import current_user, login_user, logout_user

from app import db, limiter, oauth
from app.auth import auth_bp
from app.models import User


@auth_bp.route("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("timeclock.dashboard"))
    ms_enabled = bool(current_app.config.get("MICROSOFT_CLIENT_ID"))
    google_enabled = bool(current_app.config.get("GOOGLE_CLIENT_ID"))
    return render_template(
        "auth/login.html", ms_enabled=ms_enabled, google_enabled=google_enabled
    )


@auth_bp.route("/login/microsoft")
@limiter.limit("10 per minute")
def login_microsoft():
    redirect_uri = url_for("auth.callback_microsoft", _external=True)
    return oauth.microsoft.authorize_redirect(redirect_uri)


@auth_bp.route("/callback/microsoft")
@limiter.limit("10 per minute")
def callback_microsoft():
    try:
        token = oauth.microsoft.authorize_access_token()
        userinfo = token.get("userinfo") or oauth.microsoft.get(
            "https://graph.microsoft.com/oidc/userinfo", token=token
        ).json()
    except Exception:
        current_app.logger.warning("Microsoft OAuth callback failed", exc_info=True)
        flash("Microsoft sign-in failed. Please try again.", "error")
        return redirect(url_for("auth.login"))
    email = userinfo.get("email", "").lower().strip()
    name = userinfo.get("name", "")
    return _handle_login(email, name, "microsoft")


@auth_bp.route("/login/google")
@limiter.limit("10 per minute")
def login_google():
    redirect_uri = url_for("auth.callback_google", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/callback/google")
@limiter.limit("10 per minute")
def callback_google():
    try:
        token = oauth.google.authorize_access_token()
        userinfo = token.get("userinfo") or oauth.google.get(
            "https://openidconnect.googleapis.com/v1/userinfo", token=token
        ).json()
    except Exception:
        current_app.logger.warning("Google OAuth callback failed", exc_info=True)
        flash("Google sign-in failed. Please try again.", "error")
        return redirect(url_for("auth.login"))
    email = userinfo.get("email", "").lower().strip()
    name = userinfo.get("name", "")
    return _handle_login(email, name, "google")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


def _handle_login(email, name, provider):
    if not email:
        flash("Could not retrieve your email address.", "error")
        return redirect(url_for("auth.login"))

    allowed = current_app.config.get("ALLOWED_DOMAINS", [])
    if allowed:
        domain = email.split("@")[-1]
        if domain not in allowed:
            current_app.logger.warning(f"Domain rejected: {email} via {provider}")
            flash("Your email domain is not authorized to access this application.", "error")
            return redirect(url_for("auth.login"))

    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(email=email, name=name, provider=provider)
        db.session.add(user)

    user.name = name
    user.last_login = datetime.now()
    user.is_admin = email in current_app.config.get("ADMIN_EMAILS", [])
    db.session.commit()

    session.clear()
    login_user(user, remember=True)
    current_app.logger.info(f"Login: {email} via {provider}")
    return redirect(url_for("timeclock.dashboard"))
