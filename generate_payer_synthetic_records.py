#!/usr/bin/env python3
"""
Generate payer-use-case synthetic records for complex case clinical snapshots.

Outputs:
  ./Payer Synthetic Records/
    - record_a_*.pdf/json
    - record_b_*.pdf/json
    - record_c_*.pdf/json
    - manifest.json
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Sequence

from generate_synthetic_patient_pdf import (
    Canvas,
    PDFDocument,
    MARGIN,
    PAGE_H,
    PAGE_W,
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


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug


def render_member_demographics(doc: PDFDocument, rec: Dict[str, object], page_num: int) -> int:
    m = rec["member"]  # type: ignore[index]
    c = Canvas()
    page_chrome(
        c,
        f"Record {rec['record_label']} | {rec['risk_tier']} | Member Demographics",  # type: ignore[index]
        page_num,
        m["name"],  # type: ignore[index]
        m["member_id"],  # type: ignore[index]
    )
    y = PAGE_H - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Member Demographics")
    y = draw_kv_grid(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        [
            ("Record Label", str(rec["record_label"])),
            ("Risk Tier", str(rec["risk_tier"])),
            ("Theme", str(rec["theme"])),
            ("Insurance Type", str(m["insurance_type"])),
            ("Member Name", str(m["name"])),
            ("Member ID", str(m["member_id"])),
            ("Age", str(m["age"])),
            ("Gender", str(m["gender"])),
            ("PCP", str(m["pcp"])),
            ("Care Manager", str(rec["care_manager"])),
        ],
        cols=2,
        label_w=102,
    )
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Clinical Snapshot Intent")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 118, PAGE_W - 2 * MARGIN, 118, fill=False, stroke=True)
    paragraph_block(
        c,
        MARGIN + 8,
        y - 12,
        (
            f"Synthetic payer care-management record {rec['record_label']} for high-cost/high-need scenario review. "
            "All member demographics, providers, events, and costs are fictional and created for testing and demos."
        ),
        max_width=PAGE_W - 2 * MARGIN - 16,
        size=8.4,
        leading=11.2,
    )
    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_chronic_and_utilization(doc: PDFDocument, rec: Dict[str, object], page_num: int) -> int:
    m = rec["member"]  # type: ignore[index]
    c = Canvas()
    page_chrome(
        c,
        f"Record {rec['record_label']} | {rec['risk_tier']} | Conditions and Utilization",  # type: ignore[index]
        page_num,
        m["name"],  # type: ignore[index]
        m["member_id"],  # type: ignore[index]
    )
    y = PAGE_H - 92

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Chronic Conditions Summary")
    cond_rows = [[str(r["condition"]), str(r["status"]), str(r["impact"]), str(r["hcc"])] for r in rec["chronic_conditions"]]  # type: ignore[index]
    y = draw_table_checked(
        c,
        MARGIN,
        y,
        widths=[160, 90, 190, 100],
        headers=["Condition", "Status", "Clinical Impact", "HCC/Risk Flag"],
        rows=cond_rows,
        max_width=PAGE_W - 2 * MARGIN,
        row_h=19,
        header_h=21,
        font_size=7.8,
    )

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Hospitalizations and ED Visits (Last 6-12 Months)")
    util_rows = [
        [
            str(v["date"]),
            str(v["type"]),
            str(v["facility"]),
            str(v["reason"]),
            str(v["paid_amount"]),
        ]
        for v in rec["utilization_events"]  # type: ignore[index]
    ]
    y = draw_table_checked(
        c,
        MARGIN,
        y,
        widths=[72, 74, 120, 190, 84],
        headers=["Date", "Visit Type", "Facility", "Primary Reason", "Paid Amount"],
        rows=util_rows,
        max_width=PAGE_W - 2 * MARGIN,
        row_h=19,
        header_h=21,
        font_size=7.7,
    )

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Claims Cost Concentration")
    claim_rows = [
        [
            str(v["claim_month"]),
            str(v["claim_category"]),
            str(v["episodes"]),
            str(v["member_oop"]),
            str(v["plan_paid"]),
        ]
        for v in rec["claims_summary"]  # type: ignore[index]
    ]
    draw_table_checked(
        c,
        MARGIN,
        y,
        widths=[86, 170, 84, 84, 116],
        headers=["Month", "Claim Category", "Episodes", "Member OOP", "Plan Paid"],
        rows=claim_rows,
        max_width=PAGE_W - 2 * MARGIN,
        row_h=18,
        header_h=20,
        font_size=7.7,
    )

    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_medications(doc: PDFDocument, rec: Dict[str, object], page_num: int) -> int:
    m = rec["member"]  # type: ignore[index]
    meds = rec["medications"]  # type: ignore[index]
    c = Canvas()
    page_chrome(
        c,
        f"Record {rec['record_label']} | {rec['risk_tier']} | Medication Profile",  # type: ignore[index]
        page_num,
        m["name"],  # type: ignore[index]
        m["member_id"],  # type: ignore[index]
    )
    y = PAGE_H - 92
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Medication List")
    rows = [
        [
            str(v["medication"]),
            str(v["dose"]),
            str(v["class"]),
            str(v["schedule"]),
            str(v["risk_note"]),
        ]
        for v in meds
    ]
    y = draw_table_checked(
        c,
        MARGIN,
        y,
        widths=[122, 72, 104, 78, 164],
        headers=["Medication", "Dose", "Class", "Schedule", "Care-Management Concern"],
        rows=rows,
        max_width=PAGE_W - 2 * MARGIN,
        row_h=17,
        header_h=21,
        font_size=7.3,
    )

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Medication Risk Focus")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 106, PAGE_W - 2 * MARGIN, 106, fill=False, stroke=True)
    bullet_block(
        c,
        MARGIN + 8,
        y - 10,
        [str(v) for v in rec["medication_risk_focus"]],  # type: ignore[index]
        max_width=PAGE_W - 2 * MARGIN - 16,
        size=8.0,
        leading=10.5,
    )

    draw_signature_block(
        c,
        MARGIN + 8,
        48,
        250,
        str(rec["pharmacist_reviewer"]),
        "Pharmacy Review",
        str(rec["pharmacy_review_signed_at"]),
    )
    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_functional_and_social(doc: PDFDocument, rec: Dict[str, object], page_num: int) -> int:
    m = rec["member"]  # type: ignore[index]
    fn = rec["functional_assessment"]  # type: ignore[index]
    sf = rec["social_factors"]  # type: ignore[index]
    c = Canvas()
    page_chrome(
        c,
        f"Record {rec['record_label']} | {rec['risk_tier']} | Functional and SDOH",  # type: ignore[index]
        page_num,
        m["name"],  # type: ignore[index]
        m["member_id"],  # type: ignore[index]
    )
    y = PAGE_H - 92

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Functional Assessment Note")
    y = draw_kv_grid(
        c,
        MARGIN,
        y,
        PAGE_W - 2 * MARGIN,
        [
            ("Mobility", str(fn["mobility"])),
            ("DME Use", str(fn["dme_use"])),
            ("Oxygen Use", str(fn["oxygen_use"])),
            ("PT/OT Evaluation", str(fn["pt_ot_eval"])),
        ],
        cols=1,
        label_w=132,
    )
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 95, PAGE_W - 2 * MARGIN, 95, fill=False, stroke=True)
    c.text(MARGIN + 8, y - 12, "ADL Status", font="F2", size=8.4, color=(0.08, 0.08, 0.08))
    bullet_block(
        c,
        MARGIN + 8,
        y - 22,
        [str(v) for v in fn["adl_details"]],  # type: ignore[index]
        max_width=PAGE_W - 2 * MARGIN - 16,
        size=8.0,
    )

    y = y - 105
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Social Factors Note")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 128, PAGE_W - 2 * MARGIN, 128, fill=False, stroke=True)
    bullet_block(
        c,
        MARGIN + 8,
        y - 10,
        [str(v) for v in sf["findings"]],  # type: ignore[index]
        max_width=PAGE_W - 2 * MARGIN - 16,
        size=8.0,
        leading=10.2,
    )

    if rec.get("behavioral_health_note"):
        y2 = y - 138
        y2 = draw_section_header(c, MARGIN, y2, PAGE_W - 2 * MARGIN, "Behavioral Health Note")
        c.set_stroke(0.2, 0.2, 0.2)
        c.rect(MARGIN, y2 - 62, PAGE_W - 2 * MARGIN, 62, fill=False, stroke=True)
        paragraph_block(
            c,
            MARGIN + 8,
            y2 - 12,
            str(rec["behavioral_health_note"]),
            max_width=PAGE_W - 2 * MARGIN - 16,
            size=8.0,
            leading=10.2,
        )

    draw_signature_block(
        c,
        MARGIN + 8,
        48,
        250,
        str(rec["care_manager"]),
        "Care Management Note",
        str(rec["care_manager_signed_at"]),
    )
    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_care_management_snapshot(doc: PDFDocument, rec: Dict[str, object], page_num: int) -> int:
    m = rec["member"]  # type: ignore[index]
    c = Canvas()
    page_chrome(
        c,
        f"Record {rec['record_label']} | {rec['risk_tier']} | Complex Case Clinical Snapshot",  # type: ignore[index]
        page_num,
        m["name"],  # type: ignore[index]
        m["member_id"],  # type: ignore[index]
    )
    y = PAGE_H - 92

    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Care Management Risk Synopsis")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 118, PAGE_W - 2 * MARGIN, 118, fill=False, stroke=True)
    bullet_block(
        c,
        MARGIN + 8,
        y - 10,
        [str(v) for v in rec["snapshot_points"]],  # type: ignore[index]
        max_width=PAGE_W - 2 * MARGIN - 16,
        size=8.2,
        leading=10.6,
    )

    y = y - 128
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Interventions and Follow-up Plan")
    c.set_stroke(0.2, 0.2, 0.2)
    c.rect(MARGIN, y - 122, PAGE_W - 2 * MARGIN, 122, fill=False, stroke=True)
    bullet_block(
        c,
        MARGIN + 8,
        y - 10,
        [str(v) for v in rec["follow_up_plan"]],  # type: ignore[index]
        max_width=PAGE_W - 2 * MARGIN - 16,
        size=8.0,
        leading=10.2,
    )

    y = y - 132
    y = draw_section_header(c, MARGIN, y, PAGE_W - 2 * MARGIN, "Documentation / Risk Gaps")
    gap_rows = [[str(v["gap"]), str(v["impact"])] for v in rec["risk_gaps"]]  # type: ignore[index]
    draw_table_checked(
        c,
        MARGIN,
        y,
        widths=[220, 320],
        headers=["Gap Finding", "Payer Impact / Next Action"],
        rows=gap_rows,
        max_width=PAGE_W - 2 * MARGIN,
        row_h=21,
        header_h=21,
        font_size=7.8,
    )

    draw_signature_block(
        c,
        MARGIN + 8,
        48,
        260,
        str(rec["medical_director"]),
        "Medical Director Review",
        str(rec["medical_director_signed_at"]),
    )
    doc.add_page(c.to_bytes(), c.used_images)
    return page_num + 1


def render_record(rec: Dict[str, object], out_pdf: Path, out_json: Path) -> None:
    doc = PDFDocument()
    page_num = 1
    page_num = render_member_demographics(doc, rec, page_num)
    page_num = render_chronic_and_utilization(doc, rec, page_num)
    page_num = render_medications(doc, rec, page_num)
    page_num = render_functional_and_social(doc, rec, page_num)
    page_num = render_care_management_snapshot(doc, rec, page_num)
    _ = page_num
    doc.save(str(out_pdf))
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2)


def make_records() -> List[Dict[str, object]]:
    return [
        {
            "record_label": "A",
            "risk_tier": "High-Risk Member",
            "theme": "Frequent CHF exacerbations",
            "member": {
                "name": "Renee M. Caldwell",
                "member_id": "M-8301124",
                "age": "74",
                "gender": "Female",
                "insurance_type": "Medicare Advantage PPO",
                "pcp": "Harold Kim, MD",
            },
            "care_manager": "Sonia Patel, RN, CCM",
            "care_manager_signed_at": "2026-02-25 15:22",
            "medical_director": "Priya Raman, MD",
            "medical_director_signed_at": "2026-02-26 11:04",
            "pharmacist_reviewer": "Elena Russo, PharmD",
            "pharmacy_review_signed_at": "2026-02-25 17:31",
            "chronic_conditions": [
                {"condition": "Congestive heart failure", "status": "Active", "impact": "Frequent volume overload and readmission risk", "hcc": "HCC 85"},
                {"condition": "COPD", "status": "Active", "impact": "Dyspnea overlap with CHF symptoms", "hcc": "HCC 111"},
                {"condition": "CKD stage 3", "status": "Active", "impact": "Diuretic dosing and renal monitoring complexity", "hcc": "HCC 137"},
                {"condition": "Type 2 diabetes mellitus", "status": "Active", "impact": "Glycemic variability with admissions", "hcc": "HCC 37"},
                {"condition": "Hypertension", "status": "Active", "impact": "Contributes to HF progression", "hcc": "Non-HCC"},
            ],
            "utilization_events": [
                {"date": "2025-11-12", "type": "Inpatient", "facility": "Community General", "reason": "Acute CHF exacerbation", "paid_amount": "$28,420"},
                {"date": "2026-01-04", "type": "Inpatient", "facility": "Community General", "reason": "CHF + fluid overload", "paid_amount": "$24,910"},
                {"date": "2026-02-10", "type": "ED", "facility": "Community General ED", "reason": "Shortness of breath", "paid_amount": "$2,680"},
            ],
            "claims_summary": [
                {"claim_month": "2025-11", "claim_category": "Inpatient facility", "episodes": "1", "member_oop": "$310", "plan_paid": "$23,940"},
                {"claim_month": "2026-01", "claim_category": "Inpatient facility", "episodes": "1", "member_oop": "$280", "plan_paid": "$20,670"},
                {"claim_month": "2026-02", "claim_category": "Emergency services", "episodes": "1", "member_oop": "$95", "plan_paid": "$2,410"},
                {"claim_month": "2026-02", "claim_category": "Outpatient cardiology", "episodes": "0 completed", "member_oop": "$0", "plan_paid": "$0"},
            ],
            "medications": [
                {"medication": "Insulin glargine", "dose": "22 units", "class": "Insulin", "schedule": "QHS", "risk_note": "Hypoglycemia risk; monitor fasting glucose"},
                {"medication": "Apixaban", "dose": "5 mg", "class": "Anticoagulant", "schedule": "BID", "risk_note": "Bleeding risk with falls"},
                {"medication": "Carvedilol", "dose": "12.5 mg", "class": "Beta blocker", "schedule": "BID", "risk_note": "May mask hypoglycemia symptoms"},
                {"medication": "Furosemide", "dose": "40 mg", "class": "Diuretic", "schedule": "BID", "risk_note": "Renal function and potassium monitoring"},
                {"medication": "Spironolactone", "dose": "25 mg", "class": "Diuretic", "schedule": "Daily", "risk_note": "Hyperkalemia risk"},
                {"medication": "Losartan", "dose": "50 mg", "class": "ARB", "schedule": "Daily", "risk_note": "Hypotension and AKI risk"},
                {"medication": "Rosuvastatin", "dose": "20 mg", "class": "Statin", "schedule": "Nightly", "risk_note": "Myalgias; adherence variable"},
                {"medication": "Empagliflozin", "dose": "10 mg", "class": "SGLT2", "schedule": "Daily", "risk_note": "Volume depletion concern with diuresis"},
                {"medication": "Aspirin", "dose": "81 mg", "class": "Antiplatelet", "schedule": "Daily", "risk_note": "Dual antithrombotic exposure"},
                {"medication": "Albuterol inhaler", "dose": "2 puffs", "class": "Bronchodilator", "schedule": "PRN", "risk_note": "Frequent refill suggests poor control"},
                {"medication": "Tiotropium", "dose": "18 mcg", "class": "LAMA", "schedule": "Daily", "risk_note": "Technique adherence needed"},
                {"medication": "Potassium chloride", "dose": "20 mEq", "class": "Electrolyte", "schedule": "Daily", "risk_note": "Dose tied to diuretic changes"},
                {"medication": "Hydrocodone/APAP", "dose": "5/325 mg", "class": "Opioid PRN", "schedule": "Q8h PRN", "risk_note": "Sedation and constipation risk"},
            ],
            "medication_risk_focus": [
                "Polypharmacy count: 13 active medications with multiple high-risk interactions.",
                "Insulin + variable intake after admissions increases hypoglycemia risk.",
                "Anticoagulant + aspirin combination requires bleed-risk counseling.",
                "Opioid PRN identified; monitor daytime sedation and fall risk.",
            ],
            "functional_assessment": {
                "mobility": "Ambulates short household distances with rolling walker",
                "dme_use": "Rolling walker, shower bench, home scale",
                "oxygen_use": "Home oxygen 2 L/min nocturnal and exertional",
                "pt_ot_eval": "No new PT referral completed during last 30 days",
                "adl_details": [
                    "Independent with feeding and basic grooming.",
                    "Needs standby help for bathing and lower-body dressing on bad days.",
                    "Requires frequent rest breaks due to dyspnea.",
                ],
            },
            "social_factors": {
                "findings": [
                    "Missed cardiology follow-up on 2026-02-18 due to transportation failure.",
                    "Reports financial strain with inhaler copays and oxygen supplies.",
                    "Former smoker with occasional relapse (2-3 cigarettes/week).",
                    "Lives with spouse who has limited ability to assist with transfers.",
                    "Limited support available for complex medication and appointment management.",
                    "Two missed appointments in last 60 days related to ride availability.",
                ]
            },
            "snapshot_points": [
                "Meets high-risk criteria: 2 CHF hospitalizations in 90 days and recent ED SOB visit.",
                "High claim concentration in inpatient cardiac episodes over last 4 months.",
                "Home oxygen and polypharmacy increase readmission vulnerability.",
                "Care gap: missed cardiology appointment delayed medication optimization.",
            ],
            "follow_up_plan": [
                "Schedule urgent cardiology follow-up and arrange plan-sponsored transportation.",
                "Weekly nurse call for weight/symptom check for 30 days.",
                "Pharmacy sync and blister-pack option review to reduce regimen errors.",
                "Assess eligibility for home-based heart-failure program.",
            ],
            "risk_gaps": [
                {"gap": "Missed specialty follow-up after CHF admission", "impact": "High readmission risk; escalate outreach within 48 hours"},
                {"gap": "Inconsistent oxygen and inhaler refill timing", "impact": "Potential avoidable ED use; coordinate respiratory vendor"},
            ],
        },
        {
            "record_label": "B",
            "risk_tier": "Complex Polypharmacy Case",
            "theme": "Diabetes complications + medication risk",
            "member": {
                "name": "Gerald T. Norris",
                "member_id": "M-9015560",
                "age": "67",
                "gender": "Male",
                "insurance_type": "Dual-Eligible Special Needs Plan",
                "pcp": "Nina Patel, MD",
            },
            "care_manager": "Lena Ortiz, RN, CCM",
            "care_manager_signed_at": "2026-02-24 13:16",
            "medical_director": "Aaron Feldman, MD",
            "medical_director_signed_at": "2026-02-24 16:42",
            "pharmacist_reviewer": "Thomas Reeves, PharmD",
            "pharmacy_review_signed_at": "2026-02-24 15:58",
            "chronic_conditions": [
                {"condition": "Type 2 diabetes with neuropathy", "status": "Active", "impact": "Labile glucose; hypoglycemia admissions", "hcc": "HCC 37"},
                {"condition": "CKD stage 4", "status": "Active", "impact": "High risk medication dosing complexity", "hcc": "HCC 136"},
                {"condition": "Congestive heart failure", "status": "Active", "impact": "Fluid status and med balancing challenges", "hcc": "HCC 85"},
                {"condition": "COPD", "status": "Active", "impact": "Increases exacerbation and ED risk", "hcc": "HCC 111"},
                {"condition": "Hypertension", "status": "Active", "impact": "Target control often unmet", "hcc": "Non-HCC"},
                {"condition": "Depression (major depressive disorder)", "status": "Active", "impact": "Contributes to poor adherence", "hcc": "HCC 59"},
            ],
            "utilization_events": [
                {"date": "2025-09-22", "type": "Inpatient", "facility": "Community General", "reason": "Hyperglycemia with dehydration", "paid_amount": "$19,860"},
                {"date": "2026-01-15", "type": "ED", "facility": "Community General ED", "reason": "Hypoglycemia episode", "paid_amount": "$2,140"},
                {"date": "2026-02-03", "type": "Inpatient", "facility": "Community General", "reason": "AKI on CKD stage 4", "paid_amount": "$26,330"},
            ],
            "claims_summary": [
                {"claim_month": "2025-09", "claim_category": "Inpatient medical", "episodes": "1", "member_oop": "$190", "plan_paid": "$16,480"},
                {"claim_month": "2026-01", "claim_category": "Emergency services", "episodes": "1", "member_oop": "$80", "plan_paid": "$1,940"},
                {"claim_month": "2026-02", "claim_category": "Inpatient renal", "episodes": "1", "member_oop": "$240", "plan_paid": "$21,700"},
                {"claim_month": "2026-02", "claim_category": "Pharmacy high-risk", "episodes": "15 meds", "member_oop": "$220", "plan_paid": "$3,860"},
            ],
            "medications": [
                {"medication": "Insulin glargine", "dose": "28 units", "class": "Insulin", "schedule": "QHS", "risk_note": "Nocturnal hypoglycemia risk"},
                {"medication": "Insulin lispro", "dose": "Sliding scale", "class": "Insulin", "schedule": "TID AC", "risk_note": "Missed meals create mismatch risk"},
                {"medication": "Warfarin", "dose": "4 mg", "class": "Anticoagulant", "schedule": "Daily", "risk_note": "INR instability and bleed risk"},
                {"medication": "Metoprolol succinate", "dose": "50 mg", "class": "Beta blocker", "schedule": "Daily", "risk_note": "Can mask adrenergic hypoglycemia signs"},
                {"medication": "Torsemide", "dose": "20 mg", "class": "Diuretic", "schedule": "Daily", "risk_note": "AKI risk in CKD stage 4"},
                {"medication": "Spironolactone", "dose": "25 mg", "class": "Diuretic", "schedule": "Daily", "risk_note": "Hyperkalemia monitoring needed"},
                {"medication": "Hydralazine", "dose": "25 mg", "class": "Vasodilator", "schedule": "TID", "risk_note": "Adherence burden (TID dosing)"},
                {"medication": "Isosorbide mononitrate", "dose": "30 mg", "class": "Nitrate", "schedule": "Daily", "risk_note": "Headache leads to skipped doses"},
                {"medication": "Atorvastatin", "dose": "40 mg", "class": "Statin", "schedule": "Nightly", "risk_note": "Multiple refill gaps"},
                {"medication": "Gabapentin", "dose": "300 mg", "class": "Neuropathic pain", "schedule": "TID", "risk_note": "Sedation and duplicate therapy concern"},
                {"medication": "Sertraline", "dose": "100 mg", "class": "SSRI", "schedule": "Daily", "risk_note": "Behavioral health continuity needed"},
                {"medication": "Budesonide/formoterol", "dose": "160/4.5", "class": "ICS/LABA", "schedule": "BID", "risk_note": "Inhaler adherence inconsistent"},
                {"medication": "Tiotropium", "dose": "18 mcg", "class": "LAMA", "schedule": "Daily", "risk_note": "Technique reinforcement needed"},
                {"medication": "Aspirin", "dose": "81 mg", "class": "Antiplatelet", "schedule": "Daily", "risk_note": "Added bleed risk with warfarin"},
                {"medication": "Pantoprazole", "dose": "40 mg", "class": "PPI", "schedule": "Daily", "risk_note": "Low-value continuation without review"},
            ],
            "medication_risk_focus": [
                "Medication count: 15 active agents with high interaction burden.",
                "Warfarin + aspirin + CKD stage 4 creates elevated adverse event risk.",
                "Insulin complexity plus missed meals linked to recent hypoglycemia ED visit.",
                "Medication adherence concerns documented by fill-history gaps and member report.",
            ],
            "functional_assessment": {
                "mobility": "Ambulates with single-point cane; fatigues after one block",
                "dme_use": "Cane, pill organizer, glucometer",
                "oxygen_use": "No chronic oxygen",
                "pt_ot_eval": "No active PT order",
                "adl_details": [
                    "Independent in basic ADLs but slow transfers and fatigue with stairs.",
                    "Needs help organizing weekly medications.",
                    "Self-manages glucose checks with occasional missed bedtime checks.",
                ],
            },
            "social_factors": {
                "findings": [
                    "Lives alone in second-floor apartment; limited family support.",
                    "Missed two nephrology appointments due to transportation and forgetfulness.",
                    "Reports occasional inability to afford all copays before month-end.",
                    "Financial difficulty affects adherence to warfarin monitoring and insulin supplies.",
                    "Current smoker (0.5 pack/day).",
                    "Medication adherence barriers include complex schedule and mood symptoms.",
                ]
            },
            "behavioral_health_note": (
                "Behavioral health care manager documented persistent depressive symptoms, poor sleep, and low motivation. "
                "Member agreed to virtual counseling referral and weekly adherence check-ins."
            ),
            "snapshot_points": [
                "Complex polypharmacy profile with 15 medications including insulin and warfarin.",
                "High-cost CKD stage 4 and diabetes complications drive avoidable utilization risk.",
                "Recent hypoglycemia ED event likely associated with insulin and meal inconsistency.",
                "Lives alone with adherence and behavioral health barriers.",
            ],
            "follow_up_plan": [
                "Initiate pharmacist-led medication reconciliation every 2 weeks for 60 days.",
                "Arrange home-delivery pharmacy and synchronized refill dates.",
                "Behavioral health follow-up plus depression screening at PCP visit.",
                "Provide transportation assistance for nephrology and diabetes clinic appointments.",
            ],
            "risk_gaps": [
                {"gap": "Medication adherence gaps in high-risk regimen", "impact": "Drives ED use and adverse drug events; escalate medication coaching"},
                {"gap": "Behavioral health symptoms affecting self-management", "impact": "Include integrated BH plan in care-management outreach"},
            ],
        },
        {
            "record_label": "C",
            "risk_tier": "Socially Complex Case",
            "theme": "Moderate clinical risk with high SDOH burden",
            "member": {
                "name": "Tanya L. Bishop",
                "member_id": "M-7710935",
                "age": "58",
                "gender": "Female",
                "insurance_type": "Marketplace Silver HMO",
                "pcp": "Leah Morgan, MD",
            },
            "care_manager": "Maya Chen, RN, CCM",
            "care_manager_signed_at": "2026-02-20 14:12",
            "medical_director": "Harold Kim, MD",
            "medical_director_signed_at": "2026-02-21 09:55",
            "pharmacist_reviewer": "Jordan Lee, PharmD",
            "pharmacy_review_signed_at": "2026-02-20 17:02",
            "chronic_conditions": [
                {"condition": "Congestive heart failure", "status": "Active", "impact": "Intermittent edema and fatigue", "hcc": "HCC 85"},
                {"condition": "Type 2 diabetes mellitus", "status": "Active", "impact": "A1c above target with refill gaps", "hcc": "HCC 37"},
                {"condition": "CKD stage 3", "status": "Active", "impact": "Requires renal dosing consideration", "hcc": "HCC 137"},
                {"condition": "Hypertension", "status": "Active", "impact": "Periodic uncontrolled readings", "hcc": "Non-HCC"},
                {"condition": "Depression", "status": "Active", "impact": "Reduced self-management capacity", "hcc": "HCC 59"},
                {"condition": "COPD (mild)", "status": "Active", "impact": "Exertional dyspnea with smoking exposure", "hcc": "HCC 111"},
            ],
            "utilization_events": [
                {"date": "2025-10-19", "type": "Inpatient", "facility": "Community General", "reason": "Volume overload and dyspnea", "paid_amount": "$17,440"},
                {"date": "2026-01-28", "type": "ED", "facility": "Community General ED", "reason": "Medication lapse and dizziness", "paid_amount": "$1,980"},
            ],
            "claims_summary": [
                {"claim_month": "2025-10", "claim_category": "Inpatient medical", "episodes": "1", "member_oop": "$260", "plan_paid": "$14,210"},
                {"claim_month": "2026-01", "claim_category": "Emergency services", "episodes": "1", "member_oop": "$70", "plan_paid": "$1,760"},
                {"claim_month": "2026-02", "claim_category": "Outpatient PT eval", "episodes": "1", "member_oop": "$25", "plan_paid": "$320"},
                {"claim_month": "2026-02", "claim_category": "Pharmacy", "episodes": "9 meds", "member_oop": "$165", "plan_paid": "$1,040"},
            ],
            "medications": [
                {"medication": "Insulin degludec", "dose": "18 units", "class": "Insulin", "schedule": "QHS", "risk_note": "Refill timing inconsistent"},
                {"medication": "Rivaroxaban", "dose": "20 mg", "class": "Anticoagulant", "schedule": "Daily", "risk_note": "Missed doses reported"},
                {"medication": "Metoprolol tartrate", "dose": "25 mg", "class": "Beta blocker", "schedule": "BID", "risk_note": "Occasional missed evening dose"},
                {"medication": "Furosemide", "dose": "40 mg", "class": "Diuretic", "schedule": "Daily", "risk_note": "Skipped on travel days due bathroom access"},
                {"medication": "Losartan", "dose": "50 mg", "class": "ARB", "schedule": "Daily", "risk_note": "Cost-related intermittent nonadherence"},
                {"medication": "Sertraline", "dose": "50 mg", "class": "SSRI", "schedule": "Daily", "risk_note": "Depression symptoms persist"},
                {"medication": "Albuterol inhaler", "dose": "2 puffs", "class": "Bronchodilator", "schedule": "PRN", "risk_note": "Frequent use during smoking periods"},
                {"medication": "Budesonide/formoterol", "dose": "160/4.5", "class": "ICS/LABA", "schedule": "BID", "risk_note": "Technique reviewed at PT visit"},
                {"medication": "Atorvastatin", "dose": "20 mg", "class": "Statin", "schedule": "Nightly", "risk_note": "Often delayed refill by 1 week"},
            ],
            "medication_risk_focus": [
                "Moderate medication burden but high SDOH-driven adherence risk.",
                "Financial hardship linked to delayed refill pickup for insulin and ARB.",
                "Smoking contributes to COPD symptoms and rescue inhaler overuse.",
            ],
            "functional_assessment": {
                "mobility": "Independent household ambulation; reduced endurance in community",
                "dme_use": "No routine DME, occasional borrowed cane during flares",
                "oxygen_use": "No chronic oxygen",
                "pt_ot_eval": "PT evaluation completed 2026-02-12 for deconditioning",
                "adl_details": [
                    "Independent in basic ADLs.",
                    "IADL challenges: shopping and pharmacy pickup when transportation unavailable.",
                    "PT noted reduced lower-extremity endurance and recommended home exercise plan.",
                ],
            },
            "social_factors": {
                "findings": [
                    "Limited transportation (bus-dependent, missed last-mile rides).",
                    "Financial medication hardship documented at pharmacy outreach call.",
                    "Current smoker (approximately 1 pack every 3 days).",
                    "Lives alone with minimal nearby support network.",
                    "Missed appointments tied to transportation and work-hour conflicts.",
                ]
            },
            "snapshot_points": [
                "Lower clinical acuity than Records A/B but high social complexity burden.",
                "One recent hospitalization and one ED visit with avoidable drivers.",
                "Depression, smoking, and transportation barriers increase longitudinal risk.",
                "PT evaluation supports deconditioning concern and fall-prevention planning.",
            ],
            "follow_up_plan": [
                "Enroll member in transportation benefit reminder workflow.",
                "Apply copay assistance pathway for insulin and key cardiovascular meds.",
                "Smoking cessation referral plus depression follow-up through PCP.",
                "Reinforce PT home exercise plan and schedule reassessment in 6 weeks.",
            ],
            "risk_gaps": [
                {"gap": "Transportation instability causing missed care", "impact": "High no-show risk; trigger non-emergency transport support"},
                {"gap": "Medication affordability barriers", "impact": "Potential decompensation; prioritize financial assistance intervention"},
            ],
        },
    ]


def main() -> None:
    root = Path(os.getcwd())
    out_dir = root / "Payer Synthetic Records"
    out_dir.mkdir(parents=True, exist_ok=True)

    records = make_records()
    manifest: List[Dict[str, str]] = []
    for rec in records:
        label = str(rec["record_label"]).lower()
        tier_slug = slugify(str(rec["risk_tier"]))
        stem = f"record_{label}_{tier_slug}"
        pdf_path = out_dir / f"{stem}.pdf"
        json_path = out_dir / f"{stem}.json"
        render_record(rec, pdf_path, json_path)
        manifest.append(
            {
                "record": str(rec["record_label"]),
                "risk_tier": str(rec["risk_tier"]),
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
