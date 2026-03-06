#!/usr/bin/env python3
"""
Generate a realistic-looking, clearly synthetic patient chart PDF.

This script intentionally produces fictional data and labels the record as
synthetic throughout the document.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import textwrap
import zlib
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


PAGE_W = 612.0  # US Letter width in points
PAGE_H = 792.0  # US Letter height in points
MARGIN = 36.0
DEFAULT_SHOW_CENTER_WATERMARK = False
DEFAULT_INCLUDE_SYNTHETIC_IMAGING = False


def fmt_num(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class PDFWriter:
    def __init__(self) -> None:
        self._objects: List[bytes] = []

    def add_object(self, data: bytes) -> int:
        self._objects.append(data)
        return len(self._objects)

    def add_stream(self, dict_entries: str, stream_data: bytes) -> int:
        header = f"<< {dict_entries} /Length {len(stream_data)} >>\nstream\n".encode("ascii")
        trailer = b"\nendstream"
        return self.add_object(header + stream_data + trailer)

    def build(self, root_obj_id: int) -> bytes:
        out = bytearray()
        out.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for idx, obj in enumerate(self._objects, start=1):
            offsets.append(len(out))
            out.extend(f"{idx} 0 obj\n".encode("ascii"))
            out.extend(obj)
            out.extend(b"\nendobj\n")

        xref_pos = len(out)
        out.extend(f"xref\n0 {len(self._objects) + 1}\n".encode("ascii"))
        out.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
        out.extend(
            (
                f"trailer\n<< /Size {len(self._objects) + 1} /Root {root_obj_id} 0 R >>\n"
                f"startxref\n{xref_pos}\n%%EOF\n"
            ).encode("ascii")
        )
        return bytes(out)


@dataclass
class ImageXObject:
    name: str
    width: int
    height: int
    pixels: bytes  # 8-bit grayscale
    object_id: Optional[int] = None


@dataclass
class PageContent:
    content: bytes
    width: float = PAGE_W
    height: float = PAGE_H
    image_names: List[str] = field(default_factory=list)


class PDFDocument:
    def __init__(self) -> None:
        self.writer = PDFWriter()
        self.fonts: Dict[str, int] = {}
        self.images: Dict[str, ImageXObject] = {}
        self.pages: List[PageContent] = []
        self._init_fonts()

    def _init_fonts(self) -> None:
        self._add_font("F1", "Helvetica")
        self._add_font("F2", "Helvetica-Bold")
        self._add_font("F3", "Helvetica-Oblique")
        self._add_font("F4", "Courier")

    def _add_font(self, alias: str, base_font: str) -> None:
        obj_id = self.writer.add_object(
            f"<< /Type /Font /Subtype /Type1 /BaseFont /{base_font} >>".encode("ascii")
        )
        self.fonts[alias] = obj_id

    def add_gray_image(self, name: str, width: int, height: int, pixels: bytes) -> None:
        if len(pixels) != width * height:
            raise ValueError("Image pixel length mismatch")
        self.images[name] = ImageXObject(name=name, width=width, height=height, pixels=pixels)

    def add_page(self, content: bytes, image_names: Optional[Iterable[str]] = None) -> None:
        self.pages.append(
            PageContent(content=content, image_names=list(image_names or []))
        )

    def save(self, path: str) -> None:
        # Add image XObjects first so page resources can reference object ids.
        for image in self.images.values():
            if image.object_id is not None:
                continue
            compressed = zlib.compress(image.pixels, level=9)
            image.object_id = self.writer.add_stream(
                (
                    "/Type /XObject /Subtype /Image "
                    f"/Width {image.width} /Height {image.height} "
                    "/ColorSpace /DeviceGray /BitsPerComponent 8 "
                    "/Filter /FlateDecode"
                ),
                compressed,
            )

        page_obj_ids: List[int] = []
        content_obj_ids: List[int] = []

        # Placeholder for pages tree so Page objects can reference it.
        pages_tree_placeholder_id = self.writer.add_object(b"<< /Type /Pages /Count 0 /Kids [] >>")

        font_resources = " ".join(
            f"/{alias} {obj_id} 0 R" for alias, obj_id in self.fonts.items()
        )

        for page in self.pages:
            content_obj_id = self.writer.add_stream("", page.content)
            content_obj_ids.append(content_obj_id)

            xobj_resources = ""
            if page.image_names:
                x_entries = []
                for name in page.image_names:
                    image = self.images[name]
                    if image.object_id is None:
                        raise RuntimeError(f"Image object missing id for {name}")
                    x_entries.append(f"/{name} {image.object_id} 0 R")
                xobj_resources = f"/XObject << {' '.join(x_entries)} >> "

            page_dict = (
                "<< /Type /Page "
                f"/Parent {pages_tree_placeholder_id} 0 R "
                f"/MediaBox [0 0 {fmt_num(page.width)} {fmt_num(page.height)}] "
                f"/Resources << /Font << {font_resources} >> {xobj_resources}>> "
                f"/Contents {content_obj_id} 0 R >>"
            )
            page_obj_id = self.writer.add_object(page_dict.encode("ascii"))
            page_obj_ids.append(page_obj_id)

        kids = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
        pages_tree = (
            f"<< /Type /Pages /Count {len(page_obj_ids)} /Kids [{kids}] >>"
        ).encode("ascii")
        # Overwrite placeholder object content directly.
        self.writer._objects[pages_tree_placeholder_id - 1] = pages_tree

        catalog_obj_id = self.writer.add_object(
            f"<< /Type /Catalog /Pages {pages_tree_placeholder_id} 0 R >>".encode("ascii")
        )

        pdf_bytes = self.writer.build(root_obj_id=catalog_obj_id)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(pdf_bytes)


class Canvas:
    def __init__(self, width: float = PAGE_W, height: float = PAGE_H) -> None:
        self.width = width
        self.height = height
        self._ops: List[str] = []
        self.used_images: set[str] = set()

    def raw(self, s: str) -> None:
        self._ops.append(s)

    def set_stroke(self, r: float, g: float, b: float) -> None:
        self.raw(f"{fmt_num(r)} {fmt_num(g)} {fmt_num(b)} RG")

    def set_fill(self, r: float, g: float, b: float) -> None:
        self.raw(f"{fmt_num(r)} {fmt_num(g)} {fmt_num(b)} rg")

    def set_line_width(self, w: float) -> None:
        self.raw(f"{fmt_num(w)} w")

    def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self.raw(f"{fmt_num(x1)} {fmt_num(y1)} m {fmt_num(x2)} {fmt_num(y2)} l S")

    def rect(self, x: float, y: float, w: float, h: float, fill: bool = False, stroke: bool = True) -> None:
        op = "B" if fill and stroke else ("f" if fill else "S")
        self.raw(f"{fmt_num(x)} {fmt_num(y)} {fmt_num(w)} {fmt_num(h)} re {op}")

    def rounded_rect(self, x: float, y: float, w: float, h: float, r: float, fill: bool = False, stroke: bool = True) -> None:
        # Approximate rounded rectangle with straight lines + Bezier corners.
        k = 0.552284749831 * r
        op = "B" if fill and stroke else ("f" if fill else "S")
        self.raw(
            " ".join(
                [
                    f"{fmt_num(x + r)} {fmt_num(y)} m",
                    f"{fmt_num(x + w - r)} {fmt_num(y)} l",
                    f"{fmt_num(x + w - r + k)} {fmt_num(y)} {fmt_num(x + w)} {fmt_num(y + r - k)} {fmt_num(x + w)} {fmt_num(y + r)} c",
                    f"{fmt_num(x + w)} {fmt_num(y + h - r)} l",
                    f"{fmt_num(x + w)} {fmt_num(y + h - r + k)} {fmt_num(x + w - r + k)} {fmt_num(y + h)} {fmt_num(x + w - r)} {fmt_num(y + h)} c",
                    f"{fmt_num(x + r)} {fmt_num(y + h)} l",
                    f"{fmt_num(x + r - k)} {fmt_num(y + h)} {fmt_num(x)} {fmt_num(y + h - r + k)} {fmt_num(x)} {fmt_num(y + h - r)} c",
                    f"{fmt_num(x)} {fmt_num(y + r)} l",
                    f"{fmt_num(x)} {fmt_num(y + r - k)} {fmt_num(x + r - k)} {fmt_num(y)} {fmt_num(x + r)} {fmt_num(y)} c",
                    op,
                ]
            )
        )

    def circle(self, cx: float, cy: float, r: float, fill: bool = False, stroke: bool = True) -> None:
        k = 0.552284749831 * r
        op = "B" if fill and stroke else ("f" if fill else "S")
        self.raw(
            " ".join(
                [
                    f"{fmt_num(cx + r)} {fmt_num(cy)} m",
                    f"{fmt_num(cx + r)} {fmt_num(cy + k)} {fmt_num(cx + k)} {fmt_num(cy + r)} {fmt_num(cx)} {fmt_num(cy + r)} c",
                    f"{fmt_num(cx - k)} {fmt_num(cy + r)} {fmt_num(cx - r)} {fmt_num(cy + k)} {fmt_num(cx - r)} {fmt_num(cy)} c",
                    f"{fmt_num(cx - r)} {fmt_num(cy - k)} {fmt_num(cx - k)} {fmt_num(cy - r)} {fmt_num(cx)} {fmt_num(cy - r)} c",
                    f"{fmt_num(cx + k)} {fmt_num(cy - r)} {fmt_num(cx + r)} {fmt_num(cy - k)} {fmt_num(cx + r)} {fmt_num(cy)} c",
                    op,
                ]
            )
        )

    def polyline(self, pts: Sequence[Tuple[float, float]], close: bool = False, fill: bool = False, stroke: bool = True) -> None:
        if not pts:
            return
        op = "B" if fill and stroke else ("f" if fill else "S")
        parts = [f"{fmt_num(pts[0][0])} {fmt_num(pts[0][1])} m"]
        parts.extend(f"{fmt_num(x)} {fmt_num(y)} l" for x, y in pts[1:])
        if close:
            parts.append("h")
        parts.append(op)
        self.raw(" ".join(parts))

    def text(self, x: float, y: float, text: str, *, font: str = "F1", size: float = 10, color=(0, 0, 0)) -> None:
        r, g, b = color
        self.raw(
            " ".join(
                [
                    "BT",
                    f"/{font} {fmt_num(size)} Tf",
                    f"{fmt_num(r)} {fmt_num(g)} {fmt_num(b)} rg",
                    f"1 0 0 1 {fmt_num(x)} {fmt_num(y)} Tm",
                    f"({pdf_escape(text)}) Tj",
                    "ET",
                ]
            )
        )

    def text_width(self, text: str, size: float, font: str = "F1") -> float:
        # Approximate metrics for built-in fonts.
        if font == "F4":
            return len(text) * size * 0.6
        width = 0.0
        for ch in text:
            if ch in "MW@#%&":
                width += 0.95
            elif ch in "ijl.,:;|' ":
                width += 0.28
            elif ch.isupper():
                width += 0.68
            else:
                width += 0.55
        return width * size

    def wrapped_text(
        self,
        x: float,
        y_top: float,
        text: str,
        *,
        max_width: float,
        leading: float = 12,
        font: str = "F1",
        size: float = 10,
        color=(0, 0, 0),
        bullet: bool = False,
    ) -> float:
        y = y_top
        first_prefix = "- " if bullet else ""
        hanging_prefix = "  " if bullet else ""
        words = text.split()
        lines: List[str] = []
        line = first_prefix
        for word in words:
            trial = (line + word).strip() if line.strip() == "" else line + word
            if self.text_width(trial, size, font=font) <= max_width:
                line = trial + " "
                continue
            if line.strip():
                lines.append(line.rstrip())
                line = hanging_prefix + word + " "
            else:
                # Hard-break very long tokens.
                chunk = word
                while chunk:
                    take = max(1, int(max_width / max(size * 0.52, 1)))
                    lines.append((hanging_prefix + chunk[:take]).rstrip())
                    chunk = chunk[take:]
                line = hanging_prefix
        if line.strip():
            lines.append(line.rstrip())

        for idx, ln in enumerate(lines):
            self.text(x, y - size, ln, font=font, size=size, color=color)
            y -= leading
        return y

    def paragraph_blocks(
        self,
        x: float,
        y_top: float,
        lines: Sequence[str],
        *,
        max_width: float,
        leading: float = 12,
        font: str = "F1",
        size: float = 10,
        color=(0, 0, 0),
    ) -> float:
        y = y_top
        for line in lines:
            if not line:
                y -= leading * 0.5
                continue
            y = self.wrapped_text(
                x,
                y,
                line,
                max_width=max_width,
                leading=leading,
                font=font,
                size=size,
                color=color,
                bullet=line.startswith("- "),
            )
        return y

    def image(self, name: str, x: float, y: float, w: float, h: float) -> None:
        self.used_images.add(name)
        self.raw(
            f"q {fmt_num(w)} 0 0 {fmt_num(h)} {fmt_num(x)} {fmt_num(y)} cm /{name} Do Q"
        )

    def to_bytes(self) -> bytes:
        return ("\n".join(self._ops) + "\n").encode("latin-1")


def hex_color(hex_str: str) -> Tuple[float, float, float]:
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


def page_chrome(
    c: Canvas,
    title: str,
    page_num: int,
    patient_name: str,
    mrn: str,
    show_center_watermark: bool = DEFAULT_SHOW_CENTER_WATERMARK,
) -> None:
    c.set_fill(0.95, 0.95, 0.95)
    c.rect(MARGIN, PAGE_H - 70, PAGE_W - 2 * MARGIN, 52, fill=True, stroke=False)
    c.set_stroke(0.1, 0.1, 0.1)
    c.set_line_width(1)
    c.rect(MARGIN, PAGE_H - 70, PAGE_W - 2 * MARGIN, 52, fill=False, stroke=True)
    c.text(MARGIN + 8, PAGE_H - 35, "COMMUNITY GENERAL HOSPITAL", font="F2", size=11, color=(0.08, 0.08, 0.08))
    c.text(PAGE_W - 110, PAGE_H - 35, f"PAGE {page_num}", font="F2", size=9, color=(0.08, 0.08, 0.08))
    title_text = title.upper()
    max_title_w = PAGE_W - 2 * MARGIN - 180
    while c.text_width(title_text, 11, font="F2") > max_title_w and len(title_text) > 6:
        title_text = title_text[:-4] + "..."
    c.text(MARGIN + 8, PAGE_H - 52, title_text, font="F2", size=11, color=(0.08, 0.08, 0.08))
    patient_line = f"{patient_name} | MRN {mrn}"
    px = PAGE_W - MARGIN - 8 - c.text_width(patient_line, 8.5, font="F1")
    c.text(px, PAGE_H - 64, patient_line, font="F1", size=8.5, color=(0.08, 0.08, 0.08))

    c.set_stroke(0.2, 0.2, 0.2)
    c.line(MARGIN, PAGE_H - 76, PAGE_W - MARGIN, PAGE_H - 76)

    c.set_fill(0.96, 0.96, 0.96)
    c.rect(0, 0, PAGE_W, 24, fill=True, stroke=False)
    c.set_stroke(0.2, 0.2, 0.2)
    c.line(0, 24, PAGE_W, 24)
    c.text(MARGIN, 8, "Synthetic record for testing/demo only. Not for clinical care or legal use.", font="F2", size=7.7, color=(0.05, 0.05, 0.05))

    if show_center_watermark:
        c.text(165, 390, "SYNTHETIC DEMO RECORD", font="F2", size=28, color=(0.88, 0.90, 0.93))


def stable_seed(text: str) -> int:
    seed = 0
    for i, ch in enumerate(text):
        seed = (seed * 131 + (i + 1) * ord(ch)) & 0xFFFFFFFF
    return seed or 1


def fit_text_to_width(
    c: Canvas,
    text: str,
    max_width: float,
    *,
    size: float,
    font: str = "F1",
    ellipsis: str = "...",
) -> str:
    if max_width <= 0:
        return ""
    if c.text_width(text, size, font=font) <= max_width:
        return text
    suffix = ellipsis if c.text_width(ellipsis, size, font=font) <= max_width else ""
    lo = 0
    hi = len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        trial = text[:mid].rstrip() + suffix
        if c.text_width(trial, size, font=font) <= max_width:
            lo = mid
        else:
            hi = mid - 1
    if lo <= 0:
        return suffix
    return text[:lo].rstrip() + suffix


def draw_signature_block(
    c: Canvas,
    x: float,
    y: float,
    w: float,
    provider: str,
    role: str,
    signed_at: str,
) -> None:
    c.set_stroke(0.2, 0.2, 0.2)
    c.set_line_width(0.8)
    c.line(x, y, x + w, y)
    c.text(x, y - 10, provider, font="F2", size=8.2, color=(0.08, 0.08, 0.08))
    c.text(x, y - 21, f"{role} | Signed: {signed_at}", font="F1", size=7.3, color=(0.15, 0.15, 0.15))
    c.text(x + w - 40, y - 21, "eSigned", font="F2", size=7.3, color=(0.15, 0.15, 0.15))

    rng = random.Random(stable_seed(f"{provider}|{signed_at}"))
    sig_x0 = x + 8
    sig_x1 = min(x + w - 48, x + 120)
    sig_base = y + 6
    pts = []
    for i in range(24):
        t = i / 23
        px = sig_x0 + (sig_x1 - sig_x0) * t
        py = sig_base + math.sin(5.8 * t + rng.random() * 0.25) * (3.0 + rng.random() * 1.4) + rng.uniform(-0.8, 0.8)
        pts.append((px, py))
    c.set_stroke(0.07, 0.09, 0.14)
    c.set_line_width(1.0)
    c.polyline(pts, close=False, fill=False, stroke=True)


def draw_section_header(c: Canvas, x: float, y: float, w: float, label: str) -> float:
    c.set_fill(0.93, 0.93, 0.93)
    c.rect(x, y - 18, w, 20, fill=True, stroke=False)
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(x, y - 18, w, 20, fill=False, stroke=True)
    hdr = fit_text_to_width(c, label.upper(), w - 16, size=9.5, font="F2")
    c.text(x + 8, y - 13, hdr, font="F2", size=9.5, color=(0.07, 0.07, 0.07))
    return y - 24


def draw_kv_grid(
    c: Canvas,
    x: float,
    y_top: float,
    w: float,
    pairs: Sequence[Tuple[str, str]],
    cols: int = 2,
    label_w: Optional[float] = None,
) -> float:
    row_h = 20
    col_w = w / cols
    rows = math.ceil(len(pairs) / cols)
    h = rows * row_h
    c.set_stroke(0.2, 0.2, 0.2)
    c.set_line_width(0.8)
    c.rect(x, y_top - h, w, h, fill=False, stroke=True)
    for r in range(1, rows):
        y = y_top - r * row_h
        c.line(x, y, x + w, y)
    for col in range(1, cols):
        c.line(x + col * col_w, y_top, x + col * col_w, y_top - h)

    key_width = label_w if label_w is not None else (72.0 if cols > 1 else 110.0)

    for i, (k, v) in enumerate(pairs):
        r = i // cols
        col = i % cols
        cell_x = x + col * col_w
        cell_y = y_top - r * row_h
        key_max = max(12.0, key_width - 8.0)
        val_max = max(12.0, col_w - key_width - 14.0)
        key_disp = fit_text_to_width(c, f"{k}:", key_max, size=8, font="F2")
        val_disp = fit_text_to_width(c, str(v), val_max, size=8, font="F1")
        c.text(cell_x + 6, cell_y - 13, key_disp, font="F2", size=8, color=(0.08, 0.08, 0.08))
        c.text(cell_x + 6 + key_width, cell_y - 13, val_disp, font="F1", size=8, color=(0.08, 0.08, 0.08))
    return y_top - h - 8


def draw_table(
    c: Canvas,
    x: float,
    y_top: float,
    widths: Sequence[float],
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    row_h: float = 18,
    header_h: float = 20,
    font_size: float = 8.5,
) -> float:
    total_w = sum(widths)
    table_h = header_h + row_h * len(rows)
    c.set_stroke(0.2, 0.2, 0.2)
    c.set_line_width(0.7)
    c.set_fill(0.93, 0.93, 0.93)
    c.rect(x, y_top - header_h, total_w, header_h, fill=True, stroke=True)
    c.rect(x, y_top - table_h, total_w, table_h, fill=False, stroke=True)

    cx = x
    for i, w in enumerate(widths[:-1]):
        cx += w
        c.line(cx, y_top, cx, y_top - table_h)
    for r in range(len(rows) + 1):
        y = y_top - header_h - r * row_h
        c.line(x, y, x + total_w, y)

    cx = x
    for h, w in zip(headers, widths):
        head = fit_text_to_width(c, str(h), w - 6, size=8, font="F2")
        c.text(cx + 4, y_top - 13, head, font="F2", size=8, color=(0.06, 0.06, 0.06))
        cx += w

    for ridx, row in enumerate(rows):
        base_y = y_top - header_h - ridx * row_h
        cx = x
        for cell, w in zip(row, widths):
            display = fit_text_to_width(c, str(cell), w - 6, size=font_size, font="F1")
            c.text(cx + 3, base_y - 12, display, font="F1", size=font_size, color=(0.06, 0.06, 0.06))
            cx += w
    return y_top - table_h - 10


def sparkline(c: Canvas, x: float, y: float, w: float, h: float, values: Sequence[float], stroke=(0.12, 0.12, 0.12)) -> None:
    if len(values) < 2:
        return
    vmin = min(values)
    vmax = max(values)
    span = max(vmax - vmin, 1e-6)
    pts = []
    for i, v in enumerate(values):
        px = x + (w * i / (len(values) - 1))
        py = y + ((v - vmin) / span) * h
        pts.append((px, py))
    c.set_stroke(0.45, 0.45, 0.45)
    c.set_line_width(0.5)
    c.rect(x, y, w, h, fill=False, stroke=True)
    c.set_stroke(*stroke)
    c.set_line_width(1.2)
    c.polyline(pts, close=False, fill=False, stroke=True)
    for px, py in pts:
        c.set_fill(*stroke)
        c.circle(px, py, 1.7, fill=True, stroke=False)


def draw_line_chart(
    c: Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    series: Sequence[Tuple[str, Sequence[float], Tuple[float, float, float]]],
    labels: Sequence[str],
    y_min: float,
    y_max: float,
    y_ticks: Sequence[float],
    title: str,
) -> None:
    c.set_fill(0.97, 0.97, 0.97)
    c.rect(x, y, w, h, fill=True, stroke=False)
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(x, y, w, h, fill=False, stroke=True)
    c.text(x + 10, y + h - 18, title, font="F2", size=9.5, color=(0.07, 0.07, 0.07))

    plot_x = x + 38
    plot_y = y + 26
    plot_w = w - 54
    plot_h = h - 44

    c.set_stroke(0.35, 0.35, 0.35)
    c.set_line_width(0.7)
    c.rect(plot_x, plot_y, plot_w, plot_h, fill=False, stroke=True)

    for tick in y_ticks:
        ty = plot_y + (tick - y_min) / (y_max - y_min) * plot_h
        c.set_stroke(0.75, 0.75, 0.75)
        c.line(plot_x, ty, plot_x + plot_w, ty)
        c.text(x + 4, ty - 3, fmt_num(tick), font="F1", size=7, color=(0.18, 0.18, 0.18))

    if labels:
        for i, label in enumerate(labels):
            px = plot_x + (plot_w * i / (len(labels) - 1 if len(labels) > 1 else 1))
            c.set_stroke(0.82, 0.82, 0.82)
            c.line(px, plot_y, px, plot_y + plot_h)
            c.text(px - 8, y + 10, label, font="F1", size=7, color=(0.18, 0.18, 0.18))

    for series_name, values, color in series:
        pts = []
        for i, v in enumerate(values):
            px = plot_x + (plot_w * i / (len(values) - 1 if len(values) > 1 else 1))
            py = plot_y + (v - y_min) / (y_max - y_min) * plot_h
            pts.append((px, py))
        c.set_stroke(*color)
        c.set_line_width(1.4)
        c.polyline(pts, close=False, fill=False, stroke=True)
        for px, py in pts:
            c.set_fill(*color)
            c.circle(px, py, 2.0, fill=True, stroke=False)

    legend_y = y + h - 18
    legend_x = x + w - 90
    for idx, (series_name, _, color) in enumerate(series):
        lx = legend_x
        ly = legend_y - idx * 11
        c.set_stroke(*color)
        c.set_line_width(1.5)
        c.line(lx, ly, lx + 12, ly)
        c.text(lx + 16, ly - 3, series_name, font="F1", size=7.5, color=(0.08, 0.08, 0.08))


def draw_timeline(c: Canvas, x: float, y: float, w: float, events: Sequence[Dict[str, str]]) -> None:
    c.set_fill(0.97, 0.97, 0.97)
    c.rect(x, y, w, 120, fill=True, stroke=False)
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(x, y, w, 120, fill=False, stroke=True)
    c.text(x + 10, y + 102, "CARE TIMELINE (LAST 12 MONTHS)", font="F2", size=9.5, color=(0.07, 0.07, 0.07))
    line_y = y + 56
    c.set_stroke(0.2, 0.2, 0.2)
    c.set_line_width(2)
    c.line(x + 24, line_y, x + w - 24, line_y)
    n = len(events)
    colors = [(0.1, 0.1, 0.1), (0.25, 0.25, 0.25), (0.4, 0.4, 0.4), (0.18, 0.18, 0.18), (0.32, 0.32, 0.32)]
    for i, ev in enumerate(events):
        px = x + 24 + (w - 48) * i / (n - 1 if n > 1 else 1)
        color = colors[i % len(colors)]
        c.set_fill(*color)
        c.circle(px, line_y, 5, fill=True, stroke=False)
        c.set_stroke(*color)
        c.set_line_width(1)
        c.line(px, line_y + 5, px, line_y + 28)
        c.line(px, line_y - 5, px, line_y - 24)
        c.text(px - 24, line_y + 31, ev["date"], font="F2", size=7, color=(0.08, 0.08, 0.08))
        c.text(px - 28, line_y + 19, ev["site"], font="F1", size=6.8, color=(0.18, 0.18, 0.18))
        c.text(px - 34, line_y - 17, ev["reason"], font="F1", size=6.8, color=(0.18, 0.18, 0.18))


def draw_ecg_strip(c: Canvas, x: float, y: float, w: float, h: float) -> None:
    c.set_fill(1.0, 0.995, 0.995)
    c.rounded_rect(x, y, w, h, 6, fill=True, stroke=False)
    c.text(x + 10, y + h - 18, "12-Lead ECG (rhythm strip excerpt, synthetic)", font="F2", size=10, color=(0.4, 0.1, 0.1))

    plot_x = x + 8
    plot_y = y + 10
    plot_w = w - 16
    plot_h = h - 28

    # ECG grid
    for step in range(0, int(plot_w) + 1, 10):
        xx = plot_x + step
        c.set_stroke(1.0, 0.83, 0.83) if step % 50 else c.set_stroke(0.98, 0.68, 0.68)
        c.set_line_width(0.4 if step % 50 else 0.8)
        c.line(xx, plot_y, xx, plot_y + plot_h)
    for step in range(0, int(plot_h) + 1, 10):
        yy = plot_y + step
        c.set_stroke(1.0, 0.83, 0.83) if step % 50 else c.set_stroke(0.98, 0.68, 0.68)
        c.set_line_width(0.4 if step % 50 else 0.8)
        c.line(plot_x, yy, plot_x + plot_w, yy)

    baseline = plot_y + plot_h * 0.46
    pts = []
    total_samples = 500
    for i in range(total_samples):
        t = i / (total_samples - 1)
        xx = plot_x + t * plot_w
        phase = (t * 8.0) % 1.0
        yy = baseline
        # PQRST approximation
        yy += 2 * math.exp(-((phase - 0.18) ** 2) / 0.0018)
        yy += -4 * math.exp(-((phase - 0.36) ** 2) / 0.0004)
        yy += 22 * math.exp(-((phase - 0.40) ** 2) / 0.00009)
        yy += -7 * math.exp(-((phase - 0.43) ** 2) / 0.0002)
        yy += 6 * math.exp(-((phase - 0.66) ** 2) / 0.006)
        yy += math.sin(t * 2 * math.pi * 1.5) * 0.8
        pts.append((xx, yy))
    c.set_stroke(0.55, 0.0, 0.0)
    c.set_line_width(1.1)
    c.polyline(pts, close=False, fill=False, stroke=True)


def draw_body_outline(c: Canvas, x: float, y: float, w: float, h: float) -> None:
    c.set_fill(0.985, 0.995, 1.0)
    c.rounded_rect(x, y, w, h, 6, fill=True, stroke=False)
    c.text(x + 10, y + h - 18, "Body Diagram (symptom map example)", font="F2", size=10, color=(0.1, 0.2, 0.35))

    cx = x + w * 0.5
    base_y = y + 14
    top_y = y + h - 28
    c.set_stroke(0.55, 0.63, 0.73)
    c.set_line_width(1.1)
    # head
    c.circle(cx, top_y - 22, 14, fill=False, stroke=True)
    # torso
    torso_top = top_y - 38
    torso_bottom = base_y + 62
    c.line(cx, torso_top, cx, torso_bottom)
    c.line(cx - 26, torso_top - 12, cx + 26, torso_top - 12)
    c.line(cx - 26, torso_top - 12, cx - 44, torso_top - 52)
    c.line(cx + 26, torso_top - 12, cx + 44, torso_top - 52)
    c.line(cx, torso_bottom, cx - 22, base_y + 10)
    c.line(cx, torso_bottom, cx + 22, base_y + 10)

    # highlight symptom areas
    c.set_fill(1.0, 0.84, 0.84)
    c.circle(cx + 10, torso_top - 8, 9, fill=True, stroke=False)  # chest pressure
    c.set_fill(1.0, 0.9, 0.75)
    c.circle(cx + 34, torso_top - 34, 7, fill=True, stroke=False)  # right shoulder radiation
    c.set_fill(0.85, 0.93, 1.0)
    c.circle(cx + 10, base_y + 48, 6, fill=True, stroke=False)  # epigastric discomfort
    c.text(x + 10, y + 10, "Markers used for documentation demos; not diagnostic.", font="F1", size=7, color=(0.3, 0.35, 0.4))


def generate_chest_xray(width: int, height: int) -> bytes:
    cx = width / 2
    cy = height * 0.47
    data = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            idx = y * width + x
            # Base vignette/gradient
            dx = (x - cx) / (width * 0.52)
            dy = (y - cy) / (height * 0.52)
            r2 = dx * dx + dy * dy
            val = 40 + 90 * math.exp(-r2 * 2.0)

            # Lungs (darker on x-ray)
            lx = ((x - width * 0.34) / (width * 0.17)) ** 2 + ((y - height * 0.5) / (height * 0.27)) ** 2
            rx = ((x - width * 0.66) / (width * 0.17)) ** 2 + ((y - height * 0.5) / (height * 0.27)) ** 2
            if lx < 1.0:
                val -= 35 * (1 - lx)
            if rx < 1.0:
                val -= 35 * (1 - rx)

            # Mediastinum / heart shadow
            heart = ((x - width * 0.55) / (width * 0.19)) ** 2 + ((y - height * 0.63) / (height * 0.16)) ** 2
            if heart < 1.0:
                val += 45 * (1 - heart)

            # Spine column
            spine = abs(x - cx) / (width * 0.03)
            if spine < 1.0:
                val += 35 * (1 - spine) * math.exp(-((y - height * 0.5) / (height * 0.35)) ** 2)

            # Clavicles
            for sign in (-1, 1):
                clav = ((x - (cx + sign * width * 0.14)) / (width * 0.12)) ** 2 + ((y - height * 0.29) / (height * 0.035)) ** 2
                if clav < 1.0:
                    val += 25 * (1 - clav)

            # Ribs as sinusoidal arcs (bright)
            for rib in range(6):
                rib_y = height * (0.34 + rib * 0.08)
                rib_curve = rib_y + 8 * math.sin((x / width) * math.pi * 2 + rib * 0.5)
                dist = abs(y - rib_curve)
                if dist < 1.7 and (width * 0.14 < x < width * 0.86):
                    val += 18 * (1.7 - dist)

            # Diaphragm
            dia = abs(y - (height * 0.76 + 12 * math.sin((x / width) * math.pi * 1.4)))
            if dia < 2.4:
                val += 16 * (2.4 - dia)

            # Grain/noise (deterministic)
            n = ((x * 73856093) ^ (y * 19349663)) & 0xFF
            val += (n / 255.0 - 0.5) * 10.0

            val = max(0, min(255, int(val)))
            data[idx] = val
    return bytes(data)


def generate_ultrasound(width: int, height: int, seed: int = 7) -> bytes:
    rng = random.Random(seed)
    data = bytearray(width * height)
    cx = width * 0.52
    cy = height * 0.48
    for y in range(height):
        for x in range(width):
            idx = y * width + x
            # Sector-like scan fade
            dx = (x - cx) / width
            dy = (y - cy) / height
            radius = math.sqrt(dx * dx + (dy * 1.3) ** 2)
            val = 20 + 180 * max(0, 1 - radius * 1.8)
            # Speckle noise
            val += rng.gauss(0, 22)
            # Tissue bands
            val += 18 * math.sin(y / 7.0) * math.exp(-((x - width * 0.5) / (width * 0.45)) ** 2)
            # Anechoic cyst-like circle
            cyst = ((x - width * 0.62) / (width * 0.12)) ** 2 + ((y - height * 0.56) / (height * 0.14)) ** 2
            if cyst < 1.0:
                val -= 70 * (1 - cyst * 0.7)
                if 0.82 < cyst < 1.05:
                    val += 28  # bright rim
            # Depth shadow
            if x > width * 0.65 and abs(x - width * 0.72) < width * 0.07 and y > height * 0.58:
                val -= 30 * (1 - min(1, (y - height * 0.58) / (height * 0.4)))

            val = max(0, min(255, int(val)))
            data[idx] = val
    return bytes(data)


def make_case_data() -> Dict[str, object]:
    return {
        "record_meta": {
            "generated_on": "2026-02-26",
            "disclaimer": "All information in this chart is synthetic and generated for testing/demo use.",
            "record_id": "SYN-CHART-0001",
        },
        "patient": {
            "name": "Jordan M. Alvarez",
            "dob": "1981-07-18",
            "age": "44",
            "sex_at_birth": "Female",
            "gender_identity": "Female",
            "mrn": "10458271",
            "account": "A-778231",
            "address": "2471 Meadow Ridge Ln, Franklin, TN 37067",
            "phone": "(615) 555-0148",
            "email": "jordan.alvarez@example.test",
            "language": "English",
            "marital_status": "Married",
            "occupation": "Project manager",
            "insurance": "BlueCross PPO (synthetic policy)",
            "pcp": "Nina Patel, MD",
            "emergency_contact": "Luis Alvarez (spouse) (615) 555-0191",
            "height": "165 cm (5 ft 5 in)",
            "weight": "82.3 kg (181 lb)",
            "bmi": "30.2 kg/m^2",
            "blood_type": "O+",
        },
        "allergies": [
            {"substance": "Penicillin", "reaction": "Pruritic rash", "severity": "Moderate"},
            {"substance": "Lisinopril", "reaction": "Persistent cough", "severity": "Mild"},
        ],
        "problems": [
            {"problem": "Type 2 diabetes mellitus", "status": "Active", "since": "2019", "icd10": "E11.9"},
            {"problem": "Essential hypertension", "status": "Active", "since": "2018", "icd10": "I10"},
            {"problem": "Hyperlipidemia", "status": "Active", "since": "2020", "icd10": "E78.5"},
            {"problem": "GERD", "status": "Intermittent", "since": "2021", "icd10": "K21.9"},
            {"problem": "Mild intermittent asthma", "status": "Active", "since": "Childhood", "icd10": "J45.20"},
        ],
        "medications": [
            {
                "name": "Metformin ER 1000 mg",
                "sig": "Take 1 tablet by mouth twice daily with meals",
                "status": "Active",
                "start": "2024-11-04",
                "prescriber": "N. Patel, MD",
            },
            {
                "name": "Losartan 50 mg",
                "sig": "Take 1 tablet by mouth daily",
                "status": "Active",
                "start": "2025-03-14",
                "prescriber": "N. Patel, MD",
            },
            {
                "name": "Rosuvastatin 10 mg",
                "sig": "Take 1 tablet by mouth nightly",
                "status": "Active",
                "start": "2024-08-20",
                "prescriber": "N. Patel, MD",
            },
            {
                "name": "Omeprazole 20 mg",
                "sig": "Take 1 capsule by mouth daily before breakfast as needed",
                "status": "PRN",
                "start": "2025-01-10",
                "prescriber": "N. Patel, MD",
            },
            {
                "name": "Albuterol HFA 90 mcg",
                "sig": "2 puffs inhaled every 4-6 hours as needed for wheeze",
                "status": "PRN",
                "start": "2023-06-02",
                "prescriber": "M. Chen, DO",
            },
        ],
        "immunizations": [
            {"vaccine": "Influenza (quadrivalent)", "date": "2025-10-02", "site": "Left deltoid"},
            {"vaccine": "COVID-19 booster (mRNA)", "date": "2025-10-02", "site": "Right deltoid"},
            {"vaccine": "Tdap", "date": "2024-06-18", "site": "Left deltoid"},
            {"vaccine": "Pneumococcal PCV20", "date": "2025-03-14", "site": "Left deltoid"},
        ],
        "encounters": [
            {
                "date": "2025-03-14",
                "type": "Primary Care - Annual Physical",
                "provider": "Nina Patel, MD",
                "location": "Franklin Family Medicine",
                "vitals": "BP 142/88, HR 78, Temp 98.4 F, RR 14, SpO2 98%, Wt 184 lb",
                "reason": "Annual preventive visit and chronic disease follow-up.",
                "assessment": [
                    "Type 2 diabetes: A1c above goal at 7.8%. Discussed diet consistency and exercise plan.",
                    "Hypertension: BP persistently above goal; changed from lisinopril (cough) to losartan.",
                    "Hyperlipidemia: Continue statin; repeat fasting lipids in 6 months.",
                ],
                "plan": [
                    "Increase metformin ER to 1000 mg twice daily.",
                    "Start losartan 50 mg daily.",
                    "Order CMP, A1c, urine microalbumin, fasting lipid panel.",
                    "Vaccinate with PCV20 due to diabetes risk profile.",
                ],
                "signed_at": "2025-03-14 17:42",
            },
            {
                "date": "2025-11-20",
                "type": "Urgent Care Visit",
                "provider": "Maya Chen, DO",
                "location": "Cool Springs Urgent Care",
                "vitals": "BP 136/84, HR 96, Temp 99.1 F, RR 18, SpO2 96%",
                "reason": "3-day cough, wheezing, sinus congestion after viral illness exposure.",
                "assessment": [
                    "Likely viral bronchitis with asthma exacerbation (mild).",
                    "No focal consolidation on exam; no severe respiratory distress.",
                ],
                "plan": [
                    "Albuterol refill; spacer technique reviewed.",
                    "Prednisone 40 mg daily x5 days.",
                    "Supportive care and return precautions discussed.",
                ],
                "signed_at": "2025-11-20 19:06",
            },
            {
                "date": "2026-01-09",
                "type": "Emergency Department Visit",
                "provider": "Aaron Feldman, MD",
                "location": "Williamson Medical Center ED",
                "vitals": "BP 154/92, HR 104, Temp 98.2 F, RR 20, SpO2 99%",
                "reason": "Intermittent substernal chest pressure x6 hours with mild nausea; improved on arrival.",
                "assessment": [
                    "Low-risk chest pain; serial troponins negative.",
                    "ECG: sinus tachycardia, no ST-elevation; nonspecific T-wave changes.",
                    "CXR: no acute cardiopulmonary abnormality.",
                    "Symptoms possibly reflux-related; advised close PCP follow-up.",
                ],
                "plan": [
                    "Observation and repeat troponin x2 (negative).",
                    "Trial GI cocktail with symptom improvement.",
                    "Discharge with return precautions and PCP/cardiology follow-up if recurrence.",
                ],
                "signed_at": "2026-01-09 23:11",
            },
            {
                "date": "2026-01-16",
                "type": "Primary Care Follow-up",
                "provider": "Nina Patel, MD",
                "location": "Franklin Family Medicine",
                "vitals": "BP 132/82, HR 76, Temp 98.6 F, RR 14, SpO2 98%, Wt 182 lb",
                "reason": "Post-ED follow-up for chest pain and chronic disease review.",
                "assessment": [
                    "No recurrent chest pain since ED discharge; likely GERD contributor.",
                    "BP improved with losartan; home readings averaging 128-134/78-84.",
                    "A1c trending down; patient increased walking to 4 days/week.",
                ],
                "plan": [
                    "Continue current meds; use omeprazole daily for 4 weeks then PRN.",
                    "Refer for outpatient exercise stress test due to risk factors and ED visit.",
                    "Repeat A1c/CMP in 3 months.",
                ],
                "signed_at": "2026-01-16 16:28",
            },
            {
                "date": "2026-02-20",
                "type": "Endocrinology Consult",
                "provider": "Leah Morgan, MD",
                "location": "Middle TN Endocrinology",
                "vitals": "BP 128/80, HR 74, Temp 98.1 F, RR 14, SpO2 99%, Wt 181 lb",
                "reason": "Diabetes management optimization.",
                "assessment": [
                    "A1c improved to 7.1%; still above individualized target <7.0%.",
                    "No nephropathy or retinopathy documented; annual eye exam due next month.",
                    "Discussed GLP-1 RA option for glycemic and weight benefit.",
                ],
                "plan": [
                    "Continue metformin ER 1000 mg BID.",
                    "Start semaglutide 0.25 mg weekly x4 weeks, then 0.5 mg weekly if tolerated.",
                    "Monitor fasting glucose 3-4 times/week and maintain food/activity log.",
                ],
                "signed_at": "2026-02-20 15:39",
            },
        ],
        "labs": [
            {"date": "2025-03-14", "a1c": 7.8, "glucose": 168, "creatinine": 0.82, "egfr": 91, "ldl": 118, "microalb": 13},
            {"date": "2025-06-20", "a1c": 7.5, "glucose": 154, "creatinine": 0.80, "egfr": 94, "ldl": 101, "microalb": 11},
            {"date": "2025-10-02", "a1c": 7.3, "glucose": 149, "creatinine": 0.79, "egfr": 96, "ldl": 88, "microalb": 10},
            {"date": "2026-01-16", "a1c": 7.2, "glucose": 143, "creatinine": 0.84, "egfr": 89, "ldl": 84, "microalb": 12},
            {"date": "2026-02-20", "a1c": 7.1, "glucose": 138, "creatinine": 0.81, "egfr": 92, "ldl": 80, "microalb": 9},
        ],
        "diagnostics": {
            "ecg": {
                "date": "2026-01-09",
                "summary": "Sinus tachycardia (rate 103 bpm), normal axis, QTc 437 ms, nonspecific T-wave flattening in lateral leads; no STEMI criteria.",
                "reported_by": "Aaron Feldman, MD",
            },
            "cxr": {
                "date": "2026-01-09",
                "summary": "Single-view chest radiograph: cardiac silhouette within normal size limits, no focal airspace opacity, pleural effusion, or pneumothorax. No acute osseous abnormality on this exam.",
                "reported_by": "Priya Raman, MD",
            },
            "stress_test": {
                "date": "2026-02-05",
                "summary": "Exercise treadmill test completed 9:21 Bruce protocol; no ischemic ST changes, no arrhythmia, appropriate BP response. Low-risk study.",
                "reported_by": "Thomas Reeves, MD",
            },
            "ultrasound": {
                "date": "2025-08-12",
                "summary": "RUQ ultrasound for episodic abdominal discomfort: mild hepatic steatosis, no cholelithiasis, no biliary dilation.",
                "reported_by": "Priya Raman, MD",
            },
        },
        "surgical_report": {
            "procedure_date": "2025-07-22",
            "facility": "Williamson Medical Center - Outpatient Surgery",
            "surgeon": "Caleb Monroe, MD",
            "assistant": "K. Wright, PA-C",
            "anesthesia": "General endotracheal",
            "preop_diagnosis": "Symptomatic cholelithiasis",
            "postop_diagnosis": "Symptomatic cholelithiasis without acute cholecystitis",
            "procedure": "Laparoscopic cholecystectomy",
            "findings": [
                "Chronically inflamed gallbladder with multiple cholesterol stones.",
                "Critical view of safety obtained prior to clipping cystic duct/artery.",
                "No bile leak noted after irrigation and hemostasis check.",
            ],
            "specimen_sent": "Gallbladder submitted to pathology in formalin.",
            "estimated_blood_loss_ml": "25",
            "complications": "None apparent.",
            "disposition": "Transferred to PACU in stable condition.",
            "signed_at": "2025-07-22 16:04",
        },
        "pathology_report": {
            "accession": "SP-25-071982",
            "collection_date": "2025-07-22",
            "pathologist": "Elena Russo, MD",
            "specimen": "Gallbladder, cholecystectomy",
            "gross_description": "7.8 x 3.1 x 2.9 cm gallbladder with green-brown bile and multiple yellow stones up to 0.8 cm.",
            "microscopic_description": "Mucosal flattening with chronic inflammatory infiltrate and focal Rokitansky-Aschoff sinus formation.",
            "final_diagnosis": [
                "Chronic cholecystitis with cholelithiasis.",
                "No dysplasia or malignancy identified.",
            ],
            "signed_at": "2025-07-23 09:27",
        },
        "discharge_summary": {
            "facility": "Williamson Medical Center",
            "admission_date": "2026-01-09",
            "discharge_date": "2026-01-10",
            "attending": "Aaron Feldman, MD",
            "admission_diagnosis": "Chest pain, rule out acute coronary syndrome",
            "discharge_diagnosis": "Low-risk chest pain, likely reflux-related; hypertension; type 2 diabetes mellitus",
            "hospital_course": [
                "Presented with intermittent substernal pressure with mild nausea.",
                "Serial high-sensitivity troponins remained negative and ECG showed no acute ischemic changes.",
                "Symptoms improved with GI cocktail and observation; remained hemodynamically stable overnight.",
            ],
            "discharge_medications": [
                "Metformin ER 1000 mg PO twice daily.",
                "Losartan 50 mg PO daily.",
                "Rosuvastatin 10 mg PO nightly.",
                "Omeprazole 20 mg PO daily for 4 weeks then PRN.",
            ],
            "follow_up": [
                "Primary care follow-up in 1 week.",
                "Cardiology follow-up within 2-4 weeks if recurrent symptoms.",
                "Return to ED immediately for persistent chest pain, dyspnea, syncope, or new neurologic symptoms.",
            ],
            "signed_at": "2026-01-10 09:14",
        },
        "consult_note": {
            "service": "Cardiology Consult",
            "date": "2026-02-05",
            "consultant": "Thomas Reeves, MD",
            "requesting_provider": "Nina Patel, MD",
            "reason": "Evaluation after ED chest pain episode and multiple cardiovascular risk factors.",
            "history": "No recurrent exertional chest pain. Walks 30 minutes 4 times weekly. Denies syncope, orthopnea, edema, or palpitations.",
            "assessment": [
                "Atypical chest pain with reassuring ED and outpatient treadmill workup.",
                "ASCVD risk elevated due to diabetes, hypertension, and dyslipidemia.",
                "Blood pressure and lipid control improved on current regimen.",
            ],
            "recommendations": [
                "Continue losartan and rosuvastatin without change.",
                "Maintain structured exercise and Mediterranean-style diet.",
                "No additional ischemic testing unless symptom pattern changes.",
                "Follow up in cardiology clinic in 6 months.",
            ],
            "signed_at": "2026-02-05 12:03",
        },
        "anesthesia_report": {
            "case_date": "2025-07-22",
            "anesthesiologist": "Mira Khanna, MD",
            "crna": "Jordan Lee, CRNA",
            "procedure": "Laparoscopic cholecystectomy",
            "asa_class": "ASA III",
            "airway": "Mallampati II, Grade I view with MAC 3 blade",
            "anesthetic_type": "General endotracheal anesthesia",
            "induction": "Propofol, fentanyl, rocuronium",
            "maintenance": "Sevoflurane with balanced opioid-sparing analgesia",
            "events": [
                "Intubation successful on first attempt with 7.0 cuffed ETT.",
                "Hemodynamics stable throughout case; no vasopressor requirement.",
                "Multimodal antiemetic prophylaxis administered.",
                "Extubated awake in OR and transferred to PACU on supplemental oxygen.",
            ],
            "post_anesthesia": "Pain controlled, no post-op nausea/vomiting, Aldrete 9 on arrival to PACU.",
            "signed_at": "2025-07-22 16:22",
        },
        "report_signatures": {
            "radiology_signed_at": "2026-01-09 15:11",
            "cardiology_signed_at": "2026-02-05 12:03",
            "pathology_signed_at": "2025-07-23 09:27",
            "surgery_signed_at": "2025-07-22 16:04",
        },
        "document_settings": {
            "include_synthetic_imaging_default": DEFAULT_INCLUDE_SYNTHETIC_IMAGING,
            "show_center_watermark_default": DEFAULT_SHOW_CENTER_WATERMARK,
        },
    }


def render_cover_and_demographics(doc: PDFDocument, case: Dict[str, object], page_num: int) -> int:
    p = case["patient"]  # type: ignore[index]
    c = Canvas()
    page_chrome(c, "Chart Overview & Demographics", page_num, p["name"], p["mrn"])  # type: ignore[index]

    c.set_fill(0.97, 0.97, 0.97)
    c.rect(MARGIN, PAGE_H - 150, PAGE_W - 2 * MARGIN, 66, fill=True, stroke=False)
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, PAGE_H - 150, PAGE_W - 2 * MARGIN, 66, fill=False, stroke=True)
    c.text(MARGIN + 12, PAGE_H - 110, p["name"], font="F2", size=18, color=(0.07, 0.07, 0.07))  # type: ignore[index]
    c.text(MARGIN + 12, PAGE_H - 130, "Synthetic patient profile for testing / demonstrations", font="F3", size=9.2, color=(0.1, 0.1, 0.1))
    c.text(PAGE_W - 220, PAGE_H - 110, f"Record ID: {case['record_meta']['record_id']}", font="F2", size=9.2, color=(0.07, 0.07, 0.07))  # type: ignore[index]
    c.text(PAGE_W - 220, PAGE_H - 126, f"Generated: {case['record_meta']['generated_on']}", font="F1", size=8.5, color=(0.1, 0.1, 0.1))  # type: ignore[index]

    y = PAGE_H - 170
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Patient Identifiers")
    y = draw_kv_grid(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        [
            ("DOB", p["dob"]),  # type: ignore[index]
            ("Age", p["age"]),  # type: ignore[index]
            ("MRN", p["mrn"]),  # type: ignore[index]
            ("Account", p["account"]),  # type: ignore[index]
            ("Sex at Birth", p["sex_at_birth"]),  # type: ignore[index]
            ("Gender", p["gender_identity"]),  # type: ignore[index]
            ("Height", p["height"]),  # type: ignore[index]
            ("Weight", p["weight"]),  # type: ignore[index]
            ("BMI", p["bmi"]),  # type: ignore[index]
            ("Blood Type", p["blood_type"]),  # type: ignore[index]
            ("Language", p["language"]),  # type: ignore[index]
            ("Marital Status", p["marital_status"]),  # type: ignore[index]
        ],
        cols=2,
    )

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Contact & Coverage")
    y = draw_kv_grid(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        [
            ("Address", p["address"]),  # type: ignore[index]
            ("Phone", p["phone"]),  # type: ignore[index]
            ("Email", p["email"]),  # type: ignore[index]
            ("Occupation", p["occupation"]),  # type: ignore[index]
            ("Insurance", p["insurance"]),  # type: ignore[index]
            ("PCP", p["pcp"]),  # type: ignore[index]
            ("Emergency Contact", p["emergency_contact"]),  # type: ignore[index]
            ("Preferred Pharmacy", "Franklin Community Pharmacy (synthetic)"),
        ],
        cols=1,
        label_w=126,
    )

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Chart Snapshot")
    snapshot_lines = [
        "Synthetic case summary: 44-year-old woman with type 2 diabetes, hypertension, hyperlipidemia, mild intermittent asthma, and intermittent GERD. Recent ED evaluation for low-risk chest pain was reassuring.",
        "Current focus: glycemic optimization, cardiovascular risk reduction, and follow-up after January 2026 emergency department visit.",
        "Status flags: no known chronic kidney disease; microalbumin and eGFR stable. Annual dilated eye exam due March 2026.",
    ]
    c.set_stroke(0.2, 0.2, 0.2)
    c.set_line_width(0.8)
    c.rect(MARGIN, y - 86, PAGE_W - 2 * MARGIN, 86, fill=False, stroke=True)
    c.paragraph_blocks(MARGIN + 8, y - 8, snapshot_lines, max_width=PAGE_W - 2 * MARGIN - 16, leading=13, font="F1", size=9)

    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_problem_meds_page(doc: PDFDocument, case: Dict[str, object], page_num: int) -> int:
    p = case["patient"]  # type: ignore[index]
    c = Canvas()
    page_chrome(c, "Problem List, Allergies, Medications, Immunizations", page_num, p["name"], p["mrn"])  # type: ignore[index]

    left_x = MARGIN
    right_x = PAGE_W / 2 + 8
    col_w = PAGE_W / 2 - MARGIN - 14
    y_left = PAGE_H - 92
    y_right = PAGE_H - 92

    y_left = draw_section_header(c, left_x, y_left, col_w, "Active / Historical Problems")
    problem_rows = [
        [item["problem"], item["status"], item["since"], item["icd10"]]  # type: ignore[index]
        for item in case["problems"]  # type: ignore[index]
    ]
    y_left = draw_table(
        c,
        left_x,
        y_left,
        widths=[118, 54, 40, 40],
        headers=["Problem", "Status", "Since", "ICD-10"],
        rows=problem_rows,
        row_h=20,
        font_size=7.4,
    )

    y_left = draw_section_header(c, left_x, y_left, col_w, "Allergies")
    allergy_rows = [
        [a["substance"], a["reaction"], a["severity"]]  # type: ignore[index]
        for a in case["allergies"]  # type: ignore[index]
    ]
    y_left = draw_table(
        c,
        left_x,
        y_left,
        widths=[76, 126, 50],
        headers=["Substance", "Reaction", "Severity"],
        rows=allergy_rows,
        row_h=20,
        font_size=7.8,
    )

    y_left = draw_section_header(c, left_x, y_left, col_w, "Quick Trends")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(left_x, y_left - 98, col_w, 98, fill=False, stroke=True)
    labs = case["labs"]  # type: ignore[index]
    sparkline(c, left_x + 10, y_left - 85, col_w - 20, 28, [float(v["a1c"]) for v in labs], stroke=(0.1, 0.1, 0.1))
    c.text(left_x + 10, y_left - 50, "A1c trend (%): 7.8 -> 7.1", font="F2", size=8, color=(0.07, 0.07, 0.07))
    sparkline(c, left_x + 10, y_left - 42, col_w - 20, 28, [float(v["ldl"]) for v in labs], stroke=(0.3, 0.3, 0.3))
    c.text(left_x + 10, y_left - 7, "LDL trend (mg/dL): 118 -> 80", font="F2", size=8, color=(0.07, 0.07, 0.07))

    y_right = draw_section_header(c, right_x, y_right, col_w, "Medication List")
    med_rows = []
    for med in case["medications"]:  # type: ignore[index]
        med_rows.append(
            [
                med["name"],  # type: ignore[index]
                med["status"],  # type: ignore[index]
                med["start"],  # type: ignore[index]
                med["prescriber"],  # type: ignore[index]
            ]
        )
    y_right = draw_table(
        c,
        right_x,
        y_right,
        widths=[98, 32, 50, 72],
        headers=["Medication", "Status", "Start", "Prescriber"],
        rows=med_rows,
        row_h=18,
        font_size=7.7,
    )

    c.text(right_x + 2, y_right + 2, "SIG / dosing details", font="F2", size=8, color=(0.08, 0.08, 0.08))
    sig_box_y = y_right - 148
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(right_x, sig_box_y, col_w, 150, fill=False, stroke=True)
    y_sig = sig_box_y + 140
    for med in case["medications"]:  # type: ignore[index]
        line = f"{med['name']}: {med['sig']}"  # type: ignore[index]
        y_sig = c.wrapped_text(right_x + 6, y_sig, line, max_width=col_w - 12, leading=10.0, font="F1", size=7.2)
        y_sig -= 2

    y_right = sig_box_y - 10
    y_right = draw_section_header(c, right_x, y_right, col_w, "Immunizations")
    imm_rows = [
        [imm["vaccine"], imm["date"], imm["site"]]  # type: ignore[index]
        for imm in case["immunizations"]  # type: ignore[index]
    ]
    draw_table(
        c,
        right_x,
        y_right,
        widths=[130, 46, 76],
        headers=["Vaccine", "Date", "Site"],
        rows=imm_rows,
        row_h=20,
        font_size=7.7,
    )

    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_encounter_pages(doc: PDFDocument, case: Dict[str, object], page_num: int) -> int:
    p = case["patient"]  # type: ignore[index]
    encounters = case["encounters"]  # type: ignore[index]
    current_page = page_num
    for chunk_start in range(0, len(encounters), 2):
        chunk = encounters[chunk_start : chunk_start + 2]
        c = Canvas()
        page_chrome(c, "Encounter Summaries / Provider Notes", current_page, p["name"], p["mrn"])  # type: ignore[index]
        y = PAGE_H - 92
        for enc in chunk:
            c.set_fill(0.97, 0.97, 0.97)
            c.rect(MARGIN, y - 290, PAGE_W - 2 * MARGIN, 286, fill=True, stroke=False)
            c.set_stroke(0.2, 0.2, 0.2)
            c.set_line_width(0.8)
            c.rect(MARGIN, y - 290, PAGE_W - 2 * MARGIN, 286, fill=False, stroke=True)

            c.text(MARGIN + 10, y - 20, f"{enc['date']} | {enc['type']}", font="F2", size=10.5, color=(0.08, 0.08, 0.08))
            c.text(MARGIN + 10, y - 36, f"Provider: {enc['provider']} | Location: {enc['location']}", font="F1", size=8.8, color=(0.1, 0.1, 0.1))
            c.text(MARGIN + 10, y - 51, f"Vitals: {enc['vitals']}", font="F1", size=8.5, color=(0.08, 0.08, 0.08))
            c.set_stroke(0.2, 0.2, 0.2)
            c.line(MARGIN + 8, y - 58, PAGE_W - MARGIN - 8, y - 58)

            # Subjective / HPI
            c.text(MARGIN + 10, y - 75, "Reason / HPI", font="F2", size=8.5, color=(0.08, 0.08, 0.08))
            y_text = c.wrapped_text(
                MARGIN + 10,
                y - 85,
                str(enc["reason"]),
                max_width=PAGE_W - 2 * MARGIN - 20,
                leading=11.5,
                font="F1",
                size=8.5,
            )

            # Assessment and plan columns
            col_gap = 10
            col_w = (PAGE_W - 2 * MARGIN - 20 - col_gap) / 2
            left_x = MARGIN + 10
            right_x = left_x + col_w + col_gap
            box_top = y_text - 8
            box_h = 170
            c.set_stroke(0.2, 0.2, 0.2)
            c.rect(left_x, box_top - box_h, col_w, box_h, fill=False, stroke=True)
            c.rect(right_x, box_top - box_h, col_w, box_h, fill=False, stroke=True)
            c.text(left_x + 6, box_top - 14, "Assessment", font="F2", size=8.5, color=(0.08, 0.08, 0.08))
            c.text(right_x + 6, box_top - 14, "Plan", font="F2", size=8.5, color=(0.08, 0.08, 0.08))

            y_assess = box_top - 24
            for line in enc["assessment"]:  # type: ignore[index]
                y_assess = c.wrapped_text(left_x + 6, y_assess, str(line), max_width=col_w - 12, leading=11, font="F1", size=8, bullet=True)
                y_assess -= 1

            y_plan = box_top - 24
            for line in enc["plan"]:  # type: ignore[index]
                y_plan = c.wrapped_text(right_x + 6, y_plan, str(line), max_width=col_w - 12, leading=11, font="F1", size=8, bullet=True)
                y_plan -= 1

            draw_signature_block(
                c,
                MARGIN + 12,
                y - 272,
                240,
                str(enc["provider"]),
                "Authorizing Provider",
                str(enc.get("signed_at", f"{enc['date']} 17:00")),
            )

            y -= 305

        doc.add_page(c.to_bytes(), c.used_images)
        current_page += 1
    return current_page


def render_labs_and_trends_page(doc: PDFDocument, case: Dict[str, object], page_num: int) -> int:
    p = case["patient"]  # type: ignore[index]
    c = Canvas()
    page_chrome(c, "Laboratory Results, Trends, and Timeline", page_num, p["name"], p["mrn"])  # type: ignore[index]

    labs = case["labs"]  # type: ignore[index]
    y = PAGE_H - 92

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Lab Result Summary (selected)")
    rows = []
    for lab in labs:
        rows.append(
            [
                lab["date"],  # type: ignore[index]
                f"{lab['a1c']:.1f}",  # type: ignore[index]
                str(lab["glucose"]),  # type: ignore[index]
                f"{lab['creatinine']:.2f}",  # type: ignore[index]
                str(lab["egfr"]),  # type: ignore[index]
                str(lab["ldl"]),  # type: ignore[index]
                str(lab["microalb"]),  # type: ignore[index]
            ]
        )
    y = draw_table(
        c,
        MARGIN,
        y,
        widths=[76, 54, 68, 78, 56, 60, 80],
        headers=["Date", "A1c %", "Glucose", "Creatinine", "eGFR", "LDL", "Urine MicroAlb"],
        rows=rows,
        row_h=20,
        header_h=22,
    )

    labels = [str(l["date"])[5:] for l in labs]
    draw_line_chart(
        c,
        MARGIN,
        y - 154,
        (PAGE_W - 3 * MARGIN) / 2,
        150,
        series=[
            ("A1c", [float(l["a1c"]) for l in labs], (0.1, 0.1, 0.1)),
        ],
        labels=labels,
        y_min=6.8,
        y_max=8.0,
        y_ticks=[6.8, 7.0, 7.2, 7.4, 7.6, 7.8, 8.0],
        title="A1c Trend (%)",
    )
    draw_line_chart(
        c,
        PAGE_W / 2 + 6,
        y - 154,
        (PAGE_W - 3 * MARGIN) / 2,
        150,
        series=[
            ("LDL", [float(l["ldl"]) for l in labs], (0.2, 0.2, 0.2)),
            ("Glucose", [float(l["glucose"]) for l in labs], (0.4, 0.4, 0.4)),
        ],
        labels=labels,
        y_min=70,
        y_max=180,
        y_ticks=[80, 100, 120, 140, 160, 180],
        title="LDL / Glucose Trend (mg/dL)",
    )

    # Timeline and care coordination notes
    events = []
    for enc in case["encounters"]:  # type: ignore[index]
        events.append(
            {
                "date": enc["date"][5:],  # type: ignore[index]
                "site": enc["type"].split(" - ")[0][:12],  # type: ignore[index]
                "reason": str(enc["reason"])[:24],  # type: ignore[index]
            }
        )
    draw_timeline(c, MARGIN, 82, PAGE_W - 2 * MARGIN, events)

    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_diagnostics_visuals_page(
    doc: PDFDocument,
    case: Dict[str, object],
    page_num: int,
    include_synthetic_imaging: bool,
) -> int:
    p = case["patient"]  # type: ignore[index]
    c = Canvas()
    title = "Diagnostics and Imaging Reports"
    if include_synthetic_imaging:
        title = "Diagnostics, Imaging, and Diagrams (Synthetic Visuals)"
    page_chrome(c, title, page_num, p["name"], p["mrn"])  # type: ignore[index]

    y = PAGE_H - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Diagnostic Reports")
    diag = case["diagnostics"]  # type: ignore[index]
    report_rows = [
        ["ECG", diag["ecg"]["date"], diag["ecg"]["summary"]],  # type: ignore[index]
        ["Chest X-ray", diag["cxr"]["date"], diag["cxr"]["summary"]],  # type: ignore[index]
        ["Stress Test", diag["stress_test"]["date"], diag["stress_test"]["summary"]],  # type: ignore[index]
        ["RUQ Ultrasound", diag["ultrasound"]["date"], diag["ultrasound"]["summary"]],  # type: ignore[index]
    ]
    panel_h = 126
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - panel_h, PAGE_W - 2 * MARGIN, panel_h, fill=False, stroke=True)
    row_h = panel_h / 4
    for r in range(1, 4):
        c.line(MARGIN, y - r * row_h, PAGE_W - MARGIN, y - r * row_h)
    c.line(MARGIN + 74, y, MARGIN + 74, y - panel_h)
    c.line(MARGIN + 148, y, MARGIN + 148, y - panel_h)
    for i, row in enumerate(report_rows):
        row_top = y - i * row_h
        c.text(MARGIN + 4, row_top - 17, row[0], font="F2", size=8.2, color=(0.08, 0.08, 0.08))
        c.text(MARGIN + 80, row_top - 17, row[1], font="F1", size=8.0, color=(0.08, 0.08, 0.08))
        c.wrapped_text(MARGIN + 154, row_top - 8, row[2], max_width=PAGE_W - 2 * MARGIN - 160, leading=9.8, font="F1", size=7.5)

    body_y = y - panel_h - 12
    c.set_fill(0.97, 0.97, 0.97)
    c.rect(MARGIN, body_y - 258, PAGE_W - 2 * MARGIN, 258, fill=True, stroke=False)
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, body_y - 258, PAGE_W - 2 * MARGIN, 258, fill=False, stroke=True)

    if include_synthetic_imaging:
        c.text(MARGIN + 10, body_y - 18, "Synthetic imaging placeholders", font="F2", size=9.5, color=(0.07, 0.07, 0.07))
        c.image("ImCXR", MARGIN + 10, body_y - 244, 168, 220)
        c.image("ImUS", MARGIN + 188, body_y - 126, 170, 102)
        c.set_stroke(0.2, 0.2, 0.2)
        c.rect(MARGIN + 9, body_y - 245, 170, 222, fill=False, stroke=True)
        c.rect(MARGIN + 187, body_y - 127, 172, 104, fill=False, stroke=True)
        draw_ecg_strip(c, PAGE_W - MARGIN - 206, body_y - 140, 206, 140)
        draw_body_outline(c, PAGE_W - MARGIN - 206, body_y - 258, 206, 112)
        c.text(MARGIN + 188, body_y - 141, "Synthetic placeholders only.", font="F1", size=7.5, color=(0.08, 0.08, 0.08))
    else:
        c.text(MARGIN + 10, body_y - 18, "Radiology and Cardiac Interpretation Excerpts", font="F2", size=9.5, color=(0.07, 0.07, 0.07))
        detail_rows = [
            ["ECG", str(diag["ecg"]["date"]), str(diag["ecg"]["summary"])],
            ["CXR", str(diag["cxr"]["date"]), str(diag["cxr"]["summary"])],
            ["Stress Test", str(diag["stress_test"]["date"]), str(diag["stress_test"]["summary"])],
            ["RUQ US", str(diag["ultrasound"]["date"]), str(diag["ultrasound"]["summary"])],
        ]
        y_row = body_y - 30
        for label, dt, summary in detail_rows:
            c.set_stroke(0.2, 0.2, 0.2)
            c.rect(MARGIN + 10, y_row - 50, PAGE_W - 2 * MARGIN - 20, 48, fill=False, stroke=True)
            c.text(MARGIN + 14, y_row - 13, f"{label} | {dt}", font="F2", size=8, color=(0.08, 0.08, 0.08))
            c.wrapped_text(MARGIN + 14, y_row - 23, summary, max_width=PAGE_W - 2 * MARGIN - 30, leading=10, font="F1", size=7.8)
            y_row -= 60

    sig = case["report_signatures"]  # type: ignore[index]
    draw_signature_block(c, MARGIN + 12, 148, 230, str(diag["cxr"]["reported_by"]), "Radiology", str(sig["radiology_signed_at"]))  # type: ignore[index]
    draw_signature_block(c, MARGIN + 258, 148, 230, str(diag["stress_test"]["reported_by"]), "Cardiology", str(sig["cardiology_signed_at"]))  # type: ignore[index]

    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_surgical_and_pathology_page(doc: PDFDocument, case: Dict[str, object], page_num: int) -> int:
    p = case["patient"]  # type: ignore[index]
    c = Canvas()
    page_chrome(c, "Operative and Pathology Reports", page_num, p["name"], p["mrn"])  # type: ignore[index]

    surg = case["surgical_report"]  # type: ignore[index]
    path = case["pathology_report"]  # type: ignore[index]

    y = PAGE_H - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Operative Report")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 250, PAGE_W - 2 * MARGIN, 250, fill=False, stroke=True)
    y_s = draw_kv_grid(
        c,
        MARGIN + 8,
        y - 8,
        PAGE_W - 2 * MARGIN - 16,
        [
            ("Procedure Date", str(surg["procedure_date"])),
            ("Procedure", str(surg["procedure"])),
            ("Facility", str(surg["facility"])),
            ("Surgeon", str(surg["surgeon"])),
            ("Assistant", str(surg["assistant"])),
            ("Anesthesia", str(surg["anesthesia"])),
            ("Pre-op Dx", str(surg["preop_diagnosis"])),
            ("Post-op Dx", str(surg["postop_diagnosis"])),
        ],
        cols=2,
        label_w=90,
    )
    c.text(MARGIN + 12, y_s - 4, "Intraoperative Findings", font="F2", size=8.7, color=(0.08, 0.08, 0.08))
    c.rect(MARGIN + 10, y_s - 104, PAGE_W - 2 * MARGIN - 20, 96, fill=False, stroke=True)
    y_find = y_s - 14
    for finding in surg["findings"]:  # type: ignore[index]
        y_find = c.wrapped_text(MARGIN + 14, y_find, str(finding), max_width=PAGE_W - 2 * MARGIN - 30, leading=11, font="F1", size=8, bullet=True)
        y_find -= 1
    c.text(MARGIN + 12, y_s - 116, f"Specimen sent: {surg['specimen_sent']}", font="F1", size=7.8, color=(0.12, 0.12, 0.12))
    c.text(MARGIN + 12, y_s - 128, f"Estimated blood loss: {surg['estimated_blood_loss_ml']} mL | Complications: {surg['complications']}", font="F1", size=7.8, color=(0.12, 0.12, 0.12))
    c.text(MARGIN + 12, y_s - 140, f"Disposition: {surg['disposition']}", font="F1", size=7.8, color=(0.12, 0.12, 0.12))
    draw_signature_block(c, MARGIN + 12, y - 236, 236, str(surg["surgeon"]), "Attending Surgeon", str(surg["signed_at"]))

    y2 = y - 266
    y2 = draw_section_header(c, MARGIN, y2, PAGE_W - 2 * MARGIN, "Pathology Report")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y2 - 304, PAGE_W - 2 * MARGIN, 304, fill=False, stroke=True)
    y_p = draw_kv_grid(
        c,
        MARGIN + 8,
        y2 - 8,
        PAGE_W - 2 * MARGIN - 16,
        [
            ("Accession", str(path["accession"])),
            ("Collection Date", str(path["collection_date"])),
            ("Pathologist", str(path["pathologist"])),
            ("Specimen", str(path["specimen"])),
        ],
        cols=2,
        label_w=92,
    )
    c.text(MARGIN + 12, y_p - 3, "Gross Description", font="F2", size=8.7, color=(0.08, 0.08, 0.08))
    y_gross = c.wrapped_text(MARGIN + 12, y_p - 12, str(path["gross_description"]), max_width=PAGE_W - 2 * MARGIN - 24, leading=11, font="F1", size=8)
    c.text(MARGIN + 12, y_gross - 6, "Microscopic Description", font="F2", size=8.7, color=(0.08, 0.08, 0.08))
    y_micro = c.wrapped_text(MARGIN + 12, y_gross - 15, str(path["microscopic_description"]), max_width=PAGE_W - 2 * MARGIN - 24, leading=11, font="F1", size=8)
    c.text(MARGIN + 12, y_micro - 6, "Final Diagnosis", font="F2", size=8.7, color=(0.08, 0.08, 0.08))
    y_diag = y_micro - 15
    for line in path["final_diagnosis"]:  # type: ignore[index]
        y_diag = c.wrapped_text(MARGIN + 14, y_diag, str(line), max_width=PAGE_W - 2 * MARGIN - 28, leading=11, font="F1", size=8, bullet=True)
        y_diag -= 1
    draw_signature_block(c, MARGIN + 12, 64, 236, str(path["pathologist"]), "Pathologist", str(path["signed_at"]))

    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_discharge_summary_page(doc: PDFDocument, case: Dict[str, object], page_num: int) -> int:
    p = case["patient"]  # type: ignore[index]
    ds = case["discharge_summary"]  # type: ignore[index]
    c = Canvas()
    page_chrome(c, "Hospital Discharge Summary", page_num, p["name"], p["mrn"])  # type: ignore[index]

    y = PAGE_H - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Admission / Discharge")
    y = draw_kv_grid(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        [
            ("Facility", str(ds["facility"])),
            ("Attending", str(ds["attending"])),
            ("Admission Date", str(ds["admission_date"])),
            ("Discharge Date", str(ds["discharge_date"])),
            ("Admission Dx", str(ds["admission_diagnosis"])),
            ("Discharge Dx", str(ds["discharge_diagnosis"])),
        ],
        cols=1,
        label_w=132,
    )

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Hospital Course")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 112, PAGE_W - 2 * MARGIN, 112, fill=False, stroke=True)
    y_course = y - 10
    for item in ds["hospital_course"]:  # type: ignore[index]
        y_course = c.wrapped_text(MARGIN + 8, y_course, str(item), max_width=PAGE_W - 2 * MARGIN - 16, leading=12, font="F1", size=8.2, bullet=True)
        y_course -= 1

    y = y - 122
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Discharge Medications")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 90, PAGE_W - 2 * MARGIN, 90, fill=False, stroke=True)
    y_meds = y - 10
    for med in ds["discharge_medications"]:  # type: ignore[index]
        y_meds = c.wrapped_text(MARGIN + 8, y_meds, str(med), max_width=PAGE_W - 2 * MARGIN - 16, leading=11, font="F1", size=8.0, bullet=True)
        y_meds -= 1

    y = y - 100
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Follow-Up Instructions")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 80, PAGE_W - 2 * MARGIN, 80, fill=False, stroke=True)
    y_fu = y - 10
    for step in ds["follow_up"]:  # type: ignore[index]
        y_fu = c.wrapped_text(MARGIN + 8, y_fu, str(step), max_width=PAGE_W - 2 * MARGIN - 16, leading=11, font="F1", size=8.0, bullet=True)
        y_fu -= 1

    draw_signature_block(c, MARGIN + 8, 48, 250, str(ds["attending"]), "Discharging Physician", str(ds["signed_at"]))
    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_consult_note_page(doc: PDFDocument, case: Dict[str, object], page_num: int) -> int:
    p = case["patient"]  # type: ignore[index]
    cn = case["consult_note"]  # type: ignore[index]
    c = Canvas()
    page_chrome(c, "Specialty Consult Note", page_num, p["name"], p["mrn"])  # type: ignore[index]

    y = PAGE_H - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Consult Details")
    y = draw_kv_grid(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        [
            ("Service", str(cn["service"])),
            ("Date", str(cn["date"])),
            ("Consultant", str(cn["consultant"])),
            ("Requesting Provider", str(cn["requesting_provider"])),
            ("Reason", str(cn["reason"])),
        ],
        cols=1,
        label_w=136,
    )

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "History")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 64, PAGE_W - 2 * MARGIN, 64, fill=False, stroke=True)
    c.wrapped_text(MARGIN + 8, y - 10, str(cn["history"]), max_width=PAGE_W - 2 * MARGIN - 16, leading=12, font="F1", size=8.2)

    y = y - 74
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Assessment")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 96, PAGE_W - 2 * MARGIN, 96, fill=False, stroke=True)
    y_assess = y - 10
    for line in cn["assessment"]:  # type: ignore[index]
        y_assess = c.wrapped_text(MARGIN + 8, y_assess, str(line), max_width=PAGE_W - 2 * MARGIN - 16, leading=11, font="F1", size=8.0, bullet=True)
        y_assess -= 1

    y = y - 106
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Recommendations")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 96, PAGE_W - 2 * MARGIN, 96, fill=False, stroke=True)
    y_rec = y - 10
    for line in cn["recommendations"]:  # type: ignore[index]
        y_rec = c.wrapped_text(MARGIN + 8, y_rec, str(line), max_width=PAGE_W - 2 * MARGIN - 16, leading=11, font="F1", size=8.0, bullet=True)
        y_rec -= 1

    draw_signature_block(c, MARGIN + 8, 48, 250, str(cn["consultant"]), "Consulting Physician", str(cn["signed_at"]))
    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_anesthesia_report_page(doc: PDFDocument, case: Dict[str, object], page_num: int) -> int:
    p = case["patient"]  # type: ignore[index]
    ar = case["anesthesia_report"]  # type: ignore[index]
    c = Canvas()
    page_chrome(c, "Anesthesia Record Summary", page_num, p["name"], p["mrn"])  # type: ignore[index]

    y = PAGE_H - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Case / Airway / Technique")
    y = draw_kv_grid(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        [
            ("Case Date", str(ar["case_date"])),
            ("Procedure", str(ar["procedure"])),
            ("Anesthesiologist", str(ar["anesthesiologist"])),
            ("CRNA", str(ar["crna"])),
            ("ASA Class", str(ar["asa_class"])),
            ("Airway", str(ar["airway"])),
            ("Anesthetic Type", str(ar["anesthetic_type"])),
            ("Induction", str(ar["induction"])),
            ("Maintenance", str(ar["maintenance"])),
        ],
        cols=1,
        label_w=128,
    )

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Intraoperative Events")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 114, PAGE_W - 2 * MARGIN, 114, fill=False, stroke=True)
    y_ev = y - 10
    for ev in ar["events"]:  # type: ignore[index]
        y_ev = c.wrapped_text(MARGIN + 8, y_ev, str(ev), max_width=PAGE_W - 2 * MARGIN - 16, leading=11, font="F1", size=8.0, bullet=True)
        y_ev -= 1

    y = y - 124
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Post-Anesthesia Recovery")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 60, PAGE_W - 2 * MARGIN, 60, fill=False, stroke=True)
    c.wrapped_text(MARGIN + 8, y - 10, str(ar["post_anesthesia"]), max_width=PAGE_W - 2 * MARGIN - 16, leading=11, font="F1", size=8.2)

    draw_signature_block(c, MARGIN + 8, 48, 250, str(ar["anesthesiologist"]), "Attending Anesthesiologist", str(ar["signed_at"]))
    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def build_pdf(
    output_pdf: str,
    output_json: str,
    include_synthetic_imaging: bool = DEFAULT_INCLUDE_SYNTHETIC_IMAGING,
) -> None:
    case = make_case_data()
    doc = PDFDocument()
    if include_synthetic_imaging:
        doc.add_gray_image("ImCXR", 200, 280, generate_chest_xray(200, 280))
        doc.add_gray_image("ImUS", 220, 120, generate_ultrasound(220, 120))

    page_num = 1
    page_num = render_cover_and_demographics(doc, case, page_num)
    page_num = render_problem_meds_page(doc, case, page_num)
    page_num = render_encounter_pages(doc, case, page_num)
    page_num = render_labs_and_trends_page(doc, case, page_num)
    page_num = render_diagnostics_visuals_page(doc, case, page_num, include_synthetic_imaging=include_synthetic_imaging)
    page_num = render_surgical_and_pathology_page(doc, case, page_num)
    page_num = render_discharge_summary_page(doc, case, page_num)
    page_num = render_consult_note_page(doc, case, page_num)
    page_num = render_anesthesia_report_page(doc, case, page_num)
    _ = page_num

    doc.save(output_pdf)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(case, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic patient chart PDF artifacts.")
    parser.add_argument(
        "--include-synthetic-imaging",
        action="store_true",
        help="Include generated placeholder imaging panels (disabled by default).",
    )
    args = parser.parse_args()

    out_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, "synthetic_patient_chart_case_001.pdf")
    json_path = os.path.join(out_dir, "synthetic_patient_chart_case_001.json")
    build_pdf(pdf_path, json_path, include_synthetic_imaging=args.include_synthetic_imaging)
    print(f"Wrote PDF: {pdf_path}")
    print(f"Wrote JSON: {json_path}")


if __name__ == "__main__":
    main()
