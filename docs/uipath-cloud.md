# UiPath Function Notes

This project exposes deterministic, typed UiPath Functions. Each writes its artifact beneath the requested output root and returns a path-based manifest; none accepts or emits real-person data.

## Callable functions

| Function | Use |
| --- | --- |
| `main` | Existing wrapper for one or more legacy bundle families. |
| `generate_record_packet` | Creates one consolidated PDF from a complete synthetic record specification. |
| `generate_medical_policy` | Creates one fictional policy PDF from a complete synthetic policy specification. |
| `generate_catalog_packet` | Creates one seeded, template-catalog record packet. |

The three new functions live in [agent_tools.py](../agent_tools.py). They use Pydantic input/output contracts so UiPath can export their JSON Schema and bind caller variables.

### Record packet input

- `spec`: complete synthetic record specification; `metadata.is_synthetic` must be `true` and patient MRNs must begin with `SYN-`
- `output_root`: directory where artifacts should be written; relative paths resolve from the repo root
- `output_stem`: lowercase filename stem

The tool preserves supplied document order, limits packets to 25 documents, and permits no more than one illustrative imaging panel. That panel requires both an explicit reason and the underlying renderer's synthetic/non-diagnostic labeling.

### Medical policy input

- `spec`: complete fictional policy specification; `metadata.is_synthetic` must be `true`
- `output_root` and `output_stem`: output controls as above

Policies are capped at 20 sections and retain their synthetic-use labeling.

### Catalog packet input

- `profile` or `families`: choose a catalog profile or a limited set of document families
- `scenario`, `seed`, and `record_label`: define one reproducible synthetic encounter
- `packet_order`: `received_order` for a deterministic messy packet, or `profile_order` for a clean showcase
- `apply_realism` and `include_handwriting`: control scanned-page realism; handwriting uses only a repository-provided synthetic asset
- `output_root` and `output_stem`: output controls as above

## Legacy wrapper input

`main` keeps the existing input contract:

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

## Local smoke runs

```bash
python3 main.py --input input.example.json
```

Invoke a catalog packet tool through UiPath after installing the CLI:

```bash
uipath run generate_catalog_packet '{
  "output_root": "output/agent-smoke",
  "output_stem": "sepsis_packet",
  "scenario": "provider_sepsis",
  "seed": 20260310,
  "families": ["history_and_physical", "handwritten_progress_note"],
  "packet_order": "received_order",
  "include_handwriting": true
}'
```

Each function writes artifacts under `output/` by default and returns a JSON summary that includes:

- output root
- generated bundle directories
- manifest paths
- generated files
- warnings such as missing optional scan tooling

## UiPath Packaging Files

- [pyproject.toml](../pyproject.toml)
- [uipath.json](../uipath.json)
- [entry-points.json](../entry-points.json)

`uipath.json` declares the callable functions. After modifying a Pydantic input/output contract, regenerate the schemas with:

```bash
uipath init
```

This updates `entry-points.json` and bindings for the installed UiPath runtime.

## Expected UiPath Workflow

After your normal UiPath CLI setup, this repo is ready for the standard Python-agent flow:

1. install dependencies from `pyproject.toml`
2. initialize or refresh the entrypoint schema if needed
3. run one function entrypoint with a JSON payload
4. package or deploy using the included `uipath.json`

I did not run the full cloud publish flow from this repo during the cleanup pass, so treat the packaging files as scaffolded and repo-aligned rather than cloud-certified.
