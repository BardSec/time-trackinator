FROM python:3.12-slim

# Create non-root user
RUN groupadd -r timeclock && useradd -r -g timeclock timeclock

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create instance dir and set ownership before switching user.
# This ensures the named volume inherits timeclock ownership on first mount.
RUN mkdir -p /app/instance && chown -R timeclock:timeclock /app

USER timeclock

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/login')" || exit 1

ENTRYPOINT ["sh", "entrypoint.sh"]
CMD ["gunicorn", "--workers=2", "--threads=4", "--bind=0.0.0.0:5000", "run:app"]
