# syntax=docker.io/docker/dockerfile:1

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ARG APP_UID=1000
RUN useradd -m -u "${APP_UID}" app \
  && mkdir -p /app \
  && chown -R app:app /app

WORKDIR /app

COPY --chown=app:app backend/pyproject.toml /app/pyproject.toml

USER app
RUN uv sync --no-dev
USER root

COPY --chown=app:app backend/app /app/app
COPY --chown=app:app backend/assets /app/assets
COPY --chown=app:app backend/alembic /app/alembic
COPY --chown=app:app backend/alembic.ini /app/alembic.ini

COPY --chown=app:app docker/backend/start.sh /app/start.sh
RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh

EXPOSE 8000

USER app

ENTRYPOINT []
CMD ["/app/start.sh"]
