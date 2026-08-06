from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from pypdf import PdfReader

from agent_tools import (
    CatalogPacketToolInput,
    MedicalPolicyToolInput,
    RecordPacketToolInput,
    generate_catalog_packet_tool,
    generate_medical_policy_tool,
    generate_record_packet_tool,
)
from synthetic_document_pipelines.common import SYNTHETIC_BANNER, load_spec


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "modern_pipeline"


class AgentToolsTests(unittest.TestCase):
    def test_uipath_configuration_exposes_all_three_agent_tools(self) -> None:
        config = json.loads((ROOT / "uipath.json").read_text(encoding="utf-8"))
        functions = config["functions"]
        self.assertEqual(functions["generate_record_packet"], "agent_tools.py:generate_record_packet_tool")
        self.assertEqual(functions["generate_medical_policy"], "agent_tools.py:generate_medical_policy_tool")
        self.assertEqual(functions["generate_catalog_packet"], "agent_tools.py:generate_catalog_packet_tool")
        self.assertIn(".png", config["packOptions"]["fileExtensionsIncluded"])

    def test_record_tool_writes_one_labeled_packet_and_manifest(self) -> None:
        spec = load_spec(EXAMPLES / "neurovascular_record_packet.json")
        with tempfile.TemporaryDirectory() as temp_dir:
            result = generate_record_packet_tool(
                RecordPacketToolInput(output_root=temp_dir, output_stem="agent_record", spec=spec)
            )
            output_pdf = Path(result.output_pdf)
            manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
            self.assertEqual(result.tool, "record_packet")
            self.assertEqual(result.pages, 7)
            self.assertTrue(output_pdf.is_file())
            self.assertEqual(manifest["synthetic_label"], SYNTHETIC_BANNER)
            self.assertEqual(manifest["request_summary"]["document_count"], 7)

    def test_record_tool_rejects_non_synthetic_identifier(self) -> None:
        spec = deepcopy(load_spec(EXAMPLES / "neurovascular_record_packet.json"))
        spec["patient"]["mrn"] = "12345678"
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "must start with SYN-"):
                generate_record_packet_tool(RecordPacketToolInput(output_root=temp_dir, spec=spec))

    def test_policy_tool_writes_manifest(self) -> None:
        spec = load_spec(EXAMPLES / "illustrative_imaging_policy.json")
        with tempfile.TemporaryDirectory() as temp_dir:
            result = generate_medical_policy_tool(
                MedicalPolicyToolInput(output_root=temp_dir, output_stem="agent_policy", spec=spec)
            )
            manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
            self.assertEqual(result.tool, "medical_policy")
            self.assertGreaterEqual(result.pages, 1)
            self.assertEqual(manifest["request_summary"]["policy_id"], "SYN-POL-IMG-2026-010")

    def test_catalog_tool_uses_seeded_families_and_synthetic_handwriting_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = generate_catalog_packet_tool(
                CatalogPacketToolInput(
                    output_root=temp_dir,
                    output_stem="agent_catalog",
                    scenario="provider_sepsis",
                    seed=20260310,
                    families=["lab_result_page", "handwritten_progress_note"],
                    include_handwriting=True,
                )
            )
            manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
            reader = PdfReader(result.output_pdf)
            self.assertEqual(result.tool, "catalog_packet")
            self.assertTrue(Path(result.output_pdf).is_file())
            self.assertEqual(sorted(manifest["families"]), ["handwritten_progress_note", "lab_result_page"])
            self.assertTrue(manifest["encounter"]["patient"]["mrn"].startswith("SYN-"))
            self.assertEqual(len(reader.pages), 2)
            self.assertEqual(len(reader.pages[1].images), 1)

    def test_catalog_tool_rejects_unknown_document_family(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "Unknown catalog document families"):
                generate_catalog_packet_tool(
                    CatalogPacketToolInput(output_root=temp_dir, families=["not_a_real_document"])
                )


if __name__ == "__main__":
    unittest.main()
