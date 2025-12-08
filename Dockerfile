# Multi-stage build for optimized image size
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --default-timeout=300 --retries=5 -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin


# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY main.py .
COPY run_dashboard.py .

# Set Python path
ENV PYTHONPATH=/app

# Run as non-root user for security
RUN useradd -m -u 1000 botuser && \
    mkdir -p /app/logs && \
    chown -R botuser:botuser /app && \
    chmod -R 755 /app/logs
USER botuser

# Health check (for dashboard mode; safe no-op if API not running)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (docker-compose overrides this for the dashboard)
CMD ["python", "main.py"]

