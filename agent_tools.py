"""Typed, synthetic-only generation tools for agent and workflow callers."""

from __future__ import annotations

import hashlib
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator

from synthetic_document_pipelines.common import SYNTHETIC_BANNER
from synthetic_document_pipelines.policies import generate_policy
from synthetic_document_pipelines.records import generate_record_packet
from synthetic_engine import build_seeded_encounter
from synthetic_engine.orchestrator import PacketOrchestrator
from synthetic_engine.template_catalog import TemplateCatalog


PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = "output"
SAFE_STEM = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
MAX_RECORD_DOCUMENTS = 25
MAX_POLICY_SECTIONS = 20
MAX_CATALOG_FAMILIES = 13


class _ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output_root: str = Field(
        default=DEFAULT_OUTPUT_ROOT,
        description="Directory where the agent should write generated artifacts.",
    )
    output_stem: str = Field(
        default="synthetic_document",
        description="Safe lowercase filename stem, without an extension.",
    )

    @field_validator("output_stem")
    @classmethod
    def validate_output_stem(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not SAFE_STEM.fullmatch(normalized):
            raise ValueError("output_stem must contain only lowercase letters, numbers, hyphens, and underscores")
        return normalized


class RecordPacketToolInput(_ToolInput):
    """Input for a single, consolidated synthetic record packet."""

    output_stem: str = "synthetic_record_packet"
    spec: dict[str, Any] = Field(
        ...,
        description=(
            "Complete synthetic record specification. metadata.is_synthetic must be true, "
            "patient.mrn must start with SYN-, and documents are emitted in supplied order."
        ),
    )


class MedicalPolicyToolInput(_ToolInput):
    """Input for a single synthetic medical-policy PDF."""

    output_stem: str = "synthetic_medical_policy"
    spec: dict[str, Any] = Field(
        ...,
        description="Complete synthetic policy specification. metadata.is_synthetic must be true.",
    )


class CatalogPacketToolInput(_ToolInput):
    """High-level input for a seeded, template-catalog synthetic packet."""

    output_stem: str = "synthetic_catalog_packet"
    profile: str = Field(
        default="provider_packet_full",
        description="Template-catalog profile. Ignored when families is supplied.",
    )
    scenario: Literal["provider_sepsis", "resp_failure", "lumbar_mri_appeal"] = "provider_sepsis"
    seed: int = Field(default=20260310, ge=1, le=2_147_483_647)
    record_label: Literal["A", "B", "C"] = "A"
    families: list[str] = Field(
        default_factory=list,
        max_length=MAX_CATALOG_FAMILIES,
        description="Optional document-family override. Omit for the selected profile.",
    )
    packet_order: Literal["received_order", "profile_order"] = "received_order"
    apply_realism: bool = Field(
        default=True,
        description="Apply deterministic scan/noise realism where a template calls for it.",
    )
    include_handwriting: bool = Field(
        default=False,
        description="Use only repository-provided synthetic handwriting on scanned attachment templates.",
    )


class AgentToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"
    tool: Literal["record_packet", "medical_policy", "catalog_packet"]
    output_pdf: str
    manifest_path: str
    pages: int = 0
    synthetic_label: str = SYNTHETIC_BANNER
    warnings: list[str] = Field(default_factory=list)


def _resolve_output_root(value: str) -> Path:
    raw = Path(value).expanduser()
    return raw if raw.is_absolute() else PACKAGE_ROOT / raw


def _output_paths(value: str, tool: str, stem: str) -> tuple[Path, Path]:
    output_dir = _resolve_output_root(value) / "agent-tools" / tool
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{stem}.pdf", output_dir / f"{stem}.manifest.json"


def _pdf_page_count(path: Path) -> int:
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(path)).pages)
    except Exception:
        return 0


def _write_manifest(
    path: Path,
    *,
    tool: str,
    output_pdf: Path,
    details: Mapping[str, Any],
    request_summary: Mapping[str, Any],
) -> None:
    manifest = {
        "tool": tool,
        "synthetic": True,
        "synthetic_label": SYNTHETIC_BANNER,
        "output_pdf": str(output_pdf),
        "output_sha256": hashlib.sha256(output_pdf.read_bytes()).hexdigest(),
        "details": dict(details),
        "request_summary": dict(request_summary),
    }
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _record_summary(spec: Mapping[str, Any]) -> dict[str, Any]:
    documents = spec.get("documents", [])
    return {
        "profile": str(spec.get("profile", "generic_ehr")),
        "document_count": len(documents) if isinstance(documents, list) else None,
        "document_order": (
            str(spec.get("packet", {}).get("document_order", "input_order"))
            if isinstance(spec.get("packet"), Mapping)
            else "input_order"
        ),
    }


def _validate_agent_record_spec(spec: Mapping[str, Any]) -> None:
    documents = spec.get("documents")
    if not isinstance(documents, list):
        raise ValueError("spec.documents must be a list")
    if not 1 <= len(documents) <= MAX_RECORD_DOCUMENTS:
        raise ValueError(f"spec.documents must contain between 1 and {MAX_RECORD_DOCUMENTS} documents")

    image_count = sum(1 for document in documents if isinstance(document, Mapping) and document.get("image_panel"))
    if image_count > 1:
        raise ValueError("Agent record packets allow at most one illustrative imaging panel")
    if image_count:
        rendering = spec.get("rendering")
        if not isinstance(rendering, Mapping) or rendering.get("allow_illustrative_imaging") is not True:
            raise ValueError("Illustrative imaging requires rendering.allow_illustrative_imaging=true")
        reason = str(rendering.get("illustrative_imaging_reason", "")).strip()
        if not reason:
            raise ValueError("Illustrative imaging requires rendering.illustrative_imaging_reason")
        if int(rendering.get("max_illustrative_image_panels", 1)) > 1:
            raise ValueError("Agent record packets allow a maximum of one illustrative imaging panel")


def _validate_agent_policy_spec(spec: Mapping[str, Any]) -> None:
    sections = spec.get("sections")
    if not isinstance(sections, list):
        raise ValueError("spec.sections must be a list")
    if not 1 <= len(sections) <= MAX_POLICY_SECTIONS:
        raise ValueError(f"spec.sections must contain between 1 and {MAX_POLICY_SECTIONS} sections")


@contextmanager
def _temporary_environment(overrides: Mapping[str, str | None]) -> Iterator[None]:
    previous = {name: os.environ.get(name) for name in overrides}
    try:
        for name, value in overrides.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def generate_record_packet_tool(input: RecordPacketToolInput) -> AgentToolOutput:
    """Generate one consolidated synthetic record packet from a fully specified JSON payload."""

    _validate_agent_record_spec(input.spec)
    output_pdf, manifest_path = _output_paths(input.output_root, "record-packets", input.output_stem)
    details = generate_record_packet(input.spec, output_pdf)
    _write_manifest(
        manifest_path,
        tool="record_packet",
        output_pdf=output_pdf,
        details=details,
        request_summary=_record_summary(input.spec),
    )
    return AgentToolOutput(
        tool="record_packet",
        output_pdf=str(output_pdf),
        manifest_path=str(manifest_path),
        pages=_pdf_page_count(output_pdf),
        synthetic_label=str(details.get("synthetic_label", SYNTHETIC_BANNER)),
    )


def generate_medical_policy_tool(input: MedicalPolicyToolInput) -> AgentToolOutput:
    """Generate one fictional medical-policy document from a fully specified JSON payload."""

    _validate_agent_policy_spec(input.spec)
    output_pdf, manifest_path = _output_paths(input.output_root, "medical-policies", input.output_stem)
    details = generate_policy(input.spec, output_pdf)
    policy = input.spec.get("policy", {})
    request_summary = {
        "policy_id": str(policy.get("id", "")) if isinstance(policy, Mapping) else "",
        "section_count": len(input.spec.get("sections", [])),
    }
    _write_manifest(
        manifest_path,
        tool="medical_policy",
        output_pdf=output_pdf,
        details=details,
        request_summary=request_summary,
    )
    return AgentToolOutput(
        tool="medical_policy",
        output_pdf=str(output_pdf),
        manifest_path=str(manifest_path),
        pages=_pdf_page_count(output_pdf),
        synthetic_label=str(details.get("synthetic_label", SYNTHETIC_BANNER)),
    )


def generate_catalog_packet_tool(input: CatalogPacketToolInput) -> AgentToolOutput:
    """Generate a seeded catalog packet with controlled realism and optional synthetic handwriting."""

    catalog = TemplateCatalog.from_default_location()
    selected_families = list(input.families) or catalog.profile_families(input.profile)
    if not selected_families:
        raise ValueError("At least one catalog document family is required")
    if len(selected_families) > MAX_CATALOG_FAMILIES:
        raise ValueError(f"Catalog packets allow at most {MAX_CATALOG_FAMILIES} document families")
    valid_families = set(catalog.list_families())
    unknown = sorted(set(selected_families) - valid_families)
    if unknown:
        raise ValueError(f"Unknown catalog document families: {', '.join(unknown)}")

    output_pdf, manifest_path = _output_paths(input.output_root, "catalog-packets", input.output_stem)
    encounter = build_seeded_encounter(
        input.seed,
        scenario=input.scenario,
        record_label=input.record_label,
    )
    asset_dir = PACKAGE_ROOT / "synthetic_document_pipelines" / "assets" / "handwriting"
    environment = {
        "SYNTHREC_ENABLE_HANDWRITING": "1" if input.include_handwriting else None,
        "SYNTHREC_HANDWRITING_ASSET_DIR": str(asset_dir) if input.include_handwriting else None,
    }
    with _temporary_environment(environment):
        details = PacketOrchestrator(catalog).generate_packet(
            encounter,
            profile=input.profile,
            output_pdf=output_pdf,
            output_json=manifest_path,
            seed=input.seed,
            families=selected_families,
            document_order=input.packet_order,
            apply_realism=input.apply_realism,
            handwriting_asset_dir=asset_dir if input.include_handwriting else None,
        )

    return AgentToolOutput(
        tool="catalog_packet",
        output_pdf=str(output_pdf),
        manifest_path=str(manifest_path),
        pages=_pdf_page_count(output_pdf),
        warnings=[] if input.apply_realism else ["Realism post-processing was disabled for this packet."],
    )
