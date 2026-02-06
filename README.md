# SAP ECC RFC MCP Server

A Python [MCP](https://modelcontextprotocol.io) server that exposes SAP ECC BAPIs as tools for AI agents. Built with **FastMCP v2** and **PyRFC**, it lets Claude (or any MCP client) read master data, create sales/purchase orders, and query arbitrary SAP tables — all through natural language.

Includes a full **mock mode** for development and testing without a live SAP system.

## Tools (17)

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

## Configuration

All settings use the `SAP_` env prefix and can be set via `.env` file or environment variables:

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
