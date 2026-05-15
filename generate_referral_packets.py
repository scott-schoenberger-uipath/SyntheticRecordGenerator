#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence

from generate_long_form_packets import image_report_page, note_page, save_packet_pdf, table_page
from generate_synthetic_patient_pdf import PDFDocument


PacketSpec = Dict[str, Any]


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower())
    return re.sub(r"_+", "_", slug).strip("_")


def make_patient(idx: int, name: str, dob: str, insurance: str) -> Dict[str, str]:
    return {
        "name": name,
        "dob": dob,
        "mrn": f"REF{510000 + idx:06d}",
        "address": f"{410 + idx} Meadow Glen Drive, Sample City, ST {18000 + idx}",
        "phone": f"555-61{idx:02d}",
        "insurance": insurance,
    }


def make_provider(idx: int, facility: str, clinician: str, specialty: str) -> Dict[str, str]:
    return {
        "facility": facility,
        "clinician": clinician,
        "specialty": specialty,
        "npi": f"1987{idx:06d}",
        "fax": f"555-72{idx:02d}",
        "phone": f"555-83{idx:02d}",
        "contact": f"Referral Coordinator {idx}",
    }


def make_referral_packet_specs() -> List[PacketSpec]:
    referring_primary = make_provider(10, "Harbor Family Medicine", "Mina Avery, MD", "Family Medicine")
    return [
        {
            "record_label": "RP01",
            "title": "Orthopedic Spine Referral Packet",
            "target_pages": 5,
            "urgency": "Routine",
            "referral_reason": "Persistent lumbar radicular pain despite conservative care",
            "requested_specialty": "Orthopedic Spine",
            "patient": make_patient(1, "Lena Hart", "04/16/1983", "Medicaid Managed Care"),
            "referring_provider": referring_primary,
            "receiving_provider": make_provider(1, "East Valley Spine Center", "Jon Mercer, MD", "Orthopedic Spine"),
            "diagnoses": [
                ("M54.16", "Radiculopathy, lumbar region"),
                ("M51.26", "Other intervertebral disc displacement, lumbar region"),
            ],
            "medications": ["Naproxen 500 mg twice daily", "Gabapentin 300 mg nightly", "Acetaminophen as needed"],
            "allergies": ["No known drug allergies"],
            "office_notes": [
                {
                    "date": "05/04/2026",
                    "title": "Primary Care Office Note",
                    "subjective": "Eight weeks of low back pain radiating into the left calf with limited sitting tolerance.",
                    "assessment": [
                        "Positive straight-leg raise on the left.",
                        "No bowel or bladder symptoms reported.",
                        "Home exercise program and NSAID trial provided incomplete relief.",
                    ],
                    "plan": [
                        "Refer to orthopedic spine for evaluation.",
                        "Continue conservative measures pending specialist review.",
                        "Forward PT discharge note, labs, and imaging report with referral packet.",
                    ],
                }
            ],
            "progress_notes": [
                {
                    "date": "05/11/2026",
                    "title": "Referral Follow-Up Progress Note",
                    "events": [
                        "Patient reports persistent left leg pain and missed work due to symptoms.",
                        "Referral packet assembled with clinical documentation and diagnostic summaries.",
                        "No emergent neurologic red flags at phone follow-up.",
                    ],
                    "next_steps": [
                        "Specialty appointment requested within two weeks.",
                        "Return precautions reviewed for weakness, saddle anesthesia, or bladder changes.",
                    ],
                }
            ],
            "lab_results": [
                ("05/01/2026", "CBC WBC", "7.8 K/uL", "4.0-11.0", "", "Baseline before medication change"),
                ("05/01/2026", "Hemoglobin", "13.4 g/dL", "12.0-16.0", "", "Stable"),
                ("05/01/2026", "Creatinine", "0.86 mg/dL", "0.60-1.20", "", "NSAID monitoring"),
                ("05/01/2026", "ESR", "14 mm/hr", "0-20", "", "No inflammatory red flag"),
                ("05/01/2026", "CRP", "2.1 mg/L", "0.0-5.0", "", "No inflammatory red flag"),
            ],
            "imaging_reports": [
                {
                    "date": "05/03/2026",
                    "modality": "Lumbar spine radiographs",
                    "title": "Imaging Results - Lumbar Spine",
                    "lines": [
                        "Mild L4-L5 disc space narrowing without acute osseous abnormality.",
                        "No compression deformity or destructive lesion identified.",
                        "MRI may be considered if radicular symptoms persist after conservative management.",
                    ],
                    "signer": "Radiology Review",
                    "use_ultrasound": False,
                }
            ],
        },
        {
            "record_label": "RP02",
            "title": "Cardiology Referral Packet",
            "target_pages": 8,
            "urgency": "Soon",
            "referral_reason": "Exertional dyspnea with palpitations and abnormal ambulatory rhythm findings",
            "requested_specialty": "Cardiology",
            "patient": make_patient(2, "Oscar Nguyen", "09/28/1964", "Commercial HMO"),
            "referring_provider": make_provider(11, "Harbor Family Medicine", "Mina Avery, MD", "Family Medicine"),
            "receiving_provider": make_provider(2, "Northstar Heart Institute", "Priya Desai, MD", "Cardiology"),
            "diagnoses": [
                ("R06.02", "Shortness of breath"),
                ("R00.2", "Palpitations"),
                ("I10", "Essential hypertension"),
            ],
            "medications": ["Lisinopril 20 mg daily", "Atorvastatin 40 mg daily", "Metoprolol succinate 25 mg daily"],
            "allergies": ["Penicillin - rash"],
            "office_notes": [
                {
                    "date": "04/24/2026",
                    "title": "Primary Care Office Note",
                    "subjective": "Two months of exertional dyspnea climbing stairs, intermittent palpitations, and reduced exercise tolerance.",
                    "assessment": [
                        "Blood pressure elevated at intake, improved on repeat measurement.",
                        "Office ECG showed sinus rhythm with nonspecific ST-T changes.",
                        "No chest pain at rest and no syncope reported.",
                    ],
                    "plan": [
                        "Refer to cardiology for stress testing and rhythm evaluation.",
                        "Start low-dose beta blocker after reviewing baseline heart rate.",
                        "Send recent labs and chest imaging with referral packet.",
                    ],
                },
                {
                    "date": "05/05/2026",
                    "title": "Nurse Triage Note",
                    "subjective": "Patient called after home pulse monitor showed intermittent irregular rhythm alerts.",
                    "assessment": [
                        "Symptoms resolved with rest.",
                        "No current chest pain, diaphoresis, or neurologic symptoms.",
                        "Cardiology referral upgraded to soon appointment request.",
                    ],
                    "plan": [
                        "Emergency precautions reviewed.",
                        "Referral packet updated with rhythm monitor summary.",
                    ],
                },
            ],
            "progress_notes": [
                {
                    "date": "05/08/2026",
                    "title": "Referral Progress Note",
                    "events": [
                        "Referral coordinator confirmed receipt of demographic and insurance details.",
                        "Recent labs, office ECG interpretation, and chest imaging were attached.",
                        "Patient prefers morning appointments and can travel to the main cardiology office.",
                    ],
                    "next_steps": [
                        "Cardiology to schedule consult and determine stress test pathway.",
                        "Primary care to continue blood pressure log review.",
                    ],
                }
            ],
            "lab_results": [
                ("04/24/2026", "Troponin T", "<6 ng/L", "0-14", "", "No acute injury pattern"),
                ("04/24/2026", "BNP", "88 pg/mL", "0-100", "", "Within expected range"),
                ("04/24/2026", "Potassium", "4.2 mmol/L", "3.5-5.1", "", "Stable"),
                ("04/24/2026", "Creatinine", "1.04 mg/dL", "0.60-1.30", "", "Baseline"),
                ("04/24/2026", "LDL", "142 mg/dL", "<100", "H", "Risk factor management"),
                ("04/24/2026", "A1c", "6.1 %", "4.0-5.6", "H", "Prediabetes range"),
            ],
            "imaging_reports": [
                {
                    "date": "04/26/2026",
                    "modality": "Chest radiograph",
                    "title": "Imaging Results - Chest X-Ray",
                    "lines": [
                        "Cardiomediastinal silhouette is mildly enlarged.",
                        "No focal infiltrate, pleural effusion, or pneumothorax.",
                        "Impression supports outpatient cardiology evaluation in clinical context.",
                    ],
                    "signer": "Radiology Review",
                    "use_ultrasound": False,
                }
            ],
        },
        {
            "record_label": "RP03",
            "title": "Gastroenterology Referral Packet",
            "target_pages": 12,
            "urgency": "Routine",
            "referral_reason": "Chronic epigastric pain with iron deficiency anemia and positive stool test",
            "requested_specialty": "Gastroenterology",
            "patient": make_patient(3, "Mara Ellis", "12/02/1971", "Medicaid Managed Care"),
            "referring_provider": make_provider(12, "Harbor Family Medicine", "Mina Avery, MD", "Family Medicine"),
            "receiving_provider": make_provider(3, "Lakeside Digestive Health", "Evan Brooks, MD", "Gastroenterology"),
            "diagnoses": [
                ("D50.9", "Iron deficiency anemia, unspecified"),
                ("R10.13", "Epigastric pain"),
                ("R19.5", "Other fecal abnormalities"),
            ],
            "medications": ["Pantoprazole 40 mg daily", "Ferrous sulfate 325 mg every other day", "Ondansetron 4 mg as needed"],
            "allergies": ["Sulfa antibiotics - hives"],
            "office_notes": [
                {
                    "date": "04/15/2026",
                    "title": "Primary Care Office Note",
                    "subjective": "Intermittent epigastric burning, early satiety, and fatigue over three months.",
                    "assessment": [
                        "Mild epigastric tenderness without guarding.",
                        "Microcytic anemia found on routine laboratory testing.",
                        "No hemodynamic instability or overt bleeding reported.",
                    ],
                    "plan": [
                        "Start proton pump inhibitor and oral iron.",
                        "Refer to gastroenterology for endoscopic evaluation.",
                        "Attach serial labs and abdominal ultrasound report.",
                    ],
                },
                {
                    "date": "04/29/2026",
                    "title": "Medication Follow-Up Note",
                    "subjective": "Pain improved partially with pantoprazole, but fatigue and dark stools persist intermittently.",
                    "assessment": [
                        "Repeat hemoglobin remains low.",
                        "Stool immunochemical test returned positive.",
                        "Patient denies syncope, severe pain, or hematemesis.",
                    ],
                    "plan": [
                        "Gastroenterology referral remains active.",
                        "Continue iron therapy and monitor for worsening symptoms.",
                    ],
                },
            ],
            "progress_notes": [
                {
                    "date": "05/06/2026",
                    "title": "Referral Status Progress Note",
                    "events": [
                        "GI office requested additional lab trend and medication response documentation.",
                        "Referral packet expanded to include repeat CBC, iron studies, and imaging summary.",
                        "Patient notified that appointment scheduling is in progress.",
                    ],
                    "next_steps": [
                        "GI to determine EGD and colonoscopy scheduling.",
                        "Primary care to recheck CBC if symptoms worsen before consult.",
                    ],
                }
            ],
            "lab_results": [
                ("04/15/2026", "Hemoglobin", "10.7 g/dL", "12.0-16.0", "L", "Microcytic pattern"),
                ("04/15/2026", "MCV", "74 fL", "80-96", "L", "Iron deficiency pattern"),
                ("04/15/2026", "Ferritin", "9 ng/mL", "15-150", "L", "Low iron stores"),
                ("04/15/2026", "Iron saturation", "8 %", "15-50", "L", "Low"),
                ("04/22/2026", "FIT", "Positive", "Negative", "H", "Referral driver"),
                ("04/29/2026", "Hemoglobin", "10.5 g/dL", "12.0-16.0", "L", "Persistent anemia"),
                ("04/29/2026", "Platelets", "418 K/uL", "150-400", "H", "Reactive pattern"),
            ],
            "imaging_reports": [
                {
                    "date": "04/21/2026",
                    "modality": "Abdominal ultrasound",
                    "title": "Imaging Results - Abdominal Ultrasound",
                    "lines": [
                        "No gallstones or biliary ductal dilation.",
                        "Liver echotexture is mildly heterogeneous without focal mass in this synthetic report.",
                        "Imaging does not explain iron deficiency anemia; endoscopic evaluation remains clinically relevant.",
                    ],
                    "signer": "Radiology Review",
                    "use_ultrasound": True,
                }
            ],
        },
        {
            "record_label": "RP04",
            "title": "Neurology Referral Packet",
            "target_pages": 16,
            "urgency": "Expedited",
            "referral_reason": "Recurrent transient neurologic symptoms with abnormal headache pattern",
            "requested_specialty": "Neurology",
            "patient": make_patient(4, "Theo Wallace", "06/19/1990", "Commercial PPO"),
            "referring_provider": make_provider(13, "Harbor Family Medicine", "Mina Avery, MD", "Family Medicine"),
            "receiving_provider": make_provider(4, "Clearview Neurology", "Rachel Kim, MD", "Neurology"),
            "diagnoses": [
                ("G43.109", "Migraine with aura, not intractable"),
                ("R20.2", "Paresthesia of skin"),
                ("R42", "Dizziness and giddiness"),
            ],
            "medications": ["Sumatriptan 50 mg as needed", "Magnesium oxide 400 mg daily", "Meclizine 25 mg as needed"],
            "allergies": ["No known drug allergies"],
            "office_notes": [
                {
                    "date": "04/12/2026",
                    "title": "Primary Care Office Note",
                    "subjective": "Episodes of visual aura, unilateral headache, dizziness, and transient right hand tingling.",
                    "assessment": [
                        "Neurologic exam normal between episodes.",
                        "Symptoms are recurrent and increasing in frequency.",
                        "No persistent weakness, speech deficit, or seizure activity reported.",
                    ],
                    "plan": [
                        "Refer to neurology for migraine versus transient neurologic event evaluation.",
                        "Order baseline labs and brain imaging.",
                        "Review emergency precautions for persistent neurologic deficit.",
                    ],
                },
                {
                    "date": "04/25/2026",
                    "title": "Headache Follow-Up Note",
                    "subjective": "Two additional episodes occurred despite hydration, sleep changes, and magnesium trial.",
                    "assessment": [
                        "Headaches remain unilateral with photophobia and nausea.",
                        "Paresthesia resolves within thirty minutes.",
                        "Brain imaging report is available for neurology review.",
                    ],
                    "plan": [
                        "Send expedited neurology referral.",
                        "Maintain symptom diary and avoid medication overuse.",
                    ],
                },
            ],
            "progress_notes": [
                {
                    "date": "05/02/2026",
                    "title": "Referral Coordination Progress Note",
                    "events": [
                        "Neurology requested office notes, symptom diary, basic labs, and imaging summary.",
                        "Patient confirmed no current neurologic deficit during referral call.",
                        "Packet marked expedited due to increasing frequency of transient symptoms.",
                    ],
                    "next_steps": [
                        "Neurology to triage appointment timing.",
                        "Primary care to update medication list after specialist plan is received.",
                    ],
                }
            ],
            "lab_results": [
                ("04/12/2026", "CBC WBC", "6.4 K/uL", "4.0-11.0", "", "Baseline"),
                ("04/12/2026", "Hemoglobin", "14.1 g/dL", "13.5-17.5", "", "Stable"),
                ("04/12/2026", "Sodium", "139 mmol/L", "136-145", "", "Stable"),
                ("04/12/2026", "TSH", "2.2 uIU/mL", "0.4-4.0", "", "Within range"),
                ("04/12/2026", "B12", "356 pg/mL", "200-900", "", "Low-normal"),
                ("04/12/2026", "A1c", "5.4 %", "4.0-5.6", "", "Normal"),
                ("04/25/2026", "ESR", "7 mm/hr", "0-20", "", "No inflammatory pattern"),
            ],
            "imaging_reports": [
                {
                    "date": "04/28/2026",
                    "modality": "CT head without contrast",
                    "title": "Imaging Results - CT Head",
                    "lines": [
                        "No acute intracranial hemorrhage, mass effect, or midline shift.",
                        "Ventricles are normal in size for age.",
                        "No acute imaging finding to explain transient symptoms in this synthetic report.",
                    ],
                    "signer": "Radiology Review",
                    "use_ultrasound": False,
                }
            ],
        },
        {
            "record_label": "RP05",
            "title": "Pulmonology Referral Packet",
            "target_pages": 20,
            "urgency": "Soon",
            "referral_reason": "Persistent cough and abnormal pulmonary function screening after respiratory infection",
            "requested_specialty": "Pulmonology",
            "patient": make_patient(5, "Iris Coleman", "02/07/1958", "Medicare Advantage"),
            "referring_provider": make_provider(14, "Harbor Family Medicine", "Mina Avery, MD", "Family Medicine"),
            "receiving_provider": make_provider(5, "Summit Pulmonary Associates", "Caleb Wright, MD", "Pulmonology"),
            "diagnoses": [
                ("R05.3", "Chronic cough"),
                ("R06.2", "Wheezing"),
                ("J44.9", "Chronic obstructive pulmonary disease, unspecified"),
            ],
            "medications": ["Albuterol inhaler as needed", "Tiotropium inhaler daily", "Prednisone taper completed"],
            "allergies": ["Azithromycin - nausea"],
            "office_notes": [
                {
                    "date": "03/31/2026",
                    "title": "Primary Care Office Note",
                    "subjective": "Six weeks of cough, wheeze, and exertional shortness of breath after bronchitis treatment.",
                    "assessment": [
                        "Diffuse expiratory wheeze improved with bronchodilator treatment.",
                        "Oxygen saturation stable at rest but drops mildly after hallway walk.",
                        "Cough persists despite antibiotic course and steroid taper.",
                    ],
                    "plan": [
                        "Refer to pulmonology for chronic cough and COPD assessment.",
                        "Send chest imaging, office spirometry, and medication response history.",
                        "Continue maintenance inhaler pending specialist recommendations.",
                    ],
                },
                {
                    "date": "04/18/2026",
                    "title": "Respiratory Follow-Up Note",
                    "subjective": "Cough is less productive but dyspnea remains with stairs and longer walks.",
                    "assessment": [
                        "Office spirometry suggests obstructive pattern.",
                        "No fever or focal consolidation signs today.",
                        "Patient is using rescue inhaler several times weekly.",
                    ],
                    "plan": [
                        "Pulmonology referral updated with spirometry values.",
                        "Review inhaler technique and trigger avoidance.",
                    ],
                },
            ],
            "progress_notes": [
                {
                    "date": "05/01/2026",
                    "title": "Referral Coordination Progress Note",
                    "events": [
                        "Pulmonology requested recent imaging, spirometry, oxygen saturation trend, and medication trials.",
                        "Referral packet assembled with office notes, lab screening, and radiology interpretation.",
                        "Patient prefers clinic location with onsite pulmonary function testing.",
                    ],
                    "next_steps": [
                        "Pulmonology to schedule consultation and full pulmonary function test.",
                        "Primary care to monitor for fever, worsening dyspnea, or resting hypoxia.",
                    ],
                }
            ],
            "lab_results": [
                ("03/31/2026", "CBC WBC", "8.9 K/uL", "4.0-11.0", "", "No leukocytosis"),
                ("03/31/2026", "Hemoglobin", "13.0 g/dL", "12.0-16.0", "", "Stable"),
                ("03/31/2026", "Eosinophils", "5.2 %", "0.0-5.0", "H", "Mild elevation"),
                ("03/31/2026", "BNP", "64 pg/mL", "0-100", "", "Not suggestive of fluid overload"),
                ("04/18/2026", "CO2", "29 mmol/L", "22-29", "", "Upper range"),
                ("04/18/2026", "Creatinine", "0.92 mg/dL", "0.60-1.20", "", "Baseline"),
                ("04/18/2026", "CRP", "4.9 mg/L", "0.0-5.0", "", "Borderline"),
            ],
            "imaging_reports": [
                {
                    "date": "04/02/2026",
                    "modality": "Chest radiograph",
                    "title": "Imaging Results - Chest X-Ray",
                    "lines": [
                        "Mild hyperinflation without focal airspace consolidation.",
                        "No pleural effusion or pneumothorax.",
                        "Findings support outpatient pulmonary evaluation in the setting of chronic cough.",
                    ],
                    "signer": "Radiology Review",
                    "use_ultrasound": False,
                },
                {
                    "date": "04/20/2026",
                    "modality": "Chest CT summary",
                    "title": "Imaging Results - Chest CT Summary",
                    "lines": [
                        "Mild bronchial wall thickening in the lower lobes.",
                        "No suspicious pulmonary nodule in this synthetic referral report.",
                        "No acute infiltrate; correlate with pulmonary function testing.",
                    ],
                    "signer": "Radiology Review",
                    "use_ultrasound": False,
                },
            ],
        },
    ]


def diagnosis_rows(spec: PacketSpec) -> List[List[str]]:
    return [[code, desc, "Active referral diagnosis"] for code, desc in spec["diagnoses"]]


def lab_rows(spec: PacketSpec, offset: int = 0) -> List[List[str]]:
    rows = [[str(v) for v in row] for row in spec["lab_results"]]
    if not rows:
        return []
    shift = offset % len(rows)
    return rows[shift:] + rows[:shift]


def add_fax_cover_page(doc: PDFDocument, spec: PacketSpec, page_num: int) -> int:
    patient = spec["patient"]
    referring = spec["referring_provider"]
    receiving = spec["receiving_provider"]
    header = f"{spec['record_label']} | {spec['requested_specialty']} | Referral Packet"
    return note_page(
        doc,
        page_num,
        patient["name"],
        patient["mrn"],
        header,
        "Fax Cover Sheet and Referral Face Sheet",
        meta_pairs=[
            ("To", f"{receiving['clinician']} / {receiving['facility']}"),
            ("To Fax", receiving["fax"]),
            ("From", f"{referring['clinician']} / {referring['facility']}"),
            ("From Fax", referring["fax"]),
            ("Patient", patient["name"]),
            ("DOB", patient["dob"]),
            ("MRN", patient["mrn"]),
            ("Urgency", spec["urgency"]),
            ("Specialty", spec["requested_specialty"]),
            ("Pages", str(spec["target_pages"])),
        ],
        sections=[
            (
                "Referral Request",
                "paragraph",
                f"Please evaluate this synthetic patient for {spec['referral_reason'].lower()}. The packet includes office/progress notes, lab results, and imaging results for referral intake testing.",
            ),
            (
                "Packet Contents",
                "bullets",
                [
                    "Fax cover sheet and referral face sheet",
                    "Office and progress notes",
                    "Lab result summary",
                    "Imaging result report",
                ],
            ),
        ],
        signature=(referring["clinician"], referring["specialty"], "05/12/2026 09:15"),
        scanned=True,
    )


def add_referral_summary_page(doc: PDFDocument, spec: PacketSpec, page_num: int) -> int:
    patient = spec["patient"]
    receiving = spec["receiving_provider"]
    header = f"{spec['record_label']} | {spec['requested_specialty']} | Referral Packet"
    return note_page(
        doc,
        page_num,
        patient["name"],
        patient["mrn"],
        header,
        "Referral Summary and Demographics",
        meta_pairs=[
            ("Patient", patient["name"]),
            ("DOB", patient["dob"]),
            ("MRN", patient["mrn"]),
            ("Phone", patient["phone"]),
            ("Insurance", patient["insurance"]),
            ("Receiving Facility", receiving["facility"]),
            ("Specialist", receiving["clinician"]),
            ("Specialty", receiving["specialty"]),
            ("NPI", receiving["npi"]),
            ("Contact", receiving["contact"]),
        ],
        sections=[
            ("Referral Reason", "paragraph", str(spec["referral_reason"])),
            ("Current Medications", "bullets", [str(v) for v in spec["medications"]]),
            ("Allergies", "bullets", [str(v) for v in spec["allergies"]]),
        ],
    )


def add_office_note_page(doc: PDFDocument, spec: PacketSpec, page_num: int, idx: int = 0) -> int:
    patient = spec["patient"]
    provider = spec["referring_provider"]
    notes = spec["office_notes"]
    note = notes[idx % len(notes)]
    header = f"{spec['record_label']} | {spec['requested_specialty']} | Referral Packet"
    return note_page(
        doc,
        page_num,
        patient["name"],
        patient["mrn"],
        header,
        str(note["title"]),
        meta_pairs=[
            ("Date", str(note["date"])),
            ("Author", provider["clinician"]),
            ("Facility", provider["facility"]),
            ("Reason", str(spec["referral_reason"])),
        ],
        sections=[
            ("Subjective", "paragraph", str(note["subjective"])),
            ("Assessment", "bullets", [str(v) for v in note["assessment"]]),
            ("Plan", "bullets", [str(v) for v in note["plan"]]),
        ],
        signature=(provider["clinician"], provider["specialty"], f"{note['date']} 16:20"),
        header_suffix=f"Office {idx + 1}",
    )


def add_progress_note_page(doc: PDFDocument, spec: PacketSpec, page_num: int, idx: int = 0) -> int:
    patient = spec["patient"]
    provider = spec["referring_provider"]
    notes = spec["progress_notes"]
    note = notes[idx % len(notes)]
    header = f"{spec['record_label']} | {spec['requested_specialty']} | Referral Packet"
    return note_page(
        doc,
        page_num,
        patient["name"],
        patient["mrn"],
        header,
        str(note["title"]),
        meta_pairs=[
            ("Date", str(note["date"])),
            ("Author", provider["clinician"]),
            ("Referral Status", "Submitted"),
            ("Urgency", str(spec["urgency"])),
        ],
        sections=[
            ("Events Since Referral", "bullets", [str(v) for v in note["events"]]),
            ("Next Steps", "bullets", [str(v) for v in note["next_steps"]]),
        ],
        signature=(provider["clinician"], "Referral Progress Note", f"{note['date']} 10:30"),
        header_suffix=f"Progress {idx + 1}",
    )


def add_lab_results_page(doc: PDFDocument, spec: PacketSpec, page_num: int, idx: int = 0) -> int:
    patient = spec["patient"]
    header = f"{spec['record_label']} | {spec['requested_specialty']} | Referral Packet"
    return table_page(
        doc,
        page_num,
        patient["name"],
        patient["mrn"],
        header,
        "Lab Results",
        columns=[
            ("Date", 64),
            ("Test", 118),
            ("Result", 76),
            ("Reference", 82),
            ("Flag", 42),
            ("Referral Note", 158),
        ],
        rows=lab_rows(spec, idx),
        notes=[
            "Lab values are synthetic and included for referral intake, routing, and clinical-document extraction testing.",
            f"Referral driver: {spec['referral_reason']}.",
        ],
        header_suffix=f"Labs {idx + 1}",
    )


def add_imaging_results_page(doc: PDFDocument, spec: PacketSpec, page_num: int, idx: int = 0) -> int:
    patient = spec["patient"]
    report = spec["imaging_reports"][idx % len(spec["imaging_reports"])]
    header = f"{spec['record_label']} | {spec['requested_specialty']} | Referral Packet"
    lines = [
        f"Date: {report['date']}. Modality: {report['modality']}.",
        *[str(v) for v in report["lines"]],
    ]
    return image_report_page(
        doc,
        page_num,
        patient["name"],
        patient["mrn"],
        header,
        str(report["title"]),
        report_lines=lines,
        signer=(str(report["signer"]), "Diagnostic Imaging", f"{report['date']} 13:05"),
        use_ultrasound=bool(report.get("use_ultrasound")),
    )


def add_diagnosis_medication_page(doc: PDFDocument, spec: PacketSpec, page_num: int) -> int:
    patient = spec["patient"]
    header = f"{spec['record_label']} | {spec['requested_specialty']} | Referral Packet"
    return table_page(
        doc,
        page_num,
        patient["name"],
        patient["mrn"],
        header,
        "Problem List and Medication Context",
        columns=[("Code", 72), ("Description", 248), ("Status", 110), ("Medication Context", 110)],
        rows=[
            [code, desc, "Active", spec["medications"][idx % len(spec["medications"])]]
            for idx, (code, desc) in enumerate(spec["diagnoses"])
        ],
        notes=[
            "Problem and medication context supports specialist review and referral triage.",
            "All content is synthetic and should not be used for clinical care.",
        ],
    )


def add_referral_correspondence_page(doc: PDFDocument, spec: PacketSpec, page_num: int, idx: int) -> int:
    patient = spec["patient"]
    referring = spec["referring_provider"]
    receiving = spec["receiving_provider"]
    header = f"{spec['record_label']} | {spec['requested_specialty']} | Referral Packet"
    return note_page(
        doc,
        page_num,
        patient["name"],
        patient["mrn"],
        header,
        "Referral Correspondence",
        meta_pairs=[
            ("From", referring["contact"]),
            ("To", receiving["contact"]),
            ("Specialty", receiving["specialty"]),
            ("Status", "Pending specialist review"),
        ],
        sections=[
            (
                "Message",
                "paragraph",
                f"Referral documents were transmitted to {receiving['facility']} for {spec['requested_specialty'].lower()} review. Please contact {referring['facility']} if additional source documents are needed.",
            ),
            (
                "Included Clinical Materials",
                "bullets",
                [
                    "Office/progress notes",
                    "Problem list and medication context",
                    "Lab result trend",
                    "Imaging result report",
                ],
            ),
        ],
        signature=(referring["contact"], "Referral Coordination", f"05/{12 + idx:02d}/2026 11:05"),
        scanned=True,
        header_suffix=f"Correspondence {idx + 1}",
    )


def build_referral_packet(spec: PacketSpec, out_pdf: Path, out_json: Path) -> None:
    doc = PDFDocument()
    doc._scan_targets = []
    page_num = 1
    target_pages = int(spec["target_pages"])

    page_num = add_fax_cover_page(doc, spec, page_num)
    page_num = add_office_note_page(doc, spec, page_num)
    page_num = add_progress_note_page(doc, spec, page_num)
    page_num = add_lab_results_page(doc, spec, page_num)
    page_num = add_imaging_results_page(doc, spec, page_num)

    supplemental_idx = 0
    while page_num <= target_pages:
        cycle = supplemental_idx % 6
        if cycle == 0:
            page_num = add_referral_summary_page(doc, spec, page_num)
        elif cycle == 1:
            page_num = add_diagnosis_medication_page(doc, spec, page_num)
        elif cycle == 2:
            page_num = add_office_note_page(doc, spec, page_num, supplemental_idx + 1)
        elif cycle == 3:
            page_num = add_lab_results_page(doc, spec, page_num, supplemental_idx + 1)
        elif cycle == 4:
            page_num = add_imaging_results_page(doc, spec, page_num, supplemental_idx + 1)
        else:
            page_num = add_referral_correspondence_page(doc, spec, page_num, supplemental_idx)
        supplemental_idx += 1

    save_packet_pdf(doc, out_pdf)
    payload = dict(spec)
    payload["packet_type"] = "specialty_referral_packet"
    payload["packet_target_pages"] = target_pages
    payload["packet_generated_pages"] = len(doc.pages)
    payload["required_sections"] = [
        "fax cover sheet",
        "office/progress notes",
        "lab results",
        "imaging results",
    ]
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def write_referral_packets(root: Path) -> None:
    out_dir = root / "Referral Packets"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: List[Dict[str, Any]] = []
    for spec in make_referral_packet_specs():
        stem = f"{spec['record_label'].lower()}_{slugify(str(spec['title']))}"
        pdf_path = out_dir / f"{stem}.pdf"
        json_path = out_dir / f"{stem}.json"
        build_referral_packet(spec, pdf_path, json_path)
        manifest.append(
            {
                "record": str(spec["record_label"]),
                "title": str(spec["title"]),
                "requested_specialty": str(spec["requested_specialty"]),
                "target_pages": int(spec["target_pages"]),
                "pdf": str(pdf_path),
                "json": str(json_path),
            }
        )
        print(f"Wrote referral PDF: {pdf_path}")
        print(f"Wrote referral JSON: {json_path}")
    manifest_path = out_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote referral manifest: {manifest_path}")


def main() -> None:
    write_referral_packets(Path(os.getcwd()))


if __name__ == "__main__":
    main()
