"""Parse BAPI RETURN structures and extract errors/warnings/success messages."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BAPIResult:
    success: bool
    messages: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.errors:
            return "; ".join(self.errors)
        if self.warnings:
            return "; ".join(self.warnings)
        success_msgs = [
            m.get("MESSAGE", "") for m in self.messages if m.get("TYPE") == "S"
        ]
        if success_msgs:
            return "; ".join(msg for msg in success_msgs if msg)
        return "OK"


def parse_return(return_data: dict | list[dict] | None) -> BAPIResult:
    """Parse a BAPI RETURN structure or RETURN table.

    RETURN can be:
    - A single dict (RETURN structure)
    - A list of dicts (RETURN table)
    - None (no return provided)
    """
    if return_data is None:
        return BAPIResult(success=True)

    if isinstance(return_data, dict):
        messages = [return_data] if return_data.get("TYPE") else []
    elif isinstance(return_data, list):
        messages = [m for m in return_data if isinstance(m, dict) and m.get("TYPE")]
    else:
        return BAPIResult(success=True)

    errors = []
    warnings = []
    info = []

    for msg in messages:
        msg_type = msg.get("TYPE", "")
        msg_text = msg.get("MESSAGE", "")
        if not msg_text:
            msg_text = f"{msg.get('ID', '')}-{msg.get('NUMBER', '')}"

        if msg_type in ("E", "A"):  # Error or Abort
            errors.append(msg_text)
        elif msg_type == "W":
            warnings.append(msg_text)
        elif msg_type == "I":
            info.append(msg_text)

    return BAPIResult(
        success=len(errors) == 0,
        messages=messages,
        errors=errors,
        warnings=warnings,
        info=info,
    )
