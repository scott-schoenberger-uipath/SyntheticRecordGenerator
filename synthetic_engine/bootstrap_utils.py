from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .canonical import build_seeded_encounter
from .mappers import expected_payload_keys, map_family_payload
from .template_helpers import collect_placeholders, lookup_path



def _read_synthetic_layout_summary(exemplar_pdf: Path) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "source": "synthetic-layout-reference",
        "pages": 0,
        "page_width": 612.0,
        "page_height": 792.0,
    }
    try:
        from pypdf import PdfReader
    except Exception:
        return summary

    if not exemplar_pdf.exists():
        return summary

    reader = PdfReader(str(exemplar_pdf))
    summary["pages"] = len(reader.pages)
    if reader.pages:
        first = reader.pages[0]
        summary["page_width"] = float(first.mediabox.width)
        summary["page_height"] = float(first.mediabox.height)
    return summary


def bootstrap_template_from_exemplar(
    *,
    exemplar_pdf: Path,
    family: str,
    output_template_path: Path,
    template_id: str,
    renderer: str,
    synthetic_attestation: bool,
) -> Dict[str, Any]:
    if not synthetic_attestation:
        raise ValueError("A synthetic-only attestation is required for layout bootstrapping")
    exemplar = _read_synthetic_layout_summary(exemplar_pdf)
    expected = expected_payload_keys(family)

    scaffold: Dict[str, Any] = {
        "template_id": template_id,
        "family": family,
        "renderer": renderer,
        "notes": {
            "bootstrapped_from": exemplar,
            "agent_assisted": True,
            "instructions": [
                "Adjust section titles, order, and boxes to match exemplar layout.",
                "Map each source key to payload keys from mapper outputs.",
                "Use validate_template_mapping.py before adding to manifest.",
            ],
            "expected_mapper_keys": expected,
        },
        "title": f"{family.replace('_', ' ').title()} (Bootstrapped)",
    }

    if renderer == "pdfmeRenderer":
        scaffold["fixed_sections"] = [
            {"title": "Header", "kind": "kv", "source": expected[0] if expected else "encounter_pairs"},
            {"title": "Body", "kind": "table", "columns": ["Field", "Value"], "source": expected[-1] if expected else "rows"},
        ]
    elif renderer == "overlayRenderer":
        scaffold["pages"] = [
            {"kind": "note", "title": scaffold["title"], "scanned": True},
        ]
        scaffold["handwriting"] = {"max_overlays": 2}
    else:
        scaffold["blocks"] = [
            {"kind": "kv", "title": "Header", "source": expected[0] if expected else "meta_pairs"},
            {"kind": "paragraph", "title": "Narrative", "source": expected[1] if len(expected) > 1 else "hpi"},
        ]

    output_template_path.parent.mkdir(parents=True, exist_ok=True)
    with output_template_path.open("w", encoding="utf-8") as f:
        json.dump(scaffold, f, indent=2)
    return scaffold


def validate_template_mapping(
    *,
    template_path: Path,
    family: str,
    seed: int = 1337,
    scenario: str = "provider_sepsis",
) -> Dict[str, Any]:
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    with template_path.open("r", encoding="utf-8") as f:
        template = json.load(f)

    encounter = build_seeded_encounter(seed, scenario=scenario)
    payload = map_family_payload(family, encounter)

    placeholders = sorted(collect_placeholders(template))
    missing_placeholders: List[str] = []
    for key in placeholders:
        if lookup_path(payload, key) is None:
            missing_placeholders.append(key)

    expected = expected_payload_keys(family)
    missing_expected = [key for key in expected if key not in payload]

    report = {
        "template_path": str(template_path),
        "family": family,
        "placeholder_count": len(placeholders),
        "missing_placeholders": missing_placeholders,
        "expected_payload_keys": expected,
        "missing_expected_payload_keys": missing_expected,
        "valid": (not missing_placeholders and not missing_expected),
    }
    return report
