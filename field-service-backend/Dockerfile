FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# libpq-dev + gcc needed to build psycopg2-binary / asyncpg on slim images
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev dos2unix \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY app ./app
COPY docker ./docker

RUN dos2unix /app/docker/entrypoint.sh \
    && cp /app/docker/entrypoint.sh /entrypoint.sh \
    && mkdir -p /app/uploads \
    && chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
