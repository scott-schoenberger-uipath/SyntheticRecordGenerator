from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader

from .common import SYNTHETIC_BANNER, SpecValidationError, require_list, require_mapping, require_synthetic, text


PAGE_W, PAGE_H = letter
MARGIN = 50.0
NAVY = colors.HexColor("#183B59")
BLUE = colors.HexColor("#2D638B")
MID = colors.HexColor("#5D6770")
RULE = colors.HexColor("#AAB3B8")
PALE = colors.HexColor("#EAF1F5")
RED = colors.HexColor("#A63831")
PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def _wrap(value: str, font: str, size: float, width: float) -> list[str]:
    words = value.replace("\n", " ").split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = word if not line else f"{line} {word}"
        if not line or stringWidth(candidate, font, size) <= width:
            line = candidate
        else:
            lines.append(line)
            line = word
    return lines + ([line] if line else [])


def _lines(canvas: Canvas, value: str, x: float, y: float, width: float, *, font: str = "Helvetica", size: float = 9.4, leading: float = 12.2, bullet: bool = False) -> float:
    canvas.setFillColor(colors.HexColor("#333333"))
    canvas.setFont(font, size)
    for idx, line in enumerate(_wrap(value, font, size, width - (11 if bullet else 0))):
        if bullet and idx == 0:
            canvas.drawString(x, y, "-")
            canvas.drawString(x + 11, y, line)
        else:
            canvas.drawString(x + (11 if bullet else 0), y, line)
        y -= leading
    return y


def _asset_path(value: Any) -> Path:
    supplied = Path(text(value, "")).expanduser()
    for candidate in (supplied, PACKAGE_ROOT / supplied):
        if candidate.is_file():
            return candidate
    raise SpecValidationError(f"branding.logo does not exist: {value}")


def _header(canvas: Canvas, policy: Mapping[str, Any], branding: Mapping[str, Any], page_number: int) -> float:
    canvas.setFillColor(RED)
    canvas.setFont("Helvetica-Bold", 6.6)
    canvas.drawString(MARGIN, PAGE_H - 21, SYNTHETIC_BANNER)
    canvas.setStrokeColor(RED)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, PAGE_H - 25, PAGE_W - MARGIN, PAGE_H - 25)

    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(MARGIN, PAGE_H - 48, "ILLUSTRATIVE COVERAGE POLICY")
    if branding.get("logo"):
        image = ImageReader(str(_asset_path(branding.get("logo"))))
        source_width, source_height = image.getSize()
        height = 24.0
        width = min(108.0, height * source_width / source_height)
        canvas.drawImage(image, PAGE_W - MARGIN - width, PAGE_H - 55, width=width, height=height, preserveAspectRatio=True, mask="auto")
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(MID)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 63, text(branding.get("organization"), "Synthetic Policy Office"))
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 72, f"Policy ID: {text(policy.get('id'))}")
    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(1.1)
    canvas.line(MARGIN, PAGE_H - 56, PAGE_W - MARGIN, PAGE_H - 56)
    return PAGE_H - 77


def _footer(canvas: Canvas, policy: Mapping[str, Any], page_number: int) -> None:
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 31, PAGE_W - MARGIN, 31)
    canvas.setFillColor(MID)
    canvas.setFont("Helvetica", 6.8)
    canvas.drawString(MARGIN, 20, "Illustrative synthetic policy - not an actual coverage determination")
    canvas.drawRightString(PAGE_W - MARGIN, 20, f"{text(policy.get('id'))} | Page {page_number}")


def _control_table(canvas: Canvas, policy: Mapping[str, Any], y: float) -> float:
    rows = [
        ("Status", text(policy.get("status"), "Draft")),
        ("Effective date", text(policy.get("effective_date"))),
        ("Review date", text(policy.get("review_date"))),
        ("Jurisdiction", text(policy.get("jurisdiction"), "Demonstration only")),
        ("Owner", text(policy.get("owner"), "Synthetic Policy Office")),
    ]
    left_width = 120.0
    row_height = 18.0
    canvas.setFillColor(PALE)
    canvas.rect(MARGIN, y - row_height * len(rows), PAGE_W - 2 * MARGIN, row_height * len(rows), stroke=0, fill=1)
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.35)
    for index, (label, value) in enumerate(rows):
        baseline = y - 12 - index * row_height
        canvas.line(MARGIN, y - index * row_height, PAGE_W - MARGIN, y - index * row_height)
        canvas.setFillColor(NAVY)
        canvas.setFont("Helvetica-Bold", 7.6)
        canvas.drawString(MARGIN + 7, baseline, label)
        canvas.setFillColor(colors.HexColor("#333333"))
        canvas.setFont("Helvetica", 8.2)
        canvas.drawString(MARGIN + left_width, baseline, value)
    canvas.line(MARGIN, y - row_height * len(rows), PAGE_W - MARGIN, y - row_height * len(rows))
    return y - row_height * len(rows) - 16


def generate_policy(spec: Mapping[str, Any], output_pdf: Path) -> dict[str, Any]:
    metadata = require_synthetic(spec)
    policy = require_mapping(spec.get("policy"), "policy")
    branding = require_mapping(spec.get("branding", {}), "branding")
    sections = require_list(spec.get("sections"), "sections")
    references = require_list(spec.get("references", []), "references")
    if not sections:
        raise SpecValidationError("sections must contain at least one section")

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(output_pdf), pagesize=letter, pageCompression=1, invariant=1)
    canvas.setTitle(text(policy.get("title"), "Illustrative Synthetic Policy"))
    canvas.setAuthor("SyntheticRecordGenerator")
    page_number = 1
    y = _header(canvas, policy, branding, page_number)

    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 18)
    for line in _wrap(text(policy.get("title")), "Helvetica-Bold", 18, PAGE_W - 2 * MARGIN):
        canvas.drawString(MARGIN, y, line)
        y -= 22
    canvas.setFillColor(MID)
    canvas.setFont("Helvetica", 8.7)
    y -= 3
    canvas.drawString(MARGIN, y, text(policy.get("subtitle"), "Fictional policy document for demonstration and evaluation"))
    y -= 19
    y = _control_table(canvas, policy, y)

    def new_page() -> float:
        nonlocal page_number
        _footer(canvas, policy, page_number)
        canvas.showPage()
        page_number += 1
        return _header(canvas, policy, branding, page_number)

    for raw_section in sections:
        section = require_mapping(raw_section, "section")
        heading = text(section.get("heading"), "Policy Section")
        expected_height = 28 + sum(max(1, len(_wrap(text(p), "Helvetica", 9.4, PAGE_W - 2 * MARGIN)))*12.2 + 5 for p in section.get("paragraphs", []))
        expected_height += sum(max(1, len(_wrap(text(p), "Helvetica", 9.0, PAGE_W - 2 * MARGIN - 12)))*11.5 + 3 for p in section.get("bullets", []))
        if y - expected_height < 54:
            y = new_page()
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.55)
        canvas.line(MARGIN, y, PAGE_W - MARGIN, y)
        y -= 14
        canvas.setFillColor(BLUE)
        canvas.setFont("Helvetica-Bold", 10.5)
        canvas.drawString(MARGIN, y, heading.upper())
        y -= 16
        for paragraph in section.get("paragraphs", []):
            y = _lines(canvas, text(paragraph), MARGIN, y, PAGE_W - 2 * MARGIN)
            y -= 5
        for bullet in section.get("bullets", []):
            y = _lines(canvas, text(bullet), MARGIN, y, PAGE_W - 2 * MARGIN, size=9.0, leading=11.5, bullet=True)
            y -= 3
        y -= 5

    if references:
        if y < 130:
            y = new_page()
        canvas.setStrokeColor(RULE)
        canvas.line(MARGIN, y, PAGE_W - MARGIN, y)
        y -= 14
        canvas.setFillColor(BLUE)
        canvas.setFont("Helvetica-Bold", 10.5)
        canvas.drawString(MARGIN, y, "REFERENCES AND SOURCE NOTES")
        y -= 16
        for reference in references:
            y = _lines(canvas, text(reference), MARGIN, y, PAGE_W - 2 * MARGIN, size=8.1, leading=10.2, bullet=True)
            y -= 3

    _footer(canvas, policy, page_number)
    canvas.save()
    return {"pages": page_number, "profile": text(spec.get("profile"), "public_policy"), "synthetic_label": metadata["synthetic_label"]}
