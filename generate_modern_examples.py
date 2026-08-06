#!/usr/bin/env python3
"""Render the two review artifacts for the modern, dual-pipeline implementation."""

from pathlib import Path

from synthetic_document_pipelines.common import load_spec, make_manifest, write_manifest
from synthetic_document_pipelines.policies import generate_policy
from synthetic_document_pipelines.records import generate_record_packet


ROOT = Path(__file__).resolve().parent
EXAMPLES = ROOT / "examples" / "modern_pipeline"
OUTPUT = ROOT / "generated_examples" / "modern_pipeline"


def render(kind: str, input_name: str, output_name: str) -> None:
    spec_path = EXAMPLES / input_name
    output_path = OUTPUT / output_name
    spec = load_spec(spec_path)
    details = generate_record_packet(spec, output_path) if kind == "record" else generate_policy(spec, output_path)
    manifest = make_manifest(
        kind=kind,
        input_path=spec_path,
        output_path=output_path,
        metadata=spec["metadata"],
        details=details,
    )
    write_manifest(output_path.with_suffix(".manifest.json"), manifest)
    print(f"Wrote {output_path}")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    render("record", "neurovascular_record_packet.json", "synthetic_neurovascular_record_packet.pdf")
    render("policy", "illustrative_imaging_policy.json", "illustrative_advanced_imaging_policy.pdf")


if __name__ == "__main__":
    main()
