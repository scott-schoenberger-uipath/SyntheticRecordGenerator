"""Create original fictional marks used by the checked-in demonstration specs.

These are deliberately simple geometric identifiers. They are not derived from any
provider, payer, government, EHR vendor, or agency brand.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
FONT = Path("/System/Library/Fonts/Supplemental/Verdana Bold.ttf")


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.truetype(str(FONT), size) if FONT.is_file() else ImageFont.load_default()


def _save(image: Image.Image, name: str) -> None:
    path = ROOT / "logos" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG")
    print(f"Wrote {path}")


def north_harbor_medical_center() -> None:
    image = Image.new("RGBA", (720, 180), "white")
    draw = ImageDraw.Draw(image)
    navy = "#173b59"
    teal = "#1f8092"
    draw.rounded_rectangle((18, 18, 152, 152), radius=28, fill=navy)
    draw.polygon([(83, 37), (113, 102), (83, 133), (53, 102)], fill=teal)
    draw.rectangle((75, 46, 91, 123), fill="white")
    draw.rectangle((54, 77, 112, 93), fill="white")
    draw.text((176, 42), "LUMEN HARBOR", fill=navy, font=_font(35))
    draw.text((178, 93), "MEDICAL CENTER  •  FICTIONAL", fill=teal, font=_font(18))
    _save(image, "lumen_harbor_medical_center.png")


def synthetic_policy_office() -> None:
    image = Image.new("RGBA", (650, 180), "white")
    draw = ImageDraw.Draw(image)
    navy = "#183b59"
    blue = "#2d638b"
    draw.rounded_rectangle((18, 18, 152, 152), radius=28, fill=navy)
    draw.polygon([(85, 37), (126, 69), (110, 122), (60, 122), (44, 69)], fill=blue)
    draw.rectangle((72, 55, 97, 107), fill="white")
    draw.rectangle((63, 68, 106, 81), fill="white")
    draw.text((176, 42), "SYNTHETIC POLICY", fill=navy, font=_font(34))
    draw.text((178, 93), "OFFICE  •  FICTIONAL", fill=blue, font=_font(18))
    _save(image, "synthetic_policy_office.png")


def prepare_handwriting_ink() -> None:
    """Make the generated handwriting legible after the scanned-page profile.

    The white paper is converted to transparency while the generated fictional
    marks become dark blue ink. This keeps the scanned attachment visibly
    handwritten without pretending the writing came from a real person.
    """
    source = ROOT / "handwriting" / "synthetic_handwritten_referral_note.png"
    if not source.is_file():
        raise FileNotFoundError(f"Expected generated handwriting source: {source}")
    source_image = Image.open(source).convert("RGB").crop((50, 58, 1490, 992))
    output = Image.new("RGBA", source_image.size, (0, 0, 0, 0))
    source_pixels = source_image.load()
    output_pixels = output.load()
    for y in range(source_image.height):
        for x in range(source_image.width):
            red, green, blue = source_pixels[x, y]
            brightness = (red + green + blue) // 3
            blue_bias = blue - ((red + green) // 2)
            if blue_bias > 16:
                opacity = min(255, (blue_bias - 8) * 4)
            elif brightness < 120:
                opacity = min(255, (135 - brightness) * 4)
            else:
                opacity = 0
            if opacity:
                output_pixels[x, y] = (27, 70, 137, opacity)
    path = ROOT / "handwriting" / "synthetic_handwritten_referral_ink.png"
    output.save(path, "PNG")
    print(f"Wrote {path}")


if __name__ == "__main__":
    north_harbor_medical_center()
    synthetic_policy_office()
    prepare_handwriting_ink()
