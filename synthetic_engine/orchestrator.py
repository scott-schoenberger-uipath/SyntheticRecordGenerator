from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

from .canonical import CanonicalEncounter
from .deterministic import SeedBundle
from .mappers import map_family_payload
from .postprocess import apply_packet_realism
from .renderers import HtmlPdfRenderer, OverlayRenderer, PdfmeRenderer, RenderContext, RenderRequest
from .template_catalog import TemplateCatalog
from .template_helpers import resolve_placeholders


@dataclass
class DocumentRun:
    family: str
    template_id: str
    renderer: str
    output_pdf: str
    payload: Dict[str, Any]
    render_metadata: Dict[str, Any]


class PacketOrchestrator:
    def __init__(self, catalog: TemplateCatalog | None = None) -> None:
        self.catalog = catalog or TemplateCatalog.from_default_location()
        self.renderers = {
            "pdfmeRenderer": PdfmeRenderer(),
            "htmlPdfRenderer": HtmlPdfRenderer(),
            "overlayRenderer": OverlayRenderer(),
        }

    def generate_packet(
        self,
        encounter: CanonicalEncounter,
        *,
        profile: str,
        output_pdf: Path,
        output_json: Path,
        seed: int,
        families: Sequence[str] | None = None,
        document_order: str = "received_order",
        apply_realism: bool = True,
        handwriting_asset_dir: Path | None = None,
    ) -> Dict[str, Any]:
        selected_families = list(families) if families else self.catalog.profile_families(profile)
        seeds = SeedBundle(seed)
        if document_order == "received_order":
            seeds.rng("received_order").shuffle(selected_families)
        elif document_order != "profile_order":
            raise ValueError("document_order must be 'received_order' or 'profile_order'")

        with tempfile.TemporaryDirectory(prefix="packet-build-") as tmp_dir:
            tmp_root = Path(tmp_dir)
            rendered_docs: List[Path] = []
            run_details: List[DocumentRun] = []

            for idx, family in enumerate(selected_families):
                template_def = self.catalog.default_template(family)
                template_data = self.catalog.load_template_payload(template_def)
                payload = map_family_payload(family, encounter)
                payload["packet_seed"] = seed
                payload["document_seed"] = seeds.for_label(f"{family}:{idx}")

                resolved_template = resolve_placeholders(template_data, payload)

                renderer = self.renderers.get(template_def.renderer)
                if renderer is None:
                    raise KeyError(f"Renderer '{template_def.renderer}' is not registered")

                doc_pdf = tmp_root / f"{idx + 1:03d}_{family}.pdf"
                request = RenderRequest(
                    family=family,
                    renderer_name=template_def.renderer,
                    template_id=template_def.template_id,
                    template_data=resolved_template,
                    payload=payload,
                    output_pdf=doc_pdf,
                    context=RenderContext(seed=payload["document_seed"], output_dir=tmp_root),
                )
                result = renderer.render(request)
                rendered_docs.append(result.output_pdf)
                run_details.append(
                    DocumentRun(
                        family=family,
                        template_id=template_def.template_id,
                        renderer=template_def.renderer,
                        output_pdf=str(result.output_pdf),
                        payload=payload,
                        render_metadata=result.metadata,
                    )
                )

            merged_pdf = tmp_root / "merged_packet.pdf"
            self._merge_pdfs(rendered_docs, merged_pdf)

            output_pdf.parent.mkdir(parents=True, exist_ok=True)
            if apply_realism:
                apply_packet_realism(
                    merged_pdf,
                    output_pdf,
                    seed=seeds.for_label("packet_realism"),
                    handwriting_asset_dir=handwriting_asset_dir,
                )
            else:
                shutil.copyfile(merged_pdf, output_pdf)

        manifest = {
            "synthetic": True,
            "synthetic_label": "SYNTHETIC / FICTIONAL / NOT FOR CLINICAL, BILLING, OR COVERAGE USE",
            "seed": seed,
            "profile": profile,
            "document_order": document_order,
            "families": selected_families,
            "output_pdf": str(output_pdf),
            "encounter": encounter.to_dict(),
            "documents": [asdict(item) for item in run_details],
        }

        output_json.parent.mkdir(parents=True, exist_ok=True)
        with output_json.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        return manifest

    def _merge_pdfs(self, inputs: Sequence[Path], output_pdf: Path) -> None:
        try:
            from pypdf import PdfReader, PdfWriter
        except Exception as exc:
            raise RuntimeError("pypdf is required to merge rendered documents") from exc

        writer = PdfWriter()
        for pdf in inputs:
            reader = PdfReader(str(pdf))
            for page in reader.pages:
                writer.add_page(page)
        with output_pdf.open("wb") as f:
            writer.write(f)
