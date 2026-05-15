# Synthetic Record Generation

Deterministic synthetic healthcare record generator for demos, ingestion testing, and UiPath automation scenarios.

This repo currently generates eight bundle families:

- base patient chart packets
- provider inpatient documentation packets
- payer care-management packets
- long-form provider and payer chart bundles
- lumbar MRI appeal evidence packets
- ED downgrade scenario records
- utilization management request packets, including faxbacks, PA/CCR requests, extensions, appeals, and grievances
- specialty referral packets with fax cover sheets, office/progress notes, lab results, and imaging results

All checked-in source data is synthetic. Generated PDFs and JSON artifacts are intentionally ignored by git so the public repo does not ship demo output files, PHI, or customer-branded samples.

## What Is Built

The record generators already cover the major packet components that appear throughout the codebase: demographics, encounter history, H&P content, progress notes, lab tables, imaging reports, medications, discharge content, payer utilization views, care-management notes, appeal narratives, and ED visit documentation.

See [docs/component-inventory.md](docs/component-inventory.md) for the current component-by-component inventory observed in the generator code.

## Repo Layout

- `main.py`: UiPath-friendly wrapper entrypoint for generating selected bundle families from one payload
- `input.example.json`: smoke input for the wrapper entrypoint
- `generate_synthetic_patient_pdf.py`: base patient chart generator
- `generate_provider_synthetic_records.py`: shorter provider packet generator
- `generate_payer_synthetic_records.py`: shorter payer packet generator
- `generate_long_form_packets.py`: 80+ page provider and payer packet generator
- `generate_appeal_lumbar_mri_records.py`: lumbar MRI appeal evidence packet generator
- `generate_ed_downgrade_records.py`: Epic-style ED downgrade packet renderer
- `generate_um_request_packets.py`: UM request packet generator with 5-80 page packets informed by the field-matrix taxonomy examples
- `generate_referral_packets.py`: specialty referral packet generator with 5-20 page packets
- `ed_downgrade_records.json`: sanitized synthetic source fixture for the ED downgrade bundle
- `docs/uipath-cloud.md`: local and UiPath Cloud packaging notes

## Local Usage

Generate a smoke bundle through the shared wrapper:

```bash
python3 main.py --input input.example.json
```

Generate from another working directory:

```bash
python3 /Users/peterreischer/Desktop/uipath-projects/synthetic-record-generator/SyntheticRecordGenerator/main.py \
  --input /Users/peterreischer/Desktop/uipath-projects/synthetic-record-generator/SyntheticRecordGenerator/input.example.json \
  --output-root /tmp/synthetic-records
```

If this project is installed into an environment, the same wrapper is exposed as:

```bash
synthetic-record-generator --input input.example.json --output-root /tmp/synthetic-records
```

Run the legacy generators directly when you want one family at a time:

```bash
python3 generate_synthetic_patient_pdf.py
python3 generate_provider_synthetic_records.py
python3 generate_payer_synthetic_records.py
python3 generate_long_form_packets.py
python3 generate_appeal_lumbar_mri_records.py
python3 generate_ed_downgrade_records.py
python3 generate_um_request_packets.py
python3 generate_referral_packets.py
```

The wrapper writes to `output/` by default. The legacy scripts keep their original family-specific output directories for ad hoc local generation.

For coding agents in other repos, prefer `main.py` or the `synthetic-record-generator` command over the legacy scripts because the wrapper resolves repo-local data from its own file location and accepts an explicit output root.

## UiPath Cloud Alignment

This repo now includes the standard files used by sibling UiPath Python projects:

- `pyproject.toml`
- `uipath.json`
- `entry-points.json`
- `main.py`

The entrypoint is intentionally deterministic and file-generation focused. It accepts a bundle-selection payload, writes artifacts under the requested output root, and returns a manifest-friendly summary of what it generated.

See [docs/uipath-cloud.md](docs/uipath-cloud.md) for the input contract and packaging notes.

## Optional Scanned-Page Pipeline

`generate_long_form_packets.py`, `generate_appeal_lumbar_mri_records.py`, and `generate_um_request_packets.py` can apply scan-like post-processing when `.venv-scan/bin/scanner` is present. If that environment is absent, the packets still generate successfully as normal vector PDFs.
