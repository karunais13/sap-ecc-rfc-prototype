"""BAPI transaction handling — COMMIT and ROLLBACK on the same connection."""

from __future__ import annotations

from typing import Any

from sap_mcp.bapi.return_handler import BAPIResult, parse_return


def commit_transaction(conn: Any) -> None:
    conn.call("BAPI_TRANSACTION_COMMIT", WAIT="X")


def rollback_transaction(conn: Any) -> None:
    conn.call("BAPI_TRANSACTION_ROLLBACK")


def execute_bapi_with_commit(
    conn: Any,
    func_name: str,
    return_key: str = "RETURN",
    **params: Any,
) -> tuple[dict, BAPIResult]:
    """Call a BAPI, parse RETURN, and commit or rollback on the same connection.

    Returns the full RFC result dict and the parsed BAPIResult.
    """
    result = conn.call(func_name, **params)
    bapi_result = parse_return(result.get(return_key))

    if bapi_result.success:
        commit_transaction(conn)
    else:
        rollback_transaction(conn)

    return result, bapi_result
