#!/usr/bin/env python3
"""
Generate three synthetic inpatient provider records:
- Record A (Moderate Acuity)
- Record B (High Acuity)
- Record C (Lower Acuity)

Output goes to:
  ./Provider Synthetic Records/

All records are synthetic and labeled accordingly.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from generate_synthetic_patient_pdf import (
    Canvas,
    PDFDocument,
    PAGE_H,
    PAGE_W,
    MARGIN,
    draw_kv_grid,
    draw_section_header,
    draw_signature_block,
    draw_table,
    page_chrome,
)


def draw_table_checked(
    c: Canvas,
    x: float,
    y_top: float,
    widths: Sequence[float],
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    max_width: float,
    row_h: float = 18,
    header_h: float = 20,
    font_size: float = 8.0,
) -> float:
    total = sum(widths)
    if total > max_width + 1e-6:
        raise ValueError(f"Table width overflow: {total} > {max_width}")
    return draw_table(
        c,
        x,
        y_top,
        widths=widths,
        headers=headers,
        rows=rows,
        row_h=row_h,
        header_h=header_h,
        font_size=font_size,
    )


def bullet_block(
    c: Canvas,
    x: float,
    y_top: float,
    lines: Sequence[str],
    *,
    max_width: float,
    size: float = 8.2,
    leading: float = 10.8,
) -> float:
    y = y_top
    for line in lines:
        y = c.wrapped_text(
            x,
            y,
            line,
            max_width=max_width,
            leading=leading,
            font="F1",
            size=size,
            bullet=True,
        )
        y -= 1
    return y


def paragraph_block(
    c: Canvas,
    x: float,
    y_top: float,
    text: str,
    *,
    max_width: float,
    size: float = 8.2,
    leading: float = 10.8,
) -> float:
    return c.wrapped_text(
        x,
        y_top,
        text,
        max_width=max_width,
        leading=leading,
        font="F1",
        size=size,
    )


def render_face_sheet(doc: PDFDocument, rec: Dict[str, object], page_num: int) -> int:
    patient = rec["patient"]  # type: ignore[index]
    c = Canvas()
    page_chrome(
        c,
        f"Record {rec['record_label']} | {rec['acuity']} | Face Sheet",  # type: ignore[index]
        page_num,
        patient["name"],  # type: ignore[index]
        patient["mrn"],  # type: ignore[index]
    )
    y = PAGE_H - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Face Sheet")
    y = draw_kv_grid(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        [
            ("Record Label", str(rec["record_label"])),
            ("Acuity", str(rec["acuity"])),
            ("Theme", str(rec["theme"])),
            ("Encounter Type", "Inpatient"),
            ("Age", str(patient["age"])),  # type: ignore[index]
            ("Gender", str(patient["gender"])),  # type: ignore[index]
            ("Admission Date", str(patient["admission_date"])),  # type: ignore[index]
            ("Discharge Date", str(patient["discharge_date"])),  # type: ignore[index]
            ("Length of Stay", str(patient["length_of_stay"])),  # type: ignore[index]
            ("Attending Physician", str(patient["attending_physician"])),  # type: ignore[index]
        ],
        cols=2,
        label_w=96,
    )

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Encounter Snapshot")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 120, PAGE_W - 2 * MARGIN, 120, fill=False, stroke=True)
    summary_lines = [
        f"SYNTHETIC PROVIDER RECORD {rec['record_label']} prepared for inpatient documentation demo.",
        f"Primary clinical theme: {rec['theme']}.",
        "All identifiers, dates, providers, and events are fictional and generated for testing.",
    ]
    paragraph_block(
        c,
        MARGIN + 8,
        y - 12,
        " ".join(summary_lines),
        max_width=PAGE_W - 2 * MARGIN - 16,
        size=8.8,
        leading=12.0,
    )

    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_admission_hnp(doc: PDFDocument, rec: Dict[str, object], page_num: int) -> int:
    patient = rec["patient"]  # type: ignore[index]
    hnp = rec["admission_hnp"]  # type: ignore[index]
    c = Canvas()
    page_chrome(
        c,
        f"Record {rec['record_label']} | {rec['acuity']} | Admission H&P",  # type: ignore[index]
        page_num,
        patient["name"],  # type: ignore[index]
        patient["mrn"],  # type: ignore[index]
    )
    y = PAGE_H - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Admission History and Physical")
    y = draw_kv_grid(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        [
            ("Chief Complaint", str(hnp["chief_complaint"])),
            ("Admission Context", str(hnp["admission_context"])),
        ],
        cols=1,
        label_w=122,
    )

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "History of Present Illness")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 95, PAGE_W - 2 * MARGIN, 95, fill=False, stroke=True)
    paragraph_block(
        c,
        MARGIN + 8,
        y - 12,
        str(hnp["hpi"]),
        max_width=PAGE_W - 2 * MARGIN - 16,
        size=8.2,
        leading=10.8,
    )

    y = y - 105
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Past Medical History")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 82, PAGE_W - 2 * MARGIN, 82, fill=False, stroke=True)
    y_pmh = bullet_block(
        c,
        MARGIN + 8,
        y - 10,
        [str(v) for v in hnp["past_medical_history"]],  # type: ignore[index]
        max_width=PAGE_W - 2 * MARGIN - 16,
    )
    _ = y_pmh

    y = y - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Medication List")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 96, PAGE_W - 2 * MARGIN, 96, fill=False, stroke=True)
    bullet_block(
        c,
        MARGIN + 8,
        y - 10,
        [str(v) for v in hnp["medications"]],  # type: ignore[index]
        max_width=PAGE_W - 2 * MARGIN - 16,
        size=8.0,
        leading=10.4,
    )

    y = y - 106
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Allergies")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 52, PAGE_W - 2 * MARGIN, 52, fill=False, stroke=True)
    bullet_block(
        c,
        MARGIN + 8,
        y - 10,
        [str(v) for v in hnp["allergies"]],  # type: ignore[index]
        max_width=PAGE_W - 2 * MARGIN - 16,
        size=8.0,
        leading=10.2,
    )

    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_progress_notes(doc: PDFDocument, rec: Dict[str, object], page_num: int) -> int:
    patient = rec["patient"]  # type: ignore[index]
    notes = rec["progress_notes"]  # type: ignore[index]
    current_page = page_num
    for start in range(0, len(notes), 2):
        chunk = notes[start : start + 2]
        c = Canvas()
        page_chrome(
            c,
            f"Record {rec['record_label']} | {rec['acuity']} | Daily Progress Notes",  # type: ignore[index]
            current_page,
            patient["name"],  # type: ignore[index]
            patient["mrn"],  # type: ignore[index]
        )
        y = PAGE_H - 92
        for note in chunk:
            box_h = 310
            c.set_stroke(0.2, 0.2, 0.2)
            c.rect(MARGIN, y - box_h, PAGE_W - 2 * MARGIN, box_h, fill=False, stroke=True)
            c.text(
                MARGIN + 8,
                y - 18,
                f"{note['date']} | {note['hospital_day']} | {note['title']}",  # type: ignore[index]
                font="F2",
                size=9.2,
                color=(0.08, 0.08, 0.08),
            )
            c.text(
                MARGIN + 8,
                y - 31,
                f"Author: {note['author']} | Service: {note['service']}",  # type: ignore[index]
                font="F1",
                size=7.8,
                color=(0.08, 0.08, 0.08),
            )
            c.set_stroke(0.2, 0.2, 0.2)
            c.line(MARGIN + 6, y - 36, PAGE_W - MARGIN - 6, y - 36)

            x = MARGIN + 8
            width = PAGE_W - 2 * MARGIN - 16
            yy = y - 48
            c.text(x, yy, "Clinical Events", font="F2", size=8.2, color=(0.08, 0.08, 0.08))
            yy = bullet_block(c, x, yy - 8, [str(v) for v in note["events"]], max_width=width, size=7.8, leading=10.2)  # type: ignore[index]

            c.text(x, yy - 1, "Assessment", font="F2", size=8.2, color=(0.08, 0.08, 0.08))
            yy = bullet_block(c, x, yy - 9, [str(v) for v in note["assessment"]], max_width=width, size=7.8, leading=10.2)  # type: ignore[index]

            c.text(x, yy - 1, "Plan", font="F2", size=8.2, color=(0.08, 0.08, 0.08))
            yy = bullet_block(c, x, yy - 9, [str(v) for v in note["plan"]], max_width=width, size=7.8, leading=10.2)  # type: ignore[index]
            _ = yy

            draw_signature_block(
                c,
                MARGIN + 8,
                y - box_h + 24,
                260,
                str(note["author"]),
                "Progress Note",
                str(note["signed_at"]),
            )
            y -= box_h + 12

        doc.add_page(c.to_bytes(), c.used_images)
        current_page += 1
    return current_page


def render_escalation_page(doc: PDFDocument, rec: Dict[str, object], page_num: int) -> int:
    patient = rec["patient"]  # type: ignore[index]
    event = rec["escalation_event"]  # type: ignore[index]
    c = Canvas()
    page_chrome(
        c,
        f"Record {rec['record_label']} | {rec['acuity']} | ICU / Escalation Event",  # type: ignore[index]
        page_num,
        patient["name"],  # type: ignore[index]
        patient["mrn"],  # type: ignore[index]
    )
    y = PAGE_H - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Escalation / Transfer Note")
    y = draw_kv_grid(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        [
            ("Escalation Date", str(event["date"])),
            ("Transfer", str(event["transfer_path"])),
            ("Hypotension", str(event["hypotension"])),
            ("Lactate Peak", str(event["lactate_peak"])),
            ("Pressor Use", str(event["pressor_use"])),
            ("Mechanical Ventilation", str(event["mechanical_ventilation"])),
            ("Duration", str(event["duration"])),
            ("Outcome", str(event["outcome"])),
        ],
        cols=2,
        label_w=98,
    )

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Transfer Narrative")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 112, PAGE_W - 2 * MARGIN, 112, fill=False, stroke=True)
    bullet_block(
        c,
        MARGIN + 8,
        y - 10,
        [str(v) for v in event["transfer_note"]],  # type: ignore[index]
        max_width=PAGE_W - 2 * MARGIN - 16,
        size=8.1,
    )

    draw_signature_block(
        c,
        MARGIN + 8,
        48,
        260,
        str(event["signed_by"]),
        "Transfer Note",
        str(event["signed_at"]),
    )
    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_lab_trends_page(doc: PDFDocument, rec: Dict[str, object], page_num: int) -> int:
    patient = rec["patient"]  # type: ignore[index]
    c = Canvas()
    page_chrome(
        c,
        f"Record {rec['record_label']} | {rec['acuity']} | Lab Trends",  # type: ignore[index]
        page_num,
        patient["name"],  # type: ignore[index]
        patient["mrn"],  # type: ignore[index]
    )
    y = PAGE_H - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Lab Trend Panel")
    rows = []
    for row in rec["lab_trends"]:  # type: ignore[index]
        rows.append(
            [
                str(row["date"]),  # type: ignore[index]
                str(row["time"]),  # type: ignore[index]
                str(row["wbc"]),  # type: ignore[index]
                str(row["creatinine"]),  # type: ignore[index]
                str(row["lactate"]),  # type: ignore[index]
                str(row["hemoglobin"]),  # type: ignore[index]
            ]
        )
    y = draw_table_checked(
        c,
        MARGIN,
        y,
        widths=[68, 42, 92, 100, 92, 92],
        headers=["Date", "Time", "WBC K/uL", "Creat mg/dL", "Lact mmol/L", "Hgb g/dL"],
        rows=rows,
        max_width=PAGE_W - 2 * MARGIN,
        row_h=18,
        header_h=21,
        font_size=7.8,
    )
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Abnormal Trend Summary")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 95, PAGE_W - 2 * MARGIN, 95, fill=False, stroke=True)
    bullet_block(
        c,
        MARGIN + 8,
        y - 10,
        [str(v) for v in rec["lab_interpretation"]],  # type: ignore[index]
        max_width=PAGE_W - 2 * MARGIN - 16,
        size=8.0,
    )
    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_procedure_page(doc: PDFDocument, rec: Dict[str, object], page_num: int) -> int:
    patient = rec["patient"]  # type: ignore[index]
    proc = rec["procedure_report"]  # type: ignore[index]
    c = Canvas()
    page_chrome(
        c,
        f"Record {rec['record_label']} | {rec['acuity']} | Procedure Report",  # type: ignore[index]
        page_num,
        patient["name"],  # type: ignore[index]
        patient["mrn"],  # type: ignore[index]
    )
    y = PAGE_H - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Procedure / Operative Report")
    y = draw_kv_grid(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        [
            ("Procedure", str(proc["procedure"])),
            ("Date", str(proc["date"])),
            ("Indication", str(proc["indication"])),
            ("Primary Operator", str(proc["operator"])),
            ("Anesthesia", str(proc["anesthesia"])),
            ("Complications", str(proc["complications"])),
        ],
        cols=1,
        label_w=132,
    )

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Findings")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 120, PAGE_W - 2 * MARGIN, 120, fill=False, stroke=True)
    bullet_block(
        c,
        MARGIN + 8,
        y - 10,
        [str(v) for v in proc["findings"]],  # type: ignore[index]
        max_width=PAGE_W - 2 * MARGIN - 16,
        size=8.0,
    )

    draw_signature_block(
        c,
        MARGIN + 8,
        48,
        260,
        str(proc["operator"]),
        "Procedure Report",
        str(proc["signed_at"]),
    )
    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_discharge_summary_page(doc: PDFDocument, rec: Dict[str, object], page_num: int) -> int:
    patient = rec["patient"]  # type: ignore[index]
    ds = rec["discharge_summary"]  # type: ignore[index]
    c = Canvas()
    page_chrome(
        c,
        f"Record {rec['record_label']} | {rec['acuity']} | Discharge Summary",  # type: ignore[index]
        page_num,
        patient["name"],  # type: ignore[index]
        patient["mrn"],  # type: ignore[index]
    )
    y = PAGE_H - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Discharge Summary")
    y = draw_kv_grid(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        [
            ("Final Diagnoses Count", str(len(ds["final_diagnoses"]))),  # type: ignore[index]
            ("Discharge Disposition", str(ds["disposition"])),
            ("Discharging Provider", str(ds["author"])),
        ],
        cols=1,
        label_w=146,
    )

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Final Diagnoses")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 92, PAGE_W - 2 * MARGIN, 92, fill=False, stroke=True)
    bullet_block(
        c,
        MARGIN + 8,
        y - 10,
        [str(v) for v in ds["final_diagnoses"]],  # type: ignore[index]
        max_width=PAGE_W - 2 * MARGIN - 16,
    )

    y = y - 102
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Hospital Course Summary")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 112, PAGE_W - 2 * MARGIN, 112, fill=False, stroke=True)
    bullet_block(
        c,
        MARGIN + 8,
        y - 10,
        [str(v) for v in ds["hospital_course"]],  # type: ignore[index]
        max_width=PAGE_W - 2 * MARGIN - 16,
    )

    y = y - 122
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Follow-Up Plan")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 70, PAGE_W - 2 * MARGIN, 70, fill=False, stroke=True)
    bullet_block(
        c,
        MARGIN + 8,
        y - 10,
        [str(v) for v in ds["follow_up"]],  # type: ignore[index]
        max_width=PAGE_W - 2 * MARGIN - 16,
        size=8.0,
    )

    draw_signature_block(
        c,
        MARGIN + 8,
        48,
        260,
        str(ds["author"]),
        "Discharge Summary",
        str(ds["signed_at"]),
    )
    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_coding_page(doc: PDFDocument, rec: Dict[str, object], page_num: int) -> int:
    patient = rec["patient"]  # type: ignore[index]
    coding = rec["coding"]  # type: ignore[index]
    c = Canvas()
    page_chrome(
        c,
        f"Record {rec['record_label']} | {rec['acuity']} | Coding / Diagnosis",  # type: ignore[index]
        page_num,
        patient["name"],  # type: ignore[index]
        patient["mrn"],  # type: ignore[index]
    )
    y = PAGE_H - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Coding and Diagnosis Summary")
    y = draw_kv_grid(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        [
            ("Principal Diagnosis", str(coding["principal_diagnosis"])),
            ("Principal ICD-10", str(coding["principal_icd10"])),
        ],
        cols=1,
        label_w=140,
    )

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Secondary Diagnoses")
    sec_rows = [[str(x[0]), str(x[1])] for x in coding["secondary_diagnoses"]]  # type: ignore[index]
    y = draw_table_checked(
        c,
        MARGIN,
        y,
        widths=[96, PAGE_W - 2 * MARGIN - 96],
        headers=["ICD-10", "Diagnosis"],
        rows=sec_rows,
        max_width=PAGE_W - 2 * MARGIN,
        row_h=19,
        header_h=21,
        font_size=7.8,
    )

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Documentation Gap Section")
    gap_rows = [[str(g[0]), str(g[1])] for g in coding["documentation_gaps"]]  # type: ignore[index]
    draw_table_checked(
        c,
        MARGIN,
        y,
        widths=[190, PAGE_W - 2 * MARGIN - 190],
        headers=["Incomplete Specificity Finding", "Impact / Query Focus"],
        rows=gap_rows,
        max_width=PAGE_W - 2 * MARGIN,
        row_h=21,
        header_h=22,
        font_size=7.8,
    )

    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_record(record: Dict[str, object], out_pdf: Path, out_json: Path) -> None:
    doc = PDFDocument()
    page_num = 1
    page_num = render_face_sheet(doc, record, page_num)
    page_num = render_admission_hnp(doc, record, page_num)
    page_num = render_progress_notes(doc, record, page_num)
    page_num = render_escalation_page(doc, record, page_num)
    page_num = render_lab_trends_page(doc, record, page_num)
    page_num = render_procedure_page(doc, record, page_num)
    page_num = render_discharge_summary_page(doc, record, page_num)
    page_num = render_coding_page(doc, record, page_num)
    _ = page_num
    doc.save(str(out_pdf))
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)


def make_records() -> List[Dict[str, object]]:
    return [
        {
            "record_label": "A",
            "acuity": "Moderate Acuity",
            "theme": "Sepsis with organ dysfunction",
            "patient": {
                "name": "Amelia R. Greene",
                "mrn": "30014521",
                "age": "69",
                "gender": "Female",
                "admission_date": "2026-01-08",
                "discharge_date": "2026-01-13",
                "length_of_stay": "5 days",
                "attending_physician": "Harold Kim, MD",
            },
            "admission_hnp": {
                "chief_complaint": "Fever, confusion, and decreased urine output",
                "admission_context": "Direct admission from emergency department",
                "hpi": (
                    "Patient presented with 2 days of malaise, rigors, urinary urgency, and progressive confusion. "
                    "Initial evaluation documented sepsis on admission with acute kidney injury and hypotension. "
                    "Past history includes chronic heart failure, but systolic/diastolic type was not specified in documentation."
                ),
                "past_medical_history": [
                    "Chronic heart failure (type not specified)",
                    "Type 2 diabetes mellitus",
                    "Hypertension",
                    "Coronary artery disease",
                    "Chronic kidney disease (baseline creatinine 1.1 mg/dL)",
                ],
                "medications": [
                    "Metformin 1000 mg PO BID",
                    "Losartan 50 mg PO daily",
                    "Furosemide 20 mg PO daily",
                    "Carvedilol 6.25 mg PO BID",
                    "Aspirin 81 mg PO daily",
                ],
                "allergies": [
                    "Penicillin (rash)",
                    "Sulfa drugs (hives)",
                ],
            },
            "progress_notes": [
                {
                    "date": "2026-01-08",
                    "hospital_day": "HD1",
                    "title": "Admission Progress Note",
                    "service": "Hospital Medicine",
                    "author": "Harold Kim, MD",
                    "events": [
                        "Sepsis documented on admission with suspected urinary source.",
                        "Initial BP 92/58 after fluids; urine output low over first 6 hours.",
                    ],
                    "assessment": [
                        "Sepsis with early organ dysfunction.",
                        "AKI present but stage not specified in chart.",
                    ],
                    "plan": [
                        "Broad-spectrum antibiotics and fluid resuscitation.",
                        "Trend lactate, CBC, BMP every 12 hours.",
                        "Strict intake/output and nephrology awareness.",
                    ],
                    "signed_at": "2026-01-08 18:11",
                },
                {
                    "date": "2026-01-09",
                    "hospital_day": "HD2",
                    "title": "Escalation Note",
                    "service": "Critical Care",
                    "author": "Maya Chen, DO",
                    "events": [
                        "Rapid decline with MAP 56 and lactate peak 4.5 mmol/L.",
                        "Transferred to ICU; norepinephrine started for refractory hypotension.",
                    ],
                    "assessment": [
                        "Septic shock physiology for approximately 24 hours.",
                        "Volume status and CHF history complicated fluid strategy.",
                    ],
                    "plan": [
                        "Titrate norepinephrine to MAP >= 65.",
                        "Repeat cultures and narrow antibiotics when sensitivities return.",
                        "Hourly urine output and renal function monitoring.",
                    ],
                    "signed_at": "2026-01-09 09:40",
                },
                {
                    "date": "2026-01-10",
                    "hospital_day": "HD3",
                    "title": "ICU Improvement Note",
                    "service": "Critical Care",
                    "author": "Maya Chen, DO",
                    "events": [
                        "Hemodynamics improved; pressor weaned off overnight.",
                        "Lactate declined to 2.8 mmol/L and mentation improved.",
                    ],
                    "assessment": [
                        "Sepsis physiology improving with treatment.",
                        "AKI plateauing; creatinine trending down from peak.",
                    ],
                    "plan": [
                        "Transfer back to telemetry floor.",
                        "Continue IV antibiotics and daily renal labs.",
                        "Resume home heart-failure meds cautiously.",
                    ],
                    "signed_at": "2026-01-10 07:32",
                },
                {
                    "date": "2026-01-11",
                    "hospital_day": "HD4",
                    "title": "Floor Progress Note",
                    "service": "Hospital Medicine",
                    "author": "Harold Kim, MD",
                    "events": [
                        "No recurrent hypotension; oral intake improving.",
                        "Lactate reached 2.1 mmol/L; creatinine near baseline.",
                    ],
                    "assessment": [
                        "Clinical improvement sustained.",
                        "Ready for discharge planning with close follow-up.",
                    ],
                    "plan": [
                        "Complete antibiotic course with oral transition.",
                        "Arrange PCP and cardiology follow-up within 7 days.",
                        "Discharge expected next morning if stable overnight.",
                    ],
                    "signed_at": "2026-01-11 17:05",
                },
            ],
            "escalation_event": {
                "date": "2026-01-09",
                "transfer_path": "Telemetry -> ICU -> Telemetry",
                "hypotension": "Yes (MAP nadir 56, BP 78/46)",
                "lactate_peak": "4.5 mmol/L",
                "pressor_use": "Norepinephrine infusion for 14 hours",
                "mechanical_ventilation": "No",
                "duration": "ICU stay 24 hours",
                "outcome": "Stabilized and transferred back to floor",
                "transfer_note": [
                    "Escalation triggered by persistent hypotension despite fluid challenge.",
                    "Critical care accepted transfer; central access obtained and pressor initiated.",
                    "After 24 hours, blood pressure stabilized and lactate improved.",
                ],
                "signed_by": "Maya Chen, DO",
                "signed_at": "2026-01-10 07:30",
            },
            "lab_trends": [
                {"date": "01-08", "time": "AM", "wbc": "17.2 H", "creatinine": "1.58 H", "lactate": "3.8 H", "hemoglobin": "11.2 L"},
                {"date": "01-08", "time": "PM", "wbc": "18.5 H", "creatinine": "1.72 H", "lactate": "4.5 H", "hemoglobin": "10.9 L"},
                {"date": "01-09", "time": "AM", "wbc": "16.8 H", "creatinine": "1.80 H", "lactate": "3.9 H", "hemoglobin": "10.6 L"},
                {"date": "01-09", "time": "PM", "wbc": "15.1 H", "creatinine": "1.66 H", "lactate": "3.1 H", "hemoglobin": "10.5 L"},
                {"date": "01-10", "time": "AM", "wbc": "13.9 H", "creatinine": "1.51 H", "lactate": "2.8 H", "hemoglobin": "10.3 L"},
                {"date": "01-10", "time": "PM", "wbc": "12.8 H", "creatinine": "1.39 H", "lactate": "2.4 H", "hemoglobin": "10.4 L"},
                {"date": "01-11", "time": "AM", "wbc": "11.4 H", "creatinine": "1.26 H", "lactate": "2.1 H", "hemoglobin": "10.6 L"},
                {"date": "01-11", "time": "PM", "wbc": "10.2", "creatinine": "1.14", "lactate": "1.9", "hemoglobin": "10.8 L"},
            ],
            "lab_interpretation": [
                "Abnormal trend present: lactate improved 4.5 -> 2.1 mmol/L with resuscitation.",
                "Creatinine peaked at 1.80 mg/dL then down-trended toward baseline.",
                "WBC remained elevated early and normalized by discharge trajectory.",
            ],
            "procedure_report": {
                "procedure": "Cystoscopy with left ureteral stent placement",
                "date": "2026-01-09",
                "indication": "Source control for obstructive urosepsis",
                "operator": "Elena Russo, MD",
                "anesthesia": "General endotracheal",
                "complications": "None documented",
                "findings": [
                    "Distal left ureteral obstruction with purulent efflux after decompression.",
                    "Stent deployed in satisfactory position under fluoroscopic guidance.",
                    "No immediate bleeding or perforation.",
                ],
                "signed_at": "2026-01-09 22:18",
            },
            "discharge_summary": {
                "final_diagnoses": [
                    "Sepsis on admission with transient septic shock physiology",
                    "Acute kidney injury (stage not specified in provider note)",
                    "Chronic heart failure, unspecified type",
                    "Type 2 diabetes mellitus",
                    "Hypertension",
                ],
                "hospital_course": [
                    "Admitted for sepsis and organ dysfunction with hypotension requiring ICU transfer.",
                    "Received vasopressor support for 14 hours and source-control procedure.",
                    "Progressive hemodynamic and metabolic improvement; lactate and creatinine down-trended.",
                ],
                "disposition": "Home with home-health nursing",
                "follow_up": [
                    "Primary care and cardiology follow-up in 1 week.",
                    "Repeat BMP and CBC within 72 hours after discharge.",
                    "Complete oral antibiotic course and return for recurrent fever/hypotension.",
                ],
                "author": "Harold Kim, MD",
                "signed_at": "2026-01-13 09:02",
            },
            "coding": {
                "principal_diagnosis": "Sepsis with acute organ dysfunction",
                "principal_icd10": "A41.9",
                "secondary_diagnoses": [
                    ("N17.9", "Acute kidney injury, unspecified"),
                    ("I50.9", "Heart failure, unspecified"),
                    ("E11.9", "Type 2 diabetes mellitus without complications"),
                    ("I10", "Essential hypertension"),
                    ("N39.0", "Urinary tract infection, site not specified"),
                    ("E86.0", "Dehydration"),
                ],
                "documentation_gaps": [
                    ("Heart failure documented as CHF without type", "Needs systolic/diastolic/combined specificity"),
                    ("AKI documented without stage", "Requires KDIGO stage for severity accuracy"),
                ],
            },
        },
        {
            "record_label": "B",
            "acuity": "High Acuity / Revenue Impact",
            "theme": "Respiratory failure with multiple comorbidities",
            "patient": {
                "name": "Daniel P. Morris",
                "mrn": "30018477",
                "age": "63",
                "gender": "Male",
                "admission_date": "2026-02-02",
                "discharge_date": "2026-02-10",
                "length_of_stay": "8 days",
                "attending_physician": "Priya Raman, MD",
            },
            "admission_hnp": {
                "chief_complaint": "Severe dyspnea and hypoxemia",
                "admission_context": "Emergency admission via EMS",
                "hpi": (
                    "Patient arrived in acute respiratory distress with hypoxemia requiring emergent intubation. "
                    "Hospital course complicated by atrial fibrillation with rapid ventricular response and concern for "
                    "hospital-acquired infection later in stay. Comorbid COPD, CKD stage 3, diabetes with neuropathy, "
                    "and protein-calorie malnutrition increased risk and complexity."
                ),
                "past_medical_history": [
                    "Chronic obstructive pulmonary disease",
                    "Type 2 diabetes mellitus with peripheral neuropathy",
                    "Chronic kidney disease stage 3",
                    "Hypertension",
                    "Protein-calorie malnutrition",
                ],
                "medications": [
                    "Tiotropium inhaler daily",
                    "Albuterol/ipratropium nebulizer PRN",
                    "Insulin glargine 24 units nightly",
                    "Insulin lispro sliding scale with meals",
                    "Lisinopril 10 mg PO daily",
                    "Atorvastatin 40 mg PO nightly",
                ],
                "allergies": [
                    "Levofloxacin (tendon pain)",
                    "Codeine (nausea)",
                ],
            },
            "progress_notes": [
                {
                    "date": "2026-02-02",
                    "hospital_day": "HD1",
                    "title": "MICU Admission Note",
                    "service": "Critical Care",
                    "author": "Priya Raman, MD",
                    "events": [
                        "Intubated for acute respiratory failure with severe hypoxemia.",
                        "Initial hypotension after sedation; improved with fluid and vasopressor bolus.",
                    ],
                    "assessment": [
                        "Respiratory failure requiring invasive mechanical ventilation.",
                        "COPD exacerbation with significant work of breathing.",
                    ],
                    "plan": [
                        "Lung-protective ventilation strategy and serial ABGs.",
                        "Empiric antibiotics and bronchodilator protocol.",
                        "Continuous telemetry and glucose control.",
                    ],
                    "signed_at": "2026-02-02 22:44",
                },
                {
                    "date": "2026-02-03",
                    "hospital_day": "HD2",
                    "title": "Ventilator Management Note",
                    "service": "Critical Care",
                    "author": "Priya Raman, MD",
                    "events": [
                        "Mechanical ventilation ongoing; cumulative duration 24 hours.",
                        "Lactate remained elevated; creatinine increased above baseline CKD stage 3.",
                    ],
                    "assessment": [
                        "Critical illness with multiorgan stress pattern.",
                        "Nutritional reserve poor; malnutrition documented.",
                    ],
                    "plan": [
                        "Continue ventilator support and spontaneous breathing trial readiness checks.",
                        "Early enteral nutrition and electrolyte optimization.",
                        "Daily CXR and culture follow-up.",
                    ],
                    "signed_at": "2026-02-03 16:20",
                },
                {
                    "date": "2026-02-04",
                    "hospital_day": "HD3",
                    "title": "Extubation Progress Note",
                    "service": "Critical Care",
                    "author": "Priya Raman, MD",
                    "events": [
                        "Successfully extubated after total 36 hours mechanical ventilation.",
                        "Oxygen requirement decreased to 3 L nasal cannula.",
                    ],
                    "assessment": [
                        "Clinical improvement in respiratory status.",
                        "Hemodynamics stable without sustained pressor infusion.",
                    ],
                    "plan": [
                        "Transfer from MICU to telemetry when stable for 12 hours.",
                        "Pulmonary hygiene and incentive spirometry.",
                        "Advance diet with nutrition consult follow-up.",
                    ],
                    "signed_at": "2026-02-04 14:05",
                },
                {
                    "date": "2026-02-05",
                    "hospital_day": "HD4",
                    "title": "Telemetry Escalation Note",
                    "service": "Hospital Medicine",
                    "author": "Nina Patel, MD",
                    "events": [
                        "New atrial fibrillation with RVR to 150 bpm; treated with diltiazem.",
                        "Mild hypotension and lactate rise prompted rapid-response assessment.",
                    ],
                    "assessment": [
                        "Acute arrhythmia complicating respiratory recovery.",
                        "Need to monitor for infection-related trigger.",
                    ],
                    "plan": [
                        "Rate control and anticoagulation risk discussion.",
                        "Repeat blood cultures and procalcitonin.",
                        "Continue broad-spectrum coverage pending source clarification.",
                    ],
                    "signed_at": "2026-02-05 18:31",
                },
                {
                    "date": "2026-02-06",
                    "hospital_day": "HD5",
                    "title": "Possible HAI Note",
                    "service": "Hospital Medicine",
                    "author": "Nina Patel, MD",
                    "events": [
                        "Fever and rising WBC with concern for hospital-acquired infection.",
                        "Documentation noted possible HAI but source remained unclear in note.",
                    ],
                    "assessment": [
                        "High-risk case with unresolved infection source linkage.",
                        "Respiratory status stable on low-flow oxygen.",
                    ],
                    "plan": [
                        "Targeted imaging and sputum culture review.",
                        "Continue antibiotics with de-escalation strategy once source identified.",
                        "Monitor renal function and drug dosing with CKD stage 3.",
                    ],
                    "signed_at": "2026-02-06 17:09",
                },
                {
                    "date": "2026-02-08",
                    "hospital_day": "HD7",
                    "title": "Improvement Note",
                    "service": "Hospital Medicine",
                    "author": "Nina Patel, MD",
                    "events": [
                        "No recurrent AF with RVR in last 48 hours.",
                        "WBC, lactate, and oxygen requirement improved.",
                    ],
                    "assessment": [
                        "Overall clinical recovery with residual deconditioning.",
                        "Appropriate for discharge planning and close outpatient follow-up.",
                    ],
                    "plan": [
                        "Discharge with pulmonary and cardiology appointments.",
                        "Document clear return precautions and medication reconciliation.",
                        "Nutrition support plan and diabetes regimen review.",
                    ],
                    "signed_at": "2026-02-08 16:54",
                },
            ],
            "escalation_event": {
                "date": "2026-02-02",
                "transfer_path": "ED -> MICU -> Telemetry",
                "hypotension": "Yes (MAP low 60s during intubation period)",
                "lactate_peak": "3.9 mmol/L",
                "pressor_use": "Intermittent norepinephrine bolus support, no prolonged drip",
                "mechanical_ventilation": "Yes (36 hours)",
                "duration": "MICU stay 48 hours",
                "outcome": "Extubated and stepped down to telemetry",
                "transfer_note": [
                    "Transferred to MICU after emergency intubation for respiratory failure.",
                    "Ventilation continued for 36 hours with improvement in gas exchange.",
                    "Step-down completed after extubation and stable hemodynamics.",
                ],
                "signed_by": "Priya Raman, MD",
                "signed_at": "2026-02-04 14:12",
            },
            "lab_trends": [
                {"date": "02-02", "time": "AM", "wbc": "14.1 H", "creatinine": "1.72 H", "lactate": "3.4 H", "hemoglobin": "11.0 L"},
                {"date": "02-02", "time": "PM", "wbc": "15.7 H", "creatinine": "1.89 H", "lactate": "3.9 H", "hemoglobin": "10.7 L"},
                {"date": "02-03", "time": "AM", "wbc": "16.2 H", "creatinine": "1.95 H", "lactate": "3.5 H", "hemoglobin": "10.4 L"},
                {"date": "02-03", "time": "PM", "wbc": "15.8 H", "creatinine": "1.88 H", "lactate": "3.0 H", "hemoglobin": "10.2 L"},
                {"date": "02-04", "time": "AM", "wbc": "14.6 H", "creatinine": "1.79 H", "lactate": "2.6 H", "hemoglobin": "10.1 L"},
                {"date": "02-05", "time": "AM", "wbc": "17.3 H", "creatinine": "1.84 H", "lactate": "2.9 H", "hemoglobin": "9.9 L"},
                {"date": "02-06", "time": "PM", "wbc": "15.0 H", "creatinine": "1.76 H", "lactate": "2.3 H", "hemoglobin": "9.8 L"},
                {"date": "02-06", "time": "AM", "wbc": "12.1 H", "creatinine": "1.61 H", "lactate": "1.8", "hemoglobin": "10.0 L"},
            ],
            "lab_interpretation": [
                "Abnormal trend present: persistent leukocytosis with secondary spike during possible HAI period.",
                "Lactate remained elevated early then normalized with respiratory/hemodynamic improvement.",
                "Creatinine stayed above baseline CKD stage 3 range throughout stay.",
            ],
            "procedure_report": {
                "procedure": "Flexible bronchoscopy with bronchoalveolar lavage",
                "date": "2026-02-03",
                "indication": "Acute respiratory failure with concern for infectious etiology",
                "operator": "Thomas Reeves, MD",
                "anesthesia": "Sedation while mechanically ventilated",
                "complications": "No immediate complications",
                "findings": [
                    "Diffuse erythematous airways with moderate purulent secretions.",
                    "BAL samples collected from right middle lobe for culture and cytology.",
                    "No endobronchial mass or active bleeding seen.",
                ],
                "signed_at": "2026-02-03 15:26",
            },
            "discharge_summary": {
                "final_diagnoses": [
                    "Acute respiratory failure requiring 36-hour mechanical ventilation",
                    "COPD exacerbation",
                    "Type 2 diabetes mellitus with neuropathy",
                    "Chronic kidney disease stage 3",
                    "Atrial fibrillation with rapid ventricular response, resolved",
                    "Protein-calorie malnutrition",
                    "Possible hospital-acquired infection (source not clearly linked)",
                ],
                "hospital_course": [
                    "Required ICU admission and ventilatory support for high-acuity respiratory decompensation.",
                    "Extubated successfully after 36 hours with gradual oxygen wean.",
                    "Developed AF with RVR and possible HAI event before eventual stabilization.",
                ],
                "disposition": "Skilled nursing facility for rehab",
                "follow_up": [
                    "Pulmonology follow-up in 1 week with repeat chest imaging.",
                    "Cardiology follow-up in 2 weeks for AF monitoring.",
                    "Nephrology and nutrition follow-up within 2-3 weeks.",
                ],
                "author": "Priya Raman, MD",
                "signed_at": "2026-02-10 10:41",
            },
            "coding": {
                "principal_diagnosis": "Acute respiratory failure",
                "principal_icd10": "J96.00",
                "secondary_diagnoses": [
                    ("J44.1", "Chronic obstructive pulmonary disease with exacerbation"),
                    ("E11.40", "Type 2 diabetes mellitus with diabetic neuropathy"),
                    ("N18.30", "Chronic kidney disease, stage 3"),
                    ("E46", "Protein-calorie malnutrition"),
                    ("I48.91", "Atrial fibrillation, unspecified"),
                    ("Y95", "Nosocomial condition"),
                    ("R65.20", "Severe systemic response without shock, monitored"),
                ],
                "documentation_gaps": [
                    ("Respiratory failure documented without type qualifier", "Clarify hypoxic vs hypercapnic vs both"),
                    ("Hospital-acquired infection noted without linked source", "Specify source: pneumonia, line, urinary, or other"),
                ],
            },
        },
        {
            "record_label": "C",
            "acuity": "Lower Acuity (Gap-Heavy)",
            "theme": "CHF exacerbation",
            "patient": {
                "name": "Patricia L. Bowen",
                "mrn": "30021904",
                "age": "72",
                "gender": "Female",
                "admission_date": "2026-03-04",
                "discharge_date": "2026-03-08",
                "length_of_stay": "4 days",
                "attending_physician": "Leah Morgan, MD",
            },
            "admission_hnp": {
                "chief_complaint": "Progressive shortness of breath and leg swelling",
                "admission_context": "Admitted from clinic due volume overload symptoms",
                "hpi": (
                    "Patient reported one week of worsening orthopnea, edema, and reduced exertional tolerance. "
                    "Documentation identified CHF exacerbation but did not include EF data or systolic/diastolic type. "
                    "CKD and diabetes were listed as comorbidities, with no CKD stage documented in provider note."
                ),
                "past_medical_history": [
                    "Congestive heart failure (type unspecified)",
                    "Type 2 diabetes mellitus",
                    "Chronic kidney disease (stage not documented)",
                    "Class II obesity",
                    "Hypertension",
                ],
                "medications": [
                    "Furosemide 40 mg PO daily",
                    "Metoprolol succinate 50 mg PO daily",
                    "Losartan 25 mg PO daily",
                    "Metformin 500 mg PO BID",
                    "Insulin glargine 18 units nightly",
                ],
                "allergies": [
                    "Lisinopril (cough)",
                    "Latex (contact rash)",
                ],
            },
            "progress_notes": [
                {
                    "date": "2026-03-04",
                    "hospital_day": "HD1",
                    "title": "Admission Floor Note",
                    "service": "Hospital Medicine",
                    "author": "Leah Morgan, MD",
                    "events": [
                        "Admitted for CHF exacerbation with peripheral edema and bibasilar crackles.",
                        "Started on IV loop diuretic regimen.",
                    ],
                    "assessment": [
                        "Volume overload likely cardiac in origin, but linkage not explicitly documented.",
                        "Baseline CKD noted without stage detail.",
                    ],
                    "plan": [
                        "IV furosemide and daily weights.",
                        "Fluid and sodium restriction.",
                        "Monitor renal function twice daily.",
                    ],
                    "signed_at": "2026-03-04 19:18",
                },
                {
                    "date": "2026-03-05",
                    "hospital_day": "HD2",
                    "title": "Ward Escalation Note",
                    "service": "Hospital Medicine",
                    "author": "Leah Morgan, MD",
                    "events": [
                        "Escalation event: worsening dyspnea and poor urine response to initial diuretic dose.",
                        "Diuretic intensification to high-dose IV regimen with add-on thiazide.",
                    ],
                    "assessment": [
                        "Persistent fluid overload requiring medication escalation.",
                        "No ICU criteria met; remained stable on telemetry floor.",
                    ],
                    "plan": [
                        "Increase IV diuretic frequency and strict output monitoring.",
                        "Repeat BMP and lactate after escalation.",
                        "Cardiology consult for optimization recommendations.",
                    ],
                    "signed_at": "2026-03-05 16:47",
                },
                {
                    "date": "2026-03-06",
                    "hospital_day": "HD3",
                    "title": "Improvement Note",
                    "service": "Hospital Medicine",
                    "author": "Leah Morgan, MD",
                    "events": [
                        "Urine output improved and oxygen requirement returned to baseline.",
                        "Edema reduced by approximately 2+ to 1+ lower extremities.",
                    ],
                    "assessment": [
                        "Clinical response to escalated diuretic strategy.",
                        "Renal function mildly worsened then stabilized.",
                    ],
                    "plan": [
                        "Transition toward oral regimen as tolerated.",
                        "Continue daily weights and telemetry monitoring.",
                        "Prepare discharge teaching for fluid management.",
                    ],
                    "signed_at": "2026-03-06 15:58",
                },
                {
                    "date": "2026-03-07",
                    "hospital_day": "HD4",
                    "title": "Pre-Discharge Note",
                    "service": "Hospital Medicine",
                    "author": "Leah Morgan, MD",
                    "events": [
                        "Net negative fluid balance sustained for 48 hours.",
                        "Ambulating with stable oxygen saturation.",
                    ],
                    "assessment": [
                        "Lower-acuity course with improvement, ready for discharge.",
                        "Documentation gaps remain regarding CHF type and CKD stage.",
                    ],
                    "plan": [
                        "Discharge home with close cardiology follow-up.",
                        "Outpatient echocardiogram order placed (EF not yet documented).",
                        "Recheck labs and weights within 72 hours.",
                    ],
                    "signed_at": "2026-03-07 17:14",
                },
            ],
            "escalation_event": {
                "date": "2026-03-05",
                "transfer_path": "Telemetry floor (no ICU transfer)",
                "hypotension": "Transient borderline BP 92/60, no shock",
                "lactate_peak": "2.4 mmol/L",
                "pressor_use": "No",
                "mechanical_ventilation": "No",
                "duration": "Ward escalation over 10 hours",
                "outcome": "Improved with diuretic escalation and monitoring",
                "transfer_note": [
                    "Rapid-response style bedside reassessment performed for increased work of breathing.",
                    "Escalation handled on monitored floor with intensified diuresis.",
                    "No ICU transfer required; patient stabilized on same unit.",
                ],
                "signed_by": "Leah Morgan, MD",
                "signed_at": "2026-03-05 20:09",
            },
            "lab_trends": [
                {"date": "03-04", "time": "AM", "wbc": "9.8", "creatinine": "1.42 H", "lactate": "1.9", "hemoglobin": "10.8 L"},
                {"date": "03-04", "time": "PM", "wbc": "10.4", "creatinine": "1.50 H", "lactate": "2.2 H", "hemoglobin": "10.6 L"},
                {"date": "03-05", "time": "AM", "wbc": "10.9", "creatinine": "1.61 H", "lactate": "2.4 H", "hemoglobin": "10.5 L"},
                {"date": "03-05", "time": "PM", "wbc": "10.2", "creatinine": "1.58 H", "lactate": "2.1 H", "hemoglobin": "10.4 L"},
                {"date": "03-06", "time": "AM", "wbc": "9.6", "creatinine": "1.54 H", "lactate": "1.8", "hemoglobin": "10.2 L"},
                {"date": "03-06", "time": "PM", "wbc": "9.3", "creatinine": "1.49 H", "lactate": "1.6", "hemoglobin": "10.2 L"},
                {"date": "03-07", "time": "AM", "wbc": "8.9", "creatinine": "1.44 H", "lactate": "1.4", "hemoglobin": "10.3 L"},
                {"date": "03-07", "time": "PM", "wbc": "8.7", "creatinine": "1.40 H", "lactate": "1.3", "hemoglobin": "10.4 L"},
            ],
            "lab_interpretation": [
                "Abnormal trend present: creatinine rise with high-dose diuresis, then stabilization.",
                "Lactate mildly elevated during escalation event and normalized with improvement.",
                "Hemoglobin remained low and stable throughout admission.",
            ],
            "procedure_report": {
                "procedure": "Ultrasound-guided right thoracentesis",
                "date": "2026-03-05",
                "indication": "Symptomatic pleural effusion during CHF exacerbation",
                "operator": "Aaron Feldman, MD",
                "anesthesia": "Local lidocaine only",
                "complications": "No immediate complication",
                "findings": [
                    "Removed 650 mL clear straw-colored pleural fluid.",
                    "Post-procedure ultrasound confirmed decreased effusion and no pneumothorax.",
                    "Respiratory comfort improved after drainage.",
                ],
                "signed_at": "2026-03-05 14:22",
            },
            "discharge_summary": {
                "final_diagnoses": [
                    "Congestive heart failure exacerbation (type not documented)",
                    "Volume overload",
                    "Type 2 diabetes mellitus",
                    "Obesity",
                    "Chronic kidney disease (stage not documented)",
                    "Hypertension",
                ],
                "hospital_course": [
                    "Managed on telemetry floor without ICU transfer.",
                    "Required diuretic escalation for persistent fluid overload, then improved.",
                    "Discharged after symptom control and sustained negative fluid balance.",
                ],
                "disposition": "Home",
                "follow_up": [
                    "Cardiology follow-up within 7 days.",
                    "Outpatient echocardiogram for EF characterization.",
                    "Repeat BMP, weight check, and PCP review within 72 hours.",
                ],
                "author": "Leah Morgan, MD",
                "signed_at": "2026-03-08 10:16",
            },
            "coding": {
                "principal_diagnosis": "Congestive heart failure exacerbation",
                "principal_icd10": "I50.9",
                "secondary_diagnoses": [
                    ("E11.9", "Type 2 diabetes mellitus"),
                    ("E66.9", "Obesity, unspecified"),
                    ("N18.9", "Chronic kidney disease, unspecified"),
                    ("I10", "Essential hypertension"),
                    ("E87.70", "Fluid overload, unspecified"),
                    ("J90", "Pleural effusion"),
                ],
                "documentation_gaps": [
                    ("CHF documented without type", "Need systolic/diastolic/combined classification"),
                    ("No EF documented during admission", "Missing severity characterization and treatment linkage"),
                    ("CKD present without stage", "Requires stage 1-5 specification"),
                    ("Fluid overload not explicitly linked to CHF", "Clarify causal relationship for coding accuracy"),
                ],
            },
        },
    ]


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug


def main() -> None:
    root = Path(os.getcwd())
    out_dir = root / "Provider Synthetic Records"
    out_dir.mkdir(parents=True, exist_ok=True)

    records = make_records()
    manifest: List[Dict[str, str]] = []
    for rec in records:
        label = str(rec["record_label"]).lower()
        acuity_slug = slugify(str(rec["acuity"]))
        stem = f"record_{label}_{acuity_slug}"
        pdf_path = out_dir / f"{stem}.pdf"
        json_path = out_dir / f"{stem}.json"
        render_record(rec, pdf_path, json_path)
        manifest.append(
            {
                "record": str(rec["record_label"]),
                "acuity": str(rec["acuity"]),
                "pdf": str(pdf_path),
                "json": str(json_path),
            }
        )
        print(f"Wrote PDF: {pdf_path}")
        print(f"Wrote JSON: {json_path}")

    manifest_path = out_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote manifest: {manifest_path}")


if __name__ == "__main__":
    main()
