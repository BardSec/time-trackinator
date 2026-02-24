from datetime import datetime, date

from flask_login import UserMixin

from app import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), nullable=False, unique=True)
    name = db.Column(db.String(200), default="")
    provider = db.Column(db.String(50), default="")
    is_admin = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    pay_rate = db.Column(db.Float, default=0.0)
    dark_mode = db.Column(db.Boolean, default=False)
    pay_period_start = db.Column(db.Date, nullable=True)
    pay_period_end = db.Column(db.Date, nullable=True)

    time_entries = db.relationship(
        "TimeEntry", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def active_entry(self):
        return TimeEntry.query.filter_by(user_id=self.id, clock_out=None).first()

    def get_weekly_hours(self):
        from datetime import timedelta
        now = datetime.now()
        week_start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        entries = TimeEntry.query.filter(
            TimeEntry.user_id == self.id,
            TimeEntry.clock_in >= week_start,
            TimeEntry.clock_out.isnot(None),
        ).all()
        return sum(e.duration_hours for e in entries)

    def get_pay_period_hours(self):
        if not (self.pay_period_start and self.pay_period_end):
            return 0.0
        pp_start = datetime.combine(self.pay_period_start, datetime.min.time())
        pp_end = datetime.combine(self.pay_period_end, datetime.max.time())
        entries = TimeEntry.query.filter(
            TimeEntry.user_id == self.id,
            TimeEntry.clock_in >= pp_start,
            TimeEntry.clock_in <= pp_end,
            TimeEntry.clock_out.isnot(None),
        ).all()
        return sum(e.duration_hours for e in entries)

    def __repr__(self):
        return f"<User {self.email}>"


class TimeEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    clock_in = db.Column(db.DateTime, nullable=False)
    clock_out = db.Column(db.DateTime, nullable=True)
    note = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    user = db.relationship("User", back_populates="time_entries")

    @property
    def duration_hours(self):
        if self.clock_out is None:
            return 0.0
        return (self.clock_out - self.clock_in).total_seconds() / 3600

    @property
    def duration_display(self):
        h = self.duration_hours
        hours = int(h)
        minutes = int((h % 1) * 60)
        return f"{hours}h {minutes:02d}m"

    def __repr__(self):
        return f"<TimeEntry {self.user_id} {self.clock_in}>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
