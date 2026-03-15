ARG SANDBOX_IMAGE=ghcr.io/poco-ai/sandbox
ARG SANDBOX_VARIANT=lite
FROM ${SANDBOX_IMAGE}:${SANDBOX_VARIANT}

# Re-declare ARG after FROM (required for multi-stage builds)
ARG SANDBOX_VARIANT

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN mkdir -p /app && chown -R ubuntu:ubuntu /app
WORKDIR /app

COPY --chown=ubuntu:ubuntu executor/pyproject.toml /app/pyproject.toml

USER ubuntu
RUN uv sync --no-dev
# Pre-install Playwright MCP for full variant to speed up cold start
RUN if [ "${SANDBOX_VARIANT:?}" = "full" ]; then \
      npx -y @playwright/mcp@latest --help > /dev/null 2>&1 || true; \
    fi
USER root

COPY --chown=ubuntu:ubuntu executor/app /app/app

COPY --chown=ubuntu:ubuntu docker/executor/start.sh /app/start.sh
RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh

EXPOSE 8000 8080

ENTRYPOINT []
CMD ["/app/start.sh"]
