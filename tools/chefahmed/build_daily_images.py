#!/usr/bin/env python3
"""Build real photo collages, keeping chef and meal originals unaltered.

Sources: chef.jpg and visible meal photos from menu.json. No AI-generated
faces, food or ingredients. Outputs only generated JPEGs and a manifest.
"""
from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "social" / "daily-images"
WIDTH = HEIGHT = 1080


def font(size):
    for name in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ):
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def image_for(meal: Path, chef: Image.Image, destination: Path) -> None:
    with Image.open(meal) as original:
        plate = ImageOps.exif_transpose(original).convert("RGB")
    bg = ImageOps.fit(
        plate, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5)
    ).convert("RGBA")

    # A gentle gradient helps labels without obscuring the real dish.
    gradient = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gradient)
    for y in range(HEIGHT - 220, HEIGHT):
        strength = int(168 * ((y - (HEIGHT - 220)) / 220))
        gd.line((0, y, WIDTH, y), fill=(6, 24, 28, strength))
    bg = Image.alpha_composite(bg, gradient)

    # Chef's original portrait appears as a small circular photo, not a fake.
    circle = 320
    portrait = ImageOps.fit(
        chef, (circle, circle), method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.37)
    ).convert("RGBA")
    mask = Image.new("L", (circle, circle), 0)
    ImageDraw.Draw(mask).ellipse((1, 1, circle - 2, circle - 2), fill=255)
    portrait.putalpha(mask)

    x, y = 1080 - circle - 36, 1080 - circle - 38
    shadow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse(
        (x - 11, y - 8, x + circle + 15, y + circle + 18), fill=(0, 0, 0, 120)
    )
    bg = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(bg)
    d.ellipse((x - 10, y - 10, x + circle + 10, y + circle + 10), fill=(255, 255, 255, 255))
    d.ellipse((x - 6, y - 6, x + circle + 6, y + circle + 6), outline=(15, 183, 176, 255), width=8)
    bg.alpha_composite(portrait, (x, y))

    label = ImageDraw.Draw(bg)
    label.rounded_rectangle((35, 38, 337, 103), radius=20, fill=(3, 36, 44, 217))
    label.text((57, 51), "CHEF AHMED", fill=(255, 255, 255, 255), font=font(37))
    label.text((40, 958), "0689199142", fill=(255, 255, 255, 255), font=font(43))

    destination.parent.mkdir(parents=True, exist_ok=True)
    bg.convert("RGB").save(destination, "JPEG", quality=85, optimize=True,
                           progressive=True, subsampling=0)


def main():
    data = json.loads((ROOT / "menu.json").read_text(encoding="utf-8"))
    chef_path = ROOT / "chef.jpg"
    if not chef_path.is_file():
        raise FileNotFoundError(chef_path)
    with Image.open(chef_path) as src:
        chef = ImageOps.exif_transpose(src).convert("RGB")

    records = []
    for file, info in data["items"].items():
        if info.get("hidden") or not info.get("name_ar"):
            continue
        if info.get("category") == "أجواء المطبخ":
            continue
        meal = ROOT / file
        if not meal.is_file() or meal.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        idx = len(records) + 1
        rel = "social/daily-images/%02d.jpg" % idx
        image_for(meal, chef, ROOT / rel)
        records.append({
            "index": idx, "source": file, "image": rel,
            "name_ar": info.get("name_ar"),
            "desc_ar": info.get("desc_ar"),
            "category": info.get("category"),
        })
    if len(records) < 20:
        raise ValueError("Too few real meal photos found")
    (OUT / "index.json").write_text(
        json.dumps({"chef": "chef.jpg", "items": records},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("Generated %s real food + chef composite images." % len(records))
    print("For publication use URL https://raw.githubusercontent.com/univcours/ahmed/main/<image>")


if __name__ == "__main__":
    main()
