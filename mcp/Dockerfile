# sgnl-mcp in a container. Build from the repository root (the image needs both
# workspace packages):
#
#   docker build -f mcp/Dockerfile -t sgnl-mcp .
#
# The server speaks MCP over stdio, so run it with -i (see mcp/README.md):
#
#   docker run -i --rm --init --env-file ~/.sgnl-mcp.env -v sgnl-mcp-data:/data sgnl-mcp

ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS build
RUN pip install --no-cache-dir --disable-pip-version-check uv==0.9.5
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /src

# Third-party dependencies first, pinned by uv.lock, so code changes reuse this layer.
COPY pyproject.toml uv.lock ./
COPY mcp/pyproject.toml mcp/
RUN uv sync --frozen --no-dev --package sgnl-mcp --no-install-workspace

# Then sgnl-api and sgnl-mcp themselves, installed as regular (non-editable) packages.
COPY README.md LICENSE ./
COPY sgnl_api sgnl_api
COPY mcp/README.md mcp/
COPY mcp/sgnl_mcp mcp/sgnl_mcp
RUN uv sync --frozen --no-dev --package sgnl-mcp --no-editable


FROM python:${PYTHON_VERSION}-slim
LABEL org.opencontainers.image.title="sgnl-mcp" \
      org.opencontainers.image.description="MCP server for the SIGNAL Integration API" \
      org.opencontainers.image.source="https://github.com/gritsyuk/sgnl-api" \
      org.opencontainers.image.licenses="MIT"

# Unprivileged user. /data keeps the audit log and the idempotency journal;
# /uploads is where the host directory with files to upload is mounted.
RUN useradd --system --uid 10001 --create-home --home-dir /home/sgnl sgnl \
 && mkdir -p /data /uploads \
 && chown sgnl:sgnl /data

COPY --from=build /app/.venv /app/.venv

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SGNL_MCP_AUDIT_PATH=/data/audit.jsonl \
    SGNL_MCP_STATE_PATH=/data/state.sqlite \
    SGNL_MCP_UPLOAD_ROOT=/uploads

USER sgnl
WORKDIR /home/sgnl
VOLUME ["/data"]
ENTRYPOINT ["sgnl-mcp"]
