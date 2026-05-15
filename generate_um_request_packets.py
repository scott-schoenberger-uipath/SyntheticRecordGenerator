#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from generate_long_form_packets import (
    maybe_reexec_in_scan_env,
    note_page,
    save_packet_pdf,
    table_page,
)
from generate_synthetic_patient_pdf import PDFDocument


PacketSpec = Dict[str, Any]


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower())
    return re.sub(r"_+", "_", slug).strip("_")


def make_member(idx: int, name: str, dob: str, plan: str) -> Dict[str, str]:
    return {
        "name": name,
        "dob": dob,
        "member_id": f"ACFC{820000 + idx:06d}",
        "address": f"{100 + idx} Harbor View Lane, Sample City, ST {19000 + idx}",
        "phone": f"555-01{idx:02d}",
        "plan": plan,
    }


def make_provider(idx: int, facility: str, clinician: str, specialty: str) -> Dict[str, str]:
    return {
        "facility": facility,
        "provider_name": clinician,
        "specialty": specialty,
        "provider_id": f"PRV{30000 + idx}",
        "npi": f"1740{idx:06d}",
        "fax": f"555-2{idx:02d}-44{idx:02d}",
        "phone": f"555-3{idx:02d}-88{idx:02d}",
        "contact": f"UM Coordinator {idx}",
    }


def make_packet_specs() -> List[PacketSpec]:
    return [
        {
            "record_label": "UM01",
            "title": "Outpatient MRI Prior Authorization",
            "taxonomy": "PH/BH PA New",
            "matrix_sheets": ["PA New", "OP PA Extension"],
            "action_type": "Create New Auth",
            "auth_request_type": "PH OP",
            "category": "standard_um",
            "target_pages": 5,
            "priority": "Standard",
            "episode_type": "Outpatient",
            "treatment_setting": "Outpatient hospital imaging",
            "treatment_type": "Advanced imaging",
            "existing_auth": "N/A",
            "member": make_member(1, "Amelia Hart", "03/14/1981", "Medicaid Managed Care"),
            "provider": make_provider(1, "Riverbend Orthopedics", "Nora Singh, MD", "Orthopedics"),
            "diagnoses": [
                ("M54.16", "Radiculopathy, lumbar region"),
                ("M51.26", "Other intervertebral disc displacement, lumbar region"),
            ],
            "service_lines": [
                ("72148", "MRI lumbar spine without contrast", "1 unit", "05/18/2026", "05/18/2026"),
            ],
            "clinical_summary": [
                "Eight weeks of conservative therapy completed with persistent left leg radicular pain.",
                "Straight-leg raise remains positive and exam documents reduced ankle reflex.",
                "MRI is requested to guide injection versus surgical consultation.",
            ],
            "review_focus": [
                "Confirm member identity, provider identifiers, diagnosis code, procedure code, start date, and urgent/standard flag.",
                "Validate that conservative care documentation supports advanced imaging criteria.",
            ],
            "attachments": [
                "Orthopedic office note",
                "Physical therapy discharge summary",
                "Medication trial list",
            ],
            "criteria": [
                ("Conservative therapy", "PT, NSAID, gabapentin, and activity modification documented"),
                ("Neurologic finding", "Positive SLR and reflex change present"),
                ("Decision impact", "Result determines injection or surgical pathway"),
            ],
        },
        {
            "record_label": "UM02",
            "title": "HIPAA Validation Faxback Exception",
            "taxonomy": "PH/BH HIPAA",
            "matrix_sheets": ["HIPAA"],
            "action_type": "Faxback",
            "auth_request_type": "All",
            "category": "faxback",
            "target_pages": 6,
            "priority": "Standard",
            "episode_type": "Outpatient",
            "treatment_setting": "Office",
            "treatment_type": "Incomplete authorization intake",
            "existing_auth": "N/A",
            "member": make_member(2, "Benjamin Ortiz", "09/02/1974", "Medicaid Managed Care"),
            "provider": make_provider(2, "Lakeside Digestive Health", "Evan Brooks, MD", "Gastroenterology"),
            "diagnoses": [
                ("R10.13", "Epigastric pain"),
                ("K21.9", "Gastro-esophageal reflux disease without esophagitis"),
            ],
            "service_lines": [
                ("43239", "Upper GI endoscopy with biopsy", "1 unit", "05/27/2026", "05/27/2026"),
            ],
            "clinical_summary": [
                "Fax lacks enough member identifiers to complete three-point validation.",
                "Provider name and fax are legible, but member DOB conflicts with plan record.",
                "Faxback requests corrected member ID, member name, and DOB before intake can proceed.",
            ],
            "review_focus": [
                "Use HIPAA taxonomy fields for Provider Name, Provider Fax, Member ID, Member Name, and Member DOB.",
                "Route as validation exception until required identity data is corrected.",
            ],
            "attachments": [
                "Original request form with mismatched DOB",
                "Provider fax cover page",
                "Plan member search screenshot placeholder",
            ],
            "criteria": [
                ("Provider name", "Meets minimum text validation"),
                ("Provider fax", "Matches 555-202-4402 return fax"),
                ("Member DOB", "Conflicts with eligibility record and requires correction"),
            ],
        },
        {
            "record_label": "UM03",
            "title": "Ineligible Member Authorization Faxback",
            "taxonomy": "PH/BH Ineligible",
            "matrix_sheets": ["Ineligible"],
            "action_type": "Faxback",
            "auth_request_type": "All",
            "category": "faxback",
            "target_pages": 8,
            "priority": "Standard",
            "episode_type": "Outpatient",
            "treatment_setting": "Ambulatory surgery center",
            "treatment_type": "Surgical authorization intake",
            "existing_auth": "N/A",
            "member": make_member(3, "Carmen Miles", "12/22/1967", "Expired Medicaid Managed Care"),
            "provider": make_provider(3, "Summit Ambulatory Surgery", "Maya Chen, MD", "General Surgery"),
            "diagnoses": [
                ("K80.20", "Calculus of gallbladder without cholecystitis without obstruction"),
            ],
            "service_lines": [
                ("47562", "Laparoscopic cholecystectomy", "1 unit", "06/03/2026", "06/03/2026"),
            ],
            "clinical_summary": [
                "Eligibility search shows no active coverage for the requested date of service.",
                "Faxback advises provider to confirm coverage or submit corrected insurance information.",
                "Clinical content is retained but not routed to medical review while eligibility is inactive.",
            ],
            "review_focus": [
                "Validate Member ID, Member Name, DOB, and coverage span before clinical routing.",
                "Document ineligible reason and faxback outcome.",
            ],
            "attachments": [
                "Surgery request form",
                "Eligibility response page",
                "Provider contact history",
            ],
            "criteria": [
                ("Eligibility", "Inactive for requested service date"),
                ("Faxback", "Provider notified with corrected resubmission instructions"),
                ("Clinical routing", "Held because eligibility fails business requirement"),
            ],
        },
        {
            "record_label": "UM04",
            "title": "Outpatient Therapy Extension Request",
            "taxonomy": "SC Therapy / OP PA Extension",
            "matrix_sheets": ["SC_Therapy", "OP PA Extension"],
            "action_type": "Extend Existing Auth",
            "auth_request_type": "PH OP",
            "category": "standard_um",
            "target_pages": 12,
            "priority": "Standard",
            "episode_type": "Outpatient",
            "treatment_setting": "Therapy clinic",
            "treatment_type": "Physical therapy extension",
            "existing_auth": "AUTH-PT-441902",
            "member": make_member(4, "Devon Reed", "05/11/1992", "Medicaid Managed Care"),
            "provider": make_provider(4, "Greenfield Rehabilitation", "Lila Morgan, PT", "Physical Therapy"),
            "diagnoses": [
                ("S83.511D", "Sprain of anterior cruciate ligament of right knee, subsequent encounter"),
                ("M25.561", "Pain in right knee"),
            ],
            "service_lines": [
                ("97110", "Therapeutic exercises", "12 visits", "05/20/2026", "07/03/2026"),
                ("97112", "Neuromuscular reeducation", "8 visits", "05/20/2026", "07/03/2026"),
            ],
            "clinical_summary": [
                "Member completed initial post-operative therapy but remains below expected functional benchmark.",
                "Gait mechanics, quad strength, and stair tolerance require additional supervised therapy.",
                "Extension request seeks additional visits under the existing outpatient authorization.",
            ],
            "review_focus": [
                "Map service-line table values for procedure code, units, start date, and end date.",
                "Confirm existing authorization number and extension dates.",
            ],
            "attachments": [
                "Initial PT evaluation",
                "Four-week progress note",
                "Surgeon protocol",
                "Visit attendance log",
            ],
            "criteria": [
                ("Functional progress", "Objective gains but incomplete goal attainment"),
                ("Visit use", "Initial authorized visits nearly exhausted"),
                ("Plan of care", "Therapist and surgeon document continued need"),
            ],
        },
        {
            "record_label": "UM05",
            "title": "Durable Medical Equipment Prior Authorization",
            "taxonomy": "CHC_KF / DME",
            "matrix_sheets": ["CHC_KF", "KF_New", "NH"],
            "action_type": "Create New Auth",
            "auth_request_type": "PH OP",
            "category": "standard_um",
            "target_pages": 18,
            "priority": "Standard",
            "episode_type": "Outpatient",
            "treatment_setting": "Home",
            "treatment_type": "DME rental or purchase",
            "existing_auth": "N/A",
            "member": make_member(5, "Elaine Parker", "08/19/1958", "Community HealthChoices"),
            "provider": make_provider(5, "Home Mobility Partners", "Caleb Wright, ATP", "DME Supplier"),
            "diagnoses": [
                ("G35", "Multiple sclerosis"),
                ("R26.2", "Difficulty in walking, not elsewhere classified"),
            ],
            "service_lines": [
                ("K0823", "Power wheelchair, group 2 standard", "1 purchase", "06/01/2026", "06/01/2026"),
                ("E0973", "Adjustable height armrests", "2 units", "06/01/2026", "06/01/2026"),
            ],
            "clinical_summary": [
                "Member cannot safely use cane, walker, or manual wheelchair due to upper-extremity fatigue.",
                "Home assessment supports use of a power mobility device for toileting, meals, and transfers.",
                "Provider requests purchase authorization with accessories listed as service lines.",
            ],
            "review_focus": [
                "Matrix examples include DME, home, provider NPI, member ID, and service-line procedure codes.",
                "Confirm medical necessity documentation includes home assessment and face-to-face evaluation.",
            ],
            "attachments": [
                "Face-to-face mobility exam",
                "Home assessment",
                "DME supplier quote",
                "Physical therapy mobility evaluation",
            ],
            "criteria": [
                ("Mobility limitation", "Prevents MRADLs in the home"),
                ("Least costly alternative", "Manual mobility ruled out"),
                ("Supplier detail", "HCPCS, units, accessories, and quote included"),
            ],
        },
        {
            "record_label": "UM06",
            "title": "Physical Health Concurrent Review New Request",
            "taxonomy": "PH Concurrent New",
            "matrix_sheets": ["CCR New"],
            "action_type": "Create New Auth",
            "auth_request_type": "PH CCR",
            "category": "concurrent_um",
            "target_pages": 24,
            "priority": "Urgent",
            "episode_type": "Inpatient",
            "treatment_setting": "Acute inpatient medical/surgical",
            "treatment_type": "Concurrent inpatient review",
            "existing_auth": "N/A",
            "member": make_member(6, "Felix Nguyen", "02/27/1949", "Medicaid Managed Care"),
            "provider": make_provider(6, "Northstar Medical Center", "Priya Desai, MD", "Hospital Medicine"),
            "diagnoses": [
                ("J18.9", "Pneumonia, unspecified organism"),
                ("J96.01", "Acute respiratory failure with hypoxia"),
                ("N17.9", "Acute kidney failure, unspecified"),
            ],
            "service_lines": [
                ("0110", "Medical/surgical inpatient bed", "4 days", "05/10/2026", "05/13/2026"),
            ],
            "admission_date": "05/10/2026",
            "length_of_stay": "4 days requested",
            "requested_level_of_care": "Acute inpatient",
            "clinical_summary": [
                "Member admitted through ED with hypoxia, fever, and imaging consistent with pneumonia.",
                "Requires IV antibiotics, oxygen titration, renal monitoring, and daily physician assessment.",
                "Concurrent request is submitted while services are already in progress.",
            ],
            "review_focus": [
                "CCR fields include transplant/NICU flags, member ID, diagnosis code table, admission date, LOS, level of care, setting, and treatment type.",
                "Assess whether inpatient criteria are met through current vitals, oxygen need, and IV therapy.",
            ],
            "attachments": [
                "ED note",
                "Admission H&P",
                "Chest imaging report",
                "Medication administration record",
                "Daily labs",
            ],
            "criteria": [
                ("Acute severity", "Hypoxia and abnormal labs require inpatient monitoring"),
                ("Active treatment", "IV antibiotics and oxygen support ongoing"),
                ("Discharge readiness", "Not met at time of request"),
            ],
        },
        {
            "record_label": "UM07",
            "title": "Behavioral Health Concurrent Review New Request",
            "taxonomy": "BH Concurrent New",
            "matrix_sheets": ["BH CCR New"],
            "action_type": "Create New Auth",
            "auth_request_type": "BH CCR",
            "category": "concurrent_um",
            "target_pages": 32,
            "priority": "Urgent",
            "episode_type": "BH IP",
            "treatment_setting": "Inpatient behavioral health",
            "treatment_type": "Acute psychiatric stabilization",
            "existing_auth": "N/A",
            "member": make_member(7, "Grace Patel", "11/30/2007", "Medicaid Managed Care"),
            "provider": make_provider(7, "Clearview Behavioral Health", "Marcus Reed, MD", "Psychiatry"),
            "diagnoses": [
                ("F33.2", "Major depressive disorder, recurrent severe without psychotic features"),
                ("R45.851", "Suicidal ideations"),
            ],
            "service_lines": [
                ("0124", "Inpatient psychiatric bed", "5 days", "05/09/2026", "05/13/2026"),
            ],
            "admission_date": "05/09/2026",
            "length_of_stay": "5 days requested",
            "requested_level_of_care": "Acute inpatient psychiatry",
            "clinical_summary": [
                "Member admitted after ED crisis evaluation with suicidal ideation and inability to maintain safety at home.",
                "Requires locked unit monitoring, medication initiation, therapy groups, and safety planning.",
                "Family meeting and step-down planning remain incomplete at initial concurrent review.",
            ],
            "review_focus": [
                "BH CCR fields include member ID, diagnosis table, admission date, LOS, requested level of care, treatment setting, and treatment type.",
                "Review risk assessment, observation level, medication response, and discharge safety plan.",
            ],
            "attachments": [
                "Crisis evaluation",
                "Psychiatric admission note",
                "Daily risk assessments",
                "Medication consent",
                "Family meeting plan",
            ],
            "criteria": [
                ("Safety risk", "Recent suicidal ideation with plan and impaired supervision"),
                ("Active treatment", "Medication start and daily psychiatry review"),
                ("Step-down readiness", "Safety plan not yet complete"),
            ],
        },
        {
            "record_label": "UM08",
            "title": "Inpatient Prior Authorization Extension With New Diagnosis",
            "taxonomy": "PH/BH IP PA Ext w New Dx",
            "matrix_sheets": ["IP PA Extension", "IP PA Ext w New Dx ", "IP PA Ext w Dx Updates"],
            "action_type": "Extend Existing Auth with Dx Changes",
            "auth_request_type": "PH IP",
            "category": "extension_um",
            "target_pages": 40,
            "priority": "Urgent",
            "episode_type": "Inpatient",
            "treatment_setting": "Acute inpatient",
            "treatment_type": "Extension with diagnosis update",
            "existing_auth": "AUTH-IP-771438",
            "member": make_member(8, "Henry Collins", "07/04/1961", "Medicaid Managed Care"),
            "provider": make_provider(8, "Oak Ridge Hospital", "Sofia Ramirez, MD", "Internal Medicine"),
            "diagnoses": [
                ("I50.33", "Acute on chronic diastolic heart failure"),
                ("E87.1", "Hypo-osmolality and hyponatremia"),
                ("N18.32", "Chronic kidney disease, stage 3b"),
            ],
            "service_lines": [
                ("0110", "Medical/surgical inpatient bed extension", "3 days", "05/14/2026", "05/16/2026"),
            ],
            "admission_date": "05/11/2026",
            "length_of_stay": "3 additional days",
            "requested_level_of_care": "Acute inpatient",
            "new_primary_dx": "I50.33",
            "clinical_summary": [
                "Existing authorization covered initial stay for dyspnea and volume overload.",
                "Updated labs and cardiology consult add hyponatremia and CKD complexity to the review.",
                "Provider requests extension plus new diagnosis mapping for the existing authorization.",
            ],
            "review_focus": [
                "IP extension matrix fields include existing authorization number, urgency, providers, extension dates, LOS, and diagnosis changes.",
                "Validate whether the new diagnosis table should add codes or update the primary diagnosis.",
            ],
            "attachments": [
                "Current inpatient progress notes",
                "Cardiology consultation",
                "Daily weights and intake/output flowsheet",
                "Chemistry trend",
            ],
            "criteria": [
                ("Existing auth", "AUTH-IP-771438 present and active"),
                ("Extension need", "Ongoing IV diuresis and sodium monitoring"),
                ("Diagnosis update", "New primary and secondary diagnosis data supplied"),
            ],
        },
        {
            "record_label": "UM09",
            "title": "NICU Concurrent Extension Request",
            "taxonomy": "PH/BH Concurrent Extension",
            "matrix_sheets": ["CCR Extension", "CCR New"],
            "action_type": "Extend Existing Auth",
            "auth_request_type": "PH CCR",
            "category": "extension_um",
            "target_pages": 56,
            "priority": "Urgent",
            "episode_type": "Inpatient",
            "treatment_setting": "NICU",
            "treatment_type": "Neonatal intensive care extension",
            "existing_auth": "AUTH-NICU-550218",
            "member": make_member(9, "Isla Morgan", "04/28/2026", "Medicaid Managed Care"),
            "provider": make_provider(9, "Starlight Childrens Hospital", "Olivia Grant, MD", "Neonatology"),
            "diagnoses": [
                ("P22.0", "Respiratory distress syndrome of newborn"),
                ("P07.32", "Preterm newborn, gestational age 29 completed weeks"),
                ("P59.9", "Neonatal jaundice, unspecified"),
            ],
            "service_lines": [
                ("0174", "NICU level III bed extension", "7 days", "05/12/2026", "05/18/2026"),
            ],
            "admission_date": "04/28/2026",
            "length_of_stay": "7 additional days",
            "requested_level_of_care": "NICU level III",
            "clinical_summary": [
                "Premature newborn remains on non-invasive respiratory support with feeding immaturity.",
                "Extension request includes daily weight, oxygen requirement, bilirubin treatment, and feeding advancement.",
                "Discharge is delayed until apnea-free interval and oral feeding goals are met.",
            ],
            "review_focus": [
                "CCR extension matrix includes NICU flag, existing authorization, disposition days, extension start date, and LOS.",
                "Review neonatal acuity, respiratory support, feeding status, and discharge milestones.",
            ],
            "attachments": [
                "NICU daily progress notes",
                "Respiratory therapy flowsheets",
                "Nutrition and weight trend",
                "Phototherapy record",
                "Discharge readiness checklist",
            ],
            "criteria": [
                ("NICU flag", "NICU = true"),
                ("Extension dates", "Start and end dates align to requested seven-day span"),
                ("Medical need", "Respiratory support and feeding immaturity persist"),
            ],
        },
        {
            "record_label": "AP10",
            "title": "Appeal of Denied Lumbar MRI Authorization",
            "taxonomy": "Member/Provider Appeal",
            "matrix_sheets": ["PA New", "OP PA Ext w Prim Dx", "PA Ext - Add Doc Only"],
            "action_type": "Appeal Existing Determination",
            "auth_request_type": "PH OP Appeal",
            "category": "appeal",
            "target_pages": 68,
            "priority": "Expedited",
            "episode_type": "Outpatient",
            "treatment_setting": "Outpatient hospital imaging",
            "treatment_type": "Advanced imaging appeal",
            "existing_auth": "DEN-OP-882104",
            "member": make_member(10, "Jonah Price", "01/18/1986", "Medicaid Managed Care"),
            "provider": make_provider(10, "East Valley Spine Clinic", "Lauren Mercer, MD", "Spine Surgery"),
            "diagnoses": [
                ("M54.16", "Radiculopathy, lumbar region"),
                ("M48.061", "Spinal stenosis, lumbar region without neurogenic claudication"),
            ],
            "service_lines": [
                ("72148", "MRI lumbar spine without contrast", "1 unit", "05/21/2026", "05/21/2026"),
            ],
            "clinical_summary": [
                "Initial authorization was denied for insufficient conservative-care documentation.",
                "Appeal adds PT logs, neurologic exam trend, medication trials, and surgical consult statement.",
                "Provider requests expedited reversal due to progressive weakness and treatment-planning impact.",
            ],
            "review_focus": [
                "Treat as add-document appeal tied to the original PA new request.",
                "Compare submitted evidence against imaging medical policy criteria and denial rationale.",
            ],
            "attachments": [
                "Denial notice",
                "Appeal letter",
                "PT visit log",
                "Medication history",
                "Specialist consult",
                "Updated exam table",
            ],
            "criteria": [
                ("Denial rationale", "Insufficient conservative-care evidence"),
                ("New evidence", "Six-week PT, medication trials, and neurologic decline now supplied"),
                ("Expedited need", "Weakness progression may alter surgical planning"),
            ],
            "adverse_determination": "Medical necessity not established in initial submission",
            "requested_resolution": "Overturn denial and authorize CPT 72148",
        },
        {
            "record_label": "GR11",
            "title": "Grievance for Delayed Home Infusion Authorization",
            "taxonomy": "Member Grievance",
            "matrix_sheets": ["PA New", "PA Ext - Add Doc Only", "DC"],
            "action_type": "Grievance Review",
            "auth_request_type": "PH OP Grievance",
            "category": "grievance",
            "target_pages": 74,
            "priority": "Expedited",
            "episode_type": "Outpatient",
            "treatment_setting": "Home",
            "treatment_type": "Home infusion access complaint",
            "existing_auth": "AUTH-HI-339017",
            "member": make_member(11, "Karen Brooks", "06/06/1956", "Medicaid Managed Care"),
            "provider": make_provider(11, "Metro Home Infusion", "Iris Coleman, PharmD", "Home Infusion"),
            "diagnoses": [
                ("M86.171", "Other acute osteomyelitis, right ankle and foot"),
                ("E11.621", "Type 2 diabetes mellitus with foot ulcer"),
            ],
            "service_lines": [
                ("J0696", "Ceftriaxone sodium injection", "42 doses", "05/08/2026", "06/18/2026"),
                ("S9500", "Home infusion therapy, per diem", "42 days", "05/08/2026", "06/18/2026"),
            ],
            "clinical_summary": [
                "Member grievance alleges delay in home infusion start after hospital discharge.",
                "Packet includes authorization timestamps, provider call logs, discharge orders, and member complaint details.",
                "Review focuses on timeliness, access-to-care impact, and corrective action.",
            ],
            "review_focus": [
                "Use PA service-line fields for drug code, units, start/end dates, and provider information.",
                "For grievance review, reconcile plan timeline against discharge order and member outreach history.",
            ],
            "attachments": [
                "Member complaint form",
                "Discharge orders",
                "Home infusion referral",
                "Authorization activity log",
                "Provider call notes",
                "Resolution letter draft",
            ],
            "criteria": [
                ("Timeliness", "Authorization decision and vendor notification timestamps under review"),
                ("Access impact", "Delay caused missed first home dose per member statement"),
                ("Resolution", "Expedited corrective action and written response requested"),
            ],
            "adverse_determination": "Member-reported delay in authorized service initiation",
            "requested_resolution": "Confirm authorization, restore timely service, and issue written grievance response",
        },
        {
            "record_label": "AP12",
            "title": "Expedited Appeal and Grievance for Inpatient Rehab Denial",
            "taxonomy": "Appeal and Grievance Packet",
            "matrix_sheets": ["IP PA Extension", "IP PA Ext w Prim Dx ", "PA Ext - Add Doc Only"],
            "action_type": "Appeal Existing Determination",
            "auth_request_type": "PH IP Appeal",
            "category": "appeal_grievance",
            "target_pages": 80,
            "priority": "Expedited",
            "episode_type": "Inpatient",
            "treatment_setting": "Inpatient rehabilitation facility",
            "treatment_type": "IRF level-of-care appeal",
            "existing_auth": "DEN-IPR-664290",
            "member": make_member(12, "Marcus Bell", "10/09/1959", "Medicaid Managed Care"),
            "provider": make_provider(12, "Harborview Rehabilitation Hospital", "Rachel Kim, MD", "Physical Medicine and Rehabilitation"),
            "diagnoses": [
                ("I69.354", "Hemiplegia following cerebral infarction affecting left nondominant side"),
                ("R13.12", "Dysphagia, oropharyngeal phase"),
                ("R26.89", "Other abnormalities of gait and mobility"),
            ],
            "service_lines": [
                ("0118", "Inpatient rehabilitation bed", "10 days", "05/15/2026", "05/24/2026"),
            ],
            "admission_date": "05/15/2026",
            "length_of_stay": "10 days requested",
            "requested_level_of_care": "Inpatient rehabilitation",
            "new_primary_dx": "I69.354",
            "clinical_summary": [
                "IRF authorization was denied with recommendation for skilled nursing facility level of care.",
                "Appeal adds PT/OT/ST intensity plan, physician supervision statement, and stroke recovery prognosis.",
                "Member grievance alleges unsafe discharge planning and lack of timely peer-to-peer scheduling.",
            ],
            "review_focus": [
                "Use IP extension fields for existing authorization, diagnosis update, start date, LOS, and level of care.",
                "Review appeal evidence and grievance timeline together because both concern the same adverse determination.",
            ],
            "attachments": [
                "Notice of adverse benefit determination",
                "Expedited appeal letter",
                "Member grievance statement",
                "PT/OT/ST evaluations",
                "Physiatry admission screen",
                "Hospital discharge planner notes",
                "Peer-to-peer request log",
            ],
            "criteria": [
                ("IRF intensity", "Member can participate in three therapy disciplines with physician oversight"),
                ("Medical complexity", "Stroke deficits, dysphagia, fall risk, and medication adjustment require rehab physician review"),
                ("Grievance issue", "Member disputes timeliness and adequacy of discharge alternatives"),
            ],
            "adverse_determination": "IRF level of care denied; SNF recommended",
            "requested_resolution": "Overturn IRF denial and resolve grievance with documented corrective action",
        },
    ]


def matrix_field_rows(spec: PacketSpec) -> List[List[str]]:
    base_fields = [
        ("Member ID", spec["member"]["member_id"], "Common HIPAA/PA/CCR member identifier"),
        ("Member Name", spec["member"]["name"], "Common validation field"),
        ("Member DOB", spec["member"]["dob"], "HIPAA or ineligible validation cue"),
        ("Provider Name", spec["provider"]["provider_name"], "Provider identity cue"),
        ("Provider Fax", spec["provider"]["fax"], "Faxback return routing cue"),
        ("Treating Provider ID", spec["provider"]["provider_id"], "PA and extension provider field"),
        ("Diagnosis Code", ", ".join(code for code, _ in spec["diagnoses"][:3]), "Diagnosis table field"),
    ]
    if spec.get("existing_auth") and spec["existing_auth"] != "N/A":
        base_fields.append(("Existing Authorization Number", spec["existing_auth"], "Extension or appeal linkage field"))
    if spec.get("new_primary_dx"):
        base_fields.append(("New Primary Dx Code", spec["new_primary_dx"], "Primary diagnosis update field"))
    if spec.get("admission_date"):
        base_fields.append(("Admission Date", spec["admission_date"], "Concurrent/IP request field"))
    if spec.get("length_of_stay"):
        base_fields.append(("Length of Stay", spec["length_of_stay"], "CCR or IP extension field"))
    for idx, (code, desc, qty, start, end) in enumerate(spec["service_lines"][:3], start=1):
        base_fields.append((
            f"Service Line {idx}",
            f"{code} | {qty} | {start}-{end}",
            f"Procedure/service line cue: {desc}",
        ))
    return [[field, value, cue, f"Sheet examples: {', '.join(spec['matrix_sheets'])}"] for field, value, cue in base_fields[:12]]


def code_rows(spec: PacketSpec) -> List[List[str]]:
    rows: List[List[str]] = []
    for code, desc in spec["diagnoses"]:
        rows.append([code, desc, "Diagnosis", "", ""])
    for code, desc, qty, start, end in spec["service_lines"]:
        rows.append([code, desc, "Service line", qty, f"{start} to {end}"])
    return rows


def review_timeline_rows(spec: PacketSpec) -> List[List[str]]:
    target = int(spec["target_pages"])
    return [
        ["05/01/2026", "Provider fax received", spec["action_type"], "Intake opened"],
        ["05/01/2026", "Identity / eligibility check", spec["taxonomy"], "Validation complete" if spec["category"] != "faxback" else "Exception found"],
        ["05/02/2026", "Clinical packet indexed", spec["treatment_type"], "Attachments mapped"],
        ["05/03/2026", "Nurse review", spec["priority"], "Criteria review started"],
        ["05/04/2026", "Medical director review", f"Target {target} pages", "Escalated" if spec["priority"] in {"Urgent", "Expedited"} else "As needed"],
    ]


def attachment_rows(spec: PacketSpec) -> List[List[str]]:
    rows: List[List[str]] = []
    for idx, name in enumerate(spec["attachments"], start=1):
        rows.append([
            f"A{idx:02d}",
            name,
            "Clinical" if idx % 2 else "Administrative",
            "Indexed",
            f"Pages vary within {spec['target_pages']}-page packet",
        ])
    return rows


def add_base_pages(doc: PDFDocument, spec: PacketSpec, page_num: int) -> int:
    member = spec["member"]
    provider = spec["provider"]
    owner_name = member["name"]
    owner_id = member["member_id"]
    header = f"{spec['record_label']} | {spec['taxonomy']} | UM Packet"

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Fax Cover and UM Packet Face Sheet",
        meta_pairs=[
            ("Record", spec["record_label"]),
            ("Scenario", spec["title"]),
            ("Taxonomy", spec["taxonomy"]),
            ("Action Type", spec["action_type"]),
            ("Auth Request Type", spec["auth_request_type"]),
            ("Priority", spec["priority"]),
            ("Target Pages", str(spec["target_pages"])),
            ("Matrix Examples", ", ".join(spec["matrix_sheets"])),
            ("Member", member["name"]),
            ("Provider Facility", provider["facility"]),
        ],
        sections=[
            (
                "Packet Intent",
                "paragraph",
                "Synthetic healthcare insurance packet for utilization management, faxback, appeal, or grievance testing. All names, IDs, facilities, dates, and clinical details are fictional.",
            ),
            (
                "Primary Routing Signals",
                "bullets",
                [
                    f"Episode type: {spec['episode_type']}",
                    f"Treatment setting: {spec['treatment_setting']}",
                    f"Treatment type: {spec['treatment_type']}",
                    f"Existing authorization: {spec['existing_auth']}",
                ],
            ),
        ],
    )

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Request Classification and Matrix Cues",
        meta_pairs=[
            ("Action", spec["action_type"]),
            ("Request Type", spec["auth_request_type"]),
            ("Urgent / Standard", spec["priority"]),
            ("Inpatient / Outpatient", spec["episode_type"]),
            ("Setting", spec["treatment_setting"]),
            ("Existing Auth", spec["existing_auth"]),
        ],
        sections=[
            (
                "Matrix-Derived Fields",
                "bullets",
                [
                    "Member identifiers, provider identifiers, diagnosis codes, service lines, dates, units, and level of care are represented when applicable.",
                    "Extension scenarios include existing authorization number, extension start date, length of stay or visit count, and diagnosis update cues.",
                    "Faxback scenarios emphasize HIPAA validation, eligibility status, provider fax, and corrected resubmission instructions.",
                ],
            ),
            ("Review Focus", "bullets", spec["review_focus"]),
        ],
    )

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Member, Provider, and Contact Verification",
        meta_pairs=[
            ("Member ID", member["member_id"]),
            ("Member Name", member["name"]),
            ("DOB", member["dob"]),
            ("Plan", member["plan"]),
            ("Member Phone", member["phone"]),
            ("Provider", provider["provider_name"]),
            ("Facility", provider["facility"]),
            ("Specialty", provider["specialty"]),
            ("Provider ID", provider["provider_id"]),
            ("NPI", provider["npi"]),
            ("Fax", provider["fax"]),
            ("Contact", provider["contact"]),
        ],
        sections=[
            (
                "Validation Notes",
                "bullets",
                [
                    "Identity and routing fields mirror common HIPAA, ineligible, PA, and CCR taxonomy fields.",
                    "The packet intentionally includes both provider-facing fax data and payer-facing intake data.",
                    "Any clinical review should be read with the service-line and attachment pages.",
                ],
            )
        ],
    )

    page_num = table_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Diagnosis and Service Line Detail",
        columns=[("Code", 70), ("Description", 245), ("Type", 82), ("Units / Days", 70), ("Date Span", 73)],
        rows=code_rows(spec),
        notes=[
            f"Taxonomy examples: {', '.join(spec['matrix_sheets'])}.",
            "Service-line dates, units, diagnosis mapping, and procedure codes are present where relevant.",
        ],
    )

    page_num = note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        "Clinical Rationale and Attachment Index",
        sections=[
            ("Clinical Summary", "bullets", spec["clinical_summary"]),
            ("Attachments Submitted", "bullets", spec["attachments"]),
        ],
        signature=(provider["provider_name"], provider["specialty"], "05/11/2026 10:15"),
    )

    return page_num


def add_matrix_and_review_pages(doc: PDFDocument, spec: PacketSpec, page_num: int, target_pages: int) -> int:
    member = spec["member"]
    owner_name = member["name"]
    owner_id = member["member_id"]
    header = f"{spec['record_label']} | {spec['taxonomy']} | UM Packet"

    if page_num <= target_pages:
        page_num = table_page(
            doc,
            page_num,
            owner_name,
            owner_id,
            header,
            "Matrix Field Extraction Crosswalk",
            columns=[("Field", 128), ("Synthetic Value", 170), ("Matrix Cue", 142), ("Source", 100)],
            rows=matrix_field_rows(spec),
            notes=[
                "Crosswalk is based on field names observed in the supplied taxonomy workbook.",
                "Values are synthetic and are intended for extraction, routing, and validation demos.",
            ],
        )
    if page_num <= target_pages:
        page_num = table_page(
            doc,
            page_num,
            owner_name,
            owner_id,
            header,
            "UM Intake and Review Timeline",
            columns=[("Date", 78), ("Event", 150), ("Context", 180), ("Status", 132)],
            rows=review_timeline_rows(spec),
            notes=[
                "Timeline is included for payer workflow testing and does not represent a real plan record.",
            ],
        )
    if page_num <= target_pages:
        page_num = table_page(
            doc,
            page_num,
            owner_name,
            owner_id,
            header,
            "Clinical Criteria Crosswalk",
            columns=[("Criterion", 160), ("Evidence Present", 260), ("Reviewer Note", 120)],
            rows=[[crit, ev, "Review"] for crit, ev in spec["criteria"]],
            notes=[
                "Criteria rows support utilization review, appeal review, or grievance investigation depending on scenario.",
            ],
        )
    return page_num


def add_appeal_or_grievance_pages(doc: PDFDocument, spec: PacketSpec, page_num: int) -> int:
    member = spec["member"]
    provider = spec["provider"]
    owner_name = member["name"]
    owner_id = member["member_id"]
    header = f"{spec['record_label']} | {spec['taxonomy']} | UM Packet"

    if spec["category"] in {"appeal", "appeal_grievance"}:
        page_num = note_page(
            doc,
            page_num,
            owner_name,
            owner_id,
            header,
            "Notice of Adverse Benefit Determination",
            meta_pairs=[
                ("Prior Case", spec["existing_auth"]),
                ("Adverse Determination", spec.get("adverse_determination", "Prior denial")),
                ("Requested Resolution", spec.get("requested_resolution", "Overturn denial")),
                ("Appeal Priority", spec["priority"]),
            ],
            sections=[
                (
                    "Denial Summary",
                    "paragraph",
                    "Synthetic adverse determination page documenting the plan rationale that triggered the appeal packet.",
                ),
                ("Appeal Evidence to Review", "bullets", spec["attachments"]),
            ],
            signature=("Medical Management", "Adverse Determination Notice", "05/05/2026 16:20"),
        )
        page_num = note_page(
            doc,
            page_num,
            owner_name,
            owner_id,
            header,
            "Provider Appeal Letter",
            sections=[
                (
                    "Appeal Narrative",
                    "paragraph",
                    f"{provider['provider_name']} requests reconsideration of {spec['existing_auth']} because the additional documentation supports the requested {spec['treatment_type'].lower()}.",
                ),
                ("New Evidence", "bullets", spec["clinical_summary"] + spec["review_focus"]),
            ],
            signature=(provider["provider_name"], "Appeal Submission", "05/08/2026 09:45"),
        )
        page_num = table_page(
            doc,
            page_num,
            owner_name,
            owner_id,
            header,
            "Appeal Evidence Index",
            columns=[("Exhibit", 58), ("Document", 210), ("Purpose", 190), ("Status", 82)],
            rows=[[f"EX-{idx:02d}", doc_name, "Supports appeal review", "Included"] for idx, doc_name in enumerate(spec["attachments"], start=1)],
            notes=[
                "Appeal packets are intentionally longer than routine UM intake packets.",
                "Evidence is repeated across clinical notes, logs, criteria pages, and correspondence.",
            ],
        )

    if spec["category"] in {"grievance", "appeal_grievance"}:
        page_num = note_page(
            doc,
            page_num,
            owner_name,
            owner_id,
            header,
            "Member Grievance Intake",
            meta_pairs=[
                ("Grievance Priority", spec["priority"]),
                ("Related Case", spec["existing_auth"]),
                ("Complaint Topic", spec["treatment_type"]),
                ("Requested Resolution", spec.get("requested_resolution", "Written response requested")),
            ],
            sections=[
                (
                    "Member Statement",
                    "paragraph",
                    "The member or authorized representative reports that plan processing affected access, discharge planning, or timely service initiation.",
                ),
                ("Investigation Focus", "bullets", spec["review_focus"] + spec["clinical_summary"][:2]),
            ],
            signature=("Grievance Coordinator", "Grievance Intake", "05/09/2026 11:05"),
        )
        page_num = table_page(
            doc,
            page_num,
            owner_name,
            owner_id,
            header,
            "Grievance Investigation Log",
            columns=[("Date", 78), ("Contact", 156), ("Issue", 196), ("Outcome", 110)],
            rows=[
                ["05/09/2026", "Member", "Complaint received and expedited review requested", "Opened"],
                ["05/09/2026", "Provider", "Clinical documents and timeline requested", "Pending"],
                ["05/10/2026", "UM Ops", "Authorization timestamps reconciled", "In review"],
                ["05/10/2026", "Vendor / facility", "Service access or discharge plan verified", "In review"],
                ["05/11/2026", "Plan response", "Draft written response prepared", "Pending approval"],
            ],
            notes=[
                "Synthetic grievance log supports payer complaint, appeal, and timeliness workflow testing.",
            ],
        )
        page_num = note_page(
            doc,
            page_num,
            owner_name,
            owner_id,
            header,
            "Draft Resolution Letter",
            sections=[
                (
                    "Resolution Summary",
                    "paragraph",
                    spec.get("requested_resolution", "The plan will issue a written response after investigation is complete."),
                ),
                (
                    "Corrective Actions",
                    "bullets",
                    [
                        "Confirm authorization status and notify provider/facility of outcome.",
                        "Document member communication and appeal or grievance rights.",
                        "Route operational delay findings to quality review if substantiated.",
                    ],
                ),
            ],
            signature=("Grievance Coordinator", "Draft Resolution", "05/11/2026 15:25"),
        )

    return page_num


def supplemental_table_rows(spec: PacketSpec, idx: int) -> List[List[str]]:
    service = spec["service_lines"][idx % len(spec["service_lines"])]
    dx = spec["diagnoses"][idx % len(spec["diagnoses"])]
    return [
        ["Member", spec["member"]["name"], "Identifier", spec["member"]["member_id"]],
        ["Provider", spec["provider"]["facility"], "NPI", spec["provider"]["npi"]],
        ["Diagnosis", dx[0], "Description", dx[1]],
        ["Service", service[0], "Requested", f"{service[2]} from {service[3]}"],
        ["Routing", spec["taxonomy"], "Priority", spec["priority"]],
    ]


def add_supplemental_page(doc: PDFDocument, spec: PacketSpec, page_num: int, idx: int) -> int:
    member = spec["member"]
    provider = spec["provider"]
    owner_name = member["name"]
    owner_id = member["member_id"]
    header = f"{spec['record_label']} | {spec['taxonomy']} | UM Packet"
    title_cycle = [
        "Provider Fax Attachment",
        "Clinical Office Note",
        "Nursing or Care Management Note",
        "Medical Policy Review Worksheet",
        "Service Authorization Activity Log",
        "Imported Lab or Imaging Summary",
        "Provider Correspondence",
        "Member Outreach Note",
        "Attachment Continuation Page",
        "Reviewer Work Queue Note",
    ]
    title = title_cycle[idx % len(title_cycle)]
    scanned = title in {"Provider Fax Attachment", "Provider Correspondence", "Attachment Continuation Page"}

    if idx % 4 == 0:
        return table_page(
            doc,
            page_num,
            owner_name,
            owner_id,
            header,
            title,
            columns=[("Field", 100), ("Value", 190), ("Field", 90), ("Value", 160)],
            rows=supplemental_table_rows(spec, idx),
            notes=[
                "Supplemental page included to create realistic packet length and repeated source data.",
                f"Scenario remains {spec['title']}.",
            ],
            scanned=scanned,
            header_suffix=f"Supplement {idx + 1}",
        )

    if idx % 4 == 1:
        return note_page(
            doc,
            page_num,
            owner_name,
            owner_id,
            header,
            title,
            meta_pairs=[
                ("Author", provider["provider_name"]),
                ("Facility", provider["facility"]),
                ("Specialty", provider["specialty"]),
                ("Packet Page Type", "Clinical attachment"),
            ],
            sections=[
                ("Clinical Detail", "bullets", spec["clinical_summary"]),
                ("Reviewer Cue", "bullets", spec["review_focus"]),
            ],
            signature=(provider["provider_name"], provider["specialty"], f"05/{(idx % 28) + 1:02d}/2026 14:{10 + (idx % 40):02d}"),
            scanned=scanned,
            header_suffix=f"Clinical {idx + 1}",
        )

    if idx % 4 == 2:
        return table_page(
            doc,
            page_num,
            owner_name,
            owner_id,
            header,
            title,
            columns=[("Item", 132), ("Evidence", 250), ("Status", 80), ("Owner", 78)],
            rows=[[crit, ev, "Present", "UM"] for crit, ev in spec["criteria"]],
            notes=[
                "Criteria evidence is intentionally distributed across the packet rather than kept in one page.",
            ],
            scanned=scanned,
            header_suffix=f"Criteria {idx + 1}",
        )

    return note_page(
        doc,
        page_num,
        owner_name,
        owner_id,
        header,
        title,
        sections=[
            (
                "Packet Continuation",
                "bullets",
                [
                    f"Continuation page {idx + 1} supports the {spec['taxonomy']} scenario.",
                    f"Relevant matrix examples: {', '.join(spec['matrix_sheets'])}.",
                    f"Requested service context: {spec['treatment_type']}.",
                ],
            ),
            ("Attachments Referenced", "bullets", spec["attachments"][:5]),
        ],
        signature=("UM Operations", title, f"05/{(idx % 28) + 1:02d}/2026 16:{10 + (idx % 40):02d}"),
        scanned=scanned,
        header_suffix=f"Continuation {idx + 1}",
    )


def build_um_packet(spec: PacketSpec, out_pdf: Path, out_json: Path) -> None:
    doc = PDFDocument()
    doc._scan_targets = []
    page_num = 1
    target_pages = int(spec["target_pages"])

    page_num = add_base_pages(doc, spec, page_num)
    if page_num <= target_pages:
        page_num = add_matrix_and_review_pages(doc, spec, page_num, target_pages)
    if page_num <= target_pages and spec["category"] in {"appeal", "grievance", "appeal_grievance"}:
        page_num = add_appeal_or_grievance_pages(doc, spec, page_num)

    supplemental_idx = 0
    while page_num <= target_pages:
        page_num = add_supplemental_page(doc, spec, page_num, supplemental_idx)
        supplemental_idx += 1

    save_packet_pdf(doc, out_pdf)
    payload = dict(spec)
    payload["packet_type"] = "utilization_management_request"
    payload["packet_target_pages"] = target_pages
    payload["packet_generated_pages"] = len(doc.pages)
    payload["matrix_source_note"] = "Taxonomy and field cues based on supplied Field Matrix workbook examples."
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def write_um_packets(root: Path) -> None:
    out_dir = root / "UM Request Packets"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: List[Dict[str, str]] = []
    for spec in make_packet_specs():
        stem = f"{spec['record_label'].lower()}_{slugify(spec['title'])}"
        pdf_path = out_dir / f"{stem}.pdf"
        json_path = out_dir / f"{stem}.json"
        build_um_packet(spec, pdf_path, json_path)
        manifest.append(
            {
                "record": str(spec["record_label"]),
                "title": str(spec["title"]),
                "taxonomy": str(spec["taxonomy"]),
                "category": str(spec["category"]),
                "target_pages": str(spec["target_pages"]),
                "pdf": str(pdf_path),
                "json": str(json_path),
            }
        )
        print(f"Wrote UM PDF: {pdf_path}")
        print(f"Wrote UM JSON: {json_path}")
    manifest_path = out_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote UM manifest: {manifest_path}")


def main() -> None:
    maybe_reexec_in_scan_env()
    write_um_packets(Path(os.getcwd()))


if __name__ == "__main__":
    main()
