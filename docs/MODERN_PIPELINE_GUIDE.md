# Modern Record and Policy Pipelines

`synthetic_document_pipelines` is the forward path for generation. It intentionally separates the two jobs that have different source controls and layouts:

- `record` creates one consolidated fictional patient packet. The caller supplies a list of page-sized clinical document objects, so packet length is explicit and reproducible.
- `policy` creates a standalone fictional policy document with document control, structured sections, references, and revision history.

Both pipelines require `metadata.is_synthetic: true`, write a manifest with the output checksum, display a clear synthetic-use restriction on every page, and render deterministically from the same specification and assets.

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

The `documents` array determines the exact number of pages and is preserved **in the supplied order**. This matters because production packets commonly arrive in received order, not clinical-time order. Add `clinical_datetime`, `filed_datetime`, `source_state`, and `record_flags` to make late-filed, duplicate, partial, unsigned, or otherwise messy documents reviewable without hiding the conflict.

Set `scanned: true` for a fictional outside/fax attachment; the selective scan profile rasterizes only that page with an off-axis, grainy paper treatment and preserves one consolidated PDF output. Its `annotations` are drawn on the page *before* rasterization, so handwriting and fax stamps belong to the scan rather than floating above it.

`image_panel` is intentionally opt-in. A packet with an image panel must set `rendering.allow_illustrative_imaging: true`, provide `rendering.illustrative_imaging_reason`, and remains limited to one panel unless the caller explicitly raises `rendering.max_illustrative_image_panels`. Every panel is permanently labeled illustrative and non-diagnostic.

The generic renderer supports any page-sized record type, including admission/H&P, physician and consultant notes, nursing notes, lab and diagnostic results, medication records, discharge documents, referrals, and outside attachments. Use `type`, `details`, `sections`, and `record_flags` to describe the desired source document rather than treating the packet as a clean chronological timeline. Use `result_rows` for a compact result-table treatment (lab, vital-sign, or similar structured results); it preserves test, value, units, reference context, and flag.

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

The modern record example intentionally uses generic EHR-inspired patterns common in mixed inbound packets: lab results, nursing documentation, imaging result, an imaging-specific attachment, an imported fax referral, an admission note, and a specialty consultation. The pages are deliberately in received order rather than clinical-time order and include duplicate/late-filed/partial-document flags. The example's Lumen Harbor mark is an original fictional logo; it does not recreate an Epic, Oracle Health/Cerner, CMS, insurer, or hospital template.

The policy example intentionally uses generic public-program conventions: visible document control, section hierarchy, policy statement, documentation considerations, limitations, references, revision history, and an original fictional agency mark. It is not an actual policy or a coverage decision.
