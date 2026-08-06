from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from .base import RenderRequest, RenderResult, Renderer
from .html_pdf_renderer import HtmlPdfRenderer


class PdfmeRenderer(Renderer):
    mode = "pdfmeRenderer"

    def __init__(self) -> None:
        self._bridge = Path(__file__).resolve().parent / "pdfme_bridge.mjs"

    def render(self, request: RenderRequest) -> RenderResult:
        template = request.template_data
        payload = request.payload

        if self._pdfme_available() and self._bridge.exists():
            try:
                pdfme_template, inputs = self._build_pdfme_inputs(template, payload)
                with tempfile.TemporaryDirectory(prefix="pdfme-render-") as td:
                    root = Path(td)
                    template_json = root / "template.json"
                    inputs_json = root / "inputs.json"
                    template_json.write_text(json.dumps(pdfme_template), encoding="utf-8")
                    inputs_json.write_text(json.dumps(inputs), encoding="utf-8")
                    cmd = [
                        "node",
                        str(self._bridge),
                        "--template-json",
                        str(template_json),
                        "--inputs-json",
                        str(inputs_json),
                        "--out",
                        str(request.output_pdf),
                    ]
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return RenderResult(request.output_pdf, self.mode, {"used_pdfme": True})
            except Exception:
                # fallback below
                pass

        fallback = self._fallback_template(template, payload)
        html_renderer = HtmlPdfRenderer()
        fallback_req = RenderRequest(
            family=request.family,
            renderer_name=html_renderer.mode,
            template_id=request.template_id,
            template_data=fallback,
            payload=payload,
            output_pdf=request.output_pdf,
            context=request.context,
        )
        result = html_renderer.render(fallback_req)
        return RenderResult(result.output_pdf, self.mode, {"used_pdfme": False, "fallback_renderer": html_renderer.mode})

    def _pdfme_available(self) -> bool:
        if shutil.which("node") is None:
            return False
        try:
            probe = ["node", "-e", "require.resolve('@pdfme/generator');require.resolve('@pdfme/schemas')"]
            subprocess.run(probe, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def _build_pdfme_inputs(self, template: Dict[str, Any], payload: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        sections = template.get("fixed_sections", [])
        if not isinstance(sections, list):
            sections = []

        schemas: List[List[Dict[str, Any]]] = [[]]
        current_page = 0
        y = 20.0
        field_idx = 0
        inputs: Dict[str, str] = {}

        def add_line(text: str, size: float = 9.0, bold: bool = False) -> None:
            nonlocal y, current_page, field_idx
            if y > 275:
                schemas.append([])
                current_page += 1
                y = 20.0
            name = f"f_{field_idx:04d}"
            field_idx += 1
            schemas[current_page].append(
                {
                    "name": name,
                    "type": "text",
                    "position": {"x": 10.0, "y": y},
                    "width": 188.0,
                    "height": 5.2,
                    "fontSize": size,
                    "fontName": "Helvetica-Bold" if bold else "Helvetica",
                }
            )
            inputs[name] = text
            y += 5.6

        add_line("SYNTHETIC / FICTIONAL / NOT FOR CLINICAL, BILLING, OR COVERAGE USE", size=6.5, bold=True)
        title = str(template.get("title") or payload.get("title") or "Synthetic Form")
        subtitle = str(payload.get("header_subtitle", ""))
        add_line(title, size=12.0, bold=True)
        if subtitle:
            add_line(subtitle, size=9.0)
        y += 2.0

        for sec in sections:
            if not isinstance(sec, dict):
                continue
            sec_title = str(sec.get("title", "Section"))
            add_line(sec_title.upper(), size=9.5, bold=True)
            kind = str(sec.get("kind", "kv"))
            if kind == "kv":
                src = sec.get("source")
                pairs = payload.get(str(src), []) if src else sec.get("pairs", [])
                if isinstance(pairs, list):
                    for pair in pairs:
                        if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                            add_line(f"{pair[0]}: {pair[1]}", size=8.5)
            elif kind == "table":
                cols = sec.get("columns", [])
                if isinstance(cols, list) and cols:
                    add_line(" | ".join(str(c) for c in cols), size=8.0, bold=True)
                src = sec.get("source")
                rows = payload.get(str(src), []) if src else sec.get("rows", [])
                if isinstance(rows, list):
                    for row in rows[:40]:
                        if isinstance(row, list):
                            add_line(" | ".join(str(v) for v in row), size=7.2)
            y += 1.5

        pdfme_template = {
            "basePdf": {"width": 210, "height": 297, "padding": [8, 8, 8, 8]},
            "schemas": schemas,
        }
        return pdfme_template, [inputs]

    def _fallback_template(self, template: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        sections = template.get("fixed_sections", [])
        if not isinstance(sections, list):
            sections = []
        blocks: List[Dict[str, Any]] = []
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            kind = str(sec.get("kind", "kv"))
            block: Dict[str, Any] = {"kind": "kv" if kind == "kv" else "table", "title": str(sec.get("title", "Section"))}
            if "source" in sec:
                block["source"] = str(sec["source"])
            if "pairs" in sec:
                block["pairs"] = sec["pairs"]
            if "columns" in sec:
                block["columns"] = sec["columns"]
            if "rows" in sec:
                block["rows"] = sec["rows"]
            blocks.append(block)

        return {
            "title": str(template.get("title") or payload.get("title") or "Synthetic Form"),
            "blocks": blocks,
        }
