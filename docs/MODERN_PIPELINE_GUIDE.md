# Modern Record and Policy Pipelines

`synthetic_document_pipelines` is the forward path for generation. It intentionally separates the two jobs that have different source controls and layouts:

- `record` creates one consolidated fictional patient packet. The caller supplies a list of page-sized clinical document objects, so packet length is explicit and reproducible.
- `policy` creates a standalone fictional policy document with document control, structured sections, references, and revision history.

Both pipelines require `metadata.is_synthetic: true`, write a manifest with the output checksum, and display a clear synthetic-use restriction on every page.

## Install

```bash
python -m pip install -r requirements-modern-pipeline.txt
```

## Generate a patient packet

```bash
python -m synthetic_document_pipelines record \
  --input examples/modern_pipeline/neurovascular_record_packet.json \
  --output generated_examples/modern_pipeline/synthetic_neurovascular_record_packet.pdf
```

The `documents` array determines the exact number of pages. Set `scanned: true` for a fictional outside/fax attachment; the selective scan profile will rasterize only that page and preserve one consolidated PDF output. A document can also include an `image_panel` (a clearly labeled illustrative raster) and scan annotations can include a `text` note or an `asset` image, such as a fictional handwriting sample. The record example includes all three deliberately distinct modalities.

## Generate a policy

```bash
python -m synthetic_document_pipelines policy \
  --input examples/modern_pipeline/illustrative_imaging_policy.json \
  --output generated_examples/modern_pipeline/illustrative_advanced_imaging_policy.pdf
```

Use the `sections` array to control policy length and content. For policy content based on a public source, retain source title, URL, jurisdiction, effective date, and revision history in the input and output; never assume a source remains current.

## Generate both reviewed examples

```bash
python generate_modern_examples.py
python -m unittest discover -s tests -v
```

## Generic visual profiles

The modern record example intentionally uses generic EHR-inspired patterns common in result exports: patient banner, status bar, charge/result grid, narrative report, care-coordination area, a selectively scanned referral attachment, a generated handwriting asset, and a labeled non-diagnostic image panel. The example's Lumen Harbor mark is an original fictional logo; it does not recreate an Epic, Oracle Health/Cerner, CMS, insurer, or hospital template.

The policy example intentionally uses generic public-program conventions: visible document control, section hierarchy, policy statement, documentation considerations, limitations, references, revision history, and an original fictional agency mark. It is not an actual policy or a coverage decision.
