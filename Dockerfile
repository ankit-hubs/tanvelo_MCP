# ==============================================================================
# Multi-Stage Production Dockerfile for Tanvelo Memory Layer
# ==============================================================================

# --- Stage 1: Build & Dependency Resolution ---
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# --- Stage 2: Minimal Production Runtime ---
FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000 \
    MCP_PORT=8001 \
    TANVELO_ENV=production

# Install minimal runtime shared libraries & curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root security user
RUN groupadd -g 10001 tanvelo && \
    useradd -u 10001 -g tanvelo -s /bin/bash -m tanvelo

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application source code
COPY --chown=tanvelo:tanvelo . .

# Set non-root user
USER tanvelo

# Expose HTTP API (8000) and MCP Server (8001)
EXPOSE 8000 8001

# Health check using readiness probe
HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1

# Default Command: Start FastAPI Backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
