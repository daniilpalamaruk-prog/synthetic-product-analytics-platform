from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


def deep_get(mapping: dict, path: str, default: Any = None) -> Any:
    value: Any = mapping
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value


def deep_merge(base: dict, extra: dict) -> dict:
    result = dict(base)
    for key, value in extra.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_model(config_dir: Path) -> dict:
    model: dict = {}
    for name in ("generation.yaml", "business_rules.yaml", "scenarios.yaml"):
        path = config_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Required config file not found: {path}")
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(value, dict):
            raise ValueError(f"Config root must be a mapping: {path}")
        model = deep_merge(model, value)
    return model


def model_hash(model: dict) -> str:
    payload = json.dumps(model, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()

