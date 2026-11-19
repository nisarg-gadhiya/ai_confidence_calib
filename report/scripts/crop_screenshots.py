"""Crop full-page screenshots (report/figures/raw) to the region each figure discusses.

    report/.venv/Scripts/python.exe report/scripts/crop_screenshots.py

Boxes are (top, bottom) in device pixels of the 2x captures; width is kept.
"""
from pathlib import Path

from PIL import Image

FIG = Path(__file__).resolve().parents[1] / "figures"
RAW = FIG / "raw"

BOXES = {
    "ui_ask_empty": (0, None),
    "ui_ask_arithmetic": (1480, 3720),   # answer card, tiles, charts, first steps
    "ui_ask_factual": (3000, 4530),      # reasoning chain with expanded sources
    "ui_ask_logical": (3000, 4940),      # proof steps and knowledge base
    "ui_analytics": (0, None),
    "ui_run_history": (0, 2600),         # first rows of the history
    "ui_dark_detail": (0, 3060),         # run detail without trailing empty space
    "ui_json_view": (0, None),
    "ui_mobile": (1700, 4650),           # answer, gauge, tiles and charts at phone width
}


def trim_bottom(image: Image.Image, background_tolerance: int = 6) -> Image.Image:
    """Remove uniform rows at the bottom (empty page area)."""
    gray = image.convert("L")
    width, height = gray.size
    ref = gray.getpixel((width // 2, height - 1))
    bottom = height
    for y in range(height - 1, 0, -4):
        row = gray.crop((0, y, width, y + 1)).getextrema()
        if row[1] - row[0] > background_tolerance or abs(row[0] - ref) > background_tolerance:
            bottom = min(height, y + 40)
            break
    return image.crop((0, 0, width, bottom))


def main():
    for name, (top, bottom) in BOXES.items():
        src = RAW / f"{name}.png"
        if not src.exists():
            print("missing", src)
            continue
        image = Image.open(src)
        box = (0, top, image.width, bottom or image.height)
        cropped = trim_bottom(image.crop(box))
        cropped.save(FIG / f"{name}.png", optimize=True)
        print(name, cropped.size)


if __name__ == "__main__":
    main()
