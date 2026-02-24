import json
from datetime import datetime, timedelta, date
from functools import wraps

from flask import Response, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.admin import admin_bp
from app.models import TimeEntry, User


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash("Admin access required.", "error")
            return redirect(url_for("timeclock.dashboard"))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/")
@admin_required
def dashboard():
    users = User.query.order_by(User.name).all()
    now = datetime.now()
    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    user_data = []
    dept_week_hours = 0.0
    for user in users:
        weekly_entries = TimeEntry.query.filter(
            TimeEntry.user_id == user.id,
            TimeEntry.clock_in >= week_start,
            TimeEntry.clock_out.isnot(None),
        ).all()
        weekly_hours = sum(e.duration_hours for e in weekly_entries)
        dept_week_hours += weekly_hours
        active = TimeEntry.query.filter_by(user_id=user.id, clock_out=None).first()
        user_data.append(
            {
                "user": user,
                "weekly_hours": weekly_hours,
                "is_active": active is not None,
            }
        )

    return render_template(
        "admin/dashboard.html",
        user_data=user_data,
        dept_week_hours=dept_week_hours,
    )


@admin_bp.route("/user/<int:user_id>")
@admin_required
def user_report(user_id):
    user = db.session.get(User, user_id) or db.session.get(User, user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("admin.dashboard"))

    start_str = request.args.get("start", "")
    end_str = request.args.get("end", "")

    query = TimeEntry.query.filter_by(user_id=user_id)
    if start_str:
        try:
            query = query.filter(
                TimeEntry.clock_in >= datetime.fromisoformat(start_str)
            )
        except ValueError:
            pass
    if end_str:
        try:
            end_dt = datetime.fromisoformat(end_str).replace(
                hour=23, minute=59, second=59
            )
            query = query.filter(TimeEntry.clock_in <= end_dt)
        except ValueError:
            pass

    entries = query.order_by(TimeEntry.clock_in.desc()).all()
    total_hours = sum(e.duration_hours for e in entries if e.clock_out)

    return render_template(
        "admin/user_report.html",
        user=user,
        entries=entries,
        total_hours=total_hours,
        start_str=start_str,
        end_str=end_str,
    )


@admin_bp.route("/report")
@admin_required
def dept_report():
    start_str = request.args.get("start", "")
    end_str = request.args.get("end", "")

    users = User.query.order_by(User.name).all()
    report_data = []
    dept_total = 0.0

    for user in users:
        query = TimeEntry.query.filter(
            TimeEntry.user_id == user.id,
            TimeEntry.clock_out.isnot(None),
        )
        if start_str:
            try:
                query = query.filter(
                    TimeEntry.clock_in >= datetime.fromisoformat(start_str)
                )
            except ValueError:
                pass
        if end_str:
            try:
                end_dt = datetime.fromisoformat(end_str).replace(
                    hour=23, minute=59, second=59
                )
                query = query.filter(TimeEntry.clock_in <= end_dt)
            except ValueError:
                pass

        entries = query.all()
        total = sum(e.duration_hours for e in entries)
        dept_total += total
        report_data.append(
            {"user": user, "hours": total, "entry_count": len(entries)}
        )

    return render_template(
        "admin/dept_report.html",
        report_data=report_data,
        dept_total=dept_total,
        start_str=start_str,
        end_str=end_str,
    )


@admin_bp.route("/entry/new/<int:user_id>", methods=["GET", "POST"])
@admin_required
def new_entry(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        try:
            clock_in_str = request.form["clock_in"]
            clock_out_str = request.form.get("clock_out", "").strip()
            note = request.form.get("note", "").strip()

            clock_in_dt = datetime.fromisoformat(clock_in_str)
            clock_out_dt = None
            if clock_out_str:
                clock_out_dt = datetime.fromisoformat(clock_out_str)
                if clock_out_dt <= clock_in_dt:
                    flash("Clock-out must be after clock-in.", "error")
                    return redirect(url_for("admin.new_entry", user_id=user_id))

            entry = TimeEntry(
                user_id=user_id,
                clock_in=clock_in_dt,
                clock_out=clock_out_dt,
                note=note,
            )
            db.session.add(entry)
            db.session.commit()
            flash("Time entry added.", "success")
            return redirect(url_for("admin.user_report", user_id=user_id))
        except (ValueError, KeyError):
            flash("Invalid date/time format.", "error")

    return render_template(
        "admin/edit_entry.html",
        entry=None,
        target_user=user,
        title=f"Add Entry for {user.name or user.email}",
    )


@admin_bp.route("/entry/<int:entry_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_entry(entry_id):
    entry = db.session.get(TimeEntry, entry_id)
    if not entry:
        flash("Entry not found.", "error")
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        try:
            clock_in_str = request.form["clock_in"]
            clock_out_str = request.form.get("clock_out", "").strip()
            note = request.form.get("note", "").strip()

            clock_in_dt = datetime.fromisoformat(clock_in_str)
            clock_out_dt = None
            if clock_out_str:
                clock_out_dt = datetime.fromisoformat(clock_out_str)
                if clock_out_dt <= clock_in_dt:
                    flash("Clock-out must be after clock-in.", "error")
                    return redirect(url_for("admin.edit_entry", entry_id=entry_id))

            entry.clock_in = clock_in_dt
            entry.clock_out = clock_out_dt
            entry.note = note
            db.session.commit()
            flash("Time entry updated.", "success")
            return redirect(url_for("admin.user_report", user_id=entry.user_id))
        except (ValueError, KeyError):
            flash("Invalid date/time format.", "error")

    return render_template(
        "admin/edit_entry.html",
        entry=entry,
        target_user=entry.user,
        title=f"Edit Entry — {entry.user.name or entry.user.email}",
    )


@admin_bp.route("/entry/<int:entry_id>/delete", methods=["POST"])
@admin_required
def delete_entry(entry_id):
    entry = db.session.get(TimeEntry, entry_id)
    if not entry:
        flash("Entry not found.", "error")
        return redirect(url_for("admin.dashboard"))
    user_id = entry.user_id
    db.session.delete(entry)
    db.session.commit()
    flash("Time entry deleted.", "success")
    return redirect(url_for("admin.user_report", user_id=user_id))


@admin_bp.route("/backup")
@admin_required
def backup():
    users = User.query.all()
    entries = TimeEntry.query.all()

    data = {
        "exported_at": datetime.now().isoformat(),
        "app": "time-trackinator",
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "provider": u.provider,
                "is_admin": u.is_admin,
                "pay_rate": u.pay_rate,
                "dark_mode": u.dark_mode,
                "pay_period_start": (
                    u.pay_period_start.isoformat() if u.pay_period_start else None
                ),
                "pay_period_end": (
                    u.pay_period_end.isoformat() if u.pay_period_end else None
                ),
            }
            for u in users
        ],
        "time_entries": [
            {
                "id": e.id,
                "user_id": e.user_id,
                "clock_in": e.clock_in.isoformat() if e.clock_in else None,
                "clock_out": e.clock_out.isoformat() if e.clock_out else None,
                "note": e.note,
            }
            for e in entries
        ],
    }

    payload = json.dumps(data, indent=2)
    filename = f"timeclock-backup-{date.today().isoformat()}.json"
    return Response(
        payload,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@admin_bp.route("/restore", methods=["GET", "POST"])
@admin_required
def restore():
    if request.method == "POST":
        f = request.files.get("backup_file")
        if not f:
            flash("No file uploaded.", "error")
            return redirect(url_for("admin.restore"))
        try:
            data = json.loads(f.read())
            if data.get("app") != "time-trackinator":
                flash("This does not appear to be a valid Time Trackinator backup.", "error")
                return redirect(url_for("admin.restore"))

            # Upsert users
            old_to_new_id = {}
            for u_data in data.get("users", []):
                user = User.query.filter_by(email=u_data["email"]).first()
                if user is None:
                    user = User(email=u_data["email"])
                    db.session.add(user)
                user.name = u_data.get("name", "")
                user.provider = u_data.get("provider", "")
                user.is_admin = u_data.get("is_admin", False)
                user.pay_rate = u_data.get("pay_rate", 0.0)
                user.dark_mode = u_data.get("dark_mode", False)
                if u_data.get("pay_period_start"):
                    user.pay_period_start = date.fromisoformat(u_data["pay_period_start"])
                if u_data.get("pay_period_end"):
                    user.pay_period_end = date.fromisoformat(u_data["pay_period_end"])
                db.session.flush()
                old_to_new_id[u_data["id"]] = user.id

            # Restore time entries (skip duplicates by clock_in + user)
            for e_data in data.get("time_entries", []):
                new_uid = old_to_new_id.get(e_data["user_id"])
                if new_uid is None:
                    continue
                if not e_data.get("clock_in"):
                    continue
                ci = datetime.fromisoformat(e_data["clock_in"])
                existing = TimeEntry.query.filter_by(
                    user_id=new_uid, clock_in=ci
                ).first()
                if existing:
                    continue
                entry = TimeEntry(
                    user_id=new_uid,
                    clock_in=ci,
                    clock_out=(
                        datetime.fromisoformat(e_data["clock_out"])
                        if e_data.get("clock_out")
                        else None
                    ),
                    note=e_data.get("note", ""),
                )
                db.session.add(entry)

            db.session.commit()
            flash("Backup restored successfully.", "success")
            return redirect(url_for("admin.dashboard"))

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            db.session.rollback()
            flash(f"Restore failed: {e}", "error")

    return render_template("admin/backup.html")
