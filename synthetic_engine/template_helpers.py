from __future__ import annotations

import re
from typing import Any, Dict

PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_\.\-]+)\s*\}\}")


def lookup_path(data: Dict[str, Any], path: str) -> Any:
    parts = path.split(".")
    value: Any = data
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list):
            try:
                idx = int(part)
            except ValueError:
                return None
            if idx < 0 or idx >= len(value):
                return None
            value = value[idx]
        else:
            return None
    return value


def _resolve_string(value: str, payload: Dict[str, Any]) -> Any:
    only = PLACEHOLDER_RE.fullmatch(value.strip())
    if only:
        resolved = lookup_path(payload, only.group(1))
        return "" if resolved is None else resolved

    def repl(match: re.Match[str]) -> str:
        resolved = lookup_path(payload, match.group(1))
        if resolved is None:
            return ""
        if isinstance(resolved, (dict, list)):
            return str(resolved)
        return str(resolved)

    return PLACEHOLDER_RE.sub(repl, value)


def resolve_placeholders(value: Any, payload: Dict[str, Any]) -> Any:
    if isinstance(value, str):
        return _resolve_string(value, payload)
    if isinstance(value, list):
        return [resolve_placeholders(v, payload) for v in value]
    if isinstance(value, dict):
        return {k: resolve_placeholders(v, payload) for k, v in value.items()}
    return value


def collect_placeholders(value: Any) -> set[str]:
    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, str):
            for m in PLACEHOLDER_RE.finditer(node):
                found.add(m.group(1))
            return
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if isinstance(node, dict):
            for item in node.values():
                walk(item)

    walk(value)
    return found
