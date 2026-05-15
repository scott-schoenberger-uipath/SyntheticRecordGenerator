# UiPath Cloud Notes

This repo now exposes a single deterministic entrypoint in [main.py](../main.py) that wraps the existing generators in a UiPath-friendly contract.

## Input Contract

- `output_root`: directory where artifacts should be written; relative paths resolve from the repo root
- `bundle_names`: bundle families to generate
- `include_synthetic_imaging`: enables optional placeholder imaging in the base patient chart
- `record_limit_per_bundle`: optional cap for smoke runs or faster cloud jobs

Supported `bundle_names` values:

- `base_patient_chart`
- `provider_records`
- `payer_records`
- `provider_long_form_packets`
- `payer_long_form_packets`
- `appeal_packets`
- `ed_downgrade_records`
- `um_request_packets`
- `referral_packets`

## Local Smoke Run

```bash
python3 main.py --input input.example.json
```

From another directory, use an absolute path and optionally override the output location:

```bash
python3 /Users/peterreischer/Desktop/uipath-projects/synthetic-record-generator/SyntheticRecordGenerator/main.py \
  --input /Users/peterreischer/Desktop/uipath-projects/synthetic-record-generator/SyntheticRecordGenerator/input.example.json \
  --output-root /tmp/synthetic-records
```

The command writes artifacts under `output/` and prints a JSON summary that includes:

- output root
- generated bundle directories
- manifest paths
- generated files
- warnings such as missing optional scan tooling

## UiPath Packaging Files

- [pyproject.toml](../pyproject.toml)
- [uipath.json](../uipath.json)
- [entry-points.json](../entry-points.json)

These match the same general shape used across nearby UiPath Python repos: deterministic `main()` entrypoint, `uipath.json` packaging metadata, and a declared entry-point schema for cloud execution.

## Expected UiPath Workflow

After your normal UiPath CLI setup, this repo is ready for the standard Python-agent flow:

1. install dependencies from `pyproject.toml`
2. initialize or refresh the entrypoint schema if needed
3. run the `main` entrypoint with a JSON payload
4. package or deploy using the included `uipath.json`

I did not run the full cloud publish flow from this repo during the cleanup pass, so treat the packaging files as scaffolded and repo-aligned rather than cloud-certified.
