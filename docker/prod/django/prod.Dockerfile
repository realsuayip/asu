FROM ghcr.io/astral-sh/uv:0.5.27-python3.12-alpine AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apk \
    --mount=type=cache,target=/etc/apk/cache \
    apk update && apk add gcc musl-dev libpq-dev

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --group prod

COPY . .

FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apk update && apk add --no-cache libpq libmagic tini
RUN addgroup -S django && adduser -S django -G django --disabled-password

COPY --from=builder --chown=django:django /app /app

USER django
ENTRYPOINT ["/sbin/tini", "--"]
