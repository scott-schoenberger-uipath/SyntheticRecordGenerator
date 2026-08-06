from __future__ import annotations

import unittest
from pathlib import Path

from synthetic_engine.bootstrap_utils import bootstrap_template_from_exemplar
from synthetic_engine.canonical import build_seeded_encounter
from synthetic_engine.mappers import map_family_payload
from synthetic_engine.template_catalog import TemplateCatalog


class TemplateEngineTests(unittest.TestCase):
    def test_seeded_encounter_is_reproducible_and_synthetic(self) -> None:
        first = build_seeded_encounter(20260310, scenario="provider_sepsis")
        second = build_seeded_encounter(20260310, scenario="provider_sepsis")
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertTrue(first.patient.mrn.startswith("SYN-"))
        self.assertTrue(first.patient.member_id.startswith("SYN-M-"))
        self.assertTrue(first.encounter.encounter_id.startswith("SYN-ENC-"))

    def test_catalog_templates_have_a_synthetic_mapper_payload(self) -> None:
        catalog = TemplateCatalog.from_default_location()
        encounter = build_seeded_encounter(20260310, scenario="provider_sepsis")
        for family in catalog.profile_families("provider_packet_full"):
            template = catalog.default_template(family)
            self.assertTrue(template.path.is_file(), template.path)
            payload = map_family_payload(family, encounter)
            self.assertEqual(payload["patient_mrn"], encounter.patient.mrn)

    def test_bootstrap_requires_synthetic_attestation(self) -> None:
        with self.assertRaisesRegex(ValueError, "synthetic-only attestation"):
            bootstrap_template_from_exemplar(
                exemplar_pdf=Path("unused.pdf"),
                family="registration_face_sheet",
                output_template_path=Path("unused.json"),
                template_id="unused",
                renderer="pdfmeRenderer",
                synthetic_attestation=False,
            )


if __name__ == "__main__":
    unittest.main()
