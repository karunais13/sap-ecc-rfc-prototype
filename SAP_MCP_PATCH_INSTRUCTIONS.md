# SAP RFC MCP Server — Patch Instructions

**Repo:** `karunais13/sap-ecc-rfc-prototype`
**Target system observed:** SAP **S/4HANA**, release **758** (`npmsap1` / P01, MY gateway).
**Verified:** 2026-06-21, by live RFC testing against the MY system.
**Author of report:** automated diagnostics run (Claude Code).

> **Why this matters:** the server is labelled "SAP ECC" but the live box is **S/4HANA**.
> Several convenience tools were coded against assumed ECC BAPI signatures that do
> not match the function modules actually installed on this S/4 system. Each failure
> below was reproduced live and the *correct* interface was confirmed by reading
> table `FUPARAREF` (the FM parameter dictionary) on the system itself — so the fixes
> are verified, not guessed.

---

## 0. Important: deployment drift

The deployed MY server is **ahead of this repo** for at least one tool:
`search_sales_orders` returns rich item-level data live (SD_DOC, MATERIAL, SHORT_TEXT,
NET_VALUE…) that the repo's `BAPI_SALESORDER_GETLIST` call would not produce. So the
running server already contains edits not in `main`. **Before patching, reconcile the
deployed source with the repo** (or patch directly on the deployed copy). Line numbers
here refer to the current repo `main`.

---

## 1. Summary of all tools (tested live)

| Tool | File | Status | Root cause |
|---|---|---|---|
| `read_table` | generic_rfc.py | ✅ OK | — |
| `read_source` | source_code.py | ✅ OK | — |
| `call_rfc` | generic_rfc.py | ✅ OK | — |
| `get_customer` | master_data.py | ✅ OK | returns ADDRESS ref (by design) |
| `get_vendor` | master_data.py | ✅ OK | — |
| `search_sales_orders` | sales.py | ✅ OK (deployed) | works live; repo code differs |
| `describe_rfc` | generic_rfc.py | ⚠️ Partial | pyrfc library `long` bug on some FMs |
| `get_material` | master_data.py | ⚠️ Partial | unconditional `zfill(18)` corrupts alphanumeric matnr |
| `get_sales_order` | sales.py | ❌ Broken | `BAPI_SALESORDER_GETDETAIL` not RFC-installed |
| `get_purchase_order` | purchasing.py | ❌ Broken | reads wrong result keys (`PO_HEADER`/`PO_ITEMS`) |
| `get_invoices` | invoices.py | ❌ Broken | wrong BAPI (MM, not SD) + invalid params |
| `search_customers` | master_data.py | ❌ Broken | `BAPI_CUSTOMER_GETLIST` has no NAME/CITY input |
| `search_materials` | master_data.py | ❌ Broken | invalid params `MATNR_RA`/`MATERIAL_DESCRIPTION` |
| `search_purchase_orders` | purchasing.py | ❌ Broken | invalid params `DOC_DATE_FROM`/`DOC_DATE_TO` |
| `search_vendors` | master_data.py | ❌ Broken | `BAPI_VENDOR_GETLIST` not RFC-installed |

Create-tools (`create_sales_order`, `create_purchase_order`, `change_sales_order`)
were **not** tested (out of scope) — but note they share the same `zfill(18)`
material-padding bug (see §2) and will fail for alphanumeric materials. Apply the
same `_pad_material` fix there.

---

## 2. Add a shared, padding-safe material helper

Several tools pad materials with `zfill(18)`. On S/4 this corrupts every
alphanumeric / lexical material number. Replace the helper everywhere.

**`src/sap_mcp/tools/master_data.py`** (and reuse in `sales.py`, `purchasing.py`):

```python
def _pad_material(number: str) -> str:
    """Format a material number for SAP internal use.

    Numeric material numbers are stored zero-padded to 18 chars; alphanumeric
    (lexical) numbers are stored left-justified, UPPERCASE, with NO padding.
    Blindly zfill-ing corrupts alphanumeric matnr (e.g. CC132 -> 0000000000000CC132).
    """
    n = number.strip().upper()
    return n.zfill(18) if n.isdigit() else n
```

> If you maintain copies of this helper in `sales.py` / `purchasing.py`
> (`item["material"].zfill(18)` appears in the create tools), replace those inline
> calls with `_pad_material(item["material"])` too.

---

## 3. `get_material` — fix padding + support long matnr

**File:** `src/sap_mcp/tools/master_data.py` (lines ~22-38)

**Why:** `_pad_material` corrupted alphanumeric materials (confirmed: `CC132` failed
as `0000000000000CC132`; numeric `9705` worked). S/4 also has 40-char `MATNR_LONG`.

**Replace the body with:**

```python
@mcp.tool()
def get_material(material_number: str) -> dict:
    """Read material master data by material number."""
    n = material_number.strip().upper()
    if len(n) > 18:                       # S/4 long material number
        kwargs = {"MATERIAL_LONG": n}
    else:
        kwargs = {"MATERIAL": _pad_material(n)}
    with pool.acquire() as conn:
        result = conn.call("BAPI_MATERIAL_GET_DETAIL", **kwargs)
    bapi = parse_return(result.get("RETURN"))
    if not bapi.success:
        return {"error": bapi.summary}
    return {"material": result.get("MATERIAL_GENERAL_DATA", {})}
```

**Verify:** `get_material("CC132")` → returns ZCCM material; `get_material("9705")`
→ still returns the FERT material.

---

## 4. `get_purchase_order` — fix result keys

**File:** `src/sap_mcp/tools/purchasing.py` (lines ~31-40)

**Why:** `BAPI_PO_GETDETAIL1` exports **`POHEADER`** (structure `BAPIMEPOHEADER`) and
table **`POITEM`** (`BAPIMEPOITEM`) — confirmed via FUPARAREF. The code reads
non-existent keys `PO_HEADER` / `PO_ITEMS`, so it always returned empty.

**Replace:**

```python
        padded = _pad_po(purchase_order_number)
        with pool.acquire() as conn:
            result = conn.call("BAPI_PO_GETDETAIL1", PURCHASEORDER=padded)
        bapi = parse_return(result.get("RETURN"))
        if not bapi.success:
            return {"error": bapi.summary}
        return {
            "header": result.get("POHEADER", {}),
            "items": result.get("POITEM", []),
        }
```

(`POITEM` is returned by default — no item flag needed. There is no `ITEMS='X'`
parameter on this BAPI.)

**Verify:** `get_purchase_order("4500064165")` → header populated + 1 item (MATNR
`S016`, "DOWANOL PMA").

---

## 5. `search_purchase_orders` — remove invalid date-range params

**File:** `src/sap_mcp/tools/purchasing.py` (lines ~58-69)

**Why:** `BAPI_PO_GETITEMS` has a single scalar **`DOC_DATE`** (no `_FROM`/`_TO`).
Passing `DOC_DATE_FROM` triggered `RFC_INVALID_PARAMETER`. `VENDOR` and the output
table `PO_ITEMS` are correct.

**Minimal fix (keeps the BAPI):**

```python
        params: dict[str, Any] = {}
        if vendor_number:
            params["VENDOR"] = vendor_number.zfill(10)
        if date_from:
            params["DOC_DATE"] = date_from     # BAPI supports an exact date only
        with pool.acquire() as conn:
            result = conn.call("BAPI_PO_GETITEMS", **params)
        items = result.get("PO_ITEMS", [])
        return {"purchase_order_items": items, "count": len(items)}
```

**Preferred fix (true date range):** reimplement on `read_table` EKKO →
`AEDAT BETWEEN date_from AND date_to` (and `LIFNR` if vendor given) then EKPO. See the
`query_table` helper in §10.

**Verify:** `search_purchase_orders(vendor_number="124543")` → returns items without error.

---

## 6. `get_invoices` — wrong BAPI; reimplement on VBRK/VBRP

**File:** `src/sap_mcp/tools/invoices.py`

**Why:** `BAPI_INCOMINGINVOICE_GETLIST` is for **MM incoming (vendor/MIRO) invoices**,
not SD customer billing, and uses none of `COMP_CODE` / `REF_DOC` / `DOC_DATE_FROM`
(all rejected live). The tool's documented purpose ("invoices by company code / date /
reference sales order") is SD billing → tables **VBRK** (header) + **VBRP** (items).

**Replace the whole tool with a read_table implementation** (uses `query_table`, §10):

```python
@mcp.tool()
def get_invoices(
    company_code: str = "",
    date_from: str = "",
    date_to: str = "",
    reference_document: str = "",
) -> dict:
    """Search SD billing documents (invoices) by company code, date, or source order."""
    with pool.acquire() as conn:
        # reference_document = the originating sales order -> resolve via VBRP-AUBEL
        if reference_document:
            items = query_table(
                conn, "VBRP",
                ["VBELN", "POSNR", "AUBEL", "MATNR", "ARKTX", "FKIMG", "NETWR"],
                [f"AUBEL = '{reference_document.zfill(10)}'"],
            )
            return {"invoices": items, "count": len(items)}

        where = []
        if company_code:
            where.append(f"BUKRS = '{company_code}'")
        if date_from and date_to:
            where.append(f"FKDAT >= '{date_from}' AND FKDAT <= '{date_to}'")
        elif date_from:
            where.append(f"FKDAT >= '{date_from}'")
        headers = query_table(
            conn, "VBRK",
            ["VBELN", "FKART", "FKDAT", "KUNAG", "NETWR", "MWSBK", "WAERK", "VBTYP"],
            [" AND ".join(where)] if where else None,
            max_rows=200,
        )
    return {"invoices": headers, "count": len(headers)}
```

**Verify:** `get_invoices(reference_document="1110000022")` → returns the billing
item(s); `get_invoices(company_code="2000", date_from="20250519", date_to="20250519")`
→ returns headers without error.

---

## 7. `search_customers` — reimplement on KNA1 (BAPI has no name filter)

**File:** `src/sap_mcp/tools/master_data.py` (lines ~82-96)

**Why:** `BAPI_CUSTOMER_GETLIST`'s only input is `IDRANGE` (a customer-**number**
range, confirmed via FUPARAREF) — it **cannot filter by name or city**. Passing
`NAME` raised `RFC_INVALID_PARAMETER`.

**Replace with:**

```python
@mcp.tool()
def search_customers(name: str = "", city: str = "") -> dict:
    """Search customers by name and/or city (KNA1; descriptions stored UPPERCASE)."""
    where = []
    if name:
        where.append(f"NAME1 LIKE '%{name.upper()}%'")
    if city:
        where.append(f"ORT01 LIKE '%{city.upper()}%'")
    with pool.acquire() as conn:
        rows = query_table(
            conn, "KNA1",
            ["KUNNR", "NAME1", "ORT01", "LAND1", "STCD1"],
            [" AND ".join(where)] if where else None,
            max_rows=50,
        )
    return {"customers": rows, "count": len(rows)}
```

> Note: if `NAME1` is blank in KNA1 on this system, fall back to searching ADRC by
> `NAME1` and mapping `ADDRNUMBER` back to `KNA1-ADRNR` (see the project customer
> playbook). For most rows KNA1-NAME1 is populated.

**Verify:** `search_customers(name="HIAP LOONG CHAN")` → returns customer `637976`.

---

## 8. `search_materials` — reimplement on MAKT/MARA

**File:** `src/sap_mcp/tools/master_data.py` (lines ~40-62)

**Why:** real `BAPI_MATERIAL_GETLIST` inputs are range tables `MATNRSELECTION` /
`MATERIALSHORTDESCSEL` (not `MATNR_RA` / `MATERIAL_DESCRIPTION`), and its output
`MATNRLIST` carries only material numbers (no description). Text search is far cleaner
on `MAKT`.

**Replace with:**

```python
@mcp.tool()
def search_materials(description: str = "", material_type: str = "") -> dict:
    """Search materials by description (MAKT) and/or material type (MARA)."""
    with pool.acquire() as conn:
        if description:
            rows = query_table(
                conn, "MAKT",
                ["MATNR", "MAKTX", "SPRAS"],
                [f"MAKTX LIKE '%{description.upper()}%' AND SPRAS = 'E'"],
                max_rows=50,
            )
        else:
            rows = []
        if material_type:
            mat = query_table(
                conn, "MARA", ["MATNR", "MTART", "MEINS"],
                [f"MTART = '{material_type.upper()}'"], max_rows=50,
            )
            if description:                       # intersect by MATNR
                keep = {r["MATNR"] for r in mat}
                rows = [r for r in rows if r["MATNR"] in keep]
            else:
                rows = mat
    return {"materials": rows, "count": len(rows)}
```

**Verify:** `search_materials(description="ECO 100 ORGANIC YELLOW")` → returns `CC132`.

---

## 9. `get_sales_order` & `search_vendors` — FU_NOT_FOUND, reimplement on tables

**Why:** `BAPI_SALESORDER_GETDETAIL` and `BAPI_VENDOR_GETLIST` are **not
RFC-enabled/installed** on this S/4 system (`FU_NOT_FOUND`). No parameter change helps.

### 9a. `get_sales_order` — `src/sap_mcp/tools/sales.py` (lines ~21-40)

```python
@mcp.tool()
def get_sales_order(sales_order_number: str) -> dict:
    """Read a sales order header (VBAK) and items (VBAP)."""
    vbeln = sales_order_number.zfill(10)
    with pool.acquire() as conn:
        header = query_table(
            conn, "VBAK",
            ["VBELN", "AUART", "ERDAT", "KUNNR", "NETWR", "WAERK",
             "VKORG", "VTWEG", "SPART", "BSTNK"],
            [f"VBELN = '{vbeln}'"],
        )
        items = query_table(
            conn, "VBAP",
            ["VBELN", "POSNR", "MATNR", "ARKTX", "KWMENG", "VRKME",
             "NETWR", "WERKS", "PSTYV", "ABGRU"],
            [f"VBELN = '{vbeln}'"], max_rows=200,
        )
    if not header:
        return {"error": f"Sales order {vbeln} not found in VBAK"}
    return {"header": header[0], "items": items}
```

**Verify:** `get_sales_order("1110000022")` → header (cust 637976, net 1423.30) + 15 items.

### 9b. `search_vendors` — `src/sap_mcp/tools/master_data.py` (lines ~116-129)

```python
@mcp.tool()
def search_vendors(name: str = "") -> dict:
    """Search vendors by name (LFA1; descriptions stored UPPERCASE)."""
    where = [f"NAME1 LIKE '%{name.upper()}%'"] if name else None
    with pool.acquire() as conn:
        rows = query_table(
            conn, "LFA1",
            ["LIFNR", "NAME1", "ORT01", "LAND1", "STCD1"],
            where, max_rows=50,
        )
    return {"vendors": rows, "count": len(rows)}
```

**Verify:** `search_vendors(name="NIPPON PAINT")` → returns vendor `124543` and others.

---

## 10. Shared `query_table` helper (needed by §5–§9)

Extract the existing `read_table` parsing (in `generic_rfc.py`) into a reusable
function so the rewrites above don't duplicate RFC_READ_TABLE plumbing.

**New file `src/sap_mcp/bapi/table.py`:**

```python
"""Reusable RFC_READ_TABLE helper."""
from __future__ import annotations
from typing import Any


def query_table(conn, table_name: str, fields: list[str] | None = None,
                where_clauses: list[str] | None = None, max_rows: int = 100,
                delimiter: str = "|") -> list[dict]:
    """Run RFC_READ_TABLE and return a list of row dicts (keyed by field name)."""
    params: dict[str, Any] = {
        "QUERY_TABLE": table_name, "DELIMITER": delimiter, "ROWCOUNT": max_rows,
    }
    if fields:
        params["FIELDS"] = [{"FIELDNAME": f} for f in fields]
    if where_clauses:
        params["OPTIONS"] = [{"TEXT": c} for c in where_clauses]
    result = conn.call("RFC_READ_TABLE", **params)
    field_names = [f["FIELDNAME"] for f in result.get("FIELDS", [])]
    rows = []
    for row in result.get("DATA", []):
        values = [v.strip() for v in row.get("WA", "").split(delimiter)]
        rows.append({fn: (values[i] if i < len(values) else "")
                     for i, fn in enumerate(field_names)})
    return rows
```

Then in each tool file add: `from sap_mcp.bapi.table import query_table`, and refactor
`generic_rfc.read_table` to call it (keeps one parser).

> **WHERE-clause caveat (RFC_READ_TABLE):** put multiple conditions in **one** string
> joined by `AND`/`OR` (as the rewrites do). Keep each `OPTIONS` line ≤ 72 chars; if a
> clause is longer, split at a space across multiple list elements with the connector
> word attached. Use UPPERCASE in `LIKE` patterns (SAP text is case-sensitive and
> stored uppercase).

---

## 11. `describe_rfc` — library-level `long` bug

**File:** `src/sap_mcp/tools/generic_rfc.py` (line ~27, `conn.get_function_description`)

**Symptom:** for some FMs (e.g. `BAPI_SALESORDER_GETLIST`) the call raises
`name 'long' is not defined`. `long` is a **Python-2 type** that the installed
**pyrfc** still references when describing 8-byte integer (INT8) fields present in
newer S/4 interfaces. This is in the library/runtime, not your app code.

**Fixes (do one or both):**
1. **Upgrade the runtime:** bump `pyrfc` to a current release and rebuild against an
   up-to-date SAP NW RFC SDK in the Dockerfile. Confirm on Python 3.x.
2. **Add a fallback** so the tool degrades gracefully instead of erroring:

```python
@mcp.tool()
def describe_rfc(function_name: str) -> dict:
    try:
        with pool.acquire() as conn:
            desc = conn.get_function_description(function_name)
            params = [{
                "name": p["name"] if isinstance(p, dict) else p.name,
                "direction": p["direction"] if isinstance(p, dict) else p.direction,
                "parameter_type": p["parameter_type"] if isinstance(p, dict) else p.parameter_type,
                "optional": p["optional"] if isinstance(p, dict) else p.optional,
                "parameter_text": p["parameter_text"] if isinstance(p, dict) else p.parameter_text,
                "default_value": p["default_value"] if isinstance(p, dict) else p.default_value,
            } for p in desc.parameters]
            return {"function_name": desc.name, "parameters": params}
    except Exception as exc:
        # Fallback: read the FM parameter dictionary directly (avoids pyrfc metadata bug)
        from sap_mcp.bapi.table import query_table
        with pool.acquire() as conn:
            rows = query_table(
                conn, "FUPARAREF",
                ["PARAMETER", "PARAMTYPE", "STRUCTURE", "OPTIONAL", "DEFAULTVAL"],
                [f"FUNCNAME = '{function_name.upper()}'"], max_rows=200,
            )
        return {"function_name": function_name, "source": "FUPARAREF",
                "warning": f"pyrfc describe failed: {exc}", "parameters": rows}
```

**Verify:** `describe_rfc("BAPI_SALESORDER_GETLIST")` → returns a parameter list
(via fallback) instead of raising.

---

## 12. Test checklist (run after patching, against the MY system)

| Call | Expected |
|---|---|
| `get_material("CC132")` | ZCCM material returned |
| `get_material("9705")` | FERT material still returned |
| `get_purchase_order("4500064165")` | header + item `S016` |
| `search_purchase_orders(vendor_number="124543")` | items, no error |
| `get_invoices(reference_document="1110000022")` | billing item(s) |
| `get_invoices(company_code="2000", date_from="20250519", date_to="20250519")` | headers, no error |
| `search_customers(name="HIAP LOONG CHAN")` | customer `637976` |
| `search_materials(description="ECO 100 ORGANIC YELLOW")` | `CC132` |
| `get_sales_order("1110000022")` | header + 15 items |
| `search_vendors(name="NIPPON PAINT")` | vendor `124543` |
| `describe_rfc("BAPI_SALESORDER_GETLIST")` | parameter list, no `long` error |

Also update the unit tests in `tests/test_tools.py` to assert the new result keys
(`POHEADER`/`POITEM`, VBRK/VBRP fields, etc.) and the alphanumeric-material path.

---

## 13. Priority / risk

| # | Tool | Effort | Risk | Priority |
|---|---|---|---|---|
| 3 | get_material | 2-line helper | Very low | **P0** |
| 4 | get_purchase_order | 2-line keys | Very low | **P0** |
| 5 | search_purchase_orders | small | Low | P1 |
| 6 | get_invoices | rewrite | Low (read-only) | P1 |
| 7 | search_customers | rewrite | Low | P1 |
| 8 | search_materials | rewrite | Low | P1 |
| 9 | get_sales_order / search_vendors | rewrite | Low | P1 |
| 10 | query_table helper | new util | Low | P0 (enables 5–9) |
| 11 | describe_rfc | lib upgrade + fallback | Medium (Docker rebuild) | P2 |

P0 items are tiny and unblock the rest. All rewrites are **read-only** (RFC_READ_TABLE),
so functional risk is low. Re-run §12 against the **ID** and **TH** gateways too — they
are also labelled "ECC"; confirm whether they are ECC or S/4 and whether the same FMs
are installed there before assuming identical behaviour.
