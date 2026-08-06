#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from synthetic_engine.bootstrap_utils import bootstrap_template_from_exemplar



def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Agent-assisted template bootstrap from a synthetic exemplar PDF")
    p.add_argument("--synthetic-exemplar", required=True, help="Path to a synthetic-only exemplar PDF")
    p.add_argument(
        "--attest-synthetic-exemplar",
        action="store_true",
        help="Required attestation that the exemplar contains no real-person medical data",
    )
    p.add_argument("--family", required=True, help="Template family name")
    p.add_argument("--renderer", required=True, choices=["pdfmeRenderer", "htmlPdfRenderer", "overlayRenderer"])
    p.add_argument("--template-id", required=True)
    p.add_argument("--out", required=True, help="Output template JSON path")
    return p.parse_args()



def main() -> None:
    args = parse_args()
    scaffold = bootstrap_template_from_exemplar(
        exemplar_pdf=Path(args.synthetic_exemplar).expanduser(),
        family=args.family,
        output_template_path=Path(args.out).expanduser(),
        template_id=args.template_id,
        renderer=args.renderer,
        synthetic_attestation=args.attest_synthetic_exemplar,
    )
    print(f"Wrote scaffold template: {args.out}")
    print(f"Expected mapper keys: {', '.join(scaffold.get('notes', {}).get('expected_mapper_keys', []))}")


if __name__ == "__main__":
    main()
