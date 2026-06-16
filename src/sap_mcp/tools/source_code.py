"""Source code tools: read ABAP source of programs and function modules.

Backed by the custom RFC ``ZRFC_READ_SOURCE`` which auto-detects whether a name
is a function module or a report/include, runs an S_DEVELOP authority check, and
returns the source lines via the ET_SOURCE table (rows of ABAPTXT255).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from sap_mcp.connection.manager import pool as default_pool
from sap_mcp.connection.manager import ConnectionManager


def _line_text(row: object) -> str:
    """Extract the text of one ET_SOURCE row.

    ABAPTXT255 has a single field ``LINE``; depending on the RFC library the
    row may come back as a dict or as a bare string.
    """
    if isinstance(row, dict):
        return row.get("LINE", "")
    return str(row)


def register(mcp: FastMCP, pool: ConnectionManager = default_pool) -> None:

    @mcp.tool()
    def read_source(name: str, object_type: str = "AUTO") -> dict:
        """Read the ABAP source code of a program, include, or function module.

        Calls the custom RFC ZRFC_READ_SOURCE. With object_type 'AUTO' the
        server detects whether the name is a function module (and resolves it to
        the include that holds the code) or a report/include, then returns the
        source. The calling SAP user needs S_DEVELOP display (ACTVT 03)
        authorization for the object.

        Args:
            name: Object name — a function module (e.g. 'BAPI_MATERIAL_GET_DETAIL'),
                a report/program, or an include.
            object_type: 'AUTO' (default, auto-detect), 'FUNC' to force function
                module resolution, or 'PROG' for a report/include.

        Returns:
            Dictionary with the resolved object_type, the report/include actually
            read (read_name), the line count, the source as a single string, and
            the source as a list of lines.
        """
        with pool.acquire() as conn:
            try:
                result = conn.call(
                    "ZRFC_READ_SOURCE",
                    IV_NAME=name,
                    IV_TYPE=object_type.upper(),
                )
            except Exception as exc:  # noqa: BLE001 - surface ABAP exceptions cleanly
                # ZRFC_READ_SOURCE raises NOT_FOUND / NOT_AUTHORIZED, which pyrfc
                # turns into an ABAPApplicationError carrying a `.key`.
                key = getattr(exc, "key", "") or ""
                if key == "NOT_FOUND":
                    return {"error": f"Object '{name}' not found.", "name": name}
                if key == "NOT_AUTHORIZED":
                    return {
                        "error": f"Not authorized to read source of '{name}' "
                        "(S_DEVELOP display authorization required).",
                        "name": name,
                    }
                return {"error": str(exc), "name": name}

        lines = [_line_text(row) for row in result.get("ET_SOURCE", [])]

        return {
            "name": name,
            "object_type": result.get("EV_OBJECT_TYPE", ""),
            "read_name": result.get("EV_READ_NAME", ""),
            "line_count": result.get("EV_LINES", len(lines)),
            "source": "\n".join(lines),
            "lines": lines,
        }
