#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from synthetic_engine.bootstrap_utils import validate_template_mapping



def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate template->mapper wiring")
    p.add_argument("--template", required=True, help="Template JSON path")
    p.add_argument("--family", required=True)
    p.add_argument("--seed", type=int, default=1337)
    p.add_argument("--scenario", default="provider_sepsis", choices=["provider_sepsis", "resp_failure", "lumbar_mri_appeal"])
    return p.parse_args()



def main() -> None:
    args = parse_args()
    report = validate_template_mapping(
        template_path=Path(args.template).expanduser(),
        family=args.family,
        seed=args.seed,
        scenario=args.scenario,
    )
    print(json.dumps(report, indent=2))
    if not report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
