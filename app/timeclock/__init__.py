from flask import Blueprint

timeclock_bp = Blueprint("timeclock", __name__)

from app.timeclock import routes  # noqa: E402, F401
