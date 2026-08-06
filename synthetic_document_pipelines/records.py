from __future__ import annotations

import random
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from reportlab.lib import colors
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader

from .common import SYNTHETIC_BANNER, SpecValidationError, require_list, require_mapping, require_synthetic, text
from .scan import apply_scan_profile


PAGE_W, PAGE_H = letter
MARGIN = 42.0
INK = colors.HexColor("#383838")
MID = colors.HexColor("#69737C")
RULE = colors.HexColor("#A5A9AC")
BLUE = colors.HexColor("#415D72")
PALE_BLUE = colors.HexColor("#E9EFF3")
PALE_GRAY = colors.HexColor("#F4F4F2")
RED = colors.HexColor("#A63831")
PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def _wrap(value: str, font_name: str, font_size: float, width: float) -> list[str]:
    words = value.replace("\n", " ").split()
    if not words:
        return [""]
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = word if not line else f"{line} {word}"
        if stringWidth(candidate, font_name, font_size) <= width or not line:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _draw_lines(canvas: Canvas, value: str, *, x: float, y: float, width: float, font: str = "Helvetica", size: float = 8.7, leading: float = 11.2, color: Color = INK) -> float:
    canvas.setFont(font, size)
    canvas.setFillColor(color)
    for line in _wrap(value, font, size, width):
        canvas.drawString(x, y, line)
        y -= leading
    return y


def _draw_rule(canvas: Canvas, y: float) -> float:
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.6)
    canvas.line(MARGIN, y, PAGE_W - MARGIN, y)
    return y - 11


def _section_header(canvas: Canvas, heading: str, y: float) -> float:
    y = _draw_rule(canvas, y)
    canvas.setFillColor(BLUE)
    canvas.setFont("Helvetica-Bold", 10.5)
    canvas.drawString(MARGIN, y, heading.upper())
    return y - 15


def _asset_path(value: Any, field_name: str) -> Path:
    raw_value = text(value, "")
    if not raw_value:
        raise SpecValidationError(f"{field_name} is required when an asset is requested")
    supplied = Path(raw_value).expanduser()
    candidates = (supplied, PACKAGE_ROOT / supplied)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise SpecValidationError(f"{field_name} does not exist: {raw_value}")


def _draw_brand_logo(canvas: Canvas, branding: Mapping[str, Any]) -> None:
    logo = branding.get("logo")
    if not logo:
        return
    image = ImageReader(str(_asset_path(logo, "branding.logo")))
    source_width, source_height = image.getSize()
    height = 29.0
    width = min(116.0, height * source_width / source_height)
    x = PAGE_W - MARGIN - width
    y = PAGE_H - 58
    canvas.drawImage(image, x, y, width=width, height=height, preserveAspectRatio=True, mask="auto")
    organization = text(branding.get("organization"), "Fictional organization")
    canvas.setFillColor(MID)
    canvas.setFont("Helvetica", 5.8)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 66, organization)


def _header(
    canvas: Canvas,
    patient: Mapping[str, Any],
    encounter: Mapping[str, Any],
    document: Mapping[str, Any],
    branding: Mapping[str, Any],
    page_number: int,
) -> float:
    canvas.setFillColor(RED)
    canvas.setFont("Helvetica-Bold", 6.6)
    canvas.drawString(MARGIN, PAGE_H - 21, SYNTHETIC_BANNER)
    canvas.setStrokeColor(RED)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, PAGE_H - 25, PAGE_W - MARGIN, PAGE_H - 25)

    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(MARGIN, PAGE_H - 50, text(patient.get("name"), "Synthetic Patient"))
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(MID)
    canvas.drawString(MARGIN, PAGE_H - 64, f"DOB: {text(patient.get('dob'))}    Sex: {text(patient.get('sex'))}    MRN: {text(patient.get('mrn'))}")
    _draw_brand_logo(canvas, branding)
    canvas.setFont("Helvetica", 6.6)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 77, f"Encounter: {text(encounter.get('id'))}")

    canvas.setFillColor(PALE_BLUE)
    canvas.rect(MARGIN, PAGE_H - 88, PAGE_W - 2 * MARGIN, 21, stroke=0, fill=1)
    canvas.setFillColor(BLUE)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(MARGIN + 8, PAGE_H - 81, text(document.get("title"), "Clinical Record"))
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawRightString(PAGE_W - MARGIN - 8, PAGE_H - 80, text(document.get("status"), "Final result"))
    provenance: list[str] = [f"Packet position: {page_number}"]
    if document.get("clinical_datetime"):
        provenance.append(f"Event: {text(document.get('clinical_datetime'))}")
    if document.get("filed_datetime"):
        provenance.append(f"Filed: {text(document.get('filed_datetime'))}")
    if document.get("source_state"):
        provenance.append(f"Source state: {text(document.get('source_state'))}")
    canvas.setFillColor(MID)
    canvas.setFont("Helvetica", 6.15)
    canvas.drawString(MARGIN, PAGE_H - 99, "  |  ".join(provenance))
    return PAGE_H - 113


def _draw_record_flags(canvas: Canvas, flags: Iterable[Any], y: float) -> float:
    values = [text(flag, "") for flag in flags if text(flag, "")]
    if not values:
        return y
    label = "RECORD IRREGULARITIES: " + " | ".join(values)
    lines = _wrap(label, "Helvetica-Bold", 6.8, PAGE_W - 2 * MARGIN - 12)
    height = 9 + len(lines) * 8.5
    canvas.setFillColor(colors.HexColor("#FFF5D8"))
    canvas.setStrokeColor(colors.HexColor("#D7B66E"))
    canvas.setLineWidth(0.45)
    canvas.rect(MARGIN, y - height, PAGE_W - 2 * MARGIN, height, stroke=1, fill=1)
    canvas.setFillColor(colors.HexColor("#76541E"))
    canvas.setFont("Helvetica-Bold", 6.8)
    line_y = y - 8
    for line in lines:
        canvas.drawString(MARGIN + 6, line_y, line)
        line_y -= 8.5
    return y - height - 7


def _draw_charges(canvas: Canvas, rows: Iterable[Any], y: float) -> float:
    parsed = [row for row in rows if isinstance(row, dict)]
    if not parsed:
        return y
    y = _section_header(canvas, "Existing Charges", y)
    headers = [("Line", 48), ("Charge", 170), ("Code", 65), ("Status", 135), ("Trigger", 90)]
    x = MARGIN
    canvas.setFillColor(PALE_GRAY)
    canvas.rect(MARGIN, y - 15, PAGE_W - 2 * MARGIN, 15, stroke=0, fill=1)
    canvas.setFont("Helvetica-Bold", 6.8)
    canvas.setFillColor(MID)
    for label, width in headers:
        canvas.drawString(x + 4, y - 10, label)
        x += width
    y -= 18

    for row in parsed[:4]:
        values = [
            text(row.get("line"), "SYN"),
            text(row.get("charge")),
            text(row.get("code")),
            text(row.get("status")),
            text(row.get("trigger")),
        ]
        x = MARGIN
        baseline = y - 9
        lowest_point = baseline
        for value, (_, width) in zip(values, headers):
            y_after = _draw_lines(canvas, value, x=x + 4, y=baseline, width=width - 8, size=7.2, leading=8.6)
            x += width
            lowest_point = min(lowest_point, y_after)
        row_height = max(20, y - lowest_point + 4)
        canvas.setStrokeColor(colors.HexColor("#CFD3D5"))
        canvas.setLineWidth(0.35)
        canvas.line(MARGIN, y - row_height, PAGE_W - MARGIN, y - row_height)
        y -= row_height
    return y - 5


def _draw_details(canvas: Canvas, values: Iterable[Any], y: float) -> float:
    parsed = [item for item in values if isinstance(item, dict)]
    if not parsed:
        return y
    y = _section_header(canvas, "Details", y)
    for item in parsed:
        label = text(item.get("label"), "Field")
        value = text(item.get("value"))
        canvas.setFont("Helvetica-Bold", 7.7)
        canvas.setFillColor(MID)
        canvas.drawString(MARGIN + 2, y, label)
        y = _draw_lines(canvas, value, x=MARGIN + 128, y=y, width=PAGE_W - MARGIN - (MARGIN + 128), size=8.2, leading=10.0)
        y -= 2
    return y - 3


def _draw_result_table(canvas: Canvas, rows: Iterable[Any], y: float) -> float:
    parsed = [row for row in rows if isinstance(row, dict)]
    if not parsed:
        return y
    y = _section_header(canvas, "Results", y)
    headers = [("Test", 148), ("Result", 95), ("Units", 58), ("Reference", 133), ("Flag", 74)]
    x = MARGIN
    canvas.setFillColor(PALE_GRAY)
    canvas.rect(MARGIN, y - 15, PAGE_W - 2 * MARGIN, 15, stroke=0, fill=1)
    canvas.setFillColor(MID)
    canvas.setFont("Helvetica-Bold", 6.8)
    for label, width in headers:
        canvas.drawString(x + 4, y - 10, label)
        x += width
    y -= 18
    for row in parsed[:8]:
        values = [
            text(row.get("test")),
            text(row.get("result")),
            text(row.get("units")),
            text(row.get("reference")),
            text(row.get("flag"), "Normal"),
        ]
        x = MARGIN
        baseline = y - 9
        lowest_point = baseline
        for value, (_, width) in zip(values, headers):
            y_after = _draw_lines(canvas, value, x=x + 4, y=baseline, width=width - 8, size=7.2, leading=8.6)
            x += width
            lowest_point = min(lowest_point, y_after)
        row_height = max(20, y - lowest_point + 4)
        canvas.setStrokeColor(colors.HexColor("#CFD3D5"))
        canvas.setLineWidth(0.35)
        canvas.line(MARGIN, y - row_height, PAGE_W - MARGIN, y - row_height)
        y -= row_height
    return y - 5


def _draw_sections(canvas: Canvas, values: Iterable[Any], y: float) -> float:
    for section in values:
        if not isinstance(section, dict):
            continue
        heading = text(section.get("heading"), "Narrative")
        y = _section_header(canvas, heading, y)
        for paragraph in section.get("paragraphs", []):
            y = _draw_lines(canvas, text(paragraph), x=MARGIN + 2, y=y, width=PAGE_W - 2 * MARGIN - 4)
            y -= 4
        for item in section.get("items", []):
            if isinstance(item, dict):
                label = text(item.get("label"), "Item")
                value = text(item.get("value"))
                y = _draw_lines(canvas, f"{label}: {value}", x=MARGIN + 10, y=y, width=PAGE_W - 2 * MARGIN - 14, size=8.2, leading=10.4)
                y -= 2
    return y


def _draw_image_panel(canvas: Canvas, panel: Any, y: float) -> float:
    if not isinstance(panel, dict):
        return y
    asset = _asset_path(panel.get("asset"), "image_panel.asset")
    image = ImageReader(str(asset))
    source_width, source_height = image.getSize()
    max_width = min(float(panel.get("width", 240.0)), PAGE_W - 2 * MARGIN)
    height = max_width * source_height / source_width
    x = MARGIN + (PAGE_W - 2 * MARGIN - max_width) / 2
    y -= 2
    canvas.setFillColor(colors.HexColor("#171B1E"))
    canvas.rect(x - 4, y - height - 4, max_width + 8, height + 8, stroke=0, fill=1)
    canvas.drawImage(image, x, y - height, width=max_width, height=height, preserveAspectRatio=True, mask="auto")
    label = text(panel.get("label"), "SYNTHETIC / NON-DIAGNOSTIC / ILLUSTRATIVE ONLY")
    canvas.setFillColor(colors.Color(0, 0, 0, alpha=0.62))
    canvas.rect(x, y - height, max_width, 15, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 6.4)
    canvas.drawCentredString(x + max_width / 2, y - height + 4.4, label)
    caption = text(panel.get("caption"), "Illustrative synthetic image panel")
    return _draw_lines(canvas, caption, x=MARGIN + 2, y=y - height - 16, width=PAGE_W - 2 * MARGIN - 4, font="Helvetica-Oblique", size=7.2, leading=9.0, color=MID) - 5


def _validate_illustrative_imaging(spec: Mapping[str, Any], documents: Iterable[Any]) -> int:
    panels = [document for document in documents if isinstance(document, dict) and isinstance(document.get("image_panel"), dict)]
    if not panels:
        return 0
    rendering = require_mapping(spec.get("rendering", {}), "rendering")
    if rendering.get("allow_illustrative_imaging") is not True:
        raise SpecValidationError(
            "Illustrative imaging is opt-in: set rendering.allow_illustrative_imaging to true when a packet specifically needs it"
        )
    if not str(rendering.get("illustrative_imaging_reason", "")).strip():
        raise SpecValidationError("rendering.illustrative_imaging_reason is required when illustrative imaging is enabled")
    maximum = int(rendering.get("max_illustrative_image_panels", 1))
    if maximum < 1 or len(panels) > maximum:
        raise SpecValidationError("The number of illustrative image panels exceeds rendering.max_illustrative_image_panels")
    return len(panels)


def _draw_scan_marks(canvas: Canvas, annotations: Iterable[Any], y: float, rng: random.Random) -> None:
    canvas.saveState()
    for _ in range(110):
        x = rng.uniform(MARGIN, PAGE_W - MARGIN)
        yy = rng.uniform(36, PAGE_H - 96)
        shade = rng.uniform(0.76, 0.90)
        canvas.setFillColor(colors.Color(shade, shade, shade, alpha=rng.uniform(0.11, 0.24)))
        radius = rng.uniform(0.12, 0.35)
        canvas.circle(x, yy, radius, stroke=0, fill=1)
    canvas.setStrokeColor(colors.Color(0.60, 0.60, 0.60, alpha=0.18))
    canvas.setLineWidth(0.35)
    canvas.line(MARGIN + rng.uniform(2, 10), 42, MARGIN + rng.uniform(2, 10), PAGE_H - 100)
    # The paper/noise layer uses transparency; handwritten assets must restore
    # full opacity so they remain legible after rasterizing the fax page.
    canvas.setFillAlpha(1.0)
    canvas.setStrokeAlpha(1.0)

    for item in annotations:
        if not isinstance(item, dict):
            continue
        x = float(item.get("x", PAGE_W - 170))
        yy = float(item.get("y", max(75, y - 6)))
        canvas.saveState()
        canvas.translate(x, yy)
        canvas.rotate(float(item.get("angle", rng.uniform(-4, 4))))
        if item.get("asset"):
            image = ImageReader(str(_asset_path(item.get("asset"), "annotations.asset")))
            source_width, source_height = image.getSize()
            width = float(item.get("width", 360.0))
            height = width * source_height / source_width
            canvas.drawImage(image, 0, 0, width=width, height=height, preserveAspectRatio=True, mask="auto")
        else:
            value = text(item.get("text"), "reviewed")
            canvas.setFillColor(colors.HexColor("#315A83"))
            canvas.setFont("Helvetica-Oblique", float(item.get("size", 11)))
            canvas.drawString(0, 0, value)
        canvas.restoreState()
    canvas.restoreState()


def _draw_footer(canvas: Canvas, page_number: int) -> None:
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 27, PAGE_W - MARGIN, 27)
    canvas.setFont("Helvetica", 6.7)
    canvas.setFillColor(MID)
    canvas.drawString(MARGIN, 17, "Fictional demonstration record - not a real EHR export")
    canvas.drawRightString(PAGE_W - MARGIN, 17, f"Page {page_number}")


def generate_record_packet(spec: Mapping[str, Any], output_pdf: Path) -> dict[str, Any]:
    metadata = require_synthetic(spec)
    patient = require_mapping(spec.get("patient"), "patient")
    encounter = require_mapping(spec.get("encounter"), "encounter")
    branding = require_mapping(spec.get("branding", {}), "branding")
    packet = require_mapping(spec.get("packet", {}), "packet")
    documents = require_list(spec.get("documents"), "documents")
    if not documents:
        raise SpecValidationError("documents must contain at least one page")
    image_panel_count = _validate_illustrative_imaging(spec, documents)

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    seed = int(metadata.get("seed", 0))
    scan_pages: list[int] = []

    with tempfile.TemporaryDirectory(prefix="synthetic-record-") as temp_dir:
        native_pdf = Path(temp_dir) / "native.pdf"
        canvas = Canvas(str(native_pdf), pagesize=letter, pageCompression=1, invariant=1)
        canvas.setTitle(text(spec.get("title"), "Synthetic Medical Record Packet"))
        canvas.setAuthor("SyntheticRecordGenerator")

        for page_number, raw_document in enumerate(documents, start=1):
            document = require_mapping(raw_document, f"documents[{page_number - 1}]")
            y = _header(canvas, patient, encounter, document, branding, page_number)
            y = _draw_record_flags(canvas, document.get("record_flags", []), y)
            y = _draw_charges(canvas, document.get("charges", []), y)
            y = _draw_details(canvas, document.get("details", []), y)
            y = _draw_result_table(canvas, document.get("result_rows", []), y)
            y = _draw_image_panel(canvas, document.get("image_panel"), y)
            y = _draw_sections(canvas, document.get("sections", []), y)
            scanned = bool(document.get("scanned", False))
            if scanned:
                _draw_scan_marks(canvas, document.get("annotations", []), y, random.Random(seed + page_number * 104729))
                scan_pages.append(page_number)
            _draw_footer(canvas, page_number)
            canvas.showPage()
        canvas.save()

        scan_info = apply_scan_profile(native_pdf, output_pdf, selected_pages=scan_pages, seed=seed)

    document_type_counts = Counter(
        text(document.get("type"), "unspecified")
        for document in documents
        if isinstance(document, dict)
    )
    return {
        "pages": len(documents),
        "profile": text(spec.get("profile"), "generic_ehr"),
        "scan": scan_info,
        "packet_order": text(packet.get("document_order"), "input_order"),
        "document_types": dict(sorted(document_type_counts.items())),
        "illustrative_image_panels": image_panel_count,
        "flagged_pages": [
            page_number
            for page_number, document in enumerate(documents, start=1)
            if isinstance(document, dict) and document.get("record_flags")
        ],
        "synthetic_label": metadata["synthetic_label"],
    }
