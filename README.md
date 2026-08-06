# Synthetic Record Generator

Synthetic Record Generator creates realistic-looking, **entirely fictional** healthcare record packets and medical-policy documents for demos, testing, document-ingestion evaluation, and reviewer-training workflows.

It is not a clinical system. Do not use it with real-person medical data, real provider/payer/government logos, clinical decisions, billing, claims, coverage determinations, or patient care.

## What to use

| Need | Use |
| --- | --- |
| A controlled JSON-in/PDF-out record or policy, with one PDF per patient packet | `synthetic_document_pipelines/` |
| A larger multi-document packet built from a deterministic synthetic encounter and template catalog | `synthetic_engine/` + `template-catalog/` |
| Existing scenario generators | Root-level `generate_*.py` scripts (compatibility paths) |

The two supported paths are complementary. The JSON pipeline is the recommended starting point for predictable, source-aware review packets. The catalog pipeline assembles larger mixes of clinical-document families from one synthetic encounter.

## Quick start: JSON record and policy pipeline

```bash
python -m pip install -r requirements-modern-pipeline.txt
python generate_modern_examples.py
python -m unittest discover -s tests -v
```

The reviewed outputs are written to `generated_examples/modern_pipeline/`:

- `synthetic_neurovascular_record_packet.pdf`
- `illustrative_advanced_imaging_policy.pdf`

Generate a packet directly:

```bash
python -m synthetic_document_pipelines record \
  --input examples/modern_pipeline/neurovascular_record_packet.json \
  --output output/neurovascular_packet.pdf
```

Generate a policy directly:

```bash
python -m synthetic_document_pipelines policy \
  --input examples/modern_pipeline/illustrative_imaging_policy.json \
  --output output/illustrative_policy.pdf
```

## Quick start: catalog packet pipeline

The catalog pipeline can compose registration, H&P, nursing-style scanned notes, lab pages, radiology, procedure, pathology, MAR, discharge, prior-authorization, appeal, and denial document families.

```bash
python generate_template_driven_packet.py \
  --profile provider_packet_full \
  --scenario provider_sepsis \
  --seed 20260310 \
  --packet-order received_order \
  --out-dir output/catalog-demo \
  --output-stem provider_packet
```

`received_order` deliberately produces a deterministic mixed inbound order. Use `--packet-order profile_order` for an ordered showcase packet instead.

To add handwriting to catalog-generated scanned attachments, opt in with local-only assets:

```bash
python generate_template_driven_packet.py \
  --enable-handwriting \
  --handwriting-asset-dir handwriting_assets \
  --out-dir output/catalog-demo
```

For the optional fixed-layout renderer, install the Node dependencies once:

```bash
npm install
```

Without them, the catalog renderer falls back to the built-in PDF layout path.

## Designed-for-reality details

- One consolidated PDF per patient packet.
- Source-aware packet metadata: packet position, event time, filed time, source state, duplicates, partial records, and other irregularities.
- Native EHR-inspired, lab-table, imported/faxed, and scanned-page treatments.
- Handwriting is applied to scanned attachments before scan rasterization, so it looks part of the source page.
- Generated imaging-style panels are opt-in, limited by default to one per packet, and permanently labeled illustrative/non-diagnostic.
- Original fictional provider and agency marks only; never use a real organization mark.
- Deterministic seeds and output manifests for regression testing.

## Repository layout

```text
synthetic_document_pipelines/  Primary JSON record and policy PDF pipeline
synthetic_engine/              Canonical synthetic encounter and packet orchestrator
template-catalog/              Versioned JSON templates and profiles
examples/                      Small checked-in input examples
generated_examples/            Reviewed, checked-in output PDFs and manifests
docs/                          Design, research, and pipeline guidance
tests/                         Regression tests
handwriting_assets/            Local-only optional assets (ignored by Git)
output/                        Local generated work (ignored by Git)
```

## Safety and source rules

1. Use fictional data only. The catalog pipeline generates seeded synthetic demographics with `SYN-` identifiers; the JSON pipeline rejects patient MRNs without that prefix.
2. Every output must retain its synthetic-use label.
3. Preserve uncertainty, conflicts, missing records, and received order. Do not silently normalize a messy inbound packet into a clinical timeline.
4. Use the synthetic-exemplar bootstrap utility only with a synthetic PDF and its required attestation. It retains layout dimensions only, never source text or source paths.
5. Keep optional handwriting assets local. Do not commit signatures, handwriting samples, screenshots, or any real clinical data.

## Documentation

- [Modern pipeline guide](docs/MODERN_PIPELINE_GUIDE.md)
- [Research and design decisions](docs/PIPELINE_RESEARCH.md)
- [Template catalog guide](template-catalog/README.md)

## Legacy generators

The root-level scenario generators remain available for compatibility with existing demos. New work should use the JSON pipeline or the catalog pipeline above, then migrate a legacy script only after it has a documented input specification and regression coverage.
