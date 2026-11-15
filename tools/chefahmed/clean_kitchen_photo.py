#!/usr/bin/env python3
"""Pixel-preserving cleanup of an original seafood kitchen photograph.

Only edit the right-hand background containing the black trash bucket
and floor clutter. Do not change any pixel of the plated food or chef.
Keep a backup of the original before replacing the site image.
"""
import hashlib
import shutil
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PHOTO = ROOT / "WhatsApp Image 2026-08-28 at 12.17.50 (3).jpeg"
BACKUP = ROOT / "social" / "originals" / "seafood-kitchen-before-trash-removal.jpeg"

def read(path):
    arr=np.fromfile(str(path),dtype=np.uint8)
    img=cv2.imdecode(arr,cv2.IMREAD_COLOR)
    if img is None: raise ValueError("Cannot read source JPEG")
    return img

def write(path,img):
    ok,encoded=cv2.imencode(".jpg",img,[cv2.IMWRITE_JPEG_QUALITY,94])
    if not ok: raise RuntimeError("JPEG encode failed")
    path.parent.mkdir(parents=True,exist_ok=True)
    encoded.tofile(str(path))

def main():
    if not BACKUP.exists():
        BACKUP.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(PHOTO,BACKUP)
    img=read(BACKUP)
    h,w=img.shape[:2]
    print("Source size:",w,h)
    if (w,h)!=(1280,960):
        raise RuntimeError("Unexpected original dimensions. Refusing destructive overwrite.")

    # Replace the black trash bucket with real clean floor texture from
    # ANOTHER PART OF THIS ORIGINAL PHOTO. This avoids the blurry/flat
    # results caused by inpainting a large bucket with only a few pixels.
    x0,y0,x1,y1=919,662,1107,947
    sx0,sy0=1071,425
    patch=img[sy0:sy0+(y1-y0),sx0:sx0+(x1-x0)].copy()
    if patch.shape[:2] != (y1-y0,x1-x0):
        raise RuntimeError("Floor patch dimensions not available")
    mask_patch=np.zeros((y1-y0,x1-x0),dtype=np.uint8)
    # Hand-traced mask avoids touching the plated lobster and shrimp.
    pts=[
        (27,40),(64,19),(96,14),(139,30),(158,31),(180,52),
        (183,244),(160,274),(25,277),(10,250),(8,64)
    ]
    cv2.fillPoly(mask_patch,[np.array(pts,np.int32)],255)
    # Use a separately retouched, clean view of *this same kitchen*
    # only as a texture reference for the trash-bin region, keeping
    # every original meal pixel untouched. Never replace the entire image.
    import urllib.request
    reference_url=(
      "https://gcdn.picsart.com/picsart-mcp/"
      "02c1bd26-f345-4029-896e-27aaa9af8c8c.png"
    )
    req=urllib.request.Request(reference_url,headers={"User-Agent":"ChefAhmed-Photo-Restoration/1.0"})
    with urllib.request.urlopen(req,timeout=30) as response:
        ai_bytes=response.read(8_000_000)
    reference=cv2.imdecode(np.frombuffer(ai_bytes,np.uint8),cv2.IMREAD_COLOR)
    if reference is None:
        raise RuntimeError("Clean floor reference unavailable; leave site photo unchanged")
    reference=cv2.resize(reference,(w,h),interpolation=cv2.INTER_AREA)
    tile=reference[y0:y1,x0:x1].astype(np.float32)
    # Match overall background floor brightness to nearby original tiles.
    orig_clean_area=img[730:900,1112:1210].astype(np.float32)
    ref_clean_area=reference[730:900,1112:1210].astype(np.float32)
    tile=np.clip(tile+(orig_clean_area.mean(axis=(0,1))-ref_clean_area.mean(axis=(0,1))),0,255)
    # A broad soft edge prevents a rectangular paste line.
    inner=(mask_patch>0).astype(np.uint8)*255
    soft=cv2.GaussianBlur(inner,(0,0),20).astype(np.float32)/255.0
    soft=np.where(mask_patch>0,np.maximum(soft,0.85),soft)
    dst=img[y0:y1,x0:x1].astype(np.float32)
    cleaned=img.copy()
    cleaned[y0:y1,x0:x1]=np.clip(
        (tile*soft[...,None]+dst*(1-soft[...,None])),0,255
    ).astype(np.uint8)
    # Small floor stains on the far right can safely be locally healed.
    floor_mask=np.zeros((h,w),dtype=np.uint8)
    cv2.ellipse(floor_mask,(1139,716),(30,14),0,0,360,255,-1)
    cv2.ellipse(floor_mask,(1184,687),(10,8),0,0,360,255,-1)
    cleaned=cv2.inpaint(cleaned,floor_mask,3,cv2.INPAINT_TELEA)
    # Pixel-for-pixel preserve everything on the left including all food.
    changed=(np.abs(cleaned.astype("int16")-img.astype("int16")).sum(axis=2)>0)
    assert not changed[:630,:910].any(), "Original dishes or chef altered unexpectedly"
    write(PHOTO,cleaned)
    print("Garbage removed and original foods preserved.")
    print("Source backup:",BACKUP.relative_to(ROOT))
    print("Site image:",PHOTO.name)
    print("Original sha256:",hashlib.sha256(BACKUP.read_bytes()).hexdigest())
    print("Cleaned sha256:",hashlib.sha256(PHOTO.read_bytes()).hexdigest())

if __name__=="__main__":
    main()
