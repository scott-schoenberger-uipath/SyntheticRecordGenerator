from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence, Tuple

from generate_synthetic_patient_pdf import (
    Canvas,
    MARGIN,
    PAGE_H,
    PAGE_W,
    PDFDocument,
    draw_kv_grid,
    draw_section_header,
    draw_signature_block,
    draw_table,
    page_chrome,
)

from .base import RenderRequest, RenderResult, Renderer


class HtmlPdfRenderer(Renderer):
    mode = "htmlPdfRenderer"

    def render(self, request: RenderRequest) -> RenderResult:
        payload = request.payload
        template = request.template_data
        title = str(template.get("title") or payload.get("title") or request.family.replace("_", " ").title())
        blocks = template.get("blocks", [])
        if not isinstance(blocks, list):
            blocks = []

        doc = PDFDocument()
        page_num = 1
        c, y = self._new_page(page_num, payload, request.family, title)

        for block in blocks:
            if not isinstance(block, dict):
                continue
            kind = str(block.get("kind", "")).strip().lower()
            if kind == "kv":
                section_title = str(block.get("title", "Details"))
                pairs = self._pairs_from_block(block, payload)
                estimated_h = 44 + 20 * max(1, math.ceil(len(pairs) / 2))
                if y - estimated_h < 70:
                    doc.add_page(c.to_bytes(), c.used_images)
                    page_num += 1
                    c, y = self._new_page(page_num, payload, request.family, title)
                y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, section_title)
                y = draw_kv_grid(c, MARGIN, y, PAGE_W - 2 * MARGIN, pairs, cols=2 if len(pairs) > 5 else 1, label_w=120)
                continue

            if kind == "paragraph":
                section_title = str(block.get("title", "Narrative"))
                text = self._string_from_block(block, payload)
                est_lines = max(1, int(len(text) / 92) + 1)
                box_h = min(260, 20 + est_lines * 10)
                if y - (box_h + 24) < 70:
                    doc.add_page(c.to_bytes(), c.used_images)
                    page_num += 1
                    c, y = self._new_page(page_num, payload, request.family, title)
                y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, section_title)
                c.set_stroke(0.2, 0.2, 0.2)
                c.rect(MARGIN, y - box_h, PAGE_W - 2 * MARGIN, box_h, fill=False, stroke=True)
                y_after = c.wrapped_text(
                    MARGIN + 8,
                    y - 10,
                    text,
                    max_width=PAGE_W - 2 * MARGIN - 16,
                    leading=10.4,
                    font="F1",
                    size=8.0,
                )
                y = min(y - box_h - 10, y_after - 8)
                continue

            if kind == "bullets":
                section_title = str(block.get("title", "Summary"))
                items = self._list_from_block(block, payload)
                box_h = min(280, 18 + len(items) * 12)
                if y - (box_h + 24) < 70:
                    doc.add_page(c.to_bytes(), c.used_images)
                    page_num += 1
                    c, y = self._new_page(page_num, payload, request.family, title)
                y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, section_title)
                c.set_stroke(0.2, 0.2, 0.2)
                c.rect(MARGIN, y - box_h, PAGE_W - 2 * MARGIN, box_h, fill=False, stroke=True)
                yy = y - 10
                for item in items:
                    yy = c.wrapped_text(
                        MARGIN + 8,
                        yy,
                        str(item),
                        max_width=PAGE_W - 2 * MARGIN - 16,
                        leading=10.2,
                        font="F1",
                        size=8.0,
                        bullet=True,
                    )
                    yy -= 1
                y = y - box_h - 10
                continue

            if kind == "table":
                section_title = str(block.get("title", "Table"))
                columns = block.get("columns", [])
                if not isinstance(columns, list) or not columns:
                    continue
                rows = self._rows_from_block(block, payload)
                headers = [str(cn) for cn in columns]
                table_w = PAGE_W - 2 * MARGIN
                widths = [table_w / len(headers)] * len(headers)
                row_h = 17.0
                header_h = 20.0
                chunk_size = max(1, int((y - 140) / row_h))
                row_idx = 0
                while row_idx < len(rows):
                    chunk = rows[row_idx : row_idx + chunk_size]
                    if y - (header_h + row_h * len(chunk) + 40) < 70:
                        doc.add_page(c.to_bytes(), c.used_images)
                        page_num += 1
                        c, y = self._new_page(page_num, payload, request.family, title)
                    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, section_title if row_idx == 0 else f"{section_title} (cont.)")
                    y = draw_table(
                        c,
                        MARGIN,
                        y,
                        widths=widths,
                        headers=headers,
                        rows=chunk,
                        row_h=row_h,
                        header_h=header_h,
                        font_size=7.4,
                    )
                    row_idx += len(chunk)
                continue

            if kind == "heading":
                section_title = self._string_from_block(block, payload)
                if y - 28 < 70:
                    doc.add_page(c.to_bytes(), c.used_images)
                    page_num += 1
                    c, y = self._new_page(page_num, payload, request.family, title)
                y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, section_title)
                continue

        signer = payload.get("signature")
        if isinstance(signer, list) and len(signer) >= 3:
            draw_signature_block(c, MARGIN + 8, 48, 260, str(signer[0]), str(signer[1]), str(signer[2]))

        doc.add_page(c.to_bytes(), c.used_images)
        doc.save(str(request.output_pdf))
        return RenderResult(request.output_pdf, self.mode, {"pages": len(doc.pages)})

    def _new_page(self, page_num: int, payload: Dict[str, Any], family: str, title: str) -> Tuple[Canvas, float]:
        c = Canvas()
        header = f"{payload.get('facility', 'Community General Hospital')} | {family.replace('_', ' ').title()}"
        page_chrome(c, header, page_num, str(payload.get("patient_name", "Synthetic Patient")), str(payload.get("patient_mrn", "0000000")))
        y = PAGE_H - 92
        y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, title)
        return c, y

    def _pairs_from_block(self, block: Dict[str, Any], payload: Dict[str, Any]) -> List[Tuple[str, str]]:
        if "source" in block:
            src = payload.get(str(block["source"]), [])
            if isinstance(src, list):
                out: List[Tuple[str, str]] = []
                for item in src:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        out.append((str(item[0]), str(item[1])))
                return out
        pairs = block.get("pairs", [])
        out: List[Tuple[str, str]] = []
        if isinstance(pairs, list):
            for p in pairs:
                if isinstance(p, (list, tuple)) and len(p) >= 2:
                    out.append((str(p[0]), str(p[1])))
        return out

    def _list_from_block(self, block: Dict[str, Any], payload: Dict[str, Any]) -> List[str]:
        if "source" in block:
            src = payload.get(str(block["source"]), [])
            if isinstance(src, list):
                return [str(v) for v in src]
        items = block.get("items", [])
        if isinstance(items, list):
            return [str(v) for v in items]
        return [str(items)] if items else []

    def _rows_from_block(self, block: Dict[str, Any], payload: Dict[str, Any]) -> List[List[str]]:
        if "source" in block:
            src = payload.get(str(block["source"]), [])
            if isinstance(src, list):
                out: List[List[str]] = []
                for row in src:
                    if isinstance(row, list):
                        out.append([str(v) for v in row])
                return out
        rows = block.get("rows", [])
        out: List[List[str]] = []
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, list):
                    out.append([str(v) for v in row])
        return out

    def _string_from_block(self, block: Dict[str, Any], payload: Dict[str, Any]) -> str:
        if "source" in block:
            src = payload.get(str(block["source"]), "")
            if isinstance(src, list):
                return " ".join(str(v) for v in src)
            return str(src)
        return str(block.get("text", ""))
