# syntax=docker/dockerfile:1

FROM python:3.12-slim-bullseye AS builder

ENV POETRY_VERSION=1.8.3 \
    POETRY_NO_INTERACTION=1 \
    PIP_NO_CACHE_DIR=on \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* ./

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}" \
    && poetry export --only main --without-hashes -f requirements.txt -o requirements.txt

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim-bullseye AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    APP_DIR=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system app && adduser --system --ingroup app --home /app app

COPY --from=builder /opt/venv /opt/venv

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

COPY visitor_system visitor_system
COPY templates templates
COPY grafana grafana

RUN chown -R app:app /app

USER app

EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["gunicorn", "visitor_system.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:8000"]
