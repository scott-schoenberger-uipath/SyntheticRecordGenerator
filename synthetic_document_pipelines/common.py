from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


SYNTHETIC_BANNER = "SYNTHETIC / FICTIONAL / NOT FOR CLINICAL, BILLING, OR COVERAGE USE"


class SpecValidationError(ValueError):
    """Raised when an input does not meet the synthetic-only contract."""


def load_spec(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise SpecValidationError("Input JSON must be an object")
    return value


def require_synthetic(spec: Mapping[str, Any]) -> dict[str, Any]:
    metadata = spec.get("metadata")
    if not isinstance(metadata, dict) or metadata.get("is_synthetic") is not True:
        raise SpecValidationError("metadata.is_synthetic must be true")

    label = str(metadata.get("synthetic_label", "")).strip()
    if not label:
        raise SpecValidationError("metadata.synthetic_label is required")

    patient = spec.get("patient")
    if isinstance(patient, dict):
        identifier = str(patient.get("mrn", "")).strip().upper()
        if not identifier.startswith("SYN-"):
            raise SpecValidationError("patient.mrn must start with SYN- to guard against real-person input")
    return dict(metadata)


def require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SpecValidationError(f"{name} must be an object")
    return dict(value)


def require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise SpecValidationError(f"{name} must be a list")
    return value


def text(value: Any, default: str = "Not documented") -> str:
    rendered = str(value).strip() if value is not None else ""
    return rendered or default


def make_manifest(
    *,
    kind: str,
    input_path: Path,
    output_path: Path,
    metadata: Mapping[str, Any],
    details: Mapping[str, Any],
) -> dict[str, Any]:
    def display_path(path: Path) -> str:
        try:
            return str(path.resolve().relative_to(Path.cwd().resolve()))
        except ValueError:
            return str(path)

    return {
        "kind": kind,
        "synthetic": True,
        "synthetic_label": text(metadata.get("synthetic_label")),
        "input": display_path(input_path),
        "output": display_path(output_path),
        "output_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "details": dict(details),
    }


def write_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(dict(manifest), handle, indent=2)
        handle.write("\n")
