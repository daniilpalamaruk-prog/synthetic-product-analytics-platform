"""Small JSON-contract validator used at the ingestion boundary.

The repository intentionally avoids a runtime dependency on a full JSON Schema
engine.  It enforces the contract subset used here: required fields, primitive
types, enums, minimums and regular-expression patterns.  CI still treats the
JSON files as the source of truth.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any


class ContractViolation(ValueError):
    pass


def load_contract(name: str, root: Path = Path("contracts")) -> dict[str, Any]:
    return json.loads((root / f"{name}.schema.json").read_text(encoding="utf-8"))


def validate_record(record: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in contract.get("required", []):
        if field not in record or record[field] is None:
            errors.append(f"{field}: required")
    for field, rule in contract.get("properties", {}).items():
        if field not in record:
            continue
        value = record[field]
        allowed_types = rule.get("type")
        if allowed_types:
            names = [allowed_types] if isinstance(allowed_types, str) else allowed_types
            mapping = {"string": str, "number": (int, float), "integer": int,
                       "boolean": bool, "null": type(None), "object": dict, "array": list}
            format_accepts_temporal = (
                "string" in names and rule.get("format") in {"date", "date-time"}
                and isinstance(value, (date, datetime))
            )
            if not format_accepts_temporal and not any(isinstance(value, mapping[name]) for name in names):
                errors.append(f"{field}: expected {'/'.join(names)}")
                continue
        if "enum" in rule and value not in rule["enum"]:
            errors.append(f"{field}: not in allowed enum")
        if "minimum" in rule and value < rule["minimum"]:
            errors.append(f"{field}: below minimum")
        if "exclusiveMinimum" in rule and value <= rule["exclusiveMinimum"]:
            errors.append(f"{field}: must exceed minimum")
        if "pattern" in rule and isinstance(value, str) and not re.search(rule["pattern"], value):
            errors.append(f"{field}: pattern mismatch")
    return errors


def require_valid(record: dict[str, Any], contract: dict[str, Any]) -> None:
    errors = validate_record(record, contract)
    if errors:
        raise ContractViolation("; ".join(errors))
