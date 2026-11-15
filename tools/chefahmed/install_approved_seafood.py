#!/usr/bin/env python3
"""Install the exact user-selected, cleaned seafood-kitchen photograph.

The user supplied a 1448x1086 PNG. Store the exact uploaded PNG separately,
then convert it to JPEG at the existing menu filename so every existing
website link, menu entry and share page points to the corrected photograph.
This script does not call Facebook or modify captions/recipes.
"""
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
from PIL import Image, ImageOps
import hashlib
import os

ROOT = Path(__file__).resolve().parents[2]
APPROVED = ROOT / "social" / "approved-seafood-photo.png"
TARGET = ROOT / "WhatsApp Image 2026-08-28 at 12.17.50 (3).jpeg"
URL = "https://gcdn.picsart.com/picsart-mcp/98f8dbe0-6987-48ae-a18d-95b380436ce1.png"

def main():
    req = Request(URL, headers={"User-Agent": "ChefAhmed-Approved-Photo-Import/1.0"})
    with urlopen(req, timeout=35) as response:
        data = response.read(10_000_000)
    with Image.open(BytesIO(data)) as img:
        img.load()
        img = ImageOps.exif_transpose(img)
        if img.size != (1448, 1086):
            raise RuntimeError("Unexpected uploaded image dimensions; site unchanged")
        if img.format not in ("PNG", "JPEG", "WEBP"):
            raise RuntimeError("Unsupported verified image encoding; site unchanged")
        rgb = img.convert("RGB")
    APPROVED.parent.mkdir(parents=True, exist_ok=True)
    # The approved image host may transcode PNG into WEBP or JPEG.
    # Persist the approved visual pixels in a real, standards-compliant PNG.
    rgb.save(APPROVED, format="PNG", optimize=True)
    print("Downloaded approved photo encoding:", Image.open(BytesIO(data)).format)
    temp = TARGET.with_suffix(".jpeg.tmp")
    rgb.save(temp, format="JPEG", quality=96, subsampling=0, optimize=True)
    os.replace(temp, TARGET)
    with Image.open(TARGET) as verify:
        if verify.size != (1448, 1086) or verify.format != "JPEG":
            raise RuntimeError("Post-save verification failed")
    print("Updated original image path:", TARGET.name)
    print("Kept unchanged source:", APPROVED.relative_to(ROOT))
    print("Archived PNG sha256:", hashlib.sha256(APPROVED.read_bytes()).hexdigest())
    print("JPEG sha256:", hashlib.sha256(TARGET.read_bytes()).hexdigest())

if __name__ == "__main__":
    main()
