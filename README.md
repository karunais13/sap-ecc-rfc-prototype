# SAP ECC RFC MCP Server

A Python [MCP](https://modelcontextprotocol.io) server that exposes SAP ECC BAPIs as tools for AI agents. Built with **FastMCP v2** and **PyRFC**, it lets Claude (or any MCP client) read master data, create sales/purchase orders, and query arbitrary SAP tables — all through natural language.

Includes a full **mock mode** for development and testing without a live SAP system.

## Tools (18)

### Master Data (read-only)
| Tool | BAPI | Description |
|------|------|-------------|
| `get_material` | `BAPI_MATERIAL_GET_DETAIL` | Read material by number |
| `search_materials` | `BAPI_MATERIAL_GETLIST` | Search by description/type |
| `get_customer` | `BAPI_CUSTOMER_GETDETAIL2` | Read customer by number |
| `search_customers` | `BAPI_CUSTOMER_GETLIST` | Search by name/city |
| `get_vendor` | `BAPI_VENDOR_GETDETAIL` | Read vendor by number |
| `search_vendors` | `BAPI_VENDOR_GETLIST` | Search by name |

### Sales
| Tool | BAPI | Description |
|------|------|-------------|
| `get_sales_order` | `BAPI_SALESORDER_GETDETAIL` | Read SO header + items |
| `search_sales_orders` | `BAPI_SALESORDER_GETLIST` | Search by customer/date |
| `create_sales_order` | `BAPI_SALESORDER_CREATEFROMDAT2` | Create SO with COMMIT |
| `change_sales_order` | `BAPI_SALESORDER_CHANGE` | Update SO with COMMIT |

### Purchasing
| Tool | BAPI | Description |
|------|------|-------------|
| `get_purchase_order` | `BAPI_PO_GETDETAIL1` | Read PO header + items |
| `search_purchase_orders` | `BAPI_PO_GETITEMS` | Search by vendor/date |
| `create_purchase_order` | `BAPI_PO_CREATE1` | Create PO with COMMIT |

### Invoices
| Tool | BAPI | Description |
|------|------|-------------|
| `get_invoices` | `BAPI_INCOMINGINVOICE_GETLIST` | Search invoices |

### Generic RFC
| Tool | RFC | Description |
|------|-----|-------------|
| `describe_rfc` | `get_function_description` | Get FM parameter signature |
| `call_rfc` | *(any)* | Call any RFC-enabled FM dynamically |
| `read_table` | `RFC_READ_TABLE` | Read any SAP table with filters |

### Source Code
| Tool | RFC | Description |
|------|-----|-------------|
| `read_source` | `ZRFC_READ_SOURCE` | Read ABAP source of a program, include, or function module (auto-detects type; needs S_DEVELOP display authorization) |

## Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Install and run (mock mode)

```bash
git clone <repo-url> && cd sap-ecc-rfc-prototype
uv sync --extra dev
SAP_MOCK_MODE=true uv run sap-mcp
```

### Run tests

```bash
uv run pytest -v
```

### Claude Desktop integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sap-ecc": {
      "command": "uv",
      "args": ["--directory", "/path/to/sap-ecc-rfc-prototype", "run", "sap-mcp"],
      "env": {
        "SAP_MOCK_MODE": "true"
      }
    }
  }
}
```

Restart Claude Desktop and the 17 tools will appear.

## Hosting over HTTP (remote access by URL)

By default the server uses **stdio** (local subprocess). To make it reachable by
URL from other machines, run it with the **streamable-http** transport:

```bash
MCP_TRANSPORT=streamable-http \
MCP_HOST=0.0.0.0 \
MCP_PORT=8000 \
SAP_MOCK_MODE=true \
uv run sap-mcp
```

In HTTP mode the server is **multi-country**: it serves one MCP instance per
country at `http://<server-ip>:8000/mcp/{country_code}`, each with its own SAP
connection (see [Per-country routing](#per-country-routing) below).

### Per-country routing

Each country has a different SAP system, so connection settings are supplied via
a JSON file (mounted as a volume in Docker, path set by `SAP_COUNTRIES_FILE`,
default `/app/countries.json`). Copy the sample and edit it:

```bash
cp countries.sample.json countries.json
```

```json
{
  "my": { "ashost": "sap-my.company.com", "client": "100", "user": "RFC_USER", "passwd": "...", "mock_mode": false },
  "th": { "ashost": "sap-th.company.com", "client": "200", "user": "RFC_USER", "passwd": "...", "mock_mode": false },
  "id": { "ashost": "sap-id.company.com", "client": "300", "user": "RFC_USER", "passwd": "...", "mock_mode": false }
}
```

Per-country fields: `ashost`, `sysnr`, `client`, `user`, `passwd`, `lang`,
`mock_mode`, `connection_pool_size` (missing fields fall back to defaults). Each
code is then served at its own URL with an isolated connection pool:

| Endpoint | SAP system |
|----------|------------|
| `GET  /healthz` | health + list of served countries |
| `POST /mcp/my` | Malaysia |
| `POST /mcp/th` | Thailand |
| `POST /mcp/id` | Indonesia |

An unknown country code returns `404`. A request to `/mcp/id` can only ever reach
the Indonesia SAP system — no cross-country leakage.

> If `countries.json` is absent, the server falls back to a single `default`
> system built from the `SAP_*` env vars (served at `/mcp/default`).

### Run with Docker

```bash
cp countries.sample.json countries.json   # then edit per-country SAP settings

# docker-compose.yml runs the published image karunais13/sap-rfc-mcp:latest
docker compose up -d

docker compose pull         # update to the latest image
docker compose logs -f      # view logs
docker compose down         # stop
```

To build the image from source instead of pulling, use the `Dockerfile`
directly: `docker build --platform linux/amd64 -t sap-rfc-mcp .`

Endpoints: `http://<server-ip>:8000/mcp/{country_code}` and `/healthz`.

### Connecting a client to the URL

An MCP client that supports HTTP transport points at the country URL, e.g. a
Claude Desktop / Claude Code config:

```json
{
  "mcpServers": {
    "sap-my": { "type": "http", "url": "http://<server-ip>:8000/mcp/my" },
    "sap-th": { "type": "http", "url": "http://<server-ip>:8000/mcp/th" },
    "sap-id": { "type": "http", "url": "http://<server-ip>:8000/mcp/id" }
  }
}
```

### Behind a reverse proxy

The proxy forwards `/mcp/` to the container **without rewriting the path** so the
app can dispatch by country code. A sample nginx config is in
[`nginx.sample.conf`](nginx.sample.conf) — it preserves the path, disables
buffering (so SSE streams through), and has commented hooks for TLS + auth.

> **Security:** the HTTP server is **unauthenticated** and binds to `0.0.0.0`.
> Only expose it on a trusted network, or put it behind a reverse proxy (nginx,
> Caddy, Traefik) that adds TLS and an auth layer before opening it to the internet.

### Live SAP in Docker

The Docker image **bundles the SAP NWRFC SDK and PyRFC**, so it can connect to a
real SAP system — it just defaults to mock mode so it boots with no config.

Requirements:
- Place the SAP NWRFC SDK 7.50 **Linux x86-64** tarball at `nwrfcsdk.tar.gz` in
  the repo root before building (it extracts to a top-level `nwrfcsdk/` dir).
  This file is license-restricted and git-ignored — do not commit it.
- The image is **amd64-only** (the SDK has no arm64 build). On Apple Silicon it
  builds/runs under emulation; `docker compose` already pins `linux/amd64`.

Switch to live SAP per country by setting `"mock_mode": false` and the real
connection fields in `countries.json` (see [Per-country routing](#per-country-routing)),
then restart the container. Credentials live in that file, not in compose.

The PyRFC version is pinned via the `PYRFC_VERSION` build arg (default `v3.3.1`).

## Configuration

### Transport / HTTP settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | `stdio` for local clients, `streamable-http` for URL access |
| `MCP_HOST` | `0.0.0.0` | Bind address for HTTP transport |
| `MCP_PORT` | `8000` | Port for HTTP transport |
| `MCP_PATH` | `/mcp` | Base URL path; countries are served at `{MCP_PATH}/{code}` |
| `SAP_COUNTRIES_FILE` | `/app/countries.json` | Per-country SAP config (HTTP mode) |

### SAP settings (stdio mode / fallback)

In stdio mode (and as the fallback when no countries file exists) settings use
the `SAP_` env prefix and can be set via `.env` file or environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SAP_ASHOST` | `localhost` | SAP application server host |
| `SAP_SYSNR` | `00` | System number |
| `SAP_CLIENT` | `100` | SAP client |
| `SAP_USER` | `RFC_USER` | RFC user |
| `SAP_PASSWD` | *(empty)* | RFC password |
| `SAP_LANG` | `EN` | Logon language |
| `SAP_MOCK_MODE` | `true` | Use mock connection (no SAP needed) |
| `SAP_CONNECTION_POOL_SIZE` | `5` | Max concurrent RFC connections |

## Connecting to a Real SAP System

### 1. Install SAP NWRFC SDK

Download the SAP NW RFC SDK 7.50 from the [SAP Support Portal](https://support.sap.com/en/product/connectors/nwrfcsdk.html) for your platform (e.g. ARM64 for Apple Silicon).

```bash
# macOS example
sudo mkdir -p /usr/local/sap/nwrfcsdk
sudo tar xzf nwrfc750-macos-arm64.tar.gz -C /usr/local/sap/nwrfcsdk

export SAPNWRFC_HOME=/usr/local/sap/nwrfcsdk
export DYLD_LIBRARY_PATH=/usr/local/sap/nwrfcsdk/lib
```

### 2. Install PyRFC

PyRFC is not listed in `pyproject.toml` dependencies (the package is yanked on PyPI). Install it separately after the NWRFC SDK is in place:

```bash
pip install pyrfc
```

Verify:

```bash
python -c "from pyrfc import Connection; print('PyRFC OK')"
```

### 3. Run with real credentials

```bash
SAP_MOCK_MODE=false \
SAP_ASHOST=sap-server.company.com \
SAP_SYSNR=00 \
SAP_CLIENT=100 \
SAP_USER=RFC_USER \
SAP_PASSWD=secret \
uv run sap-mcp
```

## Architecture

```
src/sap_mcp/
├── server.py              # FastMCP entry point, registers tool modules
├── config.py              # Pydantic Settings (SAP_ env prefix)
├── connection/
│   ├── manager.py         # Thread-safe connection pool (acquire/release)
│   └── mock.py            # Mock connection with realistic SAP responses
├── bapi/
│   ├── return_handler.py  # BAPI RETURN parsing (E/A → error, W/S/I)
│   └── transaction.py     # COMMIT/ROLLBACK on same connection
└── tools/
    ├── generic_rfc.py     # describe_rfc, call_rfc, read_table
    ├── source_code.py     # read_source (ZRFC_READ_SOURCE)
    ├── master_data.py     # Materials, customers, vendors
    ├── sales.py           # Sales orders (read + create + change)
    ├── purchasing.py      # Purchase orders (read + create)
    └── invoices.py        # Invoice queries
```

### Key design decisions

- **Tool registration pattern**: Each tool module exports `register(mcp)` to avoid circular imports. Tools use `@mcp.tool()` inside `register()`.
- **Thread-safe connection pool**: FastMCP runs sync tools in a threadpool — `ConnectionManager` uses `threading.Lock` + `deque` to safely share connections. `acquire()` is a context manager that returns the connection to the pool on success and discards it on error.
- **COMMIT/ROLLBACK on same connection**: Write operations use `execute_bapi_with_commit()` which calls the BAPI, parses the RETURN, and commits or rolls back on the same connection — required by SAP's transaction model.
- **Number padding**: SAP expects zero-padded numbers (materials: 18 chars, customers/vendors: 10 chars). All tools pad automatically.

## Example Use Case: Stock Check and Auto-Reorder

An AI agent can combine tools to implement business logic. For example, checking stock levels and creating a purchase order when inventory is low:

1. **`read_table("MARD")`** — Read stock from the storage location table
2. **Agent logic** — Filter materials where unrestricted stock < threshold
3. **`get_material()`** — Look up details for each low-stock item
4. **`search_vendors()`** — Find a suitable vendor
5. **`create_purchase_order()`** — Create and commit a PO for the reorder

This flow is fully tested in `tests/test_stock_reorder_flow.py`.

## License

MIT
