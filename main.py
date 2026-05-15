from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from generate_appeal_lumbar_mri_records import (
    build_appeal_packet,
    build_record_templates,
)
from generate_ed_downgrade_records import (
    render_record as render_ed_record,
    slugify as ed_slugify,
)
from generate_long_form_packets import SCAN_CLI, build_payer_packet, build_provider_packet
from generate_payer_synthetic_records import (
    make_records as make_payer_records,
    render_record as render_payer_record,
)
from generate_provider_synthetic_records import (
    make_records as make_provider_records,
    render_record as render_provider_record,
)
from generate_referral_packets import (
    build_referral_packet,
    make_referral_packet_specs,
    slugify as referral_slugify,
)
from generate_synthetic_patient_pdf import build_pdf
from generate_um_request_packets import (
    build_um_packet,
    make_packet_specs as make_um_packet_specs,
    slugify as um_slugify,
)


PACKAGE_ROOT = Path(__file__).resolve().parent
BundleName = Literal[
    "base_patient_chart",
    "provider_records",
    "payer_records",
    "provider_long_form_packets",
    "payer_long_form_packets",
    "appeal_packets",
    "ed_downgrade_records",
    "um_request_packets",
    "referral_packets",
]

BUNDLE_COMPONENTS: dict[str, list[str]] = {
    "base_patient_chart": [
        "cover sheet and demographics",
        "problem list and medications",
        "encounters and follow-up notes",
        "lab trends and diagnostics",
        "surgical, pathology, discharge, consult, and anesthesia pages",
    ],
    "provider_records": [
        "face sheet",
        "admission H&P",
        "progress notes",
        "escalation note",
        "lab trends",
        "procedure report",
        "discharge summary",
        "coding page",
    ],
    "payer_records": [
        "member demographics",
        "conditions and utilization",
        "claims and medication profile",
        "functional and social factors",
        "care-management snapshot",
    ],
    "provider_long_form_packets": [
        "registration and packet header",
        "indexed source pages",
        "hospital-day notes",
        "flowsheets and MAR extracts",
        "consults, CDI, discharge, and imported filler pages",
    ],
    "payer_long_form_packets": [
        "risk header",
        "claims detail pages",
        "pharmacy fill history",
        "outreach logs",
        "authorization and correspondence pages",
        "risk-gap and supplemental packet pages",
    ],
    "appeal_packets": [
        "appeal face sheet and fax cover",
        "appeal letter and chronology",
        "office, consult, PT, medication, and injection evidence",
        "criteria crosswalk and imaging reports",
    ],
    "ed_downgrade_records": [
        "Epic-style encounter header",
        "chief complaint and HPI",
        "ED course and nursing notes",
        "lab and radiology results",
        "MAR and discharge instructions",
    ],
    "um_request_packets": [
        "fax cover and UM intake fields",
        "member, provider, HIPAA, and eligibility validation cues",
        "diagnosis and service-line tables",
        "PA new, concurrent review, extension, DME, therapy, NICU, appeal, and grievance scenarios",
        "matrix field crosswalks, clinical criteria, correspondence, and supplemental attachments",
    ],
    "referral_packets": [
        "fax cover sheet and referral face sheet",
        "specialty referral reason, demographics, and routing details",
        "office and progress notes",
        "lab result summaries",
        "imaging result reports",
        "variable packet sizes from 5 to 20 pages",
    ],
}

PROVIDER_SHORT_NAMES = {
    "A": "moderate_acuity",
    "B": "high_acuity_revenue_impact",
    "C": "lower_acuity_gap_heavy",
}
PAYER_SHORT_NAMES = {
    "A": "high_risk_member",
    "B": "complex_polypharmacy_case",
    "C": "socially_complex_case",
}


class GeneratorInput(BaseModel):
    output_root: str = Field(
        default="output",
        description="Directory where generated artifacts should be written.",
    )
    bundle_names: list[BundleName] = Field(
        default_factory=lambda: list(BUNDLE_COMPONENTS),
        description="Bundle families to generate in this run.",
    )
    include_synthetic_imaging: bool = Field(
        default=False,
        description="Include placeholder imaging panels in the base patient chart.",
    )
    record_limit_per_bundle: int | None = Field(
        default=None,
        ge=1,
        le=25,
        description="Optional cap for smoke runs or shorter cloud jobs.",
    )


class BundleResult(BaseModel):
    bundle_name: str
    output_directory: str
    record_count: int
    components: list[str]
    manifest_path: str | None = None
    generated_files: list[str] = Field(default_factory=list)


class GeneratorOutput(BaseModel):
    output_root: str
    bundle_results: list[BundleResult]
    warnings: list[str] = Field(default_factory=list)


def _resolve_output_root(output_root: str) -> Path:
    raw = Path(output_root).expanduser()
    return raw if raw.is_absolute() else PACKAGE_ROOT / raw


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _limit_records(records: list[dict[str, Any]], limit: int | None) -> list[dict[str, Any]]:
    if limit is None:
        return records
    return records[:limit]


def _write_manifest(output_dir: Path, manifest_rows: list[dict[str, Any]]) -> Path:
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_rows, indent=2), encoding="utf-8")
    return manifest_path


def _base_patient_chart(output_root: Path, payload: GeneratorInput) -> BundleResult:
    output_dir = output_root / "base-patient-chart"
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = output_dir / "synthetic_patient_chart_case_001.pdf"
    json_path = output_dir / "synthetic_patient_chart_case_001.json"
    build_pdf(str(pdf_path), str(json_path), include_synthetic_imaging=payload.include_synthetic_imaging)

    manifest_path = _write_manifest(
        output_dir,
        [
            {
                "record": "case_001",
                "pdf": str(pdf_path),
                "json": str(json_path),
            }
        ],
    )

    return BundleResult(
        bundle_name="base_patient_chart",
        output_directory=str(output_dir),
        record_count=1,
        components=BUNDLE_COMPONENTS["base_patient_chart"],
        manifest_path=str(manifest_path),
        generated_files=[str(pdf_path), str(json_path), str(manifest_path)],
    )


def _provider_records(output_root: Path, payload: GeneratorInput) -> BundleResult:
    output_dir = output_root / "provider-records"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, Any]] = []
    generated_files: list[str] = []
    for record in _limit_records(make_provider_records(), payload.record_limit_per_bundle):
        label = str(record["record_label"])
        stem = f"record_{label.lower()}_{PROVIDER_SHORT_NAMES[label]}"
        pdf_path = output_dir / f"{stem}.pdf"
        json_path = output_dir / f"{stem}.json"
        render_provider_record(record, pdf_path, json_path)
        manifest_rows.append(
            {
                "record": label,
                "type": "provider",
                "pdf": str(pdf_path),
                "json": str(json_path),
            }
        )
        generated_files.extend([str(pdf_path), str(json_path)])

    manifest_path = _write_manifest(output_dir, manifest_rows)
    generated_files.append(str(manifest_path))
    return BundleResult(
        bundle_name="provider_records",
        output_directory=str(output_dir),
        record_count=len(manifest_rows),
        components=BUNDLE_COMPONENTS["provider_records"],
        manifest_path=str(manifest_path),
        generated_files=generated_files,
    )


def _payer_records(output_root: Path, payload: GeneratorInput) -> BundleResult:
    output_dir = output_root / "payer-records"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, Any]] = []
    generated_files: list[str] = []
    for record in _limit_records(make_payer_records(), payload.record_limit_per_bundle):
        label = str(record["record_label"])
        stem = f"record_{label.lower()}_{PAYER_SHORT_NAMES[label]}"
        pdf_path = output_dir / f"{stem}.pdf"
        json_path = output_dir / f"{stem}.json"
        render_payer_record(record, pdf_path, json_path)
        manifest_rows.append(
            {
                "record": label,
                "type": "payer",
                "pdf": str(pdf_path),
                "json": str(json_path),
            }
        )
        generated_files.extend([str(pdf_path), str(json_path)])

    manifest_path = _write_manifest(output_dir, manifest_rows)
    generated_files.append(str(manifest_path))
    return BundleResult(
        bundle_name="payer_records",
        output_directory=str(output_dir),
        record_count=len(manifest_rows),
        components=BUNDLE_COMPONENTS["payer_records"],
        manifest_path=str(manifest_path),
        generated_files=generated_files,
    )


def _provider_long_form_packets(output_root: Path, payload: GeneratorInput) -> BundleResult:
    output_dir = output_root / "provider-long-form-packets"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, Any]] = []
    generated_files: list[str] = []
    for record in _limit_records(make_provider_records(), payload.record_limit_per_bundle):
        label = str(record["record_label"])
        stem = f"record_{label.lower()}_{PROVIDER_SHORT_NAMES[label]}"
        pdf_path = output_dir / f"{stem}.pdf"
        json_path = output_dir / f"{stem}.json"
        build_provider_packet(record, pdf_path, json_path)
        manifest_rows.append(
            {
                "record": label,
                "type": "provider_long_form",
                "pdf": str(pdf_path),
                "json": str(json_path),
            }
        )
        generated_files.extend([str(pdf_path), str(json_path)])

    manifest_path = _write_manifest(output_dir, manifest_rows)
    generated_files.append(str(manifest_path))
    return BundleResult(
        bundle_name="provider_long_form_packets",
        output_directory=str(output_dir),
        record_count=len(manifest_rows),
        components=BUNDLE_COMPONENTS["provider_long_form_packets"],
        manifest_path=str(manifest_path),
        generated_files=generated_files,
    )


def _payer_long_form_packets(output_root: Path, payload: GeneratorInput) -> BundleResult:
    output_dir = output_root / "payer-long-form-packets"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, Any]] = []
    generated_files: list[str] = []
    for record in _limit_records(make_payer_records(), payload.record_limit_per_bundle):
        label = str(record["record_label"])
        stem = f"record_{label.lower()}_{PAYER_SHORT_NAMES[label]}"
        pdf_path = output_dir / f"{stem}.pdf"
        json_path = output_dir / f"{stem}.json"
        build_payer_packet(record, pdf_path, json_path)
        manifest_rows.append(
            {
                "record": label,
                "type": "payer_long_form",
                "pdf": str(pdf_path),
                "json": str(json_path),
            }
        )
        generated_files.extend([str(pdf_path), str(json_path)])

    manifest_path = _write_manifest(output_dir, manifest_rows)
    generated_files.append(str(manifest_path))
    return BundleResult(
        bundle_name="payer_long_form_packets",
        output_directory=str(output_dir),
        record_count=len(manifest_rows),
        components=BUNDLE_COMPONENTS["payer_long_form_packets"],
        manifest_path=str(manifest_path),
        generated_files=generated_files,
    )


def _appeal_packets(output_root: Path, payload: GeneratorInput) -> BundleResult:
    output_dir = output_root / "appeal-packets"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, Any]] = []
    generated_files: list[str] = []
    templates = list(build_record_templates())
    for record in _limit_records(templates, payload.record_limit_per_bundle):
        label = str(record["record_label"])
        stem = f"appeal_record_{label.lower()}_{_slugify(str(record['title']))}"
        pdf_path = output_dir / f"{stem}.pdf"
        json_path = output_dir / f"{stem}.json"
        build_appeal_packet(record, pdf_path, json_path)
        manifest_rows.append(
            {
                "record": label,
                "title": str(record["title"]),
                "pdf": str(pdf_path),
                "json": str(json_path),
            }
        )
        generated_files.extend([str(pdf_path), str(json_path)])

    manifest_path = _write_manifest(output_dir, manifest_rows)
    generated_files.append(str(manifest_path))
    return BundleResult(
        bundle_name="appeal_packets",
        output_directory=str(output_dir),
        record_count=len(manifest_rows),
        components=BUNDLE_COMPONENTS["appeal_packets"],
        manifest_path=str(manifest_path),
        generated_files=generated_files,
    )


def _ed_downgrade_records(output_root: Path, payload: GeneratorInput) -> BundleResult:
    output_dir = output_root / "ed-downgrade-records"
    output_dir.mkdir(parents=True, exist_ok=True)

    source_path = PACKAGE_ROOT / "ed_downgrade_records.json"
    records = json.loads(source_path.read_text(encoding="utf-8"))
    manifest_rows: list[dict[str, Any]] = []
    generated_files: list[str] = []
    for record in _limit_records(records, payload.record_limit_per_bundle):
        label = ed_slugify(record["record_label"])
        scenario_slug = ed_slugify(record["scenario"])[:50]
        stem = f"{label}_{scenario_slug}"
        pdf_path = output_dir / f"{stem}.pdf"
        json_path = output_dir / f"{stem}.json"
        render_ed_record(record, pdf_path, json_path)
        manifest_rows.append(
            {
                "record": record["record_label"],
                "scenario": record["scenario"],
                "facility": record["facility"],
                "pdf": str(pdf_path),
                "json": str(json_path),
            }
        )
        generated_files.extend([str(pdf_path), str(json_path)])

    manifest_path = _write_manifest(output_dir, manifest_rows)
    generated_files.append(str(manifest_path))
    return BundleResult(
        bundle_name="ed_downgrade_records",
        output_directory=str(output_dir),
        record_count=len(manifest_rows),
        components=BUNDLE_COMPONENTS["ed_downgrade_records"],
        manifest_path=str(manifest_path),
        generated_files=generated_files,
    )


def _um_request_packets(output_root: Path, payload: GeneratorInput) -> BundleResult:
    output_dir = output_root / "um-request-packets"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, Any]] = []
    generated_files: list[str] = []
    for spec in _limit_records(make_um_packet_specs(), payload.record_limit_per_bundle):
        stem = f"{spec['record_label'].lower()}_{um_slugify(str(spec['title']))}"
        pdf_path = output_dir / f"{stem}.pdf"
        json_path = output_dir / f"{stem}.json"
        build_um_packet(spec, pdf_path, json_path)
        manifest_rows.append(
            {
                "record": str(spec["record_label"]),
                "title": str(spec["title"]),
                "taxonomy": str(spec["taxonomy"]),
                "category": str(spec["category"]),
                "target_pages": int(spec["target_pages"]),
                "pdf": str(pdf_path),
                "json": str(json_path),
            }
        )
        generated_files.extend([str(pdf_path), str(json_path)])

    manifest_path = _write_manifest(output_dir, manifest_rows)
    generated_files.append(str(manifest_path))
    return BundleResult(
        bundle_name="um_request_packets",
        output_directory=str(output_dir),
        record_count=len(manifest_rows),
        components=BUNDLE_COMPONENTS["um_request_packets"],
        manifest_path=str(manifest_path),
        generated_files=generated_files,
    )


def _referral_packets(output_root: Path, payload: GeneratorInput) -> BundleResult:
    output_dir = output_root / "referral-packets"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, Any]] = []
    generated_files: list[str] = []
    for spec in _limit_records(make_referral_packet_specs(), payload.record_limit_per_bundle):
        stem = f"{spec['record_label'].lower()}_{referral_slugify(str(spec['title']))}"
        pdf_path = output_dir / f"{stem}.pdf"
        json_path = output_dir / f"{stem}.json"
        build_referral_packet(spec, pdf_path, json_path)
        manifest_rows.append(
            {
                "record": str(spec["record_label"]),
                "title": str(spec["title"]),
                "requested_specialty": str(spec["requested_specialty"]),
                "target_pages": int(spec["target_pages"]),
                "pdf": str(pdf_path),
                "json": str(json_path),
            }
        )
        generated_files.extend([str(pdf_path), str(json_path)])

    manifest_path = _write_manifest(output_dir, manifest_rows)
    generated_files.append(str(manifest_path))
    return BundleResult(
        bundle_name="referral_packets",
        output_directory=str(output_dir),
        record_count=len(manifest_rows),
        components=BUNDLE_COMPONENTS["referral_packets"],
        manifest_path=str(manifest_path),
        generated_files=generated_files,
    )


GENERATORS = {
    "base_patient_chart": _base_patient_chart,
    "provider_records": _provider_records,
    "payer_records": _payer_records,
    "provider_long_form_packets": _provider_long_form_packets,
    "payer_long_form_packets": _payer_long_form_packets,
    "appeal_packets": _appeal_packets,
    "ed_downgrade_records": _ed_downgrade_records,
    "um_request_packets": _um_request_packets,
    "referral_packets": _referral_packets,
}


def main(input_data: GeneratorInput | dict[str, Any] | None = None) -> dict[str, Any]:
    payload = input_data if isinstance(input_data, GeneratorInput) else GeneratorInput.model_validate(input_data or {})
    output_root = _resolve_output_root(payload.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    bundle_names: list[str] = list(dict.fromkeys(payload.bundle_names))
    warnings: list[str] = []
    scan_dependent_bundles = {
        "provider_long_form_packets",
        "payer_long_form_packets",
        "appeal_packets",
        "um_request_packets",
        "referral_packets",
    }
    if scan_dependent_bundles.intersection(bundle_names) and not SCAN_CLI.exists():
        warnings.append(
            "Optional scan-style post-processing is not configured; scan-tagged packets were generated as vector PDFs."
        )

    bundle_results = [GENERATORS[bundle_name](output_root, payload) for bundle_name in bundle_names]
    output = GeneratorOutput(
        output_root=str(output_root),
        bundle_results=bundle_results,
        warnings=warnings,
    )
    return output.model_dump()


def _resolve_input_path(input_path: str) -> Path:
    raw = Path(input_path).expanduser()
    if raw.is_absolute():
        return raw
    if raw.exists():
        return raw
    return PACKAGE_ROOT / raw


def _load_cli_payload(input_path: str) -> dict[str, Any]:
    resolved_path = _resolve_input_path(input_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"Input file not found: {resolved_path}")
    try:
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {resolved_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Input file must contain a JSON object: {resolved_path}")
    return payload


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic record bundles through the shared wrapper.")
    parser.add_argument(
        "--input",
        default="input.example.json",
        help="Path to a JSON payload matching the GeneratorInput contract.",
    )
    parser.add_argument(
        "--output-root",
        help="Override the payload output_root. Relative paths still resolve from this project directory.",
    )
    args = parser.parse_args()

    try:
        payload = _load_cli_payload(args.input)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))

    if args.output_root:
        payload["output_root"] = args.output_root

    print(json.dumps(main(payload), indent=2))


if __name__ == "__main__":
    _cli()
