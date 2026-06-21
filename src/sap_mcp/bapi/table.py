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
