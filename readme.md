# Time Trackinator

A simple, mobile-friendly time clock web app for small departments. Technicians can clock in/out, view weekly and pay-period hours, and track pay accrued. Admins can edit time cards, run reports, and export/restore backups.

## Features

**For all users**
- Sign in with Microsoft or Google (OAuth)
- One-tap clock in / clock out with live session timer
- View total hours for the current week
- Set a custom pay period and see hours for that period
- Add your hourly pay rate to see pay accrued
- Add or edit time entries manually (for missed punches)
- Light mode (default) with dark mode toggle per user

**For admins**
- Overview of all team members with live status and weekly hours
- Individual time card with date-range filtering and edit/delete
- Department-wide report with date-range filtering
- JSON backup export and restore

## Quick Start

### 1. Configure OAuth

**Microsoft:** [Azure Portal → App Registrations](https://portal.azure.com) — add redirect URI `https://yourdomain.com/callback/microsoft`.

**Google:** [Google Cloud Console → Credentials](https://console.cloud.google.com) — add redirect URI `https://yourdomain.com/callback/google`.

### 2. Set Up Environment

```bash
cp .env.example .env
# Edit .env with your SECRET_KEY, OAuth credentials, ADMIN_EMAILS, and TZ
```

### 3. Deploy

```bash
docker compose up -d
```

App runs on port 5000 (or set `PORT=` in `.env`). Put it behind a reverse proxy (Nginx, Caddy, Cloudflare Tunnel) with HTTPS.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | **Yes** | Random 32+ char string for session signing |
| `MICROSOFT_CLIENT_ID` | One of | Azure app client ID |
| `MICROSOFT_CLIENT_SECRET` | One of | Azure app client secret |
| `MICROSOFT_TENANT_ID` | No | Azure tenant ID (default: `common`) |
| `GOOGLE_CLIENT_ID` | One of | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | One of | Google OAuth client secret |
| `ADMIN_EMAILS` | **Yes** | Comma-separated emails that get admin on first login |
| `ALLOWED_DOMAINS` | No | Restrict sign-in to these domains (e.g. `example.com`) |
| `PORT` | No | Host port (default: `5000`) |
| `TZ` | **Yes** | Server timezone — must match your department's local TZ |

## Timezone

Times are stored as naive datetimes in server-local time. **Set `TZ` in `.env` to match your department's timezone** (e.g. `America/Chicago`). All users should be in the same timezone.

## Backup & Restore

Admins can export a full JSON backup from **Admin → Backup / Restore**. The same page lets you upload a backup to restore (merge) data. Restoring does not delete existing records — duplicate entries (matched by user email + clock-in time) are skipped.

## Data

SQLite database stored in a named Docker volume (`timeclock_data`). To back up the raw database:

```bash
docker cp time-trackinator:/app/instance/timeclock.db ./timeclock.db
```

## Tech Stack

- **Backend:** Python 3.12, Flask, SQLAlchemy, Authlib, Flask-Login, Flask-WTF
- **Database:** SQLite (via named Docker volume)
- **Auth:** Microsoft Azure AD / Google OAuth 2.0 (OpenID Connect)
- **Container:** Docker Compose, Gunicorn (2 workers, 4 threads)
