from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Dict, List

from .deterministic import SeedBundle


SYNTHETIC_REFERENCE_DATE = date(2026, 8, 6)


@dataclass
class PatientDemographics:
    name: str
    dob: str
    age: int
    gender: str
    insurance_type: str
    member_id: str
    mrn: str
    pcp: str
    phone: str
    address: str


@dataclass
class EncounterMeta:
    encounter_id: str
    encounter_type: str
    facility: str
    record_label: str
    acuity: str
    theme: str
    admission_date: str
    discharge_date: str
    length_of_stay_days: int
    attending_physician: str


@dataclass
class Condition:
    code: str
    name: str
    status: str
    onset: str


@dataclass
class Medication:
    name: str
    dose: str
    route: str
    frequency: str
    start_date: str
    indication: str
    prescriber: str
    prn: bool = False


@dataclass
class Allergy:
    substance: str
    reaction: str
    severity: str


@dataclass
class LabResult:
    date: str
    time: str
    wbc: float
    creatinine: float
    lactate: float
    hemoglobin: float


@dataclass
class RadiologyReport:
    study: str
    date: str
    indication: str
    findings: List[str]
    impression: List[str]
    radiologist: str


@dataclass
class ProcedureReport:
    procedure: str
    date: str
    indication: str
    findings: List[str]
    complications: str
    surgeon: str


@dataclass
class PathologyReport:
    specimen: str
    date: str
    findings: List[str]
    diagnosis: str
    pathologist: str


@dataclass
class ProgressNote:
    date: str
    author: str
    subjective: List[str]
    objective: List[str]
    assessment: List[str]
    plan: List[str]


@dataclass
class AnesthesiaRecord:
    date: str
    anesthesiologist: str
    asa_class: str
    anesthesia_type: str
    airway: str
    events: List[str]


@dataclass
class MarEntry:
    date: str
    time: str
    medication: str
    dose: str
    status: str
    nurse: str


@dataclass
class AppealArtifacts:
    requested_service: str
    denial_reason: str
    conservative_care_summary: List[str]


@dataclass
class CanonicalEncounter:
    patient: PatientDemographics
    encounter: EncounterMeta
    chief_complaint: str
    hpi: str
    conditions: List[Condition] = field(default_factory=list)
    medications: List[Medication] = field(default_factory=list)
    allergies: List[Allergy] = field(default_factory=list)
    labs: List[LabResult] = field(default_factory=list)
    radiology_reports: List[RadiologyReport] = field(default_factory=list)
    procedure_reports: List[ProcedureReport] = field(default_factory=list)
    pathology_reports: List[PathologyReport] = field(default_factory=list)
    progress_notes: List[ProgressNote] = field(default_factory=list)
    anesthesia_records: List[AnesthesiaRecord] = field(default_factory=list)
    mar_entries: List[MarEntry] = field(default_factory=list)
    discharge_diagnoses: List[str] = field(default_factory=list)
    hospital_course: List[str] = field(default_factory=list)
    follow_up_plan: List[str] = field(default_factory=list)
    discharge_disposition: str = "Home"
    appeal: AppealArtifacts | None = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


SCENARIOS = {
    "provider_sepsis": {
        "theme": "Sepsis with organ dysfunction",
        "acuity": "Moderate Acuity",
        "chief_complaint": "Fever, hypotension, and confusion",
    },
    "resp_failure": {
        "theme": "Respiratory failure with multiple comorbidities",
        "acuity": "High Acuity / Revenue Impact",
        "chief_complaint": "Severe dyspnea and hypoxemia",
    },
    "lumbar_mri_appeal": {
        "theme": "Failed conservative care with progressive lumbar radiculopathy",
        "acuity": "Outpatient Appeal Packet",
        "chief_complaint": "Low back pain radiating to left leg with progressive weakness",
    },
}


def _fmt(d: date) -> str:
    return d.isoformat()


def build_seeded_encounter(
    seed: int,
    *,
    scenario: str = "provider_sepsis",
    record_label: str = "A",
    facility: str = "Lumen Harbor Medical Center (fictional)",
) -> CanonicalEncounter:
    if scenario not in SCENARIOS:
        valid = ", ".join(sorted(SCENARIOS))
        raise ValueError(f"Unknown scenario '{scenario}'. Valid values: {valid}")

    seeds = SeedBundle(seed)
    prng = seeds.rng("patient")

    first_names = ["Jordan", "Renee", "Daniel", "Jane", "Gerald", "Maria"]
    last_names = ["Alvarez", "Caldwell", "Morris", "Doe", "Norris", "Santos"]
    genders = ["Female", "Male"]

    name = f"{prng.choice(first_names)} {prng.choice(last_names)}"
    gender = prng.choice(genders)
    age = prng.randint(41, 76)
    dob_year = SYNTHETIC_REFERENCE_DATE.year - age
    dob = date(dob_year, prng.randint(1, 12), prng.randint(1, 28))

    admit_date = date(2026, 2, prng.randint(1, 16))
    los = prng.randint(5, 9)
    discharge_date = admit_date + timedelta(days=los)

    scenario_cfg = SCENARIOS[scenario]

    patient = PatientDemographics(
        name=name,
        dob=_fmt(dob),
        age=age,
        gender=gender,
        insurance_type="Medicare Advantage PPO" if age >= 65 else "Commercial PPO",
        member_id=f"SYN-M-{prng.randint(1000000, 9999999)}",
        mrn=f"SYN-{prng.randint(1000000, 9999999)}",
        pcp="Nina Patel, MD",
        phone=f"(615) 555-{prng.randint(1000, 9999)}",
        address=f"{prng.randint(100, 9999)} Meadow Ridge Ln, Franklin, TN 37067",
    )

    encounter = EncounterMeta(
        encounter_id=f"SYN-ENC-{seeds.for_label('encounter') % 100000:05d}",
        encounter_type="Inpatient" if scenario != "lumbar_mri_appeal" else "Outpatient",
        facility=facility,
        record_label=record_label,
        acuity=scenario_cfg["acuity"],
        theme=scenario_cfg["theme"],
        admission_date=_fmt(admit_date),
        discharge_date=_fmt(discharge_date),
        length_of_stay_days=los,
        attending_physician="Priya Raman, MD" if scenario != "lumbar_mri_appeal" else "Emily Roberts, MD",
    )

    conditions = [
        Condition("I10", "Essential hypertension", "Active", "2018"),
        Condition("E11.9", "Type 2 diabetes mellitus", "Active", "2019"),
        Condition("N18.3", "Chronic kidney disease stage 3", "Active", "2021"),
        Condition("J44.9", "COPD", "Active", "2017"),
    ]
    if scenario == "provider_sepsis":
        conditions.extend([
            Condition("A41.9", "Sepsis", "Admission", _fmt(admit_date)),
            Condition("N17.9", "Acute kidney injury", "Admission", _fmt(admit_date)),
        ])
    if scenario == "resp_failure":
        conditions.extend([
            Condition("J96.01", "Acute hypoxic respiratory failure", "Admission", _fmt(admit_date)),
            Condition("E46", "Protein-calorie malnutrition", "Active", "2025"),
            Condition("I48.91", "Atrial fibrillation", "Hospital-acquired", _fmt(admit_date + timedelta(days=2))),
        ])
    if scenario == "lumbar_mri_appeal":
        conditions = [
            Condition("M54.16", "Lumbar radiculopathy", "Active", "2023-05-22"),
            Condition("M51.26", "Lumbar disc displacement", "Active", "2023-05-22"),
            Condition("G89.29", "Chronic pain", "Active", "2023"),
        ]

    meds = [
        Medication("Metformin", "1000 mg", "PO", "BID", _fmt(admit_date), "Diabetes", "N. Patel, MD"),
        Medication("Losartan", "50 mg", "PO", "Daily", _fmt(admit_date), "Hypertension", "N. Patel, MD"),
        Medication("Rosuvastatin", "10 mg", "PO", "Nightly", _fmt(admit_date), "Hyperlipidemia", "N. Patel, MD"),
        Medication("Furosemide", "40 mg", "IV", "Daily", _fmt(admit_date), "Volume control", "Hospitalist"),
        Medication("Heparin", "5000 units", "SQ", "q8h", _fmt(admit_date), "VTE prophylaxis", "Hospitalist"),
    ]
    if scenario == "resp_failure":
        meds.extend(
            [
                Medication("Insulin glargine", "24 units", "SQ", "Nightly", _fmt(admit_date), "Diabetes", "Endocrinology"),
                Medication("Warfarin", "5 mg", "PO", "Daily", _fmt(admit_date), "Atrial fibrillation", "Cardiology"),
                Medication("Piperacillin-tazobactam", "4.5 g", "IV", "q6h", _fmt(admit_date + timedelta(days=3)), "Possible HAI", "Infectious Disease"),
            ]
        )
    if scenario == "lumbar_mri_appeal":
        meds = [
            Medication("Naproxen", "500 mg", "PO", "BID", "2023-05-22", "Pain", "Emily Roberts, MD"),
            Medication("Gabapentin", "300 mg", "PO", "TID", "2023-06-01", "Radicular pain", "Emily Roberts, MD"),
            Medication("Cyclobenzaprine", "10 mg", "PO", "Nightly PRN", "2023-06-08", "Muscle spasm", "Emily Roberts, MD", prn=True),
            Medication("Tramadol", "50 mg", "PO", "q8h PRN", "2023-07-21", "Breakthrough pain", "Emily Roberts, MD", prn=True),
        ]

    allergies = [
        Allergy("Penicillin", "Pruritic rash", "Moderate"),
        Allergy("Lisinopril", "Persistent cough", "Mild"),
    ]

    labs: List[LabResult] = []
    for day_idx in range(5):
        d = admit_date + timedelta(days=day_idx)
        for tm in ["06:00", "12:00", "18:00"]:
            wbc = round(15.5 - day_idx * 1.8 + (0.4 if tm == "12:00" else 0.0), 1)
            cr = round(1.9 - day_idx * 0.2 + (0.05 if tm == "06:00" else 0.0), 2)
            lac = round(4.5 - day_idx * 0.6 + (0.2 if tm == "06:00" else 0.0), 1)
            hgb = round(10.9 - day_idx * 0.15, 1)
            if scenario == "resp_failure":
                lac = round(2.8 - day_idx * 0.3 + (0.1 if tm == "06:00" else 0.0), 1)
                wbc = round(13.2 - day_idx * 1.1, 1)
            if scenario == "lumbar_mri_appeal":
                wbc = 7.8
                cr = 0.9
                lac = 1.2
                hgb = 12.4
            labs.append(LabResult(_fmt(d), tm, wbc, cr, max(lac, 0.8), hgb))

    radiology_reports = [
        RadiologyReport(
            "Chest X-ray",
            _fmt(admit_date),
            "Dyspnea / sepsis workup",
            ["Patchy bibasilar opacities", "No pleural effusion", "Cardiomediastinal silhouette stable"],
            ["Mild bibasilar atelectatic change"],
            "A. Simmons, MD",
        )
    ]
    if scenario == "lumbar_mri_appeal":
        radiology_reports = [
            RadiologyReport(
                "Lumbar X-ray",
                "2023-05-22",
                "Persistent low-back pain",
                ["Mild L4-L5 degenerative disc narrowing", "No acute fracture"],
                ["Non-specific plain film findings for radiculopathy"],
                "A. Simmons, MD",
            ),
            RadiologyReport(
                "Lumbar CT",
                "2023-06-05",
                "Progressive leg pain and numbness",
                ["Left paracentral L4-L5 protrusion", "Soft tissue detail limited"],
                ["MRI recommended for nerve-root assessment"],
                "A. Simmons, MD",
            ),
        ]

    procedure_reports = [
        ProcedureReport(
            "Central line placement",
            _fmt(admit_date),
            "Vasopressor requirement",
            ["Right internal jugular line placed under ultrasound guidance"],
            "None",
            "R. Thompson, MD",
        )
    ]
    pathology_reports = [
        PathologyReport(
            "Blood culture set #1",
            _fmt(admit_date + timedelta(days=1)),
            ["Gram stain with gram-negative rods"],
            "Escherichia coli bacteremia",
            "L. Ortiz, MD",
        )
    ]
    if scenario == "lumbar_mri_appeal":
        procedure_reports = [
            ProcedureReport(
                "L4-L5 transforaminal ESI",
                "2023-07-18",
                "Persistent radicular symptoms",
                ["Fluoro-guided injection completed"],
                "None",
                "R. Thompson, MD",
            )
        ]
        pathology_reports = []

    progress_notes: List[ProgressNote] = []
    for day_idx in range(1, 5):
        d = admit_date + timedelta(days=day_idx - 1)
        progress_notes.append(
            ProgressNote(
                _fmt(d),
                "Hospitalist Team",
                [
                    "Patient reports persistent fatigue but improving appetite.",
                    "Dyspnea improved compared with admission." if scenario != "lumbar_mri_appeal" else "Pain remains 8/10 with sitting intolerance.",
                ],
                [
                    "Vitals reviewed and trended.",
                    "No new focal neurologic deficits." if scenario != "lumbar_mri_appeal" else "Left lower extremity strength remains reduced.",
                ],
                [
                    "Clinical trajectory gradually improving.",
                    "Continue active management of comorbid conditions.",
                ],
                [
                    "Continue current treatment plan.",
                    "Reassess labs and symptoms daily.",
                ],
            )
        )

    anesthesia_records = [
        AnesthesiaRecord(
            _fmt(admit_date + timedelta(days=2)),
            "M. Hernandez, MD",
            "III",
            "General endotracheal",
            "Cormack-Lehane grade II",
            ["Hemodynamics stabilized with low-dose pressor", "No airway complications"],
        )
    ]

    mar_entries: List[MarEntry] = []
    for idx, med in enumerate(meds[:8]):
        mar_entries.append(
            MarEntry(
                _fmt(admit_date + timedelta(days=idx % 3)),
                ["06:00", "10:00", "14:00", "18:00", "22:00"][idx % 5],
                med.name,
                med.dose,
                "Given" if idx % 5 != 0 else "Held",
                f"RN-{idx + 11}",
            )
        )

    discharge_diagnoses = [
        "Sepsis due to E. coli bacteremia",
        "Acute kidney injury, improved",
        "Type 2 diabetes mellitus",
        "Essential hypertension",
    ]
    if scenario == "resp_failure":
        discharge_diagnoses = [
            "Acute hypoxic respiratory failure",
            "COPD exacerbation",
            "Atrial fibrillation with rapid ventricular response",
            "CKD stage 3",
            "Protein-calorie malnutrition",
        ]
    if scenario == "lumbar_mri_appeal":
        discharge_diagnoses = [
            "Lumbar radiculopathy",
            "Lumbar disc displacement",
            "Progressive functional impairment after failed conservative care",
        ]

    hospital_course = [
        "Initial instability improved with protocolized treatment and close monitoring.",
        "Serial labs demonstrated improving lactate and renal function trends.",
        "Specialty teams documented rationale for continued escalation and follow-up.",
    ]
    if scenario == "lumbar_mri_appeal":
        hospital_course = [
            "Completed 6 weeks of supervised PT with worsening ODI and persistent radicular pain.",
            "Medication and injection history showed no durable functional improvement.",
            "Serial exams documented progressive neurologic deficits, supporting lumbar MRI necessity.",
        ]

    follow_up_plan = [
        "Primary care follow-up within 7 days.",
        "Specialty follow-up within 14 days.",
        "Repeat labs in outpatient setting.",
    ]
    if scenario == "lumbar_mri_appeal":
        follow_up_plan = [
            "Urgent payer reconsideration for CPT 72148 lumbar MRI without contrast.",
            "Spine specialist follow-up after imaging authorization.",
            "Continue home program pending definitive imaging.",
        ]

    appeal = None
    if scenario == "lumbar_mri_appeal":
        appeal = AppealArtifacts(
            requested_service="CPT 72148 MRI lumbar spine without contrast",
            denial_reason="Denial cites insufficient medical necessity documentation.",
            conservative_care_summary=[
                "12 PT visits completed over 6 weeks with worsening ODI trend.",
                "Medication trials including NSAID, gabapentin, and rescue analgesics with poor durable effect.",
                "Injection procedures provided only transient relief.",
            ],
        )

    return CanonicalEncounter(
        patient=patient,
        encounter=encounter,
        chief_complaint=scenario_cfg["chief_complaint"],
        hpi=(
            "Patient presented with multi-day symptom escalation and physiologic instability, requiring inpatient management."
            if scenario != "lumbar_mri_appeal"
            else "Three-month history of low-back pain radiating to left posterior leg with progressive weakness, numbness, and severe functional limitations despite conservative care."
        ),
        conditions=conditions,
        medications=meds,
        allergies=allergies,
        labs=labs,
        radiology_reports=radiology_reports,
        procedure_reports=procedure_reports,
        pathology_reports=pathology_reports,
        progress_notes=progress_notes,
        anesthesia_records=anesthesia_records,
        mar_entries=mar_entries,
        discharge_diagnoses=discharge_diagnoses,
        hospital_course=hospital_course,
        follow_up_plan=follow_up_plan,
        discharge_disposition="Home with outpatient follow-up" if scenario != "resp_failure" else "Skilled nursing facility",
        appeal=appeal,
    )
