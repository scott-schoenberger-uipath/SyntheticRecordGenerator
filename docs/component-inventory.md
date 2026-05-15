# Component Inventory

This inventory is based on the generator code currently in the repo. It is intended as a practical checklist for what is already implemented, not a claim that every downstream packet should always include every item.

## Base Patient Chart

- cover sheet and demographics
- problem list and active medications
- immunizations
- ambulatory, urgent care, ED, and follow-up encounters
- lab tables and trend summaries
- diagnostic summaries
- optional synthetic imaging panels
- operative report
- pathology report
- discharge summary
- specialty consult note
- anesthesia report

## Provider Records

- face sheet
- admission H&P
- daily progress notes
- escalation and ICU transfer note
- lab trend table
- procedure report
- discharge summary
- coding and documentation-gap page

## Payer Records

- member demographics
- chronic condition summary
- inpatient and ED utilization history
- claims cost concentration
- medication profile and pharmacy risk notes
- functional assessment
- social determinants and behavioral health notes
- care-management synopsis
- intervention plan
- risk-gap table

## Long-Form Provider Packets

- registration and insurance header
- admitting diagnosis and packet intent
- medication reconciliation
- indexed lab and imaging pages
- imported outside records
- hospital-day physician and nursing notes
- vitals flowsheets
- lab result packets
- MAR extracts
- consult follow-ups
- CDI query page
- discharge and after-visit packet content
- supplemental imported filler pages to simulate large chart bundles

## Long-Form Payer Packets

- member risk header
- chronic condition and utilization pages
- medication and fill-history pages
- claims detail pages
- care-management outreach logs
- authorization and transitions-of-care notes
- provider correspondence and scanned attachments
- final clinical snapshot
- risk-gap summary
- supplemental payer packet filler pages

## Appeal Evidence Packets

- appeal face sheet
- fax cover sheet
- appeal request details
- medical director appeal letter
- event chronology
- office note
- specialty consult note
- serial physical exam table
- PT initial evaluation
- PT progress and discharge notes
- PT visit log
- medication and injection history
- medical necessity summary
- criteria crosswalk
- imaging reports
- closing packet summary and signature page

## ED Downgrade Records

- Epic-style patient banner and demographics
- chief complaint and HPI
- ED course and nursing activity timeline
- lab result pages
- radiology result pages
- medication administration record
- after-visit summary and discharge instructions

## Utilization Management Request Packets

- fax cover and UM packet face sheet
- request classification and matrix-derived routing cues
- member, provider, HIPAA, and eligibility validation fields
- diagnosis and service-line detail tables
- PA new, HIPAA faxback, ineligible faxback, therapy extension, DME, concurrent review, IP extension, NICU extension, appeal, grievance, and combined appeal/grievance scenarios
- matrix field extraction crosswalks based on supplied taxonomy workbook examples
- UM review timeline, criteria crosswalk, clinical rationale, provider correspondence, member outreach, and supplemental attachments
- variable packet sizes from 5 to 80 pages, with appeal and grievance packets intentionally longer

## Specialty Referral Packets

- fax cover sheet and referral face sheet
- specialist routing details, requested specialty, urgency, and referral reason
- patient demographics, medication context, allergies, and active referral diagnoses
- office notes and referral progress notes
- lab result summaries with flags and referral notes
- imaging result reports with synthetic image placeholders
- referral correspondence and supplemental clinical pages
- variable packet sizes from 5 to 20 pages

## External Matrix Note

The utilization management request packets reference the supplied field-matrix taxonomy workbook for scenario and field examples. The workbook itself is not copied into this repo; the generator keeps only synthetic packet templates and matrix-derived field names needed for demos.
