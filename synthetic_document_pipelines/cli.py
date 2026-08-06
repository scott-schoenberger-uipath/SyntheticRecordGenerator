from __future__ import annotations

import argparse
from pathlib import Path

from .common import load_spec, make_manifest, write_manifest
from .policies import generate_policy
from .records import generate_record_packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate clearly labeled synthetic medical record packets and policy PDFs."
    )
    subparsers = parser.add_subparsers(dest="kind", required=True)
    for name in ("record", "policy"):
        command = subparsers.add_parser(name)
        command.add_argument("--input", required=True, help="Synthetic JSON specification")
        command.add_argument("--output", required=True, help="Output PDF path")
        command.add_argument("--manifest", help="Optional ground-truth manifest JSON path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    spec = load_spec(input_path)
    metadata = spec["metadata"]

    if args.kind == "record":
        details = generate_record_packet(spec, output_path)
    else:
        details = generate_policy(spec, output_path)

    manifest_path = Path(args.manifest).expanduser().resolve() if args.manifest else output_path.with_suffix(".manifest.json")
    manifest = make_manifest(
        kind=args.kind,
        input_path=input_path,
        output_path=output_path,
        metadata=metadata,
        details=details,
    )
    write_manifest(manifest_path, manifest)
    print(f"Wrote {args.kind} PDF: {output_path}")
    print(f"Wrote manifest: {manifest_path}")
