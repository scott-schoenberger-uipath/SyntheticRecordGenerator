# SyntheticRecordGenerator

Generator-first toolkit for creating realistic **synthetic** healthcare record packets for demos, testing, and document-ingestion benchmarking.

All generated records are fictional and include synthetic labeling. Not for clinical care or legal use.

## What this repo includes

- Python generators for:
  - base synthetic chart generation
  - provider record generation
  - payer record generation
  - long-form packet generation (80-120 page style)
  - lumbar MRI appeal evidence packet generation
- A small `examples/` set (2 sample records) to demonstrate output format

## Generators

- `/Users/scott.schoenberger/Documents/SyntheticPatientRecords/generate_synthetic_patient_pdf.py`
- `/Users/scott.schoenberger/Documents/SyntheticPatientRecords/generate_provider_synthetic_records.py`
- `/Users/scott.schoenberger/Documents/SyntheticPatientRecords/generate_payer_synthetic_records.py`
- `/Users/scott.schoenberger/Documents/SyntheticPatientRecords/generate_long_form_packets.py`
- `/Users/scott.schoenberger/Documents/SyntheticPatientRecords/generate_appeal_lumbar_mri_records.py`

## Quick start

```bash
python3 /Users/scott.schoenberger/Documents/SyntheticPatientRecords/generate_synthetic_patient_pdf.py
python3 /Users/scott.schoenberger/Documents/SyntheticPatientRecords/generate_provider_synthetic_records.py
python3 /Users/scott.schoenberger/Documents/SyntheticPatientRecords/generate_payer_synthetic_records.py
python3 /Users/scott.schoenberger/Documents/SyntheticPatientRecords/generate_long_form_packets.py
python3 /Users/scott.schoenberger/Documents/SyntheticPatientRecords/generate_appeal_lumbar_mri_records.py
```

## Optional scanned-page pipeline

Long-form generation supports selective scan post-processing for imported/faxed-style pages.

Recommended local env (Python 3.11+):

```bash
python3.11 -m venv /Users/scott.schoenberger/Documents/SyntheticPatientRecords/.venv-scan
/Users/scott.schoenberger/Documents/SyntheticPatientRecords/.venv-scan/bin/pip install look-like-scanned pypdf
```

If `.venv-scan` exists, long-form generators auto-use it for scan post-processing.

## Examples

- `/Users/scott.schoenberger/Documents/SyntheticPatientRecords/examples/provider_record_b_high_acuity_revenue_impact.pdf`
- `/Users/scott.schoenberger/Documents/SyntheticPatientRecords/examples/provider_record_b_high_acuity_revenue_impact.json`
- `/Users/scott.schoenberger/Documents/SyntheticPatientRecords/examples/appeal_record_a_failed_conservative_care.pdf`
- `/Users/scott.schoenberger/Documents/SyntheticPatientRecords/examples/appeal_record_a_failed_conservative_care.json`
