# syntax=docker/dockerfile:1.7
# ──────────────────────────────────────────────────────────────────────────────
# Air Côte d'Ivoire Analytics — single image for pipeline / dashboard / MCP
# ──────────────────────────────────────────────────────────────────────────────
# Why a single image:
#   The three workloads (pipeline, dashboard, MCP server) share the exact same
#   Python deps and warehouse file. Splitting them would multiply the image
#   build time without isolating anything meaningful. docker-compose drives the
#   per-service commands.
#
# Why python:3.12-slim:
#   dbt-duckdb supports Python 3.9–3.12. 3.12 is the most recent. The -slim
#   base is ~80 MB vs ~1 GB for the full image and only lacks build tooling.

ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS base

LABEL org.opencontainers.image.title="Air Côte d'Ivoire Analytics" \
      org.opencontainers.image.source="https://github.com/ettien/aci-analytics" \
      org.opencontainers.image.description="dbt + DuckDB + Streamlit + MCP analytics stack"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DBT_PROFILES_DIR=/app/dbt_project \
    HF_HOME=/app/.cache/huggingface

# System packages:
#   libgomp1  — required by torch (sentence-transformers transitive dep)
#   curl      — used by HEALTHCHECK on the dashboard service
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps. torch is installed from the CPU-only PyPI index first
# so pip won't pull the 2.7 GB of NVIDIA CUDA libs we'd never use here.
COPY requirements.txt .
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch \
 && pip install -r requirements.txt

# Pre-download the embedding model so the MCP server starts instantly.
# Adds ~90 MB to the image. If you want a leaner image, drop this RUN and
# let the model download on first MCP search_reviews call.
RUN python -c "from sentence_transformers import SentenceTransformer; \
               SentenceTransformer('all-MiniLM-L6-v2')"

# Copy the rest of the project. .dockerignore keeps .venv, target/, etc. out.
COPY . .

# Volume mount points (host data is bind-mounted via compose).
RUN mkdir -p /app/data/raw /app/data/synthetic /app/data/source /app/dbt_project/target

EXPOSE 8501

# Default command shows the available entry points; compose overrides this.
CMD ["python", "-c", "print('Available commands:\\n  pipeline   — load + generate + dbt build + validate\\n  dashboard  — streamlit on :8501\\n  mcp        — MCP server over stdio\\n\\nRun via docker compose run <service> or docker compose up.')"]
