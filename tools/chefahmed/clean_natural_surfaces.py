#!/usr/bin/env python3
"""Chef Ahmed photo surface clean-up: keep original dishes, clean only surroundings.

No generative replacement of any meal, garnish, tray, chef or human.
Uses CPU subject segmentation only to identify the *background*, then puts the
unmodified source foreground over a subtle clean worktop. Original files never
change.  Preview mode creates a QA contact sheet without changing the menu.
"""
import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps, ImageDraw
from rembg import remove, new_session

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "social" / "cleaned"
MENU = ROOT / "menu.json"
CHEF_CAT = "أجواء المطبخ"
KITCHEN = "WhatsApp Image 2026-08-28 at 12.17.50 (3).jpeg"

def texture(width, height, category, seed):
    """Photographic neutral worktop, softly mottled like polished stone or steel."""
    rng = np.random.default_rng(seed)
    steel = category == "مأكولات بحرية"
    dark = category in ("لحوم ومشوي", "لحم بالبرقوق")
    rgb = np.array([194, 200, 200] if steel else
                   [181, 177, 171] if dark else
                   [222, 218, 208], dtype=np.float32)
    scale = min(1.0, 1440 / max(width, height))
    sw, sh = max(64, round(width * scale)), max(64, round(height * scale))
    def coarse(nx, ny):
        layer = rng.standard_normal((ny, nx)).astype(np.float32)
        return cv2.resize(layer, (sw, sh), interpolation=cv2.INTER_CUBIC)
    yy, xx = np.mgrid[:sh, :sw].astype(np.float32)
    light = 7.0 * (0.45 - xx / sw) + 6.0 * (0.45 - yy / sh)
    wave = coarse(8, 8) * 3.2 + coarse(36, 36) * 1.9
    fine = rng.normal(0, 2.15 if not steel else 1.45, (sh, sw))
    if steel:
        # Fine brushed-metal grain with directional reflections, not blank ivory.
        stripe = rng.normal(0, 0.85, sw).astype(np.float32)
        wave += stripe[np.newaxis, :] + np.sin(xx * 0.014) * 0.8
    else:
        vein = coarse(12, 22)
        wave += 1.0 * np.sin(vein * 5.3 + xx / 110)
    luminance = light + wave + fine
    result = np.clip(rgb[np.newaxis, np.newaxis, :] +
                     luminance[:, :, None], 0, 255).astype(np.uint8)
    if (sw, sh) != (width, height):
        result = cv2.resize(result, (width, height), interpolation=cv2.INTER_LINEAR)
    return result

def clean_photo(src, session, category, seed):
    w, h = src.size
    factor = min(1.0, 880.0/max(w, h))
    sm = src.resize((round(w*factor), round(h*factor)), Image.Resampling.LANCZOS)
    segmented = remove(sm, session=session, only_mask=True)
    if not isinstance(segmented, Image.Image):
        raise RuntimeError("Segmentation did not return a mask")
    raw = np.asarray(segmented.convert("L").resize((w, h), Image.Resampling.BILINEAR))
    area = float(np.mean(raw > 90))
    # If the subject detector is unsure, NEVER edit the original photo.
    if area < .16 or area > .91:
        return None, area, "unsafe_foreground_coverage"
    minside = min(w, h)
    # Close holes among food elements, include all plate and garnish edges.
    radius = max(4, int(minside*.005))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(radius*2+1,radius*2+1))
    solid = cv2.morphologyEx((raw >= 65).astype(np.uint8)*255,
                            cv2.MORPH_CLOSE, kernel)
    solid = cv2.dilate(solid, kernel, iterations=2)
    # Recover original nearby background shadows so plate does not float.
    shadow = cv2.GaussianBlur(solid, (0,0), sigmaX=max(3, minside*.011))
    backdrop = texture(w,h,category,seed).astype(np.float32)
    base = np.asarray(src).astype(np.float32)
    # Preserve the photographed contact shading around the tray for grounding.
    darken = (shadow.astype(np.float32) / 255.0)*14.0
    backdrop = np.maximum(backdrop-darken[:,:,None],0)
    alpha = cv2.GaussianBlur(solid, (0,0), sigmaX=max(1.0, minside*.0012))
    # Make foreground cores fully opaque; feather only at the external edges.
    interior=cv2.erode(solid,cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,(radius*2+1,radius*2+1)))
    alpha[interior==255]=255
    alpha = alpha.astype(np.float32)[:,:,None]/255.0
    # Pixel-exact conservation of every original meal pixel in the core.
    composed = (base*alpha + backdrop*(1-alpha)).clip(0,255).astype(np.uint8)
    if not np.array_equal(composed[interior==255], np.asarray(src)[interior==255]):
        raise RuntimeError("Original meal pixels were modified")
    return Image.fromarray(composed, "RGB"), area, "original_subject_clean_worktop"

def contact_sheet(entries, output):
    width = 1000
    cell_w, cell_h = 250, 310
    rows = math.ceil(len(entries)/4)
    canvas = Image.new("RGB", (width, rows*cell_h), (243,242,239))
    draw = ImageDraw.Draw(canvas)
    for i, (name, before, after, method) in enumerate(entries):
        col, row = i % 4, i // 4
        x, y = col*cell_w, row*cell_h
        thumbnails = [before, after]
        for j, photo in enumerate(thumbnails):
            thumb = ImageOps.contain(photo, (114,250),Image.Resampling.LANCZOS)
            px = x + (3 if j == 0 else 129) + (114-thumb.width)//2
            py = y + (250-thumb.height)//2
            canvas.paste(thumb, (px,py))
        draw.text((x+7,y+253),f"{i+1:02d} ORIGINAL | CLEAN", fill=(34,39,35))
        draw.text((x+7,y+275),method[:31], fill=(84,90,86))
    output.parent.mkdir(parents=True,exist_ok=True)
    canvas.save(output, "JPEG", quality=87,optimize=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args=parser.parse_args()
    data=json.loads(MENU.read_text(encoding="utf-8"))
    listed=[(n,it) for n,it in data["items"].items() if not it.get("hidden")
            and Path(n).suffix.lower() in (".jpg",".jpeg",".png",".webp")]
    if len(listed)<35: raise RuntimeError("Unexpectedly small food gallery")
    listed = listed[:args.limit] if args.limit else listed
    session=new_session("u2net")
    manifest=[]
    comparison=[]
    for i,(name,item) in enumerate(listed,1):
        srcfile=ROOT/name
        if not srcfile.exists(): raise FileNotFoundError(name)
        photo=ImageOps.exif_transpose(Image.open(srcfile)).convert("RGB")
        category=item.get("category") or ""
        if category==CHEF_CAT or "الشيف" in (item.get("name_ar") or ""):
            result=None
            method="original_chef_preserved"
            coverage=None
        elif name==KITCHEN:
            result=None
            method="original_kitchen_preserved"
            coverage=None
        else:
            try:
                result,coverage,method=clean_photo(photo,session,category,1337+i)
            except Exception as error:
                result=None
                coverage=None
                method="original_fallback_"+type(error).__name__
        if result is not None:
            clean_path=f"social/cleaned/natural-{i:02}.jpg"
            file=ROOT/clean_path
            file.parent.mkdir(parents=True,exist_ok=True)
            result.save(file,"JPEG",quality=95,subsampling=0,optimize=True)
            item["cleaned_image"]=clean_path
        elif not args.preview:
            item.pop("cleaned_image",None)
            clean_path=None
        else:
            clean_path=None
        manifest.append({"original":name,"clean":clean_path,
                         "method":method,"coverage":coverage,
                         "original_untouched":True})
        comparison.append((name, photo, result or photo, method))
        print(f"{i:02d}/{len(listed)} {method}: {name}",flush=True)
    DEST.mkdir(parents=True,exist_ok=True)
    contact_sheet(comparison, DEST/("natural-preview.jpg" if args.preview else "natural-contact-sheet.jpg"))
    (DEST/("natural-preview.json" if args.preview else "natural-manifest.json")).write_text(
        json.dumps({"mode":"natural counter/floor cleanup, exact original food preserved",
                    "images":manifest}, ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if not args.preview:
        # No existing images or product descriptions are deleted. Menu points to
        # reversible cleaned copies; anyone can switch back to original photos.
        MENU.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("DONE",len(manifest),"sources; transformed",sum(bool(x["clean"]) for x in manifest),flush=True)

if __name__=="__main__":
    main()
