FROM ghcr.io/astral-sh/uv:0.13.9-python3.15-trixie-slim@sha256:980d6aa868431fd4ef2b32481e934ef5ee3b662c5decade3aa2d7e7ffb8075e4 AS builder

WORKDIR /

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update &&  \
    apt-get install -y --no-install-recommends \
        gcc \
        libc6-dev \
        libpq-dev \
        libmagic-dev

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen

FROM python:3.15.2-slim-trixie@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928 AS main

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        libmagic-dev \
        gettext

COPY --from=builder /.venv /.venv
