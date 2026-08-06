#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from synthetic_engine import build_seeded_encounter
from synthetic_engine.orchestrator import PacketOrchestrator


WORKSPACE_ROOT = Path(__file__).resolve().parent
SCAN_VENV_PYTHON = WORKSPACE_ROOT / ".venv-scan" / "bin" / "python3.11"



def maybe_reexec_in_scan_env() -> None:
    if os.environ.get("SYNTHREC_SCAN_ENV") == "1":
        return
    if not SCAN_VENV_PYTHON.exists():
        return
    try:
        current = Path(sys.executable).resolve()
    except Exception:
        current = Path(sys.executable)
    if current == SCAN_VENV_PYTHON.resolve():
        os.environ["SYNTHREC_SCAN_ENV"] = "1"
        return
    env = dict(os.environ)
    env["SYNTHREC_SCAN_ENV"] = "1"
    os.execve(
        str(SCAN_VENV_PYTHON),
        [str(SCAN_VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]],
        env,
    )



def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Template-driven synthetic packet generator")
    p.add_argument("--profile", default="provider_packet_full", help="Template profile name from manifest")
    p.add_argument("--families", default="", help="Optional comma-separated family override")
    p.add_argument("--scenario", default="provider_sepsis", choices=["provider_sepsis", "resp_failure", "lumbar_mri_appeal"])
    p.add_argument("--seed", type=int, default=20260310)
    p.add_argument("--record-label", default="A")
    p.add_argument(
        "--packet-order",
        default="received_order",
        choices=["received_order", "profile_order"],
        help="Use received order to model mixed inbound packets, or preserve profile order for clean demos.",
    )
    p.add_argument("--out-dir", default=str(WORKSPACE_ROOT / "Template Driven Synthetic Records"))
    p.add_argument("--output-stem", default="template_driven_packet")
    p.add_argument("--no-realism", action="store_true", help="Skip realism postprocessing")
    p.add_argument(
        "--handwriting-asset-dir",
        default=str(WORKSPACE_ROOT / "handwriting_assets"),
        help="Handwriting asset directory for realism overlays",
    )
    p.add_argument(
        "--enable-handwriting",
        action="store_true",
        help="Apply local handwriting assets only to scanned attachment pages.",
    )
    return p.parse_args()



def main() -> None:
    maybe_reexec_in_scan_env()
    args = parse_args()
    if args.enable_handwriting:
        os.environ["SYNTHREC_ENABLE_HANDWRITING"] = "1"

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    output_pdf = out_dir / f"{args.output_stem}.pdf"
    output_json = out_dir / f"{args.output_stem}.json"

    encounter = build_seeded_encounter(
        args.seed,
        scenario=args.scenario,
        record_label=args.record_label,
    )

    family_override = [item.strip() for item in args.families.split(",") if item.strip()]

    orchestrator = PacketOrchestrator()
    result = orchestrator.generate_packet(
        encounter,
        profile=args.profile,
        output_pdf=output_pdf,
        output_json=output_json,
        seed=args.seed,
        families=family_override or None,
        document_order=args.packet_order,
        apply_realism=not args.no_realism,
        handwriting_asset_dir=Path(args.handwriting_asset_dir).expanduser(),
    )

    print(f"Wrote template-driven packet PDF: {output_pdf}")
    print(f"Wrote template-driven packet JSON: {output_json}")
    print(f"Families rendered: {', '.join(result['families'])}")


if __name__ == "__main__":
    main()
