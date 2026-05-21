FROM ghcr.io/astral-sh/uv:0.11.15-python3.14-trixie-slim@sha256:1b882e1fa1834b0c26764ad6494e3151de499ed34dfa13826f9f395f5110f519 AS builder

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

FROM python:3.14.5-slim-trixie@sha256:a7185a8e40af01bf891414a4df16ef10fc6000cee460a404a13da9029fe41604 AS main

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
