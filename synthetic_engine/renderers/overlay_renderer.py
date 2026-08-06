from __future__ import annotations

import os
from typing import Any, Dict, List, Sequence, Tuple

from generate_long_form_packets import note_page, save_packet_pdf, table_page
from generate_synthetic_patient_pdf import PDFDocument

from .base import RenderRequest, RenderResult, Renderer


class OverlayRenderer(Renderer):
    mode = "overlayRenderer"

    def render(self, request: RenderRequest) -> RenderResult:
        payload = request.payload
        template = request.template_data

        doc = PDFDocument()
        doc._scan_targets = []
        doc._handwriting_targets = []

        owner_name = str(payload.get("patient_name", "Synthetic Patient"))
        owner_id = str(payload.get("patient_mrn", "0000000"))
        header = f"{payload.get('facility', 'Community General Hospital')} | {request.family.replace('_', ' ').title()}"
        page_num = 1

        pages = template.get("pages", [])
        if not isinstance(pages, list) or not pages:
            pages = [{"kind": "note", "title": str(template.get("title", "Overlay Page")), "scanned": True}]

        for page in pages:
            if not isinstance(page, dict):
                continue
            kind = str(page.get("kind", "note"))
            title = str(page.get("title") or payload.get("title") or request.family.replace("_", " ").title())
            scanned = bool(page.get("scanned", True))

            if kind == "table":
                columns = page.get("columns") or payload.get("columns") or ["Col1", "Col2"]
                rows = page.get("rows") or payload.get("rows") or []
                parsed_cols: List[Tuple[str, float]] = []
                if isinstance(columns, list) and columns:
                    width = 540.0 / len(columns)
                    parsed_cols = [(str(col), width) for col in columns]
                else:
                    parsed_cols = [("Value", 540.0)]
                parsed_rows: List[List[str]] = []
                if isinstance(rows, list):
                    for row in rows:
                        if isinstance(row, list):
                            parsed_rows.append([str(v) for v in row])
                page_num = table_page(
                    doc,
                    page_num,
                    owner_name,
                    owner_id,
                    header,
                    title,
                    columns=parsed_cols,
                    rows=parsed_rows,
                    notes=["Imported/scanned style table for packet realism."],
                    scanned=scanned,
                )
                continue

            meta_pairs = self._meta_pairs(payload)
            sections = self._sections(payload)
            signature = payload.get("signature")
            parsed_sig = None
            if isinstance(signature, list) and len(signature) >= 3:
                parsed_sig = (str(signature[0]), str(signature[1]), str(signature[2]))

            page_num = note_page(
                doc,
                page_num,
                owner_name,
                owner_id,
                header,
                title,
                meta_pairs=meta_pairs,
                sections=sections,
                signature=parsed_sig,
                scanned=scanned,
            )

        prev_overlays = os.environ.get("SYNTHREC_HANDWRITING_MAX_OVERLAYS")
        handwriting_cfg = template.get("handwriting", {})
        if isinstance(handwriting_cfg, dict) and "max_overlays" in handwriting_cfg:
            os.environ["SYNTHREC_HANDWRITING_MAX_OVERLAYS"] = str(handwriting_cfg["max_overlays"])
        try:
            save_packet_pdf(doc, request.output_pdf)
        finally:
            if prev_overlays is None:
                os.environ.pop("SYNTHREC_HANDWRITING_MAX_OVERLAYS", None)
            else:
                os.environ["SYNTHREC_HANDWRITING_MAX_OVERLAYS"] = prev_overlays

        return RenderResult(request.output_pdf, self.mode, {"pages": len(doc.pages), "scanned_pages": len(getattr(doc, "_scan_targets", []))})

    def _meta_pairs(self, payload: Dict[str, Any]) -> Sequence[Tuple[str, str]]:
        meta = payload.get("meta_pairs", [])
        out: List[Tuple[str, str]] = []
        if isinstance(meta, list):
            for item in meta:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    out.append((str(item[0]), str(item[1])))
        if out:
            return out
        return [
            ("Patient", str(payload.get("patient_name", "Synthetic Patient"))),
            ("MRN", str(payload.get("patient_mrn", "0000000"))),
            ("Encounter", str(payload.get("family", "N/A"))),
        ]

    def _sections(self, payload: Dict[str, Any]) -> Sequence[Tuple[str, str, Sequence[str] | str]]:
        sections_raw = payload.get("sections", [])
        out: List[Tuple[str, str, Sequence[str] | str]] = []
        if isinstance(sections_raw, list):
            for sec in sections_raw:
                if isinstance(sec, (list, tuple)) and len(sec) >= 2:
                    title = str(sec[0])
                    content = sec[1]
                    if isinstance(content, list):
                        out.append((title, "bullets", [str(v) for v in content]))
                    else:
                        out.append((title, "paragraph", str(content)))

        checkbox_rows = payload.get("checkbox_rows", [])
        if isinstance(checkbox_rows, list) and checkbox_rows:
            lines: List[str] = []
            for row in checkbox_rows:
                if isinstance(row, (list, tuple)) and len(row) >= 2:
                    mark = "[x]" if bool(row[1]) else "[ ]"
                    lines.append(f"{mark} {row[0]}")
            out.append(("Checklist", "bullets", lines))

        if out:
            return out
        return [("Narrative", "paragraph", str(payload.get("title", "Overlay note")))]
