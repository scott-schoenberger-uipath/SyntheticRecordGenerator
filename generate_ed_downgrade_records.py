#!/usr/bin/env python3
"""
Generate synthetic ED downgrade scenario records styled like Epic EMR printouts.

Each record represents a realistic payer downgrade of an ED visit level-of-service,
with full scoring breakdown, variance analysis, and appeal narrative.

Output goes to:
  ./ED Downgrade Records/

All records are synthetic and labeled accordingly.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from generate_synthetic_patient_pdf import (
    Canvas,
    PDFDocument,
    PAGE_H,
    PAGE_W,
    MARGIN,
    draw_table,
    fit_text_to_width,
    stable_seed,
    pdf_escape,
    fmt_num,
)


CONTENT_W = PAGE_W - 2 * MARGIN

# ─── Epic-style color palette ────────────────────────────────────────
EPIC_NAVY = (0.12, 0.16, 0.32)        # Dark navy for patient banner
EPIC_BANNER_BG = (0.13, 0.17, 0.33)   # Patient banner background
EPIC_SECTION_BG = (0.90, 0.93, 0.97)  # Light blue section header bg
EPIC_SECTION_BORDER = (0.60, 0.70, 0.82)  # Section header border
EPIC_GRAY_BG = (0.96, 0.96, 0.96)     # Alternating row background
EPIC_LIGHT_LINE = (0.78, 0.80, 0.84)  # Light separator lines
EPIC_TEXT = (0.10, 0.10, 0.10)         # Main body text
EPIC_LABEL = (0.30, 0.33, 0.38)       # Label/metadata text
EPIC_LINK = (0.05, 0.30, 0.60)        # Blue link-style text
EPIC_RED = (0.72, 0.10, 0.10)         # Alert/flag red
EPIC_GREEN = (0.10, 0.50, 0.18)       # Verified/normal


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


# ─── Epic-style page elements ────────────────────────────────────────

def epic_patient_banner(
    c: Canvas,
    patient_name: str,
    mrn: str,
    dob: str,
    age: str,
    gender: str,
    encounter_date: str,
    facility: str,
    insurance: str = "",
    page_num: int = 1,
) -> float:
    """Epic-style dark navy patient banner at top of every page."""
    banner_h = 48
    banner_y = PAGE_H - banner_h - 8

    # Dark navy banner
    c.set_fill(*EPIC_BANNER_BG)
    c.rect(0, banner_y, PAGE_W, banner_h, fill=True, stroke=False)

    # Patient name (large, white, bold)
    c.text(12, banner_y + 28, patient_name.upper(), font="F2", size=12, color=(1, 1, 1))

    # Demographics line
    demo_line = f"DOB: {dob}  |  Age: {age}  |  {gender}  |  MRN: {mrn}"
    c.text(12, banner_y + 12, demo_line, font="F1", size=8.5, color=(0.82, 0.85, 0.92))

    # Right side - encounter info
    enc_line = f"Encounter: {encounter_date}"
    enc_w = c.text_width(enc_line, 8.5, font="F1")
    c.text(PAGE_W - enc_w - 12, banner_y + 28, enc_line, font="F1", size=8.5, color=(0.82, 0.85, 0.92))

    fac_w = c.text_width(facility, 8, font="F1")
    c.text(PAGE_W - fac_w - 12, banner_y + 12, facility, font="F1", size=8, color=(0.70, 0.74, 0.82))

    # Thin colored line under banner
    c.set_fill(0.20, 0.45, 0.75)
    c.rect(0, banner_y - 2, PAGE_W, 2, fill=True, stroke=False)

    return banner_y - 6


def epic_footer(c: Canvas, page_num: int, total_pages: str = "", facility: str = "") -> None:
    """Epic-style footer with 'Printed by' info."""
    footer_y = 18
    c.set_stroke(*EPIC_LIGHT_LINE)
    c.set_line_width(0.5)
    c.line(MARGIN, footer_y + 6, PAGE_W - MARGIN, footer_y + 6)

    c.text(MARGIN, footer_y - 6,
           "Printed by: SYSTEM  |  SYNTHETIC DEMO RECORD - Not for clinical use",
           font="F1", size=6.5, color=EPIC_LABEL)

    page_text = f"Page {page_num}"
    pw = c.text_width(page_text, 7, font="F1")
    c.text(PAGE_W - MARGIN - pw, footer_y - 6, page_text, font="F1", size=7, color=EPIC_LABEL)

    # Confidentiality notice
    c.text(MARGIN, footer_y - 14,
           "This document contains confidential medical information. [SYNTHETIC]",
           font="F3", size=5.8, color=(0.45, 0.45, 0.45))


def epic_section_header(c: Canvas, y: float, label: str, icon_label: str = "") -> float:
    """Epic-style section header - light blue bg with left border accent."""
    h = 18
    # Light blue background
    c.set_fill(*EPIC_SECTION_BG)
    c.rect(MARGIN, y - h, CONTENT_W, h, fill=True, stroke=False)
    # Left accent bar
    c.set_fill(0.20, 0.45, 0.75)
    c.rect(MARGIN, y - h, 3, h, fill=True, stroke=False)
    # Bottom border
    c.set_stroke(*EPIC_SECTION_BORDER)
    c.set_line_width(0.5)
    c.line(MARGIN, y - h, MARGIN + CONTENT_W, y - h)
    # Section text
    c.text(MARGIN + 10, y - 13, label, font="F2", size=9, color=EPIC_NAVY)
    if icon_label:
        iw = c.text_width(icon_label, 7, font="F1")
        c.text(MARGIN + CONTENT_W - iw - 6, y - 12, icon_label, font="F1", size=7, color=EPIC_LABEL)
    return y - h - 4


def epic_subsection(c: Canvas, y: float, label: str) -> float:
    """Epic-style subsection - bold text with thin underline."""
    c.text(MARGIN + 6, y - 10, label, font="F2", size=8.5, color=EPIC_NAVY)
    c.set_stroke(*EPIC_LIGHT_LINE)
    c.set_line_width(0.4)
    c.line(MARGIN + 6, y - 13, MARGIN + CONTENT_W - 6, y - 13)
    return y - 18


def epic_label_value(c: Canvas, x: float, y: float, label: str, value: str,
                     label_w: float = 100, size: float = 8, value_font: str = "F1") -> None:
    """Epic-style label: value pair."""
    c.text(x, y, f"{label}:", font="F2", size=size, color=EPIC_LABEL)
    c.text(x + label_w, y, value, font=value_font, size=size, color=EPIC_TEXT)


def epic_label_value_row(c: Canvas, y: float, pairs: Sequence[Tuple[str, str]],
                         label_w: float = 80, col_w: float = 0) -> float:
    """Row of label-value pairs spanning the content width."""
    if not pairs:
        return y
    if col_w <= 0:
        col_w = CONTENT_W / len(pairs)
    for i, (label, value) in enumerate(pairs):
        x = MARGIN + 8 + i * col_w
        epic_label_value(c, x, y - 10, label, value, label_w=label_w, size=7.8)
    return y - 16


def epic_note_metadata(c: Canvas, y: float, author: str, note_time: str,
                       note_type: str = "ED Provider Note",
                       status: str = "Signed") -> float:
    """Epic-style note header with author/time metadata."""
    c.set_fill(0.97, 0.97, 0.97)
    c.rect(MARGIN + 4, y - 30, CONTENT_W - 8, 28, fill=True, stroke=False)
    c.set_stroke(*EPIC_LIGHT_LINE)
    c.set_line_width(0.3)
    c.rect(MARGIN + 4, y - 30, CONTENT_W - 8, 28, fill=False, stroke=True)

    c.text(MARGIN + 10, y - 10, note_type, font="F2", size=8.5, color=EPIC_NAVY)

    status_color = EPIC_GREEN if status == "Signed" else EPIC_LABEL
    sw = c.text_width(f"[{status}]", 7.5, font="F2")
    c.text(MARGIN + CONTENT_W - sw - 10, y - 10, f"[{status}]", font="F2", size=7.5, color=status_color)

    meta_line = f"Author: {author}  |  Note Time: {note_time}"
    c.text(MARGIN + 10, y - 24, meta_line, font="F1", size=7.5, color=EPIC_LABEL)
    return y - 36


def epic_vitals_flowsheet(c: Canvas, y: float, vitals: dict) -> float:
    """Epic-style vitals flowsheet display."""
    # Header row
    c.set_fill(*EPIC_SECTION_BG)
    c.rect(MARGIN + 4, y - 16, CONTENT_W - 8, 16, fill=True, stroke=False)
    c.set_stroke(*EPIC_SECTION_BORDER)
    c.set_line_width(0.3)
    c.rect(MARGIN + 4, y - 16, CONTENT_W - 8, 16, fill=False, stroke=True)
    c.text(MARGIN + 10, y - 12, "Vital Signs", font="F2", size=8, color=EPIC_NAVY)
    y -= 20

    items = [
        ("BP", vitals["bp"]),
        ("Pulse", str(vitals["hr"])),
        ("Resp", str(vitals["rr"])),
        ("SpO2", vitals["spo2"]),
        ("Temp", vitals["temp"]),
        ("Pain", vitals["pain"]),
    ]
    col_w = (CONTENT_W - 8) / len(items)

    # Labels row
    for i, (label, _) in enumerate(items):
        x = MARGIN + 4 + i * col_w
        c.text(x + 4, y - 10, label, font="F2", size=7, color=EPIC_LABEL)
    y -= 14

    # Values row with alternating background
    c.set_fill(0.98, 0.98, 0.98)
    c.rect(MARGIN + 4, y - 16, CONTENT_W - 8, 16, fill=True, stroke=False)
    c.set_stroke(*EPIC_LIGHT_LINE)
    c.rect(MARGIN + 4, y - 16, CONTENT_W - 8, 16, fill=False, stroke=True)

    for i, (_, value) in enumerate(items):
        x = MARGIN + 4 + i * col_w
        # Flag abnormal values
        color = EPIC_TEXT
        hr = vitals.get("hr", 0)
        if isinstance(hr, (int, float)):
            if items[i][0] == "Pulse" and (hr > 100 or hr < 60):
                color = EPIC_RED
        if items[i][0] == "SpO2" and "%" in value:
            try:
                spo2_val = int(value.split("%")[0])
                if spo2_val < 92:
                    color = EPIC_RED
            except ValueError:
                pass
        c.text(x + 4, y - 11, value, font="F4", size=8.5, color=color)

    # Column dividers
    for i in range(1, len(items)):
        x = MARGIN + 4 + i * col_w
        c.set_stroke(*EPIC_LIGHT_LINE)
        c.line(x, y + 14, x, y - 16)

    return y - 22


def epic_esignature(c: Canvas, x: float, y: float, w: float,
                    provider: str, credential: str, sign_time: str) -> float:
    """Epic-style electronic signature block."""
    c.set_stroke(*EPIC_LIGHT_LINE)
    c.set_line_width(0.3)
    c.line(x, y, x + w, y)

    # Signature wave
    rng = random.Random(stable_seed(f"{provider}|{sign_time}"))
    sig_x0 = x + 8
    sig_x1 = min(x + w - 60, x + 140)
    sig_base = y + 8
    pts = []
    for i in range(28):
        t = i / 27
        px = sig_x0 + (sig_x1 - sig_x0) * t
        py = sig_base + math.sin(5.8 * t + rng.random() * 0.3) * (3.5 + rng.random() * 1.8) + rng.uniform(-0.6, 0.6)
        pts.append((px, py))
    c.set_stroke(0.08, 0.10, 0.18)
    c.set_line_width(0.9)
    c.polyline(pts, close=False, fill=False, stroke=True)

    c.text(x, y - 10, f"Electronically signed by {provider}, {credential}",
           font="F1", size=7.5, color=EPIC_TEXT)
    c.text(x, y - 20, f"Signed: {sign_time}", font="F1", size=7, color=EPIC_LABEL)

    # Epic e-sign icon text
    c.text(x + w - 52, y - 10, "eSigned", font="F2", size=7.5, color=EPIC_GREEN)

    return y - 28


def bullet_block(
    c: Canvas, x: float, y_top: float, lines: Sequence[str],
    *, max_width: float, size: float = 8.0, leading: float = 10.6,
) -> float:
    y = y_top
    for line in lines:
        y = c.wrapped_text(
            x, y, line, max_width=max_width, leading=leading,
            font="F1", size=size, bullet=True,
        )
        y -= 1
    return y


def paragraph_block(
    c: Canvas, x: float, y_top: float, text: str,
    *, max_width: float, size: float = 8.0, leading: float = 10.6,
    font: str = "F1", color: Tuple[float, float, float] = EPIC_TEXT,
) -> float:
    return c.wrapped_text(
        x, y_top, text, max_width=max_width, leading=leading,
        font=font, size=size, color=color,
    )


def draw_table_checked(
    c: Canvas, x: float, y_top: float,
    widths: Sequence[float], headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *, max_width: float, row_h: float = 18, header_h: float = 20,
    font_size: float = 8.0,
) -> float:
    total = sum(widths)
    if total > max_width + 1e-6:
        scale = max_width / total
        widths = [w * scale for w in widths]
    return draw_table(
        c, x, y_top, widths=widths, headers=headers, rows=rows,
        row_h=row_h, header_h=header_h, font_size=font_size,
    )


# ─── Render functions ────────────────────────────────────────────────

def render_face_sheet(doc: PDFDocument, rec: dict, page_num: int) -> int:
    patient = rec["patient"]
    visit = rec["visit"]
    c = Canvas()
    y = epic_patient_banner(
        c, patient["name"], patient["mrn"], patient["dob"],
        patient["age"], patient["gender"], visit["arrival_date"],
        rec["facility"], patient.get("insurance", ""), page_num,
    )
    epic_footer(c, page_num, facility=rec["facility"])

    # Encounter header
    y = epic_section_header(c, y, "Emergency Department Encounter", "ED Visit")
    y = epic_label_value_row(c, y, [
        ("Facility", rec["facility"]),
        ("Address", rec["facility_address"]),
    ], label_w=55, col_w=CONTENT_W / 2)
    y = epic_label_value_row(c, y, [
        ("Arrival", f"{visit['arrival_date']}  {visit['arrival_time']}"),
        ("Mode", visit["mode_of_arrival"]),
        ("ESI Level", str(visit["triage_esi"])),
    ], label_w=48, col_w=CONTENT_W / 3)
    y = epic_label_value_row(c, y, [
        ("Attending", visit["ed_attending"]),
        ("Insurance", patient.get("insurance", "")),
        ("PCP", patient.get("pcp", "")),
    ], label_w=60, col_w=CONTENT_W / 3)
    y = epic_label_value_row(c, y, [
        ("Disposition", visit["disposition"]),
        ("Dispo Time", visit.get("disposition_time", "")),
    ], label_w=72, col_w=CONTENT_W / 2)

    # Chief complaint
    y -= 4
    y = epic_section_header(c, y, "Chief Complaint")
    y = paragraph_block(
        c, MARGIN + 10, y - 4, visit["chief_complaint"],
        max_width=CONTENT_W - 20, size=9, leading=12, font="F2",
    )

    # Vitals flowsheet
    y -= 8
    y = epic_vitals_flowsheet(c, y, visit["presenting_vitals"])

    # Patient demographics detail
    y -= 2
    y = epic_section_header(c, y, "Patient Demographics")
    y = epic_label_value_row(c, y, [
        ("Name", patient["name"]),
        ("DOB", patient["dob"]),
        ("MRN", patient["mrn"]),
    ], label_w=36, col_w=CONTENT_W / 3)
    y = epic_label_value_row(c, y, [
        ("Age", patient["age"]),
        ("Sex", patient["gender"]),
        ("PCP", patient.get("pcp", "")),
    ], label_w=30, col_w=CONTENT_W / 3)

    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_ed_note(doc: PDFDocument, rec: dict, page_num: int) -> int:
    """Render the main ED provider note (HPI + PMH) in Epic note style."""
    patient = rec["patient"]
    visit = rec["visit"]
    c = Canvas()
    y = epic_patient_banner(
        c, patient["name"], patient["mrn"], patient["dob"],
        patient["age"], patient["gender"], visit["arrival_date"],
        rec["facility"], page_num=page_num,
    )
    epic_footer(c, page_num, facility=rec["facility"])

    # Note metadata
    y = epic_note_metadata(
        c, y, visit["ed_attending"],
        f"{visit['arrival_date']}  {visit['arrival_time']}",
        note_type="ED Provider Note",
        status="Signed",
    )

    # HPI
    y = epic_subsection(c, y, "History of Present Illness")
    y = paragraph_block(
        c, MARGIN + 10, y - 4, visit["hpi"],
        max_width=CONTENT_W - 20, size=8.2, leading=11.2,
    )

    # PMH
    y -= 6
    y = epic_subsection(c, y, "Past Medical History")
    y = bullet_block(
        c, MARGIN + 14, y - 4, visit["relevant_pmh"],
        max_width=CONTENT_W - 28, size=8, leading=10.4,
    )

    # Signature
    y -= 14
    if y > 50:
        y = epic_esignature(
            c, MARGIN + 10, y, CONTENT_W - 20,
            visit["ed_attending"], "MD",
            f"{visit['arrival_date']}  {visit.get('disposition_time', '')}",
        )

    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_ed_course_page(doc: PDFDocument, rec: dict, page_num: int) -> int:
    """ED Course timeline in Epic activity log style."""
    patient = rec["patient"]
    visit = rec["visit"]
    entries = visit["ed_course"]

    idx = 0
    while idx < len(entries):
        c = Canvas()
        y = epic_patient_banner(
            c, patient["name"], patient["mrn"], patient["dob"],
            patient["age"], patient["gender"], visit["arrival_date"],
            rec["facility"], page_num=page_num,
        )
        epic_footer(c, page_num, facility=rec["facility"])

        y = epic_section_header(c, y, "ED Course / Activity Log", "Clinical Timeline")
        y -= 2

        while idx < len(entries) and y > 55:
            entry = entries[idx]
            est_lines = max(1, len(entry) // 75 + 1)
            needed = est_lines * 11 + 8
            if y - needed < 50 and idx > 0:
                break

            # Alternating row background
            if idx % 2 == 0:
                c.set_fill(*EPIC_GRAY_BG)
                c.rect(MARGIN + 4, y - needed + 2, CONTENT_W - 8, needed - 2, fill=True, stroke=False)

            # Extract timestamp if present (format: "HH:MM -- ")
            parts = entry.split(" -- ", 1) if " -- " in entry else entry.split(" - ", 1)
            if len(parts) == 2 and len(parts[0].strip()) <= 8:
                timestamp = parts[0].strip()
                content = parts[1].strip()
                c.text(MARGIN + 10, y - 10, timestamp, font="F4", size=7.5, color=EPIC_LINK)
                y = paragraph_block(
                    c, MARGIN + 56, y - 4, content,
                    max_width=CONTENT_W - 66, size=7.8, leading=10.2,
                )
            else:
                y = paragraph_block(
                    c, MARGIN + 10, y - 4, entry,
                    max_width=CONTENT_W - 20, size=7.8, leading=10.2,
                )
            y -= 5
            idx += 1

        doc.add_page(c.to_bytes(), c.used_images)
        page_num += 1

    return page_num


def render_nursing_page(doc: PDFDocument, rec: dict, page_num: int) -> int:
    """Nursing documentation in Epic nursing flowsheet style."""
    patient = rec["patient"]
    visit = rec["visit"]
    entries = visit["nursing_notes"]

    c = Canvas()
    y = epic_patient_banner(
        c, patient["name"], patient["mrn"], patient["dob"],
        patient["age"], patient["gender"], visit["arrival_date"],
        rec["facility"], page_num=page_num,
    )
    epic_footer(c, page_num, facility=rec["facility"])

    y = epic_note_metadata(
        c, y, "RN Staff",
        f"{visit['arrival_date']}  {visit['arrival_time']}",
        note_type="Nursing Assessment / Flowsheet",
        status="Signed",
    )
    y -= 2

    for i, entry in enumerate(entries):
        if y < 70:
            doc.add_page(c.to_bytes(), c.used_images)
            page_num += 1
            c = Canvas()
            y = epic_patient_banner(
                c, patient["name"], patient["mrn"], patient["dob"],
                patient["age"], patient["gender"], visit["arrival_date"],
                rec["facility"], page_num=page_num,
            )
            epic_footer(c, page_num, facility=rec["facility"])
            y = epic_section_header(c, y, "Nursing Assessment (continued)")
            y -= 2

        # Alternating background
        est_h = max(1, len(entry) // 75 + 1) * 11 + 4
        if i % 2 == 0:
            c.set_fill(*EPIC_GRAY_BG)
            c.rect(MARGIN + 4, y - est_h, CONTENT_W - 8, est_h, fill=True, stroke=False)

        # Extract timestamp
        parts = entry.split(" -- ", 1) if " -- " in entry else entry.split(" - ", 1)
        if len(parts) == 2 and len(parts[0].strip()) <= 8:
            timestamp = parts[0].strip()
            content = parts[1].strip()
            c.text(MARGIN + 10, y - 10, timestamp, font="F4", size=7.5, color=EPIC_LINK)
            y = paragraph_block(
                c, MARGIN + 56, y - 4, content,
                max_width=CONTENT_W - 66, size=7.8, leading=10.2,
            )
        else:
            y = paragraph_block(
                c, MARGIN + 10, y - 4, entry,
                max_width=CONTENT_W - 20, size=7.8, leading=10.2,
            )
        y -= 5

    # Signature
    if y > 50:
        y -= 8
        y = epic_esignature(
            c, MARGIN + 10, y, CONTENT_W - 20,
            "Nursing Staff, RN", "BSN",
            f"{visit['arrival_date']}  {visit.get('disposition_time', '')}",
        )

    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_lab_results_page(doc: PDFDocument, rec: dict, page_num: int) -> int:
    """Lab results in Epic Results Review style."""
    patient = rec["patient"]
    visit = rec["visit"]
    labs = rec.get("lab_results", [])
    if not labs:
        return page_num

    c = Canvas()
    y = epic_patient_banner(
        c, patient["name"], patient["mrn"], patient["dob"],
        patient["age"], patient["gender"], visit["arrival_date"],
        rec["facility"], page_num=page_num,
    )
    epic_footer(c, page_num, facility=rec["facility"])

    y = epic_section_header(c, y, "Results Review", "Lab Results")
    y -= 2

    for lab in labs:
        if y < 90:
            doc.add_page(c.to_bytes(), c.used_images)
            page_num += 1
            c = Canvas()
            y = epic_patient_banner(
                c, patient["name"], patient["mrn"], patient["dob"],
                patient["age"], patient["gender"], visit["arrival_date"],
                rec["facility"], page_num=page_num,
            )
            epic_footer(c, page_num, facility=rec["facility"])
            y = epic_section_header(c, y, "Results Review (continued)", "Lab Results")
            y -= 2

        # Lab panel header
        y = epic_subsection(c, y, f"{lab['test_name']}    Collected: {lab['collection_time']}")

        # Results table
        results = lab.get("results", [])
        if results:
            # Column headers
            col_x = [MARGIN + 10, MARGIN + 180, MARGIN + 260, MARGIN + 350, MARGIN + 470]
            c.set_fill(*EPIC_SECTION_BG)
            c.rect(MARGIN + 4, y - 12, CONTENT_W - 8, 12, fill=True, stroke=False)
            for hdr, hx in zip(["Component", "Value", "Units", "Ref Range", "Flag"], col_x):
                c.text(hx, y - 9, hdr, font="F2", size=6.8, color=EPIC_LABEL)
            y -= 14

            for ri, r in enumerate(results):
                row_h = 11
                if y - row_h < 50:
                    break
                # Alternating bg
                if ri % 2 == 0:
                    c.set_fill(*EPIC_GRAY_BG)
                    c.rect(MARGIN + 4, y - row_h, CONTENT_W - 8, row_h, fill=True, stroke=False)

                flag = r.get("flag", "")
                val_color = EPIC_RED if flag in ("H", "L", "C") else EPIC_TEXT
                flag_color = EPIC_RED if flag == "C" else ((0.80, 0.20, 0.05) if flag in ("H", "L") else EPIC_TEXT)

                c.text(col_x[0], y - 8, str(r.get("component", "")), font="F1", size=7.2, color=EPIC_TEXT)
                c.text(col_x[1], y - 8, str(r.get("value", "")), font="F4", size=7.5, color=val_color)
                c.text(col_x[2], y - 8, str(r.get("units", "")), font="F1", size=6.8, color=EPIC_LABEL)
                c.text(col_x[3], y - 8, str(r.get("reference_range", "")), font="F1", size=6.8, color=EPIC_LABEL)
                if flag:
                    c.text(col_x[4], y - 8, flag, font="F2", size=7.5, color=flag_color)
                y -= row_h

            # Thin separator
            c.set_stroke(*EPIC_LIGHT_LINE)
            c.set_line_width(0.3)
            c.line(MARGIN + 4, y, MARGIN + CONTENT_W - 4, y)
        y -= 6

    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_imaging_page(doc: PDFDocument, rec: dict, page_num: int) -> int:
    """Imaging/Radiology results in Epic radiology report style."""
    patient = rec["patient"]
    visit = rec["visit"]
    imaging = rec.get("imaging_results", [])
    if not imaging:
        return page_num

    c = Canvas()
    y = epic_patient_banner(
        c, patient["name"], patient["mrn"], patient["dob"],
        patient["age"], patient["gender"], visit["arrival_date"],
        rec["facility"], page_num=page_num,
    )
    epic_footer(c, page_num, facility=rec["facility"])

    y = epic_section_header(c, y, "Radiology Results", "Imaging")
    y -= 2

    for img in imaging:
        if y < 140:
            doc.add_page(c.to_bytes(), c.used_images)
            page_num += 1
            c = Canvas()
            y = epic_patient_banner(
                c, patient["name"], patient["mrn"], patient["dob"],
                patient["age"], patient["gender"], visit["arrival_date"],
                rec["facility"], page_num=page_num,
            )
            epic_footer(c, page_num, facility=rec["facility"])
            y = epic_section_header(c, y, "Radiology Results (continued)", "Imaging")
            y -= 2

        # Study header
        y = epic_subsection(c, y, img["study"])

        # Metadata
        y = epic_label_value_row(c, y, [
            ("Ordered", img.get("order_time", "")),
            ("Resulted", img.get("result_time", "")),
            ("Radiologist", img.get("radiologist", "")),
        ], label_w=62, col_w=CONTENT_W / 3)

        epic_label_value(c, MARGIN + 10, y - 10, "Indication", img.get("indication", ""), label_w=65, size=7.5)
        y -= 16

        # Findings
        c.text(MARGIN + 10, y - 2, "FINDINGS:", font="F2", size=7.5, color=EPIC_NAVY)
        y = paragraph_block(
            c, MARGIN + 10, y - 12, img.get("findings", ""),
            max_width=CONTENT_W - 20, size=7.8, leading=10.2,
        )
        y -= 6

        # Impression
        c.set_fill(0.96, 0.97, 0.99)
        # Estimate impression height
        imp_text = img.get("impression", "")
        imp_h = max(22, len(imp_text) // 70 * 11 + 22)
        c.rect(MARGIN + 4, y - imp_h, CONTENT_W - 8, imp_h, fill=True, stroke=False)
        c.set_stroke(*EPIC_SECTION_BORDER)
        c.set_line_width(0.3)
        c.rect(MARGIN + 4, y - imp_h, CONTENT_W - 8, imp_h, fill=False, stroke=True)
        c.text(MARGIN + 10, y - 10, "IMPRESSION:", font="F2", size=7.5, color=EPIC_NAVY)
        paragraph_block(
            c, MARGIN + 10, y - 20, imp_text,
            max_width=CONTENT_W - 20, size=7.8, leading=10.2,
        )
        y -= imp_h + 8

        # Signature line
        if y > 50:
            c.text(MARGIN + 10, y - 2,
                   f"Electronically signed by {img.get('radiologist', '')}",
                   font="F1", size=7, color=EPIC_LABEL)
            y -= 12

    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_mar_page(doc: PDFDocument, rec: dict, page_num: int) -> int:
    """Medication Administration Record (MAR) in Epic MAR style."""
    patient = rec["patient"]
    visit = rec["visit"]
    meds = rec.get("medications_administered", [])
    if not meds:
        return page_num

    c = Canvas()
    y = epic_patient_banner(
        c, patient["name"], patient["mrn"], patient["dob"],
        patient["age"], patient["gender"], visit["arrival_date"],
        rec["facility"], page_num=page_num,
    )
    epic_footer(c, page_num, facility=rec["facility"])

    y = epic_section_header(c, y, "Medication Administration Record (MAR)")
    y -= 2

    # Table header
    col_x = [MARGIN + 10, MARGIN + 56, MARGIN + 240, MARGIN + 310, MARGIN + 400]
    c.set_fill(*EPIC_SECTION_BG)
    c.rect(MARGIN + 4, y - 14, CONTENT_W - 8, 14, fill=True, stroke=False)
    for hdr, hx in zip(["Time", "Medication", "Route", "Administered By", "Indication"], col_x):
        c.text(hx, y - 10, hdr, font="F2", size=7, color=EPIC_LABEL)
    y -= 16

    for i, med in enumerate(meds):
        row_h = 13
        if y - row_h < 50:
            doc.add_page(c.to_bytes(), c.used_images)
            page_num += 1
            c = Canvas()
            y = epic_patient_banner(
                c, patient["name"], patient["mrn"], patient["dob"],
                patient["age"], patient["gender"], visit["arrival_date"],
                rec["facility"], page_num=page_num,
            )
            epic_footer(c, page_num, facility=rec["facility"])
            y = epic_section_header(c, y, "Medication Administration Record (continued)")
            y -= 2
            c.set_fill(*EPIC_SECTION_BG)
            c.rect(MARGIN + 4, y - 14, CONTENT_W - 8, 14, fill=True, stroke=False)
            for hdr, hx in zip(["Time", "Medication", "Route", "Administered By", "Indication"], col_x):
                c.text(hx, y - 10, hdr, font="F2", size=7, color=EPIC_LABEL)
            y -= 16

        if i % 2 == 0:
            c.set_fill(*EPIC_GRAY_BG)
            c.rect(MARGIN + 4, y - row_h, CONTENT_W - 8, row_h, fill=True, stroke=False)

        c.text(col_x[0], y - 9, med.get("time", ""), font="F4", size=7.2, color=EPIC_LINK)
        med_name = fit_text_to_width(c, med.get("medication", ""), 178, size=7.2, font="F1")
        c.text(col_x[1], y - 9, med_name, font="F1", size=7.2, color=EPIC_TEXT)
        c.text(col_x[2], y - 9, med.get("route", ""), font="F1", size=7.2, color=EPIC_TEXT)
        c.text(col_x[3], y - 9, med.get("administered_by", ""), font="F1", size=7.2, color=EPIC_LABEL)
        ind = fit_text_to_width(c, med.get("indication", ""), 130, size=6.8, font="F1")
        c.text(col_x[4], y - 9, ind, font="F1", size=6.8, color=EPIC_LABEL)
        y -= row_h

    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_discharge_page(doc: PDFDocument, rec: dict, page_num: int) -> int:
    """Discharge/disposition instructions in Epic AVS style."""
    patient = rec["patient"]
    visit = rec["visit"]
    dc = rec.get("discharge_instructions", {})
    if not dc:
        return page_num

    c = Canvas()
    y = epic_patient_banner(
        c, patient["name"], patient["mrn"], patient["dob"],
        patient["age"], patient["gender"], visit["arrival_date"],
        rec["facility"], page_num=page_num,
    )
    epic_footer(c, page_num, facility=rec["facility"])

    y = epic_section_header(c, y, "After Visit Summary / Discharge Instructions")

    # Diagnosis
    y = epic_subsection(c, y, "Diagnosis")
    y = paragraph_block(
        c, MARGIN + 14, y - 4, dc.get("diagnosis", ""),
        max_width=CONTENT_W - 28, size=8.2, leading=11,
    )

    # Disposition detail
    y -= 6
    y = epic_subsection(c, y, "Disposition")
    y = paragraph_block(
        c, MARGIN + 14, y - 4, dc.get("disposition_detail", visit["disposition"]),
        max_width=CONTENT_W - 28, size=8, leading=10.4,
    )

    # Follow-up
    y -= 6
    y = epic_subsection(c, y, "Follow-Up Instructions")
    y = bullet_block(
        c, MARGIN + 14, y - 4, dc.get("follow_up", []),
        max_width=CONTENT_W - 28, size=7.8, leading=10.2,
    )

    # Medications on discharge
    meds_dc = dc.get("medications_on_discharge", [])
    if meds_dc:
        y -= 6
        y = epic_subsection(c, y, "Medication Changes at Discharge")
        y = bullet_block(
            c, MARGIN + 14, y - 4, meds_dc,
            max_width=CONTENT_W - 28, size=7.8, leading=10.2,
        )

    # Return precautions
    precautions = dc.get("return_precautions", [])
    if precautions:
        y -= 6
        y = epic_subsection(c, y, "Return to Emergency Department If")
        # Alert-style box
        est_h = len(precautions) * 12 + 8
        if y - est_h > 40:
            c.set_fill(1.0, 0.97, 0.94)
            c.rect(MARGIN + 4, y - est_h - 4, CONTENT_W - 8, est_h + 4, fill=True, stroke=False)
            c.set_stroke(0.85, 0.55, 0.30)
            c.set_line_width(0.5)
            c.rect(MARGIN + 4, y - est_h - 4, CONTENT_W - 8, est_h + 4, fill=False, stroke=True)
        y = bullet_block(
            c, MARGIN + 14, y - 4, precautions,
            max_width=CONTENT_W - 28, size=7.8, leading=10.2,
        )

    # Attending signature
    y -= 14
    if y > 50:
        y = epic_esignature(
            c, MARGIN + 10, y, CONTENT_W - 20,
            visit["ed_attending"], "MD",
            f"{visit['arrival_date']}  {visit.get('disposition_time', '')}",
        )

    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


# ─── Main render pipeline ────────────────────────────────────────────

def render_record(rec: dict, pdf_path: Path, json_path: Path) -> None:
    doc = PDFDocument()
    page = 1
    page = render_face_sheet(doc, rec, page)
    page = render_ed_note(doc, rec, page)
    page = render_ed_course_page(doc, rec, page)
    page = render_nursing_page(doc, rec, page)
    page = render_lab_results_page(doc, rec, page)
    page = render_imaging_page(doc, rec, page)
    page = render_mar_page(doc, rec, page)
    page = render_discharge_page(doc, rec, page)

    doc.save(str(pdf_path))
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False)


def main() -> None:
    root = Path(os.path.dirname(os.path.abspath(__file__)))
    data_path = root / "ed_downgrade_records.json"

    with data_path.open("r", encoding="utf-8") as f:
        records = json.load(f)

    out_dir = root / "ED Downgrade Records"
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest: List[Dict[str, str]] = []

    for rec in records:
        label = slugify(rec["record_label"])
        scenario_slug = slugify(rec["scenario"])[:50]
        stem = f"{label}_{scenario_slug}"
        pdf_path = out_dir / f"{stem}.pdf"
        json_path = out_dir / f"{stem}.json"

        render_record(rec, pdf_path, json_path)
        manifest.append({
            "record": rec["record_label"],
            "scenario": rec["scenario"],
            "facility": rec["facility"],
            "disposition": rec["visit"]["disposition"],
            "pdf": str(pdf_path),
            "json": str(json_path),
        })
        print(f"  [{rec['record_label']}] {rec['scenario']}")
        print(f"    Facility: {rec['facility']}")
        print(f"    Disposition: {rec['visit']['disposition']}")
        print(f"    PDF: {pdf_path}")

    manifest_path = out_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nWrote manifest: {manifest_path}")
    print(f"Generated {len(records)} ED downgrade records.")


if __name__ == "__main__":
    main()
