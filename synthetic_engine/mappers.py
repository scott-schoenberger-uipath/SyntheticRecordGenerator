from __future__ import annotations

from typing import Any, Callable, Dict, List

from .canonical import CanonicalEncounter

FamilyMapper = Callable[[CanonicalEncounter], Dict[str, Any]]


def _condition_rows(enc: CanonicalEncounter, limit: int = 8) -> List[List[str]]:
    rows: List[List[str]] = []
    for cond in enc.conditions[:limit]:
        rows.append([cond.code, cond.name, cond.status, cond.onset])
    return rows


def _med_lines(enc: CanonicalEncounter, limit: int = 15) -> List[str]:
    out: List[str] = []
    for med in enc.medications[:limit]:
        suffix = " PRN" if med.prn else ""
        out.append(f"{med.name} {med.dose} {med.route} {med.frequency}{suffix} ({med.indication})")
    return out


def _allergy_lines(enc: CanonicalEncounter) -> List[str]:
    return [f"{a.substance}: {a.reaction} ({a.severity})" for a in enc.allergies]


def map_registration_face_sheet(enc: CanonicalEncounter) -> Dict[str, Any]:
    p = enc.patient
    e = enc.encounter
    return {
        "title": "Inpatient Registration Face Sheet",
        "header_subtitle": f"Record {e.record_label} | {e.acuity}",
        "encounter_pairs": [
            ["Facility", e.facility],
            ["Encounter", e.encounter_type],
            ["Theme", e.theme],
            ["Admission", e.admission_date],
            ["Discharge", e.discharge_date],
            ["Length of Stay", f"{e.length_of_stay_days} days"],
            ["Attending", e.attending_physician],
            ["Encounter ID", e.encounter_id],
        ],
        "demographic_pairs": [
            ["Patient", p.name],
            ["DOB", p.dob],
            ["Age", str(p.age)],
            ["Gender", p.gender],
            ["MRN", p.mrn],
            ["Member ID", p.member_id],
            ["Insurance", p.insurance_type],
            ["PCP", p.pcp],
            ["Phone", p.phone],
            ["Address", p.address],
        ],
        "condition_rows": _condition_rows(enc),
    }


def map_history_and_physical(enc: CanonicalEncounter) -> Dict[str, Any]:
    return {
        "title": "Admission History and Physical",
        "chief_complaint": enc.chief_complaint,
        "hpi": enc.hpi,
        "pmh_lines": [f"{c.name} ({c.code})" for c in enc.conditions[:6]],
        "medication_lines": _med_lines(enc, limit=10),
        "allergy_lines": _allergy_lines(enc),
    }


def map_discharge_summary(enc: CanonicalEncounter) -> Dict[str, Any]:
    e = enc.encounter
    return {
        "title": "Discharge Summary",
        "encounter_pairs": [
            ["Admission", e.admission_date],
            ["Discharge", e.discharge_date],
            ["Length of Stay", f"{e.length_of_stay_days} days"],
            ["Attending", e.attending_physician],
            ["Disposition", enc.discharge_disposition],
        ],
        "final_diagnoses": enc.discharge_diagnoses,
        "hospital_course": enc.hospital_course,
        "follow_up_plan": enc.follow_up_plan,
    }


def map_lab_result_page(enc: CanonicalEncounter) -> Dict[str, Any]:
    rows: List[List[str]] = []
    for lab in enc.labs[:24]:
        flag = ""
        if lab.wbc > 11.0:
            flag = "High WBC"
        elif lab.creatinine > 1.4:
            flag = "AKI trend"
        elif lab.lactate > 2.0:
            flag = "Lactate high"
        rows.append([
            lab.date,
            lab.time,
            f"{lab.wbc:.1f}",
            f"{lab.creatinine:.2f}",
            f"{lab.lactate:.1f}",
            f"{lab.hemoglobin:.1f}",
            flag,
        ])
    return {
        "title": "Lab Result Trend Page",
        "columns": ["Date", "Time", "WBC", "Creatinine", "Lactate", "Hemoglobin", "Flag"],
        "rows": rows,
    }


def map_radiology_report(enc: CanonicalEncounter) -> Dict[str, Any]:
    report = enc.radiology_reports[0] if enc.radiology_reports else None
    if not report:
        return {
            "title": "Radiology Report",
            "meta_pairs": [["Study", "N/A"], ["Date", "N/A"], ["Radiologist", "N/A"]],
            "findings": ["No imaging report available."],
            "impression": ["No impression available."],
        }
    return {
        "title": "Radiology Report",
        "meta_pairs": [
            ["Study", report.study],
            ["Date", report.date],
            ["Indication", report.indication],
            ["Radiologist", report.radiologist],
        ],
        "findings": report.findings,
        "impression": report.impression,
    }


def map_operative_report(enc: CanonicalEncounter) -> Dict[str, Any]:
    proc = enc.procedure_reports[0] if enc.procedure_reports else None
    if not proc:
        return {
            "title": "Operative Report",
            "meta_pairs": [["Procedure", "None documented"]],
            "findings": ["No operative report available."],
            "complications": "None",
        }
    return {
        "title": "Operative Report",
        "meta_pairs": [
            ["Procedure", proc.procedure],
            ["Date", proc.date],
            ["Surgeon", proc.surgeon],
            ["Indication", proc.indication],
        ],
        "findings": proc.findings,
        "complications": proc.complications,
    }


def map_pathology_report(enc: CanonicalEncounter) -> Dict[str, Any]:
    path = enc.pathology_reports[0] if enc.pathology_reports else None
    if not path:
        return {
            "title": "Pathology Report",
            "meta_pairs": [["Specimen", "Not submitted"], ["Date", "N/A"], ["Pathologist", "N/A"]],
            "findings": ["No pathology report available for this encounter."],
            "diagnosis": "N/A",
        }
    return {
        "title": "Pathology Report",
        "meta_pairs": [
            ["Specimen", path.specimen],
            ["Date", path.date],
            ["Pathologist", path.pathologist],
        ],
        "findings": path.findings,
        "diagnosis": path.diagnosis,
    }


def map_handwritten_progress_note(enc: CanonicalEncounter) -> Dict[str, Any]:
    note = enc.progress_notes[min(1, len(enc.progress_notes) - 1)] if enc.progress_notes else None
    if not note:
        return {
            "title": "Handwritten Progress Note",
            "meta_pairs": [["Date", "N/A"], ["Author", "N/A"]],
            "sections": [
                ["Subjective", ["No note text available."]],
                ["Objective", ["No objective data available."]],
                ["Assessment/Plan", ["No plan documented."]],
            ],
            "checkbox_rows": [["Pain controlled", False], ["Neurologic deficit present", False], ["Needs imaging", False]],
        }
    return {
        "title": "Handwritten Progress Note",
        "meta_pairs": [["Date", note.date], ["Author", note.author]],
        "sections": [
            ["Subjective", note.subjective],
            ["Objective", note.objective],
            ["Assessment/Plan", note.assessment + note.plan],
        ],
        "checkbox_rows": [
            ["Pain controlled", False],
            ["Neurologic deficit present", True],
            ["Needs MRI / escalation", True],
        ],
    }


def map_anesthesia_or_record(enc: CanonicalEncounter) -> Dict[str, Any]:
    record = enc.anesthesia_records[0] if enc.anesthesia_records else None
    if not record:
        return {
            "title": "Anesthesia / OR Record",
            "meta_pairs": [["Date", "N/A"], ["Anesthesiologist", "N/A"], ["ASA", "N/A"]],
            "events": ["No anesthesia record in this encounter."],
            "checkbox_rows": [["Airway secured", False], ["Pressor used", False], ["Complication noted", False]],
        }
    return {
        "title": "Anesthesia / OR Record",
        "meta_pairs": [
            ["Date", record.date],
            ["Anesthesiologist", record.anesthesiologist],
            ["ASA", record.asa_class],
            ["Anesthesia", record.anesthesia_type],
            ["Airway", record.airway],
        ],
        "events": record.events,
        "checkbox_rows": [
            ["Airway secured", True],
            ["Pressor used", any("pressor" in e.lower() for e in record.events)],
            ["Complication noted", False],
        ],
    }


def map_mar(enc: CanonicalEncounter) -> Dict[str, Any]:
    rows = [[m.date, m.time, m.medication, m.dose, m.status, m.nurse] for m in enc.mar_entries[:32]]
    return {
        "title": "Medication Administration Record (MAR)",
        "columns": ["Date", "Time", "Medication", "Dose", "Status", "Nurse"],
        "rows": rows,
    }


def map_prior_authorization_request(enc: CanonicalEncounter) -> Dict[str, Any]:
    appeal = enc.appeal
    service = appeal.requested_service if appeal else "Advanced diagnostic imaging"
    return {
        "title": "Prior Authorization Request",
        "meta_pairs": [
            ["Requesting Facility", enc.encounter.facility],
            ["Requesting Provider", enc.encounter.attending_physician],
            ["Requested Service", service],
            ["Primary Diagnosis", enc.conditions[0].name if enc.conditions else "N/A"],
        ],
        "medical_necessity": appeal.conservative_care_summary if appeal else enc.hospital_course,
        "requested_action": [
            "Authorize requested service for current episode.",
            "Expedite review due to progressive clinical findings.",
        ],
    }


def map_appeal_letter(enc: CanonicalEncounter) -> Dict[str, Any]:
    appeal = enc.appeal
    return {
        "title": "Appeal Letter",
        "meta_pairs": [
            ["From", enc.encounter.attending_physician],
            ["To", "Medical Director, Health Plan"],
            ["Subject", "Appeal of denied service authorization"],
        ],
        "body_lines": [
            f"This appeal concerns {enc.patient.name} (member {enc.patient.member_id}).",
            (appeal.denial_reason if appeal else "Initial request denied for medical necessity."),
            "Supporting clinical documentation demonstrates persistent symptoms and failed conservative management.",
            "Please overturn the denial and authorize the requested service.",
        ],
        "requested_service": appeal.requested_service if appeal else "Requested diagnostic service",
    }


def map_denial_letter(enc: CanonicalEncounter) -> Dict[str, Any]:
    appeal = enc.appeal
    return {
        "title": "Payer Denial Letter",
        "meta_pairs": [
            ["Plan", enc.patient.insurance_type],
            ["Member", enc.patient.member_id],
            ["Service", appeal.requested_service if appeal else "Requested service"],
            ["Decision", "Denied (sample synthetic denial)"]],
        "reasons": [
            "Clinical documentation submitted did not satisfy initial policy criteria.",
            "Insufficient linkage between progression and requested imaging on first submission.",
            "Case eligible for appeal with additional records.",
        ],
    }


MAPPER_REGISTRY: Dict[str, FamilyMapper] = {
    "registration_face_sheet": map_registration_face_sheet,
    "history_and_physical": map_history_and_physical,
    "discharge_summary": map_discharge_summary,
    "lab_result_page": map_lab_result_page,
    "radiology_report": map_radiology_report,
    "operative_report": map_operative_report,
    "pathology_report": map_pathology_report,
    "handwritten_progress_note": map_handwritten_progress_note,
    "anesthesia_or_record": map_anesthesia_or_record,
    "mar": map_mar,
    "prior_authorization_request": map_prior_authorization_request,
    "appeal_letter": map_appeal_letter,
    "denial_letter": map_denial_letter,
}


def map_family_payload(family: str, encounter: CanonicalEncounter) -> Dict[str, Any]:
    mapper = MAPPER_REGISTRY.get(family)
    if mapper is None:
        raise KeyError(f"No mapper registered for family '{family}'")
    payload = mapper(encounter)
    payload.setdefault("family", family)
    payload.setdefault("patient_name", encounter.patient.name)
    payload.setdefault("patient_mrn", encounter.patient.mrn)
    payload.setdefault("facility", encounter.encounter.facility)
    return payload


def expected_payload_keys(family: str) -> List[str]:
    table = {
        "registration_face_sheet": ["encounter_pairs", "demographic_pairs", "condition_rows"],
        "history_and_physical": ["chief_complaint", "hpi", "pmh_lines", "medication_lines", "allergy_lines"],
        "discharge_summary": ["final_diagnoses", "hospital_course", "follow_up_plan"],
        "lab_result_page": ["columns", "rows"],
        "radiology_report": ["meta_pairs", "findings", "impression"],
        "operative_report": ["meta_pairs", "findings", "complications"],
        "pathology_report": ["meta_pairs", "findings", "diagnosis"],
        "handwritten_progress_note": ["meta_pairs", "sections", "checkbox_rows"],
        "anesthesia_or_record": ["meta_pairs", "events", "checkbox_rows"],
        "mar": ["columns", "rows"],
        "prior_authorization_request": ["meta_pairs", "medical_necessity", "requested_action"],
        "appeal_letter": ["meta_pairs", "body_lines", "requested_service"],
        "denial_letter": ["meta_pairs", "reasons"],
    }
    return table.get(family, [])
