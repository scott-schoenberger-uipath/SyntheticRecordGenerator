# Generation Pipeline Research and Design Decisions

Reviewed: 2026-08-06

This repository creates demo and evaluation artifacts only. It must never ingest, train on, emit, or attempt to reconstruct real-person clinical information. The visual review of user-provided records informed generic patterns only: compact patient banners, result-status bands, charge/result tables, narrative-report hierarchy, and selected scanned attachments. No patient facts, text, identifiers, logos, or proprietary templates were copied.

## Assessed sources and libraries

| Source or library | What it offers | Decision for this repository |
| --- | --- | --- |
| [Synthea](https://github.com/synthetichealth/synthea) | Open-source synthetic patient populations with encounters, conditions, medications, allergies, labs, procedures, C-CDA, FHIR, and CSV exports. | Treat as an optional upstream data adapter for future FHIR/C-CDA imports. It is not a runtime requirement for the PDF renderer, which keeps the demo generator lightweight and deterministic. |
| [ReportLab](https://docs.reportlab.com/reportlab/userguide/ch1_intro/) | Python primitives for pagination, tables, typography, and vector PDF output. | Core renderer for the two pipelines because it reliably supports fixed-layout EHR-inspired pages and policy tables without browser dependencies. |
| [Pillow filters](https://pillow.readthedocs.io/en/stable/reference/ImageFilter.html) | Blur, contrast, grayscale, and pixel-level image transformation. | Core to the selective scan profile, which adds modest raster scanning artifacts only to chosen attachment pages. |
| [pypdfium2](https://pypdfium2.readthedocs.io/en/stable/) | PDF page rasterization used before applying scan effects. | Core scan adapter. Native pages remain vector; only flagged pages are rasterized and replaced in the same consolidated packet. |
| [look-like-scanned](https://github.com/navchandar/look-like-scanned) | MIT-licensed package focused on making PDFs look scanned. | Keep as an optional enhancement candidate. The new pipeline does not depend on its command-line wrapper, avoiding an environment-specific path while retaining the existing project integration. |
| [WeasyPrint](https://doc.courtbouillon.org/weasyprint/stable/api_reference.html) | HTML/CSS paged-media PDF generation, including bookmarks and forms. | Useful future adapter for long, branded policy documents. The initial policy pipeline uses the same deterministic ReportLab base as records, so examples run in the smallest environment. |
| [CMS Internet-Only Manuals](https://www.cms.gov/medicare/regulations-guidance/manuals/internet-only-manuals-ioms) and the [NCD Manual](https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/downloads/ncd103c1_part1.pdf) | Authoritative examples of public-program policy organization, revision controls, and document context. | Use only as structural inspiration and as a source registry target. Never automate copying of policy text; every production policy must retain its source URL, effective date, jurisdiction, and public-domain/license assessment. |

## What is kept, consolidated, and deferred

### Keep

- The existing long-form, template-driven, and legacy scenario generators remain intact. They already cover varied record families and are useful test assets.
- Existing handwriting assets and the installed `look-like-scanned` environment remain available as optional enhancers.
- The checked-in handwriting and imaging assets are fictional demonstration images. The handwriting is generated, visibly labeled as synthetic, and post-processed only to remain legible after a scan profile.
- Original fictional provider and agency marks are generated from source code in `synthetic_document_pipelines/assets/create_demo_logos.py`; no real organization or government mark is included.

### Consolidate into the new layer

- A single JSON-in/PDF-out record pipeline, with one `documents` item per physical page. This gives callers direct control of packet length and document mix.
- A separate policy pipeline with document-control fields, paginated sections, references, and revision-history support.
- One synthetic-only guard, one deterministic manifest shape, and one CLI entry point for both artifact types.
- A selective scan profile that preserves one PDF per patient packet while only converting intended non-native attachments.

### Do not remove yet

The repository has many standalone scripts and uncommitted local changes. Deleting or renaming them now would risk breaking active demos and would make a review unnecessarily broad. Migrate a legacy generator only after it has a modern JSON specification, output-parity test, and named owner; then move it to a documented `legacy/` area in a separate change.

## Safety and provenance rules

1. Every input must set `metadata.is_synthetic: true`, carry a synthetic label, and use an MRN beginning with `SYN-`.
2. Every output page carries a visible synthetic-use restriction.
3. EHR profiles are generic and inspired by common information architecture; they do not use vendor marks, logos, or copied vendor templates.
4. Handwriting, imaging-style raster panels, and scan effects are opt-in, clearly labeled, and applied only to fictional content. Imaging-style panels require an explicit reason, default to a maximum of one per packet, and are never described as DICOM, source imaging, or diagnostic evidence.
5. Brand marks must be original fictional marks. Do not use real provider, payer, government, EHR-vendor, or agency logos.
6. Public policy sources are never treated as evergreen. Callers must retain the source, jurisdiction, effective date, and any licensing/public-domain review outside the generated artifact.
