from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader

from synthetic_document_pipelines.common import SYNTHETIC_BANNER, load_spec
from synthetic_document_pipelines.policies import generate_policy
from synthetic_document_pipelines.records import generate_record_packet


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "modern_pipeline"


class SyntheticDocumentPipelineTests(unittest.TestCase):
    def test_record_packet_is_one_pdf_with_a_scanned_attachment(self) -> None:
        spec = load_spec(EXAMPLES / "neurovascular_record_packet.json")
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "record.pdf"
            details = generate_record_packet(spec, output)
            reader = PdfReader(str(output))
            full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
            self.assertEqual(len(reader.pages), 7)
            self.assertTrue(details["scan"]["applied"])
            self.assertEqual(details["packet_order"], "received_order")
            self.assertEqual(details["illustrative_image_panels"], 1)
            self.assertIn("nursing_note", details["document_types"])
            self.assertIn("laboratory_result", details["document_types"])
            self.assertIn(SYNTHETIC_BANNER, full_text)
            self.assertIn("CTA Head and Neck", full_text)
            self.assertGreaterEqual(len(reader.pages[0].images), 1)
            self.assertGreaterEqual(len(reader.pages[3].images), 2)
            self.assertGreaterEqual(len(reader.pages[4].images), 1)

    def test_illustrative_imaging_requires_an_explicit_reason(self) -> None:
        spec = load_spec(EXAMPLES / "neurovascular_record_packet.json")
        spec["rendering"] = {"allow_illustrative_imaging": True}
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "illustrative_imaging_reason"):
                generate_record_packet(spec, Path(temp_dir) / "record.pdf")

    def test_policy_is_labeled_and_paginated(self) -> None:
        spec = load_spec(EXAMPLES / "illustrative_imaging_policy.json")
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "policy.pdf"
            details = generate_policy(spec, output)
            reader = PdfReader(str(output))
            full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
            self.assertGreaterEqual(details["pages"], 1)
            self.assertIn(SYNTHETIC_BANNER, full_text)
            self.assertIn("ILLUSTRATIVE COVERAGE POLICY", full_text)
            self.assertIn("not an actual coverage determination", full_text)
            self.assertGreaterEqual(len(reader.pages[0].images), 1)


if __name__ == "__main__":
    unittest.main()
