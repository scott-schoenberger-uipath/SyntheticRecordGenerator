# Handwriting Assets

Drop optional handwriting assets here to enable overlay in generated packets.

Supported files:
- `*.png`
- `*.jpg`, `*.jpeg`
- `*.webp`
- `*.tif`, `*.tiff`
- `*.svg` (auto-converted if `cairosvg` is installed)

Recommended source workflow:
1. Generate handwriting snippets offline (for example with TypeScribe).
2. Export short snippets/signoffs as transparent PNG or SVG.
3. Keep snippets short and clinically relevant (margin notes, brief signoffs).
4. Avoid using overlays on every page.

Runtime env vars:
- `SYNTHREC_ENABLE_HANDWRITING=1`
- `SYNTHREC_HANDWRITING_ASSET_DIR` (optional override, defaults to this folder)
- `SYNTHREC_HANDWRITING_MAX_OVERLAYS` (default `8`)
