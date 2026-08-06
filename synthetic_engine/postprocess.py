from __future__ import annotations

import random
import shutil
import tempfile
from pathlib import Path


def apply_packet_realism(
    source_pdf: Path,
    output_pdf: Path,
    *,
    seed: int,
    handwriting_asset_dir: Path | None = None,
    noise_pages_ratio: float = 0.35,
) -> None:
    try:
        from pypdf import PdfReader, PdfWriter
        from reportlab.pdfgen import canvas as rl_canvas
    except Exception:
        shutil.copyfile(source_pdf, output_pdf)
        return

    # Handwriting belongs on source attachments before those pages are scanned.
    # OverlayRenderer handles that path through save_packet_pdf; packet-level
    # postprocessing must not add handwriting to arbitrary native pages.
    _ = handwriting_asset_dir
    rng = random.Random(seed)

    reader = PdfReader(str(source_pdf))
    writer = PdfWriter()

    with tempfile.TemporaryDirectory(prefix="packet-realism-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        for idx, page in enumerate(reader.pages, start=1):
            do_noise = rng.random() < noise_pages_ratio
            do_checkbox = rng.random() < 0.18

            if do_noise or do_checkbox:
                page_w = float(page.mediabox.width)
                page_h = float(page.mediabox.height)
                stamp_pdf = tmp_root / f"stamp_{idx:04d}.pdf"
                c = rl_canvas.Canvas(str(stamp_pdf), pagesize=(page_w, page_h))

                if do_noise:
                    c.setStrokeGray(0.45)
                    c.setLineWidth(0.25)
                    dot_count = int((page_w * page_h) / 6400)
                    for _ in range(dot_count):
                        x = rng.uniform(18, page_w - 18)
                        y = rng.uniform(36, page_h - 36)
                        r = rng.uniform(0.12, 0.36)
                        c.circle(x, y, r, stroke=1, fill=0)

                if do_checkbox:
                    c.setLineWidth(1)
                    x0 = page_w - 170 + rng.uniform(-14, 6)
                    y0 = page_h * 0.28 + rng.uniform(-24, 18)
                    for row in range(3):
                        yy = y0 - row * 18
                        c.rect(x0, yy, 10, 10, stroke=1, fill=0)
                        if rng.random() < 0.55:
                            c.line(x0 + 1.5, yy + 5.0, x0 + 4.5, yy + 1.0)
                            c.line(x0 + 4.5, yy + 1.0, x0 + 8.5, yy + 9.0)

                c.showPage()
                c.save()

                stamp_reader = PdfReader(str(stamp_pdf))
                if stamp_reader.pages:
                    page.merge_page(stamp_reader.pages[0])

            writer.add_page(page)

        with output_pdf.open("wb") as f:
            writer.write(f)
