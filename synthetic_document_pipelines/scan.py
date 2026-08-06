from __future__ import annotations

import random
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterable


def _soft_scan(image: Any, rng: random.Random) -> Any:
    """Apply intentionally subtle scanner artifacts to an already synthetic page."""
    from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps

    original = image.convert("L")
    original = ImageOps.autocontrast(original, cutoff=0.15)
    original = ImageEnhance.Contrast(original).enhance(rng.uniform(0.78, 0.91))
    original = original.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.10, 0.32)))

    noise = Image.effect_noise(original.size, rng.uniform(3.0, 8.0)).convert("L")
    noise = ImageEnhance.Contrast(noise).enhance(0.22)
    softened = ImageChops.multiply(original, noise)
    blended = Image.blend(original, softened, rng.uniform(0.025, 0.065))
    tinted = ImageOps.colorize(blended, black=(24, 25, 24), white=(252, 249, 240))

    angle = rng.uniform(-0.28, 0.28)
    return tinted.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor=(252, 249, 240))


def apply_scan_profile(
    source_pdf: Path,
    output_pdf: Path,
    *,
    selected_pages: Iterable[int],
    seed: int,
) -> dict[str, Any]:
    """Rasterize only selected pages, preserving a single consolidated PDF output.

    pypdfium2 and Pillow are deliberately optional. If either is unavailable, the
    pipeline leaves the native PDF intact and reports the fallback in the manifest.
    """
    page_numbers = sorted({number for number in selected_pages if number > 0})
    if not page_numbers:
        shutil.copyfile(source_pdf, output_pdf)
        return {"applied": False, "reason": "No pages selected"}

    try:
        import pypdfium2 as pdfium
        from pypdf import PdfReader, PdfWriter
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
    except ImportError:
        shutil.copyfile(source_pdf, output_pdf)
        return {"applied": False, "reason": "Optional scan dependencies unavailable"}

    base_reader = PdfReader(str(source_pdf))
    selected = [number for number in page_numbers if number <= len(base_reader.pages)]
    if not selected:
        shutil.copyfile(source_pdf, output_pdf)
        return {"applied": False, "reason": "Selected pages outside page range"}

    rng = random.Random(seed)
    with tempfile.TemporaryDirectory(prefix="synthetic-scan-") as temp_dir:
        temp_root = Path(temp_dir)
        pdfium_doc = pdfium.PdfDocument(str(source_pdf))
        scanned_pages: dict[int, Any] = {}

        for number in selected:
            page = pdfium_doc[number - 1]
            bitmap = page.render(scale=1.8)
            pil_image = bitmap.to_pil()
            bitmap.close()
            page.close()
            processed = _soft_scan(pil_image, rng).convert("RGB")
            image_path = temp_root / f"scanned-{number:03d}.jpg"
            processed.save(image_path, "JPEG", quality=88, optimize=True)

            source_page = base_reader.pages[number - 1]
            width = float(source_page.mediabox.width)
            height = float(source_page.mediabox.height)
            replacement_path = temp_root / f"replacement-{number:03d}.pdf"
            overlay = canvas.Canvas(str(replacement_path), pagesize=(width, height))
            overlay.drawImage(ImageReader(str(image_path)), 0, 0, width=width, height=height)
            overlay.showPage()
            overlay.save()
            scanned_pages[number] = PdfReader(str(replacement_path)).pages[0]

        pdfium_doc.close()

        writer = PdfWriter()
        for number, page in enumerate(base_reader.pages, start=1):
            writer.add_page(scanned_pages.get(number, page))
        with output_pdf.open("wb") as handle:
            writer.write(handle)

    return {"applied": True, "pages": selected, "profile": "soft_scan"}
