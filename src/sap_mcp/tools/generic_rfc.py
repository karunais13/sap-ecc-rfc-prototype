"""Generic RFC tools: describe_rfc, call_rfc, read_table."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from sap_mcp.connection.manager import pool as default_pool
from sap_mcp.connection.manager import ConnectionManager


def register(mcp: FastMCP, pool: ConnectionManager = default_pool) -> None:

    @mcp.tool()
    def describe_rfc(function_name: str) -> dict:
        """Get the parameter signature of an SAP RFC function module.

        Args:
            function_name: RFC function module name (e.g. 'BAPI_MATERIAL_GET_DETAIL')

        Returns:
            Dictionary with function name and list of parameters including
            name, direction, type, length, and description.
        """
        with pool.acquire() as conn:
            desc = conn.get_function_description(function_name)
            params = []
            for p in desc.parameters:
                params.append({
                    "name": p["name"] if isinstance(p, dict) else p.name,
                    "direction": p["direction"] if isinstance(p, dict) else p.direction,
                    "parameter_type": p["parameter_type"] if isinstance(p, dict) else p.parameter_type,
                    "optional": p["optional"] if isinstance(p, dict) else p.optional,
                    "parameter_text": p["parameter_text"] if isinstance(p, dict) else p.parameter_text,
                    "default_value": p["default_value"] if isinstance(p, dict) else p.default_value,
                })
            return {"function_name": desc.name, "parameters": params}

    @mcp.tool()
    def call_rfc(function_name: str, parameters: dict[str, Any] | None = None) -> dict:
        """Call any RFC-enabled SAP function module dynamically.

        Use describe_rfc first to understand the function's parameters.

        Args:
            function_name: RFC function module name
            parameters: Dictionary of input parameters to pass to the function

        Returns:
            Raw RFC result as a dictionary.
        """
        with pool.acquire() as conn:
            return conn.call(function_name, **(parameters or {}))

    @mcp.tool()
    def read_table(
        table_name: str,
        fields: list[str] | None = None,
        where_clauses: list[str] | None = None,
        max_rows: int = 100,
        delimiter: str = "|",
    ) -> dict:
        """Read data from any SAP table using RFC_READ_TABLE.

        Args:
            table_name: SAP table name (e.g. 'MARA', 'KNA1', 'VBAK')
            fields: List of field names to return. If None, returns all fields.
            where_clauses: List of ABAP WHERE conditions (e.g. ["MATNR = '100'"])
            max_rows: Maximum number of rows to return (default 100)
            delimiter: Field delimiter (default '|')

        Returns:
            Dictionary with 'fields' (list of field info) and 'rows' (list of dicts).
        """
        params: dict[str, Any] = {
            "QUERY_TABLE": table_name,
            "DELIMITER": delimiter,
            "ROWCOUNT": max_rows,
        }

        if fields:
            params["FIELDS"] = [{"FIELDNAME": f} for f in fields]

        if where_clauses:
            params["OPTIONS"] = [{"TEXT": clause} for clause in where_clauses]

        with pool.acquire() as conn:
            result = conn.call("RFC_READ_TABLE", **params)

        # Parse pipe-delimited output into dicts
        field_info = result.get("FIELDS", [])
        field_names = [f["FIELDNAME"] for f in field_info]
        data_rows = result.get("DATA", [])

        rows = []
        for row in data_rows:
            wa = row.get("WA", "")
            values = [v.strip() for v in wa.split(delimiter)]
            row_dict = {}
            for i, fname in enumerate(field_names):
                row_dict[fname] = values[i] if i < len(values) else ""
            rows.append(row_dict)

        return {
            "table": table_name,
            "fields": field_names,
            "row_count": len(rows),
            "rows": rows,
        }
