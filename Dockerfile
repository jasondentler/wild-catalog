# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:0.11.21 AS uv

FROM python:3.13-slim-bookworm AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

COPY --from=uv /uv /uvx /bin/

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential git libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE.txt NOTICE.txt ./
RUN uv sync --frozen --no-cache --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-cache --no-dev --no-editable


FROM python:3.13-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y libcurl4 libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 wild-catalog \
    && useradd --system --uid 10001 --gid wild-catalog --home-dir /app wild-catalog

WORKDIR /app
COPY --from=builder --chown=wild-catalog:wild-catalog /app/.venv ./.venv
RUN mkdir -p /app/data && chown wild-catalog:wild-catalog /app/data

USER wild-catalog

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5m --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "wild_catalog.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
