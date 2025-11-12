FROM ghcr.io/astral-sh/uv:0.9.8-python3.14-alpine@sha256:a834e872777374c695d49ef33aef1b65debda73509f72a825562955bbbdb6099 AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
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

FROM python:3.14-alpine3.22@sha256:8373231e1e906ddfb457748bfc032c4c06ada8c759b7b62d9c73ec2a3c56e710

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apk update && apk add --no-cache libpq libmagic tini
RUN addgroup -S django && adduser -S django -G django --disabled-password

COPY --from=builder --chown=django:django /app /app

USER django
ENTRYPOINT ["/sbin/tini", "--"]
