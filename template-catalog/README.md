# Template Catalog

Drop-in template architecture for synthetic packet generation.

## Add a new template

1. Add a JSON template file under one of:
   - `template-catalog/pdfme/`
   - `template-catalog/html/`
   - `template-catalog/overlay/`
2. Add a corresponding entry to `template-catalog/manifest.json` with:
   - `template_id`
   - `family`
   - `renderer` (`pdfmeRenderer`, `htmlPdfRenderer`, `overlayRenderer`)
   - `path`
   - `default`
3. Run mapping validation:

```bash
python3 tools/validate_template_mapping.py --template <path> --family <family>
```

## Bootstrapping from a synthetic exemplar PDF

```bash
python3 tools/bootstrap_template_from_exemplar.py \
  --synthetic-exemplar "/path/to/synthetic-exemplar.pdf" \
  --attest-synthetic-exemplar \
  --family registration_face_sheet \
  --renderer pdfmeRenderer \
  --template-id registration_face_sheet_v2 \
  --out template-catalog/local-bootstrap/registration_face_sheet_v2.json
```

This utility records only page dimensions and an expected mapper-key checklist. It does not extract or retain text from the exemplar, and it rejects use without a synthetic-only attestation.
