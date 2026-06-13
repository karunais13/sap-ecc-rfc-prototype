# SAP ECC RFC MCP Server — served over HTTP for remote agents.
#
# This image bundles the SAP NWRFC SDK + PyRFC so it can talk to a LIVE SAP
# system (set SAP_MOCK_MODE=false and the SAP_* connection vars at run time).
# It still defaults to mock mode so it boots with no SAP configured.
#
# The NWRFC SDK is Linux x86-64 only, so the image MUST be built for amd64.
# On Apple Silicon / arm64 hosts build with:  docker build --platform linux/amd64 .
# (docker compose already pins the platform.)
FROM --platform=linux/amd64 python:3.11-slim

# Pin PyRFC source version (PyRFC is no longer published on PyPI).
ARG PYRFC_VERSION=v3.3.1
ENV SAPNWRFC_HOME=/usr/local/sap/nwrfcsdk

# uv from the official distroless image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Build toolchain for the PyRFC C-extension + git to fetch its source.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git \
    && rm -rf /var/lib/apt/lists/*

# Install the SAP NWRFC SDK and register its libs with the dynamic loader.
COPY nwrfcsdk.tar.gz /tmp/nwrfcsdk.tar.gz
RUN mkdir -p /usr/local/sap \
    && tar xzf /tmp/nwrfcsdk.tar.gz -C /usr/local/sap \
    && rm /tmp/nwrfcsdk.tar.gz \
    && echo "${SAPNWRFC_HOME}/lib" > /etc/ld.so.conf.d/nwrfcsdk.conf \
    && ldconfig

WORKDIR /app

# Install Python dependencies first (better layer caching), then the project.
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

# Build + install PyRFC from source into the project venv against the SDK.
RUN uv pip install cython \
    && uv pip install "git+https://github.com/SAP/PyRFC.git@${PYRFC_VERSION}"

# HTTP transport so the server is reachable by URL.
# SAP_COUNTRIES_FILE points at a JSON config mounted as a volume; each country
# is served at /mcp/{country_code}. If the file is absent the server falls back
# to a single "default" system from the SAP_ env vars (mock mode).
ENV MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    MCP_PATH=/mcp \
    SAP_COUNTRIES_FILE=/app/countries.json \
    SAP_MOCK_MODE=true

EXPOSE 8000

CMD ["uv", "run", "sap-mcp"]
