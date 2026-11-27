# GliHub 3.0 Modular AI-EHS Service (Multi-Profile Build)
# Build CPU-INT8 default: docker build --build-arg AI_EXTRAS="--extra cpu-int8" -t glihub/ai-service:3.0 .
# Build 0-Plugin Core:    docker build --build-arg AI_EXTRAS="" -t glihub/ai-service:3.0-minimal .
FROM python:3.12-slim-bookworm

ARG AI_EXTRAS="--extra cpu-int8"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    DEPLOY_PROFILE=cpu-int8

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1 fonts-wqy-zenhei ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml ./
RUN uv pip install --no-cache -r pyproject.toml ${AI_EXTRAS}

COPY . .
RUN mkdir -p /app/outputs /data/models

EXPOSE 8090

HEALTHCHECK --interval=20s --timeout=5s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8090/api/v1/health || exit 1

CMD ["python3", "main.py"]
