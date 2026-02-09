# syntax=docker.io/docker/dockerfile:1

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ARG APP_UID=1000
RUN useradd -m -u "${APP_UID}" app \
  && mkdir -p /app \
  && chown -R app:app /app

WORKDIR /app

COPY --chown=app:app im/pyproject.toml /app/pyproject.toml

USER app
RUN uv sync --no-dev
USER root

COPY --chown=app:app im/app /app/app
COPY --chown=app:app im/README.md /app/README.md

COPY --chown=app:app docker/im/start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 8002

USER app

ENTRYPOINT []
CMD ["/app/start.sh"]

