#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from generate_long_form_packets import (
    image_report_page,
    maybe_reexec_in_scan_env,
    note_page,
    save_packet_pdf,
    table_page,
)
from generate_synthetic_patient_pdf import PDFDocument


PATIENT: Dict[str, str] = {
    "name": "Jane Doe",
    "dob": "04/15/1982",
    "age": "41",
    "member_id": "DXZ8887304",
    "claim_id": "9872304",
    "payer": "HealthPlus Insurance",
    "provider": "Mercy Hospital",
    "attending": "Dr. Emily Roberts",
    "appeal_submission_date": "08/15/2023",
    "appeal_id": "A-1001",
    "service_requested": "CPT 72148 MRI lumbar spine without contrast",
    "dx_1": "M54.16 Lumbar radiculopathy, lumbar region",
    "dx_2": "M51.26 Other intervertebral disc displacement, lumbar region",
}


def build_pt_visit_rows() -> List[List[str]]:
    return [
        ["1", "06/26", "Initial evaluation + HEP", "8/10", "Severe disability; ODI 52%"],
        ["2", "06/29", "Core stabilization / traction", "8/10", "Persistent left leg numbness"],
        ["3", "07/03", "Neural mobilization", "7/10", "Minimal short-term relief"],
        ["4", "07/06", "Manual therapy + HEP review", "7/10", "Sitting tolerance still limited"],
        ["5", "07/10", "Progress reassessment", "7/10", "ODI 48%; minimal functional gain"],
        ["6", "07/13", "Traction / progressive core", "7/10", "Radicular pain persists"],
        ["7", "07/17", "Manual + neuromuscular re-ed", "8/10", "Pain rebound after activity"],
        ["8", "07/20", "Neural glide progression", "8/10", "Left calf tingling ongoing"],
        ["9", "07/24", "Week-4 reassessment", "8/10", "SLR worsened to 30 deg; ODI 50%"],
        ["10", "07/27", "Lumbar stabilization", "8/10", "No sustained progress"],
        ["11", "08/01", "HEP compliance check", "8/10", "Weakness persists despite adherence"],
        ["12", "08/07", "Discharge reassessment", "8-9/10", "ODI 56%; progressive neurologic deficit"],
    ]


def build_record_templates() -> Sequence[Dict[str, object]]:
    return [
        {
            "record_label": "A",
            "title": "Failed Conservative Care With Progressive Deficits",
            "chronology_rows": [
                ["05/22/2023", "Mercy PCP", "Initial low back pain + left leg radiation", "Outpatient", "NSAID + PT referral"],
                ["06/05/2023", "Mercy Imaging", "Lumbar CT (soft tissue limitation)", "Diagnostic", "Possible disc protrusion"],
                ["06/26/2023", "Mercy PT", "PT start: severe disability ODI 52%", "Therapy", "2x/week x 6 weeks"],
                ["07/18/2023", "Spine Clinic", "Persistent radicular pain despite therapy", "Consult", "Injection + continue PT"],
                ["08/03/2023", "Neurology", "Progressive weakness and reflex changes", "Consult", "Urgent MRI advised"],
                ["08/07/2023", "Mercy PT", "Discharge: ODI 56%, strength down to 3+/5", "Therapy", "Failed conservative care"],
            ],
            "office_note": [
                "Three-month history of low back pain radiating to left posterior leg with nightly sleep disruption.",
                "Symptoms now limit sitting to less than 15 minutes and impair work participation.",
                "Home exercise program compliance confirmed; no sustained symptom control.",
            ],
            "consult_note": [
                "Positive straight-leg raise on left with reproducible radicular pattern.",
                "Reduced left lower-extremity strength and diminished Achilles reflex documented serially.",
                "Clinical concern for progressive nerve-root compression despite non-operative treatment.",
            ],
            "exam_rows": [
                ["06/20", "8/10", "35 deg", "4-/5", "Decreased", "Calf/foot paresthesia", "<15 min"],
                ["07/10", "7/10", "35 deg", "4-/5", "Decreased", "Persistent tingling", "<15 min"],
                ["07/24", "8/10", "30 deg", "4-/5", "Decreased", "Numbness worsening", "<12 min"],
                ["08/03", "8/10", "28 deg", "3+/5", "Diminished", "Dermatomal sensory loss", "<10 min"],
                ["08/07", "8-9/10", "25 deg", "3+/5", "Diminished", "Persistent numbness", "<10 min"],
            ],
            "med_rows": [
                ["Naproxen", "500 mg BID", "05/22/2023", "Trialed 6 weeks", "Insufficient pain control"],
                ["Gabapentin", "300 mg TID", "06/01/2023", "Dose escalated", "Persistent neuropathic pain"],
                ["Cyclobenzaprine", "10 mg HS", "06/08/2023", "Used PRN at night", "Sleep disturbance persists"],
                ["Methylpred dose pack", "Taper", "06/30/2023", "Completed", "Temporary mild benefit only"],
                ["Tramadol", "50 mg q8h PRN", "07/21/2023", "Intermittent rescue", "Pain rebounds with sitting"],
                ["Topical lidocaine", "5% patch", "07/25/2023", "Adjunctive", "No meaningful functional gain"],
            ],
            "injection_rows": [
                ["07/18/2023", "L4-L5 transforaminal ESI", "PM&R", "Pain 8/10 -> 6/10 for 48h", "Relief not durable"],
                ["07/31/2023", "Trigger-point lumbar paraspinal", "Pain Clinic", "Minimal transient response", "No functional change"],
            ],
            "necessity_points": [
                "Documented persistent radicular pain for >3 months with progressive neurologic deficits.",
                "Completed compliant conservative management including medications, PT, and injection therapy.",
                "Serial exams show worsening strength (4-/5 to 3+/5) and persistent reflex abnormality.",
                "PT outcomes worsened (ODI 52% to 56%) despite 12 supervised visits and home program adherence.",
                "Lumbar MRI is required to define nerve-root compression severity and guide definitive management.",
            ],
            "criteria_rows": [
                ["Persistent severe radicular pain", "Documented at office, consult, PT, and reassessment visits"],
                ["Neurologic deficit progression", "Strength decline + reflex change + dermatomal sensory findings"],
                ["Failed 6+ weeks conservative treatment", "12 PT visits, medication trials, injection history"],
                ["Need for treatment planning", "Neurology and spine consult recommend MRI for next-step intervention"],
            ],
            "addendum": "Given progressive weakness and failed conservative care, lumbar MRI remains medically necessary and time-sensitive.",
        },
        {
            "record_label": "B",
            "title": "Escalating Radiculopathy With ED/EMG Correlation",
            "chronology_rows": [
                ["05/24/2023", "Mercy PCP", "Severe low-back pain with left sciatica", "Outpatient", "NSAID + neuropathic agent"],
                ["06/06/2023", "Mercy Imaging", "Lumbar CT with concern for L4-L5 protrusion", "Diagnostic", "MRI advised if deficits progress"],
                ["06/26/2023", "Mercy PT", "Structured PT initiated", "Therapy", "12-visit protocol"],
                ["07/25/2023", "Pain Management", "Second injection after failed first response", "Procedure", "No durable benefit"],
                ["08/09/2023", "Mercy ED", "Acute pain flare with leg weakness", "ED Visit", "Urgent specialty follow-up"],
                ["08/10/2023", "Neurodiagnostics", "EMG/NCS consistent with left L5 radiculopathy", "Diagnostic", "MRI reaffirmed"],
            ],
            "office_note": [
                "Persistent left-sided radicular pain now associated with episodic gait instability.",
                "Patient reports near-falls due to left leg weakness and numbness below the knee.",
                "Unable to tolerate prolonged sitting or driving; work duties substantially limited.",
            ],
            "consult_note": [
                "Neurology confirms objective weakness and left-sided reflex diminution.",
                "EMG supports active L5 radiculopathy and ongoing nerve irritation.",
                "Advanced imaging indicated to characterize structural etiology and avoid further neurologic decline.",
            ],
            "exam_rows": [
                ["06/20", "8/10", "38 deg", "4/5", "Decreased", "Lateral calf paresthesia", "<20 min"],
                ["07/10", "7/10", "34 deg", "4-/5", "Decreased", "Intermittent foot numbness", "<15 min"],
                ["07/24", "8/10", "30 deg", "4-/5", "Diminished", "Persistent numbness", "<12 min"],
                ["08/09", "9/10", "26 deg", "3+/5", "Diminished", "Foot dorsum sensory loss", "<10 min"],
                ["08/10", "8-9/10", "25 deg", "3+/5", "Diminished", "EMG-correlated deficits", "<10 min"],
            ],
            "med_rows": [
                ["Ibuprofen", "800 mg TID", "05/24/2023", "Initial course", "Limited benefit"],
                ["Gabapentin", "300->600 mg TID", "06/02/2023", "Escalated dose", "Persistent neuropathic pain"],
                ["Cyclobenzaprine", "10 mg HS PRN", "06/08/2023", "Night use", "No sustained sleep improvement"],
                ["Prednisone taper", "Short course", "06/29/2023", "Completed", "Brief pain reduction only"],
                ["Tramadol", "50 mg q6h PRN", "07/26/2023", "Used for flares", "Frequent breakthrough pain"],
                ["Diclofenac topical", "1% gel", "07/27/2023", "Adjunctive", "Minimal added value"],
            ],
            "injection_rows": [
                ["07/07/2023", "L4-L5 transforaminal ESI", "Pain Management", "Transient improvement for ~2 days", "Symptoms recurred rapidly"],
                ["07/25/2023", "Interlaminar ESI", "Pain Management", "No clinically meaningful improvement", "Failed second intervention"],
            ],
            "necessity_points": [
                "Pain and neurologic symptoms escalated despite multimodal conservative management.",
                "Objective progression documented across PT, consult, and ED encounters.",
                "EMG/NCS corroborates left L5 radiculopathy, increasing urgency for structural clarification.",
                "Two injection attempts and medication optimization failed to restore function.",
                "Lumbar MRI is necessary to identify compressive pathology and determine procedural/surgical options.",
            ],
            "criteria_rows": [
                ["Clinical progression despite treatment", "Persistent severe pain + worsening weakness after PT/meds/injections"],
                ["Objective neurologic abnormalities", "Diminished Achilles reflex, positive SLR, reduced motor strength"],
                ["Supporting diagnostic correlation", "EMG/NCS confirms radiculopathy requiring anatomic imaging"],
                ["Decision-impact imaging need", "MRI required for definitive treatment planning"],
            ],
            "addendum": "The addition of ED escalation and EMG-confirmed radiculopathy supports urgent approval of lumbar MRI.",
        },
        {
            "record_label": "C",
            "title": "Functional Decline With Surgical Planning Requirement",
            "chronology_rows": [
                ["05/23/2023", "Mercy PCP", "Persistent lumbar pain + left radicular features", "Outpatient", "Medication + PT ordered"],
                ["06/04/2023", "Mercy Imaging", "Lumbar CT suggests disc pathology", "Diagnostic", "Soft-tissue detail limited"],
                ["06/26/2023", "Mercy PT", "Conservative PT started", "Therapy", "2x/week for 6 weeks"],
                ["07/24/2023", "Spine Surgery Consult", "Progressive deficits despite PT", "Consult", "MRI needed for surgical planning"],
                ["08/07/2023", "Mercy PT", "Discharge with worsening disability metrics", "Therapy", "Failed conservative approach"],
                ["08/14/2023", "Mercy Follow-up", "Appeal packet assembled for denied MRI", "Care Coordination", "Urgent reconsideration requested"],
            ],
            "office_note": [
                "Low-back pain with left leg radiation has progressed despite medication adherence and supervised PT.",
                "Functional ability declined: reduced sitting tolerance, disturbed sleep, and impaired daily activities.",
                "Patient reports inability to complete regular work shifts due to pain and weakness progression.",
            ],
            "consult_note": [
                "Spine surgery consult identifies possible operative candidacy pending anatomic confirmation.",
                "Current CT is insufficient for nerve-root and soft tissue characterization needed for planning.",
                "MRI required to determine operative vs. continued interventional pathway.",
            ],
            "exam_rows": [
                ["06/20", "8/10", "36 deg", "4-/5", "Decreased", "Calf/foot tingling", "<15 min"],
                ["07/10", "7/10", "34 deg", "4-/5", "Decreased", "Persistent numbness", "<15 min"],
                ["07/24", "8/10", "30 deg", "4-/5", "Diminished", "Foot numbness", "<12 min"],
                ["08/07", "8-9/10", "25 deg", "3+/5", "Diminished", "Progressive sensory deficits", "<10 min"],
                ["08/14", "8-9/10", "24 deg", "3+/5", "Diminished", "Unchanged neurologic deficit", "<10 min"],
            ],
            "med_rows": [
                ["Meloxicam", "15 mg daily", "05/23/2023", "Baseline anti-inflammatory", "Pain remains severe"],
                ["Gabapentin", "300 mg TID", "06/01/2023", "Neuropathic regimen", "Persistent paresthesias"],
                ["Cyclobenzaprine", "10 mg HS", "06/07/2023", "Muscle spasm management", "Limited sleep benefit"],
                ["Prednisone taper", "Short course", "06/29/2023", "Completed", "Temporary relief only"],
                ["Hydrocodone/APAP", "5/325 mg PRN", "07/28/2023", "Short rescue course", "No functional restoration"],
                ["Lidocaine patch", "5% daily PRN", "07/30/2023", "Adjunctive", "No sustained benefit"],
            ],
            "injection_rows": [
                ["07/14/2023", "L4-L5 transforaminal ESI", "Pain Clinic", "Mild relief for <72h", "Symptoms returned"],
                ["08/01/2023", "Facet joint injection", "Pain Clinic", "No durable benefit", "Did not improve function"],
            ],
            "necessity_points": [
                "Functional decline and worsening neurologic findings persist after complete conservative pathway.",
                "Conservative modalities included PT, medications, and injections over >6 weeks without durable improvement.",
                "Updated MRI is required for surgical/interventional treatment planning due to CT limitations.",
                "Delayed MRI risks further neurologic compromise and continued disability escalation.",
            ],
            "criteria_rows": [
                ["Conservative failure duration", "Documented >6 weeks supervised PT + med/injection trials"],
                ["Progressive neurologic signs", "Serial motor/reflex/sensory decline despite treatment"],
                ["Impact on function", "ODI worsened; sitting tolerance and ADL capacity deteriorated"],
                ["Need for definitive planning", "Surgical consult requires MRI-level soft tissue detail"],
            ],
            "addendum": "Given surgical planning needs and objective decline, lumbar MRI is medically necessary and should be authorized.",
        },
    ]


def build_appeal_packet(rec: Dict[str, object], out_pdf: Path, out_json: Path) -> None:
    doc = PDFDocument()
    doc._scan_targets = []
    page_num = 1
    header = f"Record {rec['record_label']} | Lumbar MRI Appeal Evidence Packet"
    owner_name = PATIENT["name"]
    owner_id = PATIENT["member_id"]

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Appeal Evidence Face Sheet",
        meta_pairs=[
            ("Record Label", str(rec["record_label"])),
            ("Scenario", str(rec["title"])),
            ("Patient", PATIENT["name"]),
            ("DOB", PATIENT["dob"]),
            ("Age", PATIENT["age"]),
            ("Member ID", PATIENT["member_id"]),
            ("Claim ID", PATIENT["claim_id"]),
            ("Payer", PATIENT["payer"]),
            ("Provider", PATIENT["provider"]),
            ("Attending", PATIENT["attending"]),
            ("Appeal Date", PATIENT["appeal_submission_date"]),
            ("Appeal ID", PATIENT["appeal_id"]),
            ("Service Requested", PATIENT["service_requested"]),
        ],
        sections=[
            (
                "Packet Intent",
                "paragraph",
                "Synthetic appeal-support packet prepared for demonstrations. This record compiles outpatient and consult documentation supporting medical necessity for denied lumbar MRI authorization.",
            ),
            (
                "Diagnoses Under Review",
                "bullets",
                [PATIENT["dx_1"], PATIENT["dx_2"]],
            ),
        ],
    )

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Fax Cover Sheet (Imported)",
        sections=[
            ("Transmission Detail", "bullets", [
                "Date: 08/15/2023",
                "ATTN: HealthPlus Insurance",
                f"Appeal request for {PATIENT['name']} (DOB {PATIENT['dob']})",
                f"Claim ID: {PATIENT['claim_id']}",
                f"Service requested: {PATIENT['service_requested']}",
                "Originating facility: Mercy Hospital",
            ]),
        ],
        scanned=True,
    )

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Appeal Request Details",
        meta_pairs=[
            ("Patient", PATIENT["name"]),
            ("Member ID", PATIENT["member_id"]),
            ("Payer", PATIENT["payer"]),
            ("Provider", "Dr. Emily Roberts, Mercy Hospital"),
            ("Appeal Submission", PATIENT["appeal_submission_date"]),
            ("Procedure", "Lumbar MRI"),
            ("CPT", "72148"),
            ("Diagnosis 1", PATIENT["dx_1"]),
            ("Diagnosis 2", PATIENT["dx_2"]),
        ],
        sections=[
            ("Detailed Clinical Notes", "bullets", [
                "3-month history of severe low-back pain radiating to left leg.",
                "Neurologic symptoms include numbness/tingling and progressive weakness.",
                "Conservative care completed without sustained improvement.",
                "Latest clinical findings suggest progressive disc pathology with nerve-root involvement.",
            ]),
        ],
        scanned=True,
    )

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Appeal Letter to Medical Director",
        meta_pairs=[
            ("Date", PATIENT["appeal_submission_date"]),
            ("Recipient", "Medical Director, HealthPlus Insurance"),
            ("Subject", f"Appeal for authorization of lumbar MRI for {PATIENT['name']}"),
        ],
        sections=[
            ("Appeal Narrative", "paragraph", "Mercy Hospital requests reconsideration of the denied lumbar MRI. Recent evaluations and specialist documentation demonstrate failed conservative treatment, progressive neurologic findings, and the need for advanced imaging to guide definitive management."),
            ("Requested Action", "bullets", [
                "Reverse initial denial for CPT 72148 (lumbar MRI without contrast).",
                "Authorize timely imaging due to progressive deficits and worsening function.",
            ]),
        ],
        signature=(PATIENT["attending"], "Appeal Author", "08/15/2023 09:14"),
        scanned=True,
    )

    page_num = table_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Chronology of Recent Clinical Events",
        columns=[("Date", 78), ("Source", 120), ("Event", 160), ("Type", 90), ("Outcome", 92)],
        rows=[list(r) for r in rec["chronology_rows"]],  # type: ignore[list-item]
        notes=[
            "Timeline aligns with appeal packet and demonstrates progression despite conservative management.",
        ],
    )

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Recent Office Note - Mercy Primary Care",
        meta_pairs=[
            ("Date", "07/10/2023"),
            ("Provider", PATIENT["attending"]),
            ("Visit Type", "Outpatient follow-up"),
        ],
        sections=[
            ("History / Symptoms", "bullets", [str(v) for v in rec["office_note"]]),  # type: ignore[list-item]
            ("Assessment", "bullets", [
                "Lumbar radiculopathy symptoms remain high severity.",
                "Functional tolerance remains poor despite treatment compliance.",
            ]),
            ("Plan", "bullets", [
                "Continue PT plan of care and medication optimization.",
                "Escalate to specialty consultation due to persistent deficits.",
            ]),
        ],
        signature=(PATIENT["attending"], "Office Follow-Up", "07/10/2023 16:20"),
    )

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Consult Note - Spine / Neurology",
        meta_pairs=[
            ("Date", "08/03/2023"),
            ("Consult Team", "Mercy Spine + Neurology"),
            ("Referral Source", PATIENT["attending"]),
        ],
        sections=[
            ("Consult Findings", "bullets", [str(v) for v in rec["consult_note"]]),  # type: ignore[list-item]
            ("Consult Recommendation", "bullets", [
                "Proceed with lumbar MRI without contrast for anatomic clarification.",
                "Use MRI findings to determine next interventional or surgical step.",
            ]),
        ],
        signature=("M. Chen, DO", "Neurology Consultation", "08/03/2023 14:08"),
    )

    page_num = table_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Physical Examination Trend (Serial Findings)",
        columns=[("Date", 74), ("Pain", 58), ("SLR Left", 70), ("LLE Strength", 84), ("Achilles", 72), ("Sensation", 74), ("Sitting Tol.", 108)],
        rows=[list(r) for r in rec["exam_rows"]],  # type: ignore[list-item]
        notes=[
            "Serial exams reflect progression of neurologic findings over time.",
        ],
    )

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "PT Initial Evaluation - Mercy Outpatient Rehab",
        meta_pairs=[
            ("Date", "06/26/2023"),
            ("Diagnosis", "M54.16 / M51.26"),
            ("Plan of Care", "06/26/2023 to 08/07/2023"),
            ("Frequency", "2x/week"),
        ],
        sections=[
            ("Subjective", "bullets", [
                "3-month history of low-back pain radiating to left posterior leg.",
                "Pain 8/10 with numbness/tingling in left calf and foot.",
                "Sitting tolerance under 15 minutes; sleep disrupted nightly.",
            ]),
            ("Objective", "bullets", [
                "SLR positive (left) at 35 degrees.",
                "Lumbar flexion limited 50%.",
                "Left LE strength 4-/5 with decreased Achilles reflex.",
                "ODI 52% (severe disability).",
            ]),
            ("Assessment/Plan", "bullets", [
                "Findings consistent with lumbar radiculopathy and significant functional limitation.",
                "Core stabilization, traction, neural mobilization, manual therapy, and HEP initiated.",
            ]),
        ],
        signature=("Sarah Mitchell, PT, DPT", "PT Initial Evaluation", "06/26/2023 11:40"),
    )

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "PT Weekly Progress Summary",
        sections=[
            ("Week 2 - 07/10/2023", "bullets", [
                "Pain 7/10 with persistent radicular symptoms.",
                "Slight ROM improvement but ODI still high at 48%.",
                "Functional improvement minimal.",
            ]),
            ("Week 4 - 07/24/2023", "bullets", [
                "Pain returns to 8/10 with prolonged sitting.",
                "Continued numbness in left foot and SLR positive at 30 degrees.",
                "ODI worsened to 50% despite therapy compliance.",
            ]),
        ],
        signature=("Sarah Mitchell, PT, DPT", "PT Progress Note", "07/24/2023 17:02"),
    )

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "PT Reassessment / Discharge",
        meta_pairs=[
            ("Date", "08/07/2023"),
            ("Total PT Visits", "12"),
            ("Home Program", "Compliant"),
        ],
        sections=[
            ("Discharge Findings", "bullets", [
                "Pain worsened to 8-9/10.",
                "SLR positive at 25 degrees with unchanged lumbar ROM limits.",
                "Left LE strength declined to 3+/5.",
                "ODI increased to 56% (worsened disability).",
            ]),
            ("Clinical Impression", "bullets", [
                "Failed 6-week structured conservative management.",
                "Persistent radicular pain with progressive neurologic weakness.",
                "Further diagnostic imaging (lumbar MRI) recommended for next-step care.",
            ]),
        ],
        signature=("Sarah Mitchell, PT, DPT", "PT Discharge Summary", "08/07/2023 16:18"),
        scanned=True,
    )

    page_num = table_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Physical Therapy Visit Log and Outcomes",
        columns=[("Visit", 48), ("Date", 78), ("Intervention", 176), ("Pain", 88), ("Outcome Summary", 150)],
        rows=build_pt_visit_rows(),
        notes=[
            "Visit-level outcomes show persistent high pain and deteriorating disability scores.",
        ],
    )

    page_num = table_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Medication History",
        columns=[("Medication", 112), ("Dose", 78), ("Start", 116), ("Duration", 76), ("Response / Outcome", 158)],
        rows=[list(r) for r in rec["med_rows"]],  # type: ignore[list-item]
        notes=[
            "Medication escalation did not produce durable symptom or functional improvement.",
        ],
        signature=("Nina Patel, PharmD", "Medication Review", "08/12/2023 10:36"),
    )

    page_num = table_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Injection and Procedure History",
        columns=[("Date", 88), ("Procedure", 150), ("Provider", 96), ("Immediate Response", 92), ("Sustained Outcome", 114)],
        rows=[list(r) for r in rec["injection_rows"]],  # type: ignore[list-item]
        notes=[
            "Injection interventions yielded no durable relief and did not reverse neurologic decline.",
        ],
        signature=("R. Thompson, MD", "Pain Procedure Review", "08/12/2023 11:02"),
    )

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Prior Imaging Report - Lumbar X-Ray",
        meta_pairs=[
            ("Date", "05/22/2023"),
            ("Facility", "Mercy Hospital Imaging"),
            ("Study", "Lumbar Spine X-Ray, 3 views"),
        ],
        sections=[
            ("Findings", "bullets", [
                "Mild degenerative disc space narrowing at L4-L5.",
                "No acute fracture or malalignment.",
                "Radiographic findings non-specific for nerve compression.",
            ]),
            ("Impression", "bullets", [
                "X-ray inconclusive for etiology of progressive radicular symptoms.",
                "Cross-sectional imaging recommended if neurologic deficits persist.",
            ]),
        ],
        signature=("A. Simmons, MD", "Radiology", "05/22/2023 15:47"),
    )

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Prior Imaging Report - Lumbar CT",
        meta_pairs=[
            ("Date", "06/05/2023"),
            ("Facility", "Mercy Hospital Imaging"),
            ("Study", "CT Lumbar Spine without contrast"),
        ],
        sections=[
            ("Findings", "bullets", [
                "Left paracentral disc protrusion at L4-L5 with suspected contact of traversing L5 root.",
                "Mild central canal narrowing; no acute osseous injury.",
                "Limited soft tissue and nerve-root definition by CT modality.",
            ]),
            ("Impression", "bullets", [
                "Findings concerning for disc pathology correlated with left-sided radiculopathy.",
                "MRI recommended for definitive nerve-root and soft tissue assessment.",
            ]),
        ],
        signature=("A. Simmons, MD", "Radiology", "06/05/2023 13:20"),
    )

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Historical Imaging Report - Prior Lumbar MRI",
        meta_pairs=[
            ("Date", "03/19/2021"),
            ("Facility", "Mercy Hospital Imaging"),
            ("Study", "MRI Lumbar Spine without contrast"),
        ],
        sections=[
            ("Findings", "bullets", [
                "Mild broad-based L4-L5 disc bulge without focal nerve-root impingement at that time.",
                "No severe canal stenosis on 2021 study.",
            ]),
            ("Clinical Relevance", "bullets", [
                "Current 2023 symptoms and deficits have significantly progressed from baseline imaging.",
                "Updated MRI is needed to characterize new/progressive pathology.",
            ]),
        ],
        signature=("J. Vega, MD", "Radiology Archive Review", "08/11/2023 09:05"),
        scanned=True,
    )

    page_num = image_report_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Synthetic Imaging Attachment - Lumbar Correlate 1",
        report_lines=[
            "Synthetic diagnostic attachment included to simulate a multi-modal imported record.",
            "Visual representation supports review workflow realism, not diagnostic use.",
            "Clinical interpretation remains in signed radiology reports.",
        ],
        signer=("Imaging Archive", "Attachment Review", "08/12/2023 14:10"),
        use_ultrasound=False,
    )

    page_num = image_report_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Synthetic Imaging Attachment - Lumbar Correlate 2",
        report_lines=[
            "Additional synthetic imaging page to reflect imported outside-document bundles.",
            "Used for demo of multi-modal ingestion within appeal packets.",
            "Does not replace formal radiologist interpretation.",
        ],
        signer=("Imaging Archive", "Attachment Review", "08/12/2023 14:16"),
        use_ultrasound=True,
    )

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Conservative Management Failure Summary",
        sections=[
            ("Completed Conservative Interventions", "bullets", [
                "Supervised PT: 12 visits over 6 weeks with documented compliance.",
                "Medication trials: anti-inflammatory, neuropathic, muscle relaxant, rescue analgesic regimens.",
                "Injection procedures performed with only transient or absent benefit.",
            ]),
            ("Outcome Trend", "bullets", [
                "Pain severity remained high (7-9/10).",
                "Neurologic deficits progressed on serial objective examinations.",
                "Functional metrics worsened (ODI trend deterioration, reduced sitting tolerance).",
            ]),
        ],
        signature=(PATIENT["attending"], "Clinical Summary", "08/14/2023 13:06"),
    )

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Medical Necessity Determination - Lumbar MRI",
        sections=[
            ("Rationale", "bullets", [str(v) for v in rec["necessity_points"]]),  # type: ignore[list-item]
            ("Requested Service", "bullets", [
                "CPT 72148 MRI lumbar spine without contrast.",
                "Requested to evaluate compressive pathology and direct definitive treatment.",
            ]),
        ],
        signature=(PATIENT["attending"], "Medical Necessity Attestation", "08/15/2023 08:42"),
    )

    page_num = table_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Payer Criteria Crosswalk",
        columns=[("Criterion", 170), ("Evidence in Packet", 370)],
        rows=[list(r) for r in rec["criteria_rows"]],  # type: ignore[list-item]
        notes=[
            "Appeal evidence mapped to documented criteria to support overturn of MRI denial.",
        ],
    )

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Attending Appeal Addendum",
        sections=[
            ("Attending Statement", "paragraph", str(rec["addendum"])),
            ("Final Request", "bullets", [
                "Reconsider and approve denied lumbar MRI request.",
                "Prevent further neurologic progression and prolonged disability.",
            ]),
        ],
        signature=(PATIENT["attending"], "Final Appeal Addendum", "08/15/2023 09:22"),
    )

    save_packet_pdf(doc, out_pdf)
    payload = dict(rec)
    payload["patient"] = PATIENT
    payload["packet_type"] = "lumbar_mri_appeal_evidence"
    payload["packet_generated_pages"] = len(doc.pages)
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def main() -> None:
    maybe_reexec_in_scan_env()
    root = Path(os.getcwd())
    out_dir = root / "Appeal Synthetic Records"
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest: List[Dict[str, str]] = []
    name_map = {
        "A": "failed_conservative_care",
        "B": "escalating_radiculopathy",
        "C": "surgical_planning_need",
    }
    for rec in build_record_templates():
        label = str(rec["record_label"]).lower()
        stem = f"record_{label}_{name_map[str(rec['record_label'])]}"
        pdf_path = out_dir / f"{stem}.pdf"
        json_path = out_dir / f"{stem}.json"
        build_appeal_packet(rec, pdf_path, json_path)
        manifest.append({
            "record": str(rec["record_label"]),
            "pdf": str(pdf_path),
            "json": str(json_path),
        })
        print(f"Wrote appeal PDF: {pdf_path}")
        print(f"Wrote appeal JSON: {json_path}")

    with (out_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote appeal manifest: {out_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
