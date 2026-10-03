# ============================================================
# TELECOM-NET-SIM — Multi-stage Dockerfile
# ============================================================
# Stage 1: builder — installs Python deps into a venv
# Stage 2: runtime — slim image with just what's needed
# ============================================================

# ------------------------------------------------------------
# Stage 1: builder
# ------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Build-time system deps (for matplotlib, reportlab, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install deps into a virtualenv that we'll copy to the runtime
COPY requirements-ci.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements-ci.txt

# ------------------------------------------------------------
# Stage 2: runtime
# ------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Runtime system deps — keep minimal
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the venv from the builder stage
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Copy the project (respecting .dockerignore)
COPY . .

# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/telecom_sim_output \
    && chown -R appuser:appuser /app
USER appuser

# Default command: run the simulator to generate the DB
# (override via docker-compose for the dashboards)
CMD ["python", "telecom_net_sim.py"]

# Optional healthcheck (Streamlit responds on /_stcore/health)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8501/_stcore/health || exit 1
