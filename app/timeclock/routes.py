from datetime import datetime, timedelta, date

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import TimeEntry
from app.timeclock import timeclock_bp

_MAX_NOTE_LEN = 200


@timeclock_bp.route("/")
@login_required
def dashboard():
    active_entry = TimeEntry.query.filter_by(
        user_id=current_user.id, clock_out=None
    ).first()

    now = datetime.now()
    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    weekly_entries = TimeEntry.query.filter(
        TimeEntry.user_id == current_user.id,
        TimeEntry.clock_in >= week_start,
        TimeEntry.clock_out.isnot(None),
    ).all()
    weekly_hours = sum(e.duration_hours for e in weekly_entries)

    pay_period_hours = current_user.get_pay_period_hours()
    pay_accrued = pay_period_hours * (current_user.pay_rate or 0)

    recent_entries = (
        TimeEntry.query.filter_by(user_id=current_user.id)
        .order_by(TimeEntry.clock_in.desc())
        .limit(30)
        .all()
    )

    return render_template(
        "timeclock/dashboard.html",
        active_entry=active_entry,
        weekly_hours=weekly_hours,
        pay_period_hours=pay_period_hours,
        pay_accrued=pay_accrued,
        recent_entries=recent_entries,
        now=now,
    )


@timeclock_bp.route("/clock-in", methods=["POST"])
@login_required
def clock_in():
    existing = TimeEntry.query.filter_by(
        user_id=current_user.id, clock_out=None
    ).first()
    if existing:
        flash("You are already clocked in.", "warning")
        return redirect(url_for("timeclock.dashboard"))
    entry = TimeEntry(user_id=current_user.id, clock_in=datetime.now())
    db.session.add(entry)
    db.session.commit()
    flash("Clocked in successfully.", "success")
    return redirect(url_for("timeclock.dashboard"))


@timeclock_bp.route("/clock-out", methods=["POST"])
@login_required
def clock_out():
    entry = TimeEntry.query.filter_by(
        user_id=current_user.id, clock_out=None
    ).first()
    if not entry:
        flash("You are not currently clocked in.", "warning")
        return redirect(url_for("timeclock.dashboard"))
    entry.clock_out = datetime.now()
    db.session.commit()
    flash(f"Clocked out. Session: {entry.duration_display}", "success")
    return redirect(url_for("timeclock.dashboard"))


@timeclock_bp.route("/entry/new", methods=["GET", "POST"])
@login_required
def new_entry():
    if request.method == "POST":
        try:
            clock_in_str = request.form["clock_in"]
            clock_out_str = request.form.get("clock_out", "").strip()
            note = request.form.get("note", "").strip()[:_MAX_NOTE_LEN]

            clock_in_dt = datetime.fromisoformat(clock_in_str)
            clock_out_dt = None
            if clock_out_str:
                clock_out_dt = datetime.fromisoformat(clock_out_str)
                if clock_out_dt <= clock_in_dt:
                    flash("Clock-out must be after clock-in.", "error")
                    return redirect(url_for("timeclock.new_entry"))

            entry = TimeEntry(
                user_id=current_user.id,
                clock_in=clock_in_dt,
                clock_out=clock_out_dt,
                note=note,
            )
            db.session.add(entry)
            db.session.commit()
            flash("Time entry added.", "success")
            return redirect(url_for("timeclock.dashboard"))
        except (ValueError, KeyError):
            flash("Invalid date/time format.", "error")

    return render_template("timeclock/edit_entry.html", entry=None, title="Add Entry")


@timeclock_bp.route("/entry/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
def edit_entry(entry_id):
    entry = TimeEntry.query.filter_by(
        id=entry_id, user_id=current_user.id
    ).first_or_404()

    if request.method == "POST":
        try:
            clock_in_str = request.form["clock_in"]
            clock_out_str = request.form.get("clock_out", "").strip()
            note = request.form.get("note", "").strip()[:_MAX_NOTE_LEN]

            clock_in_dt = datetime.fromisoformat(clock_in_str)
            clock_out_dt = None
            if clock_out_str:
                clock_out_dt = datetime.fromisoformat(clock_out_str)
                if clock_out_dt <= clock_in_dt:
                    flash("Clock-out must be after clock-in.", "error")
                    return redirect(url_for("timeclock.edit_entry", entry_id=entry_id))

            entry.clock_in = clock_in_dt
            entry.clock_out = clock_out_dt
            entry.note = note
            db.session.commit()
            flash("Time entry updated.", "success")
            return redirect(url_for("timeclock.dashboard"))
        except (ValueError, KeyError):
            flash("Invalid date/time format.", "error")

    return render_template("timeclock/edit_entry.html", entry=entry, title="Edit Entry")


@timeclock_bp.route("/entry/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_entry(entry_id):
    entry = TimeEntry.query.filter_by(
        id=entry_id, user_id=current_user.id
    ).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    flash("Time entry deleted.", "success")
    return redirect(url_for("timeclock.dashboard"))


@timeclock_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "pay_rate":
            try:
                rate = float(request.form.get("pay_rate", 0))
                current_user.pay_rate = max(0.0, rate)
                db.session.commit()
                flash("Pay rate updated.", "success")
            except ValueError:
                flash("Invalid pay rate.", "error")

        elif action == "pay_period":
            try:
                start_str = request.form.get("pay_period_start", "").strip()
                end_str = request.form.get("pay_period_end", "").strip()
                if start_str and end_str:
                    start = date.fromisoformat(start_str)
                    end = date.fromisoformat(end_str)
                    if end < start:
                        flash("End date must be after start date.", "error")
                    else:
                        current_user.pay_period_start = start
                        current_user.pay_period_end = end
                        db.session.commit()
                        flash("Pay period updated.", "success")
                else:
                    flash("Please enter both start and end dates.", "error")
            except ValueError:
                flash("Invalid date format.", "error")

        elif action == "theme":
            current_user.dark_mode = not current_user.dark_mode
            db.session.commit()

        return redirect(url_for("timeclock.settings"))

    return render_template("timeclock/settings.html")
