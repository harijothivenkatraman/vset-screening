FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Create non-root system user and group
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m -s /bin/bash appuser

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and files
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY seed.py .
COPY reference/ ./reference/
COPY entrypoint.sh .

# Ensure entrypoint is executable and owned by non-root user
RUN chmod +x entrypoint.sh && \
    chown -R appuser:appuser /app

USER appuser

# Python-based healthcheck without external curl dependency
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').getcode() == 200 else 1)"

ENTRYPOINT ["./entrypoint.sh"]
