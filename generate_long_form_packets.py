#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from generate_provider_synthetic_records import make_records as make_provider_records
from generate_payer_synthetic_records import make_records as make_payer_records
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
    generate_chest_xray,
    generate_ultrasound,
    page_chrome,
)

WORKSPACE_ROOT = Path(__file__).resolve().parent
SCAN_VENV_PYTHON = WORKSPACE_ROOT / ".venv-scan" / "bin" / "python3.11"
SCAN_CLI = WORKSPACE_ROOT / ".venv-scan" / "bin" / "scanner"


def maybe_reexec_in_scan_env() -> None:
    if os.environ.get("SYNTHREC_SCAN_ENV") == "1":
        return
    if not SCAN_VENV_PYTHON.exists():
        return
    try:
        current = Path(sys.executable).resolve()
    except FileNotFoundError:
        current = Path(sys.executable)
    if current == SCAN_VENV_PYTHON.resolve():
        os.environ["SYNTHREC_SCAN_ENV"] = "1"
        return
    env = dict(os.environ)
    env["SYNTHREC_SCAN_ENV"] = "1"
    os.execve(
        str(SCAN_VENV_PYTHON),
        [str(SCAN_VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]],
        env,
    )


def mark_scan_target(doc: PDFDocument, page_num: int, scanned: bool) -> None:
    if not scanned:
        return
    targets = getattr(doc, "_scan_targets", None)
    if isinstance(targets, list):
        targets.append(page_num)


def apply_selective_scanned_pages(source_pdf: Path, final_pdf: Path, scan_targets: Sequence[int]) -> None:
    selected = sorted({p for p in scan_targets if p > 0})
    if not selected or not SCAN_CLI.exists():
        shutil.move(str(source_pdf), str(final_pdf))
        return

    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        shutil.move(str(source_pdf), str(final_pdf))
        return

    base_reader = PdfReader(str(source_pdf))
    if not base_reader.pages:
        shutil.move(str(source_pdf), str(final_pdf))
        return

    selected = [p for p in selected if p <= len(base_reader.pages)]
    if not selected:
        shutil.move(str(source_pdf), str(final_pdf))
        return

    with tempfile.TemporaryDirectory(prefix="synthetic-scan-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        scan_in = tmp_root / "selected_pages.pdf"
        scan_out = tmp_root / "selected_pages_output.pdf"

        selected_writer = PdfWriter()
        for page_num in selected:
            selected_writer.add_page(base_reader.pages[page_num - 1])
        with scan_in.open("wb") as f:
            selected_writer.write(f)

        cmd = [
            str(SCAN_CLI),
            "-i",
            str(tmp_root),
            "-f",
            scan_in.name,
            "-a",
            "yes",
            "-b",
            "no",
            "-l",
            "no",
            "-n",
            "5",
            "-c",
            "1.0",
            "-sh",
            "1.0",
            "-br",
            "1.0",
        ]
        try:
            subprocess.run(
                cmd,
                cwd=str(WORKSPACE_ROOT),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            shutil.move(str(source_pdf), str(final_pdf))
            return

        if not scan_out.exists():
            shutil.move(str(source_pdf), str(final_pdf))
            return

        scanned_reader = PdfReader(str(scan_out))
        writer = PdfWriter()
        scanned_map = {
            page_num: scanned_reader.pages[idx]
            for idx, page_num in enumerate(selected)
            if idx < len(scanned_reader.pages)
        }
        for idx, page in enumerate(base_reader.pages, start=1):
            writer.add_page(scanned_map.get(idx, page))
        with final_pdf.open("wb") as f:
            writer.write(f)

    source_pdf.unlink(missing_ok=True)


def save_packet_pdf(doc: PDFDocument, out_pdf: Path) -> None:
    temp_pdf = out_pdf.with_suffix(".vector.tmp.pdf")
    doc.save(str(temp_pdf))
    apply_selective_scanned_pages(temp_pdf, out_pdf, getattr(doc, "_scan_targets", []))


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
    size: float = 8.0,
    leading: float = 10.4,
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
    size: float = 8.0,
    leading: float = 10.4,
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


def add_image_assets(doc: PDFDocument) -> None:
    if "ImgCXR" not in doc.images:
        doc.add_gray_image("ImgCXR", 220, 300, generate_chest_xray(220, 300))
    if "ImgUS" not in doc.images:
        doc.add_gray_image("ImgUS", 240, 130, generate_ultrasound(240, 130))


def note_page(
    doc: PDFDocument,
    page_num: int,
    owner_name: str,
    owner_id: str,
    header: str,
    title: str,
    meta_pairs: Optional[Sequence[Tuple[str, str]]] = None,
    sections: Optional[Sequence[Tuple[str, str, Sequence[str] | str]]] = None,
    signature: Optional[Tuple[str, str, str]] = None,
    scanned: bool = False,
    header_suffix: str = "",
) -> int:
    c = Canvas()
    display_header = header if not header_suffix else f"{header} | {header_suffix}"
    page_chrome(c, display_header, page_num, owner_name, owner_id)

    y = PAGE_H - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, title)

    if meta_pairs:
        cols = 2 if len(meta_pairs) > 4 else 1
        y = draw_kv_grid(c, MARGIN, y, PAGE_W - 2 * MARGIN, meta_pairs, cols=cols, label_w=108 if cols == 2 else 138)

    if sections:
        for sec_title, kind, payload in sections:
            if y < 150:
                break
            y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, sec_title)
            content_height = 76
            if kind == "bullets":
                content_height = min(170, 18 + len(payload) * 12)  # type: ignore[arg-type]
            elif kind == "table_stub":
                content_height = 120
            elif kind == "paragraph":
                content_height = 90
            c.set_stroke(0.2, 0.2, 0.2)
            c.rect(MARGIN, y - content_height, PAGE_W - 2 * MARGIN, content_height, fill=False, stroke=True)
            if kind == "bullets":
                bullet_block(
                    c,
                    MARGIN + 8,
                    y - 10,
                    [str(v) for v in payload],  # type: ignore[arg-type]
                    max_width=PAGE_W - 2 * MARGIN - 16,
                    size=8.0,
                    leading=10.4,
                )
            elif kind == "paragraph":
                paragraph_block(
                    c,
                    MARGIN + 8,
                    y - 10,
                    str(payload),
                    max_width=PAGE_W - 2 * MARGIN - 16,
                    size=8.0,
                    leading=10.4,
                )
            else:
                lines = [str(v) for v in payload]  # type: ignore[arg-type]
                bullet_block(
                    c,
                    MARGIN + 8,
                    y - 10,
                    lines,
                    max_width=PAGE_W - 2 * MARGIN - 16,
                    size=7.8,
                    leading=10.0,
                )
            y -= content_height + 10

    if signature:
        draw_signature_block(c, MARGIN + 8, 48, 260, signature[0], signature[1], signature[2])

    doc.add_page(c.to_bytes(), c.used_images)
    mark_scan_target(doc, page_num, scanned)
    return page_num + 1


def table_page(
    doc: PDFDocument,
    page_num: int,
    owner_name: str,
    owner_id: str,
    header: str,
    title: str,
    columns: Sequence[Tuple[str, float]],
    rows: Sequence[Sequence[str]],
    notes: Optional[Sequence[str]] = None,
    signature: Optional[Tuple[str, str, str]] = None,
    scanned: bool = False,
    header_suffix: str = "",
) -> int:
    c = Canvas()
    display_header = header if not header_suffix else f"{header} | {header_suffix}"
    page_chrome(c, display_header, page_num, owner_name, owner_id)

    y = PAGE_H - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, title)
    headers = [col[0] for col in columns]
    widths = [col[1] for col in columns]
    y = draw_table_checked(
        c,
        MARGIN,
        y,
        widths=widths,
        headers=headers,
        rows=rows,
        max_width=PAGE_W - 2 * MARGIN,
        row_h=17,
        header_h=20,
        font_size=7.4,
    )

    if notes:
        y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Reviewer Notes")
        box_h = min(120, 18 + len(notes) * 12)
        c.set_stroke(0.2, 0.2, 0.2)
        c.rect(MARGIN, y - box_h, PAGE_W - 2 * MARGIN, box_h, fill=False, stroke=True)
        bullet_block(c, MARGIN + 8, y - 10, notes, max_width=PAGE_W - 2 * MARGIN - 16, size=8.0)

    if signature:
        draw_signature_block(c, MARGIN + 8, 48, 260, signature[0], signature[1], signature[2])
    doc.add_page(c.to_bytes(), c.used_images)
    mark_scan_target(doc, page_num, scanned)
    return page_num + 1


def image_report_page(
    doc: PDFDocument,
    page_num: int,
    owner_name: str,
    owner_id: str,
    header: str,
    title: str,
    report_lines: Sequence[str],
    signer: Tuple[str, str, str],
    use_ultrasound: bool = False,
) -> int:
    add_image_assets(doc)
    c = Canvas()
    page_chrome(c, header, page_num, owner_name, owner_id)
    y = PAGE_H - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, title)
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 290, PAGE_W - 2 * MARGIN, 290, fill=False, stroke=True)
    img_name = "ImgUS" if use_ultrasound else "ImgCXR"
    img_w = 210 if use_ultrasound else 180
    img_h = 114 if use_ultrasound else 245
    c.image(img_name, MARGIN + 10, y - 280, img_w, img_h)
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN + 10, y - 280, img_w, img_h, fill=False, stroke=True)
    c.text(MARGIN + img_w + 24, y - 16, "Interpretation", font="F2", size=8.6, color=(0.08, 0.08, 0.08))
    bullet_block(
        c,
        MARGIN + img_w + 24,
        y - 26,
        [str(v) for v in report_lines],
        max_width=PAGE_W - 2 * MARGIN - img_w - 34,
        size=8.0,
        leading=10.4,
    )
    c.text(MARGIN + 10, y - 292, "Synthetic imaging placeholder for demo packet realism", font="F3", size=7.1, color=(0.1, 0.1, 0.1))
    draw_signature_block(c, MARGIN + 8, 48, 260, signer[0], signer[1], signer[2])
    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def provider_daily_vitals_rows(day_idx: int, scenario: str) -> List[List[str]]:
    rows: List[List[str]] = []
    base_bp_sys = max(92, 118 - day_idx * 4)
    if scenario == "A" and day_idx == 1:
        base_bp_sys = 84
    if scenario == "B" and day_idx == 1:
        base_bp_sys = 96
    if scenario == "C" and day_idx == 1:
        base_bp_sys = 102
    for slot, hour in enumerate(["06:00", "10:00", "14:00", "18:00", "22:00"]):
        temp = 100.8 - day_idx * 0.3 - slot * 0.05 if scenario == "A" else 99.4 - day_idx * 0.15
        hr = max(68, 106 - day_idx * 5 - slot)
        rr = max(14, 22 - day_idx - slot // 2)
        spo2 = min(99, 92 + day_idx + slot // 2) if scenario == "B" else min(99, 95 + day_idx)
        rows.append([
            hour,
            f"{temp:.1f}",
            f"{base_bp_sys + slot}/{58 + day_idx + slot}",
            str(hr),
            str(rr),
            f"{spo2}%",
        ])
    return rows


def provider_lab_rows_for_day(rec: Dict[str, object], day_idx: int) -> List[List[str]]:
    source = rec["lab_trends"]  # type: ignore[index]
    rows = []
    for row in source[:8]:
        rows.append([
            str(row["date"]),  # type: ignore[index]
            str(row["time"]),  # type: ignore[index]
            str(row["wbc"]),  # type: ignore[index]
            str(row["creatinine"]),  # type: ignore[index]
            str(row["lactate"]),  # type: ignore[index]
            str(row["hemoglobin"]),  # type: ignore[index]
        ])
    # Rotate by day to vary the page.
    shift = day_idx % len(rows) if rows else 0
    return rows[shift:] + rows[:shift]


def provider_mar_rows(rec: Dict[str, object], day_idx: int) -> List[List[str]]:
    meds = rec["admission_hnp"]["medications"]  # type: ignore[index]
    rows: List[List[str]] = []
    times = ["06:00", "09:00", "13:00", "18:00", "21:00"]
    for idx, med in enumerate(meds[:10]):
        hour = times[idx % len(times)]
        status = "Given"
        if day_idx % 3 == 1 and idx == 2:
            status = "Held"
        if day_idx % 4 == 2 and idx == 4:
            status = "Late"
        rows.append([hour, med.split(" ")[0], status, "RN initials"])  # type: ignore[union-attr]
    return rows


def provider_base_header(rec: Dict[str, object]) -> str:
    return f"Record {rec['record_label']} | {rec['acuity']} | Provider Packet"  # type: ignore[index]


def build_provider_packet(rec: Dict[str, object], out_pdf: Path, out_json: Path) -> None:
    patient = rec["patient"]  # type: ignore[index]
    doc = PDFDocument()
    doc._scan_targets = []
    page_num = 1
    target_pages = {"A": 90, "B": 96, "C": 88}[str(rec["record_label"])]
    header = provider_base_header(rec)
    owner_name = str(patient["name"])
    owner_id = str(patient["mrn"])

    # Core intake and historical context.
    page_num = note_page(
        doc, page_num, owner_name, owner_id, header,
        "Inpatient Face Sheet",
        meta_pairs=[
            ("Record", str(rec["record_label"])),
            ("Acuity", str(rec["acuity"])),
            ("Theme", str(rec["theme"])),
            ("Encounter", "Inpatient synthetic packet"),
            ("Admission", str(patient["admission_date"])),
            ("Discharge", str(patient["discharge_date"])),
            ("Length of Stay", str(patient["length_of_stay"])),
            ("Attending", str(patient["attending_physician"])),
            ("Age", str(patient["age"])),
            ("Gender", str(patient["gender"])),
        ],
        sections=[
            ("Packet Overview", "paragraph", f"Synthetic long-form provider packet for scenario {rec['record_label']}. Key acuity and documentation signals are intentionally distributed across the chart, not concentrated in a single summary page."),
        ],
    )
    hnp = rec["admission_hnp"]  # type: ignore[index]
    page_num = note_page(
        doc, page_num, owner_name, owner_id, header,
        "Admission History and Physical",
        meta_pairs=[
            ("Chief Complaint", str(hnp["chief_complaint"])),
            ("Admission Context", str(hnp["admission_context"])),
        ],
        sections=[
            ("History of Present Illness", "paragraph", str(hnp["hpi"])),
            ("Past Medical History", "bullets", [str(v) for v in hnp["past_medical_history"]]),
            ("Home Medications", "bullets", [str(v) for v in hnp["medications"][:6]]),
        ],
        signature=(str(patient["attending_physician"]), "Admission H&P", f"{patient['admission_date']} 18:10"),
    )
    page_num = note_page(
        doc, page_num, owner_name, owner_id, header,
        "Emergency Department Physician Note",
        meta_pairs=[
            ("Arrival Mode", "Emergency Department"),
            ("Triage Level", "High priority" if rec["record_label"] != "C" else "Urgent"),
            ("Initial Provider", "ED Attending"),
            ("Disposition", "Admit to inpatient service"),
        ],
        sections=[
            ("ED Narrative", "paragraph", f"Pre-admission evaluation documented {rec['theme'].lower()} with immediate concern for worsening clinical trajectory. Initial workup, medication reconciliation, and specialty coordination were completed prior to bed assignment."),
            ("Immediate Actions", "bullets", [
                "IV access established and admission labs collected.",
                "Medication list reconciled with family/outpatient dispense history.",
                "Hospitalist and admitting service notified for bed placement.",
            ]),
        ],
        signature=("Aaron Feldman, MD", "Emergency Medicine", f"{patient['admission_date']} 16:45"),
    )
    page_num = note_page(
        doc, page_num, owner_name, owner_id, header,
        "Registration / Insurance / Contacts",
        meta_pairs=[
            ("Primary Contact", "Synthetic emergency contact on file"),
            ("Insurance Status", "Verified for admission"),
            ("Advance Directive", "On file" if rec["record_label"] != "B" else "Discussed with proxy"),
            ("Code Status", "Full code"),
        ],
        sections=[
            ("Registration Comments", "bullets", [
                "Identity verified from synthetic demographic record.",
                "Admission packet includes imported outside records and scanned attachments.",
                "Case management notified due to complexity / anticipated disposition needs.",
            ]),
        ],
    )
    page_num = note_page(
        doc, page_num, owner_name, owner_id, header,
        "Medication Reconciliation",
        sections=[
            ("Pre-Admission Medications", "bullets", [str(v) for v in hnp["medications"]]),
            ("Allergies", "bullets", [str(v) for v in hnp["allergies"]]),
        ],
        signature=("Clinical Pharmacist", "Medication Reconciliation", f"{patient['admission_date']} 19:08"),
    )
    page_num = table_page(
        doc, page_num, owner_name, owner_id, header,
        "Initial Laboratory Batch",
        columns=[("Date", 66), ("Time", 42), ("WBC", 78), ("Cr", 84), ("Lactate", 86), ("Hgb", 72), ("Flag", 112)],
        rows=[row + ["Initial abnormal set"] for row in provider_lab_rows_for_day(rec, 0)[:7]],
        notes=[str(v) for v in rec["lab_interpretation"]],
    )
    page_num = image_report_page(
        doc, page_num, owner_name, owner_id, header,
        "Diagnostic Imaging Report",
        report_lines=[
            f"Imaging obtained during workup for {str(rec['theme']).lower()}.",
            "Visual artifact is synthetic, included to simulate multi-modal source records.",
            "Text interpretation remains the primary clinically meaningful content for demo purposes.",
        ],
        signer=("Radiology Review", "Diagnostic Imaging", f"{patient['admission_date']} 20:01"),
        use_ultrasound=(str(rec["record_label"]) == "A"),
    )

    # Preadmission / outside records.
    historical_docs = [
        ("Prior PCP Note", "Historical PCP documented progressive symptom burden and multiple chronic comorbidities relevant to the current admission."),
        ("Specialty Follow-Up Note", "Recent specialty note shows incomplete specificity persisted before hospitalization, setting up later CDI opportunity."),
        ("Outside Facility Discharge", "Imported outside discharge packet references related symptoms and prior treatment trajectory."),
        ("Referral Packet", "Referral correspondence includes outpatient concerns, med burden, and unresolved follow-up recommendations."),
        ("Pre-Admission Case Management", "Case management outreach noted rising risk profile and barriers to stabilization before admission."),
        ("Pre-Admission Telehealth Note", "Telehealth triage discussed symptom escalation and advised emergency evaluation."),
        ("Outside Lab Fax", "Imported outside labs corroborate trend abnormality seen at admission."),
        ("Historical Problem List", "Legacy records continue to document comorbid conditions with some incomplete specificity."),
    ]
    for idx, (title, text) in enumerate(historical_docs, start=1):
        page_num = note_page(
            doc,
            page_num,
            owner_name,
            owner_id,
            header,
            title,
            sections=[
                ("Imported Record Summary", "paragraph", text),
                ("Relevance to Current Admission", "bullets", [
                    f"Historical document {idx} of {len(historical_docs)} reviewed by admitting team.",
                    "Clinical themes align with present admission scenario.",
                    "Record imported as synthetic outside-document representation.",
                ]),
            ],
            scanned=True,
            signature=("Records Review", "Imported Chart Review", f"{patient['admission_date']} 15:{20+idx:02d}"),
        )

    # Hospital-day packet: 7 pages per documented day.
    progress_notes = rec["progress_notes"]  # type: ignore[index]
    consult_cycle = ["Cardiology", "Nephrology", "Infectious Disease", "Pharmacy", "Nutrition", "Case Management", "CDI Review", "Respiratory Therapy"]
    for day_idx, note in enumerate(progress_notes):
        day = day_idx + 1
        date = str(note["date"])
        page_num = note_page(
            doc, page_num, owner_name, owner_id, header,
            f"Hospital Day {day} Physician Progress Note",
            meta_pairs=[
                ("Date", date),
                ("Hospital Day", str(note["hospital_day"])),
                ("Service", str(note["service"])),
                ("Author", str(note["author"])),
            ],
            sections=[
                ("Clinical Events", "bullets", [str(v) for v in note["events"]]),
                ("Assessment", "bullets", [str(v) for v in note["assessment"]]),
                ("Plan", "bullets", [str(v) for v in note["plan"]]),
            ],
            signature=(str(note["author"]), "Progress Note", str(note["signed_at"])),
            header_suffix=str(note["hospital_day"]),
        )
        page_num = note_page(
            doc, page_num, owner_name, owner_id, header,
            f"Hospital Day {day} Nursing Day Shift Note",
            meta_pairs=[
                ("Shift", "07:00-19:00"),
                ("Primary Nurse", f"RN-{day:02d}A"),
                ("Location", "ICU" if day == 2 and str(rec["record_label"]) in {"A", "B"} else "Telemetry / Inpatient"),
            ],
            sections=[
                ("Assessment Findings", "bullets", [
                    "Vitals reviewed q4h and documented in flowsheet.",
                    "Symptoms and tolerance to interventions tracked throughout shift.",
                    "Escalation criteria reviewed with provider as needed.",
                ]),
                ("Interventions", "bullets", [
                    "Medication administration completed per MAR.",
                    "Mobility, skin, and fall precautions maintained.",
                    "Patient/family education reinforced on daily plan.",
                ]),
            ],
            signature=(f"RN-{day:02d}A", "Nursing Note", f"{date} 18:55"),
            header_suffix=f"HD{day} Day Shift",
        )
        page_num = note_page(
            doc, page_num, owner_name, owner_id, header,
            f"Hospital Day {day} Nursing Night Shift Note",
            meta_pairs=[
                ("Shift", "19:00-07:00"),
                ("Primary Nurse", f"RN-{day:02d}N"),
                ("Monitoring", "Continuous telemetry"),
            ],
            sections=[
                ("Overnight Clinical Status", "bullets", [
                    "No code events; close observation maintained overnight.",
                    "Pain, respiratory status, and output reassessed per protocol.",
                    "Abnormal values escalated to covering provider when indicated.",
                ]),
                ("Safety / Handoff", "bullets", [
                    "Bed alarm / fall precautions reviewed.",
                    "Shift handoff completed with updated task list.",
                    "Morning labs and medication timing prepared.",
                ]),
            ],
            signature=(f"RN-{day:02d}N", "Nursing Note", f"{date} 23:48"),
            header_suffix=f"HD{day} Night Shift",
        )
        page_num = table_page(
            doc, page_num, owner_name, owner_id, header,
            f"Hospital Day {day} Vitals Flowsheet",
            columns=[("Time", 70), ("Temp F", 70), ("BP", 110), ("HR", 60), ("RR", 60), ("SpO2", 70)],
            rows=provider_daily_vitals_rows(day_idx, str(rec["record_label"])),
            notes=[
                "Flowsheet reflects trending bedside values distributed across the admission record.",
                "Trend interpretation should be synthesized with physician and nursing notes.",
            ],
            header_suffix=f"HD{day} Flowsheet",
        )
        page_num = table_page(
            doc, page_num, owner_name, owner_id, header,
            f"Hospital Day {day} Laboratory Results",
            columns=[("Date", 70), ("Time", 46), ("WBC", 90), ("Creatinine", 96), ("Lactate", 92), ("Hgb", 78)],
            rows=provider_lab_rows_for_day(rec, day_idx)[:8],
            notes=[
                "Daily lab distribution page retained for demo of large-chart review.",
                "Abnormal trends are intentionally distributed across multiple dates/pages.",
            ],
            header_suffix=f"HD{day} Labs",
        )
        page_num = table_page(
            doc, page_num, owner_name, owner_id, header,
            f"Hospital Day {day} MAR Extract",
            columns=[("Time", 70), ("Medication", 170), ("Status", 90), ("Nurse", 180)],
            rows=provider_mar_rows(rec, day_idx),
            notes=[
                "MAR extract included to simulate packet breadth and med-timing review.",
                "Held / late entries appear intermittently to reflect real administration variance.",
            ],
            header_suffix=f"HD{day} MAR",
        )
        consult_name = consult_cycle[day_idx % len(consult_cycle)]
        page_num = note_page(
            doc, page_num, owner_name, owner_id, header,
            f"Hospital Day {day} {consult_name} Follow-Up",
            meta_pairs=[
                ("Consult Service", consult_name),
                ("Date", date),
                ("Requested By", str(patient["attending_physician"])),
            ],
            sections=[
                ("Consult Impression", "bullets", [
                    f"{consult_name} reviewed the evolving course related to {str(rec['theme']).lower()}.",
                    "Relevant chronic comorbidities and medication risks reviewed.",
                    "Documentation specificity and next-step monitoring discussed with primary team.",
                ]),
                ("Recommendations", "bullets", [
                    "Continue current monitoring with specialty-specific thresholds.",
                    "Coordinate discharge planning around identified risk factors.",
                    "Reassess if clinical trajectory worsens or key labs deteriorate.",
                ]),
            ],
            signature=(f"{consult_name} Service", "Consult Follow-Up", f"{date} 16:{10+day_idx:02d}"),
            header_suffix=f"HD{day} {consult_name}",
        )

    # Escalation, procedures, CDI, discharge, coding.
    esc = rec["escalation_event"]  # type: ignore[index]
    for title, extra in [
        ("Rapid Response Note", "Rapid reassessment occurred when bedside staff identified deterioration criteria."),
        ("Transfer / ICU Handoff", "Transfer note distributes acuity signals separately from physician daily notes."),
        ("Critical Care Addendum", "Critical-care-level support documented in its own source note."),
    ]:
        page_num = note_page(
            doc, page_num, owner_name, owner_id, header,
            title,
            meta_pairs=[
                ("Event Date", str(esc["date"])),
                ("Transfer Path", str(esc["transfer_path"])),
                ("Hypotension", str(esc["hypotension"])),
                ("Lactate Peak", str(esc["lactate_peak"])),
            ],
            sections=[
                ("Event Detail", "bullets", [str(v) for v in esc["transfer_note"]]),
                ("Supportive Measures", "bullets", [
                    f"Pressor support: {esc['pressor_use']}.",
                    f"Mechanical ventilation: {esc['mechanical_ventilation']}.",
                    f"Outcome: {esc['outcome']}.",
                    extra,
                ]),
            ],
            signature=(str(esc["signed_by"]), "Escalation Documentation", str(esc["signed_at"])),
        )
    proc = rec["procedure_report"]  # type: ignore[index]
    page_num = note_page(
        doc, page_num, owner_name, owner_id, header,
        "Procedure / Operative Note",
        meta_pairs=[
            ("Procedure", str(proc["procedure"])),
            ("Date", str(proc["date"])),
            ("Operator", str(proc["operator"])),
            ("Anesthesia", str(proc["anesthesia"])),
        ],
        sections=[
            ("Indication", "paragraph", str(proc["indication"])),
            ("Findings", "bullets", [str(v) for v in proc["findings"]]),
            ("Complications", "bullets", [str(proc["complications"])]),
        ],
        signature=(str(proc["operator"]), "Procedure Note", str(proc["signed_at"])),
    )
    page_num = note_page(
        doc, page_num, owner_name, owner_id, header,
        "Anesthesia Record",
        sections=[
            ("Intraoperative Events", "bullets", [
                f"Anesthesia type documented as {proc['anesthesia']}.",
                "Hemodynamic tolerance and airway status documented in separate anesthesia workflow.",
                "Recovery handoff communicated to floor / ICU team after procedure.",
            ]),
            ("Post-Procedure Status", "bullets", [
                "Pain and respiratory status reassessed post-procedure.",
                "No immediate anesthesia-related complication documented.",
            ]),
        ],
        signature=("Anesthesia Service", "Anesthesia Record", str(proc["signed_at"])),
    )
    if rec.get("pathology_report"):
        path = rec["pathology_report"]  # type: ignore[index]
        page_num = note_page(
            doc, page_num, owner_name, owner_id, header,
            "Pathology Report",
            meta_pairs=[
                ("Accession", str(path["accession"])),
                ("Collection", str(path["collection_date"])),
                ("Specimen", str(path["specimen"])),
            ],
            sections=[
                ("Gross Description", "paragraph", str(path["gross_description"])),
                ("Microscopic Description", "paragraph", str(path["microscopic_description"])),
                ("Final Diagnosis", "bullets", [str(v) for v in path["final_diagnosis"]]),
            ],
            signature=(str(path["pathologist"]), "Pathology", str(path["signed_at"])),
        )

    # CDI / utilization / discharge bundle.
    for title, lines in [
        ("Clinical Documentation Integrity Query", [
            "Review requested to confirm final specificity of principal diagnosis and severity indicators.",
            "Question set intentionally reflects scenario-specific documentation gaps.",
            "Provider response referenced in later coding pages, not centralized here.",
        ]),
        ("Utilization Review Note", [
            "Continued stay criteria met based on active treatment needs and ongoing monitoring.",
            "Escalation event and abnormal labs support inpatient level of care.",
            "Interdisciplinary review completed with case management and nursing leadership.",
        ]),
        ("Case Management Discharge Planning", [
            "Disposition options reviewed early and updated throughout stay.",
            "Education, follow-up coordination, and durable medical equipment planning distributed across multiple notes.",
            "Family/support needs documented separately from physician discharge summary.",
        ]),
        ("Discharge Medication Reconciliation", [
            "Home medications, inpatient changes, and hold instructions reconciled.",
            "Patient teaching and pharmacy counseling documented in separate signed entries.",
            "Return precautions and follow-up appointments added to after-visit packet.",
        ]),
    ]:
        page_num = note_page(
            doc, page_num, owner_name, owner_id, header,
            title,
            sections=[("Documentation", "bullets", lines)],
            signature=(str(patient["attending_physician"]), title, f"{patient['discharge_date']} 09:1{str(rec['record_label'])}"),
        )
    ds = rec["discharge_summary"]  # type: ignore[index]
    page_num = note_page(
        doc, page_num, owner_name, owner_id, header,
        "Discharge Summary",
        meta_pairs=[
            ("Disposition", str(ds["disposition"])),
            ("Author", str(ds["author"])),
            ("Signed", str(ds["signed_at"])),
        ],
        sections=[
            ("Final Diagnoses", "bullets", [str(v) for v in ds["final_diagnoses"]]),
            ("Hospital Course", "bullets", [str(v) for v in ds["hospital_course"]]),
            ("Follow-Up", "bullets", [str(v) for v in ds["follow_up"]]),
        ],
        signature=(str(ds["author"]), "Discharge Summary", str(ds["signed_at"])),
    )
    coding = rec["coding"]  # type: ignore[index]
    page_num = table_page(
        doc, page_num, owner_name, owner_id, header,
        "Coding and Diagnosis Page",
        columns=[("ICD-10", 96), ("Diagnosis", 444)],
        rows=[[str(coding["principal_icd10"]), str(coding["principal_diagnosis"])] ] + [[str(v[0]), str(v[1])] for v in coding["secondary_diagnoses"]],
        notes=[f"Documentation gap: {g[0]} -> {g[1]}" for g in coding["documentation_gaps"]],
        signature=("Coding Review", "Diagnosis Coding", f"{patient['discharge_date']} 13:20"),
    )

    # Imported packet expansion until target reached.
    filler_titles = [
        "Imported Nursing Flowsheet",
        "Outside Facility Faxed Note",
        "Consult Attestation",
        "Telemetry Review",
        "Respiratory Therapy Treatment Log",
        "Nutrition Follow-Up",
        "Therapy Assessment",
        "Care Coordination Follow-Up",
        "Medication Administration Continuation",
        "Lab Attachment Import",
    ]
    scanned_table_titles = {"Imported Nursing Flowsheet", "Lab Attachment Import"}
    scanned_note_titles = {"Outside Facility Faxed Note"}
    filler_idx = 0
    while page_num <= target_pages:
        title = filler_titles[filler_idx % len(filler_titles)]
        if filler_idx % 3 == 0:
            page_num = table_page(
                doc,
                page_num,
                owner_name,
                owner_id,
                header,
                title,
                columns=[("Time", 70), ("Item", 180), ("Status", 100), ("Comment", 190)],
                rows=[
                    ["06:00", "Assessment", "Complete", "Imported continuation page"],
                    ["09:00", "Medication / task", "Complete", f"Scenario {rec['record_label']} ongoing documentation"],
                    ["12:00", "Provider aware", "Noted", "Key signal distributed across packet"],
                    ["15:00", "Reassessment", "Complete", "No single-source summary dependence"],
                    ["18:00", "Handoff", "Complete", "Synthetic packet filler with clinical relevance"],
                ],
                notes=[
                    "Additional page included to simulate large packet review conditions.",
                    "Content intentionally overlaps partially with other chart elements like real packets do.",
                ],
                scanned=title in scanned_table_titles,
            )
        else:
            page_num = note_page(
                doc,
                page_num,
                owner_name,
                owner_id,
                header,
                title,
                sections=[
                    ("Imported Content", "bullets", [
                        f"Supplemental document {filler_idx + 1} supports longitudinal packet size target.",
                        "Clinical and documentation details are reiterated in a different source context.",
                        f"Scenario-specific theme remains {str(rec['theme']).lower()}.",
                    ]),
                    ("Reviewer Context", "paragraph", "This page exists to make the packet resemble a real large chart bundle, where relevant facts are distributed across repeated and partially redundant source documents."),
                ],
                scanned=title in scanned_note_titles,
                signature=("Imported Records", "Packet Assembly", f"{patient['discharge_date']} 14:{10 + (filler_idx % 40):02d}"),
            )
        filler_idx += 1

    save_packet_pdf(doc, out_pdf)
    payload = dict(rec)
    payload["packet_target_pages"] = target_pages
    payload["packet_generated_pages"] = len(doc.pages)
    payload["packet_type"] = "provider_long_form"
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def payer_claim_rows(rec: Dict[str, object], month_idx: int) -> List[List[str]]:
    base_events = rec["utilization_events"]  # type: ignore[index]
    rows: List[List[str]] = []
    for idx, ev in enumerate(base_events):
        rows.append([
            f"CLM-{month_idx+1:02d}{idx+1:03d}",
            str(ev["type"]),
            str(ev["reason"]),
            str(ev["paid_amount"]),
            "Paid" if idx % 2 == 0 else "Adj/Review",
        ])
    rows.append([
        f"CLM-{month_idx+1:02d}900",
        "Rx / ancillary",
        "Associated meds / care coordination / supplies",
        "$1,240",
        "Paid",
    ])
    return rows


def payer_fill_rows(rec: Dict[str, object], window_idx: int) -> List[List[str]]:
    meds = rec["medications"]  # type: ignore[index]
    rows: List[List[str]] = []
    for idx, med in enumerate(meds[:10]):
        days_late = (idx + window_idx) % 9
        rows.append([
            str(idx + 1),
            str(med["medication"]),  # type: ignore[index]
            str(med["class"]),  # type: ignore[index]
            f"{30 + (idx % 3) * 30}d",
            f"{days_late} days late" if days_late else "On time",
        ])
    return rows


def payer_contact_lines(rec: Dict[str, object], idx: int) -> List[str]:
    social = rec["social_factors"]["findings"]  # type: ignore[index]
    base = [str(v) for v in social]
    picks = [base[idx % len(base)], base[(idx + 1) % len(base)], base[(idx + 2) % len(base)]]
    return [
        "Outbound care-management contact attempted / completed regarding ongoing risk mitigation.",
        picks[0],
        picks[1],
        picks[2],
        "Follow-up tasks assigned for transportation, adherence, or appointment coordination as applicable.",
    ]


def payer_base_header(rec: Dict[str, object]) -> str:
    return f"Record {rec['record_label']} | {rec['risk_tier']} | Payer Packet"  # type: ignore[index]


def build_payer_packet(rec: Dict[str, object], out_pdf: Path, out_json: Path) -> None:
    member = rec["member"]  # type: ignore[index]
    doc = PDFDocument()
    doc._scan_targets = []
    page_num = 1
    target_pages = {"A": 88, "B": 92, "C": 84}[str(rec["record_label"])]
    header = payer_base_header(rec)
    owner_name = str(member["name"])
    owner_id = str(member["member_id"])

    page_num = note_page(
        doc, page_num, owner_name, owner_id, header,
        "Member Demographics and Risk Header",
        meta_pairs=[
            ("Record", str(rec["record_label"])),
            ("Risk Tier", str(rec["risk_tier"])),
            ("Theme", str(rec["theme"])),
            ("Insurance", str(member["insurance_type"])),
            ("Member", str(member["name"])),
            ("Member ID", str(member["member_id"])),
            ("Age", str(member["age"])),
            ("Gender", str(member["gender"])),
            ("PCP", str(member["pcp"])),
            ("Care Manager", str(rec["care_manager"])),
        ],
        sections=[
            ("Packet Intent", "paragraph", "Synthetic payer packet built to simulate a large multi-source care-management and claims review file. Clinical and social risk signals are intentionally distributed across the packet."),
        ],
    )
    conds = rec["chronic_conditions"]  # type: ignore[index]
    page_num = table_page(
        doc, page_num, owner_name, owner_id, header,
        "Chronic Conditions Summary",
        columns=[("Condition", 165), ("Status", 90), ("Impact", 185), ("Risk", 100)],
        rows=[[str(v["condition"]), str(v["status"]), str(v["impact"]), str(v["hcc"])] for v in conds],
        notes=[
            "Condition burden informs payer prioritization and intervention sequencing.",
            "Risk signals are corroborated in utilization, claims, and outreach sections later in the packet.",
        ],
    )
    util = rec["utilization_events"]  # type: ignore[index]
    page_num = table_page(
        doc, page_num, owner_name, owner_id, header,
        "Hospitalizations and ED Utilization",
        columns=[("Date", 74), ("Type", 72), ("Facility", 130), ("Reason", 180), ("Plan Paid", 84)],
        rows=[[str(v["date"]), str(v["type"]), str(v["facility"]), str(v["reason"]), str(v["paid_amount"])] for v in util],
        notes=[
            "This packet is not a summary; utilization is reiterated across claims and transitions-of-care documents.",
        ],
    )
    meds = rec["medications"]  # type: ignore[index]
    page_num = table_page(
        doc, page_num, owner_name, owner_id, header,
        "Medication List and Risk Flags",
        columns=[("Medication", 120), ("Dose", 64), ("Class", 100), ("Schedule", 74), ("Risk Note", 182)],
        rows=[[str(v["medication"]), str(v["dose"]), str(v["class"]), str(v["schedule"]), str(v["risk_note"])] for v in meds],
        notes=[str(v) for v in rec["medication_risk_focus"]],
        signature=(str(rec["pharmacist_reviewer"]), "Pharmacy Review", str(rec["pharmacy_review_signed_at"])),
    )
    fn = rec["functional_assessment"]  # type: ignore[index]
    sf = rec["social_factors"]  # type: ignore[index]
    sections = [
        ("Functional Assessment", "bullets", [
            f"Mobility: {fn['mobility']}",
            f"ADLs / IADLs: {fn['adl_details'][0]}",
            f"DME use: {fn['dme_use']}",
            f"Oxygen use: {fn['oxygen_use']}",
            f"PT/OT: {fn['pt_ot_eval']}",
        ]),
        ("Social Factors", "bullets", [str(v) for v in sf["findings"]]),
    ]
    if rec.get("behavioral_health_note"):
        sections += [("Behavioral Health", "paragraph", str(rec["behavioral_health_note"]))]
    page_num = note_page(
        doc, page_num, owner_name, owner_id, header,
        "Functional Assessment and Social Factors",
        sections=sections,
        signature=(str(rec["care_manager"]), "Care Management", str(rec["care_manager_signed_at"])),
    )

    # Monthly claims detail pages.
    for month_idx in range(12):
        page_num = table_page(
            doc, page_num, owner_name, owner_id, header,
            f"Claims Detail Review Month {month_idx + 1}",
            columns=[("Claim ID", 90), ("Type", 90), ("Reason / Service", 220), ("Amount", 70), ("Status", 70)],
            rows=payer_claim_rows(rec, month_idx),
            notes=[
                "Monthly claim detail included to simulate large payer packet review.",
                f"Theme remains {str(rec['theme']).lower()} with distributed utilization signal.",
            ],
            header_suffix=f"Claims M{month_idx + 1}",
        )

    # Pharmacy fill history.
    for window_idx in range(10):
        page_num = table_page(
            doc, page_num, owner_name, owner_id, header,
            f"Pharmacy Fill History Window {window_idx + 1}",
            columns=[("Seq", 40), ("Medication", 170), ("Class", 110), ("Supply", 80), ("Fill Adherence", 140)],
            rows=payer_fill_rows(rec, window_idx),
            notes=[
                "Fill timing and adherence pattern should be synthesized with social barriers and outreach logs.",
            ],
            header_suffix=f"Rx Fill {window_idx + 1}",
        )

    # Outreach and contact logs.
    for idx in range(14):
        page_num = note_page(
            doc, page_num, owner_name, owner_id, header,
            f"Care Management Outreach Log {idx + 1}",
            meta_pairs=[
                ("Contact Type", "Outbound call / voicemail / coordination"),
                ("Assigned RN", str(rec["care_manager"])),
                ("Priority", "High" if idx % 3 == 0 else "Routine follow-up"),
            ],
            sections=[
                ("Contact Summary", "bullets", payer_contact_lines(rec, idx)),
                ("Action Items", "bullets", [
                    "Document member response and barriers in next case review.",
                    "Update transportation / pharmacy support task list.",
                    "Escalate to PCP or medical director if red-flag issue persists.",
                ]),
            ],
            signature=(str(rec["care_manager"]), "Outreach Log", f"2026-02-{(idx % 28) + 1:02d} 15:{10 + (idx % 40):02d}"),
            header_suffix=f"Outreach {idx + 1}",
        )

    # Authorization, transitions, and correspondence.
    auth_titles = [
        "Utilization Review Note",
        "Authorization Case Review",
        "Transitions of Care Outreach",
        "Specialist Appointment Coordination",
        "Durable Medical Equipment Review",
        "Behavioral Health Coordination" if rec.get("behavioral_health_note") else "Community Resource Coordination",
        "Provider Correspondence",
        "Scanned Fax Attachment",
    ]
    for idx, title in enumerate(auth_titles * 4):
        if page_num > target_pages - 10:
            break
        scanned = title in {"Provider Correspondence", "Scanned Fax Attachment"}
        page_num = note_page(
            doc,
            page_num,
            owner_name,
            owner_id,
            header,
            title,
            sections=[
                ("Documentation", "bullets", [
                    f"{title} page {idx + 1} distributes risk evidence across the payer packet.",
                    "Claim history, adherence, and social barriers are referenced in multiple document types.",
                    f"Scenario-specific theme remains {str(rec['theme']).lower()}.",
                ]),
                ("Follow-Up", "bullets", [
                    "Coordinate with PCP, specialists, and member support resources.",
                    "Update next review cycle with outcome of outreach or authorization request.",
                ]),
            ],
            scanned=scanned,
            signature=(str(rec["care_manager"]), title, f"2026-03-{(idx % 28) + 1:02d} 10:{10 + (idx % 40):02d}"),
            header_suffix=f"{title[:10]} {idx + 1}",
        )

    # Final care plan and targeted filler until target.
    page_num = note_page(
        doc, page_num, owner_name, owner_id, header,
        "Complex Case Clinical Snapshot",
        sections=[
            ("Risk Synopsis", "bullets", [str(v) for v in rec["snapshot_points"]]),
            ("Intervention Plan", "bullets", [str(v) for v in rec["follow_up_plan"]]),
        ],
        signature=(str(rec["medical_director"]), "Medical Director Review", str(rec["medical_director_signed_at"])),
    )
    page_num = table_page(
        doc, page_num, owner_name, owner_id, header,
        "Documentation and Risk Gaps",
        columns=[("Gap", 240), ("Impact / Next Action", 300)],
        rows=[[str(v["gap"]), str(v["impact"])] for v in rec["risk_gaps"]],
        notes=[
            "Gaps are intentionally spread across utilization, pharmacy, and outreach sections rather than isolated here.",
        ],
    )

    filler_idx = 0
    filler_titles = [
        "Imported Claim Attachment",
        "Scanned Care Management Worksheet",
        "Pharmacy Dispense Audit",
        "Community Resource Follow-Up",
        "Member Contact Attempt",
        "Provider Office Correspondence",
    ]
    scanned_filler_titles = {
        "Imported Claim Attachment",
        "Scanned Care Management Worksheet",
        "Provider Office Correspondence",
    }
    while page_num <= target_pages:
        title = filler_titles[filler_idx % len(filler_titles)]
        if filler_idx % 2 == 0:
            page_num = table_page(
                doc,
                page_num,
                owner_name,
                owner_id,
                header,
                title,
                columns=[("Field", 140), ("Value", 400)],
                rows=[
                    ["Member", owner_name],
                    ["Theme", str(rec["theme"])],
                    ["Risk Tier", str(rec["risk_tier"])],
                    ["Packet Note", "Supplemental source page for large-document demo"],
                    ["Action", "Corroborates information located elsewhere in the packet"],
                ],
                notes=["Supplemental page included to maintain realistic packet breadth and redundancy."],
                scanned=title in scanned_filler_titles,
            )
        else:
            page_num = note_page(
                doc,
                page_num,
                owner_name,
                owner_id,
                header,
                title,
                sections=[
                    ("Supplemental Detail", "bullets", [
                        f"Supplemental payer document {filler_idx + 1} retained in packet.",
                        "High-value details may appear in multiple payer records with slight wording variation.",
                        "This page supports realistic multi-document ingestion and summarization testing.",
                    ]),
                ],
                scanned=title in scanned_filler_titles,
                signature=(str(rec["care_manager"]), "Supplemental Record", f"2026-03-{(filler_idx % 28) + 1:02d} 13:{10 + (filler_idx % 40):02d}"),
            )
        filler_idx += 1

    save_packet_pdf(doc, out_pdf)
    payload = dict(rec)
    payload["packet_target_pages"] = target_pages
    payload["packet_generated_pages"] = len(doc.pages)
    payload["packet_type"] = "payer_long_form"
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def write_provider_packets(root: Path) -> None:
    out_dir = root / "Provider Synthetic Records"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: List[Dict[str, str]] = []
    for rec in make_provider_records():
        label = str(rec["record_label"]).lower()
        acuity_map = {
            "A": "moderate_acuity",
            "B": "high_acuity_revenue_impact",
            "C": "lower_acuity_gap_heavy",
        }
        stem = f"record_{label}_{acuity_map[str(rec['record_label'])]}"
        pdf_path = out_dir / f"{stem}.pdf"
        json_path = out_dir / f"{stem}.json"
        build_provider_packet(rec, pdf_path, json_path)
        manifest.append({
            "record": str(rec["record_label"]),
            "type": "provider",
            "pdf": str(pdf_path),
            "json": str(json_path),
        })
        print(f"Wrote provider PDF: {pdf_path}")
        print(f"Wrote provider JSON: {json_path}")
    with (out_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote provider manifest: {out_dir / 'manifest.json'}")


def write_payer_packets(root: Path) -> None:
    out_dir = root / "Payer Synthetic Records"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: List[Dict[str, str]] = []
    name_map = {
        "A": "high_risk_member",
        "B": "complex_polypharmacy_case",
        "C": "socially_complex_case",
    }
    for rec in make_payer_records():
        label = str(rec["record_label"]).lower()
        stem = f"record_{label}_{name_map[str(rec['record_label'])]}"
        pdf_path = out_dir / f"{stem}.pdf"
        json_path = out_dir / f"{stem}.json"
        build_payer_packet(rec, pdf_path, json_path)
        manifest.append({
            "record": str(rec["record_label"]),
            "type": "payer",
            "pdf": str(pdf_path),
            "json": str(json_path),
        })
        print(f"Wrote payer PDF: {pdf_path}")
        print(f"Wrote payer JSON: {json_path}")
    with (out_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote payer manifest: {out_dir / 'manifest.json'}")


def main() -> None:
    maybe_reexec_in_scan_env()
    root = Path(os.getcwd())
    write_provider_packets(root)
    write_payer_packets(root)


if __name__ == "__main__":
    main()
