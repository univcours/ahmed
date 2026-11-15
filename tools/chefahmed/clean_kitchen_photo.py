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

    # Target only garbage bin and wrapper at the counter's far right.
    # The seafood plates occupy the left/bottom portions and are NEVER masked.
    mask=np.zeros((h,w),np.uint8)
    polygons=[
       # Black bin and clear plastic bag immediately behind it.
       [(933,696),(964,675),(1012,671),(1051,693),(1076,690),
        (1106,710),(1106,739),(1100,918),(1072,942),
        (938,947),(921,927),(919,731)],
       # Floor debris / wash stain beside the discarded bucket.
       [(1103,672),(1151,673),(1183,705),(1180,744),
        (1143,751),(1092,731)],
       # Dark incidental object intruding from top-right, not part of the dishes.
       [(1197,0),(1279,0),(1279,161),(1217,148),(1171,86)],
    ]
    for pts in polygons:
        cv2.fillPoly(mask,[np.array(pts,np.int32)],255)
    mask=cv2.dilate(mask,np.ones((7,7),np.uint8),iterations=1)
    # Multistage content-aware fill only of the rubbish mask.
    cleaned=cv2.inpaint(img,mask,7,cv2.INPAINT_TELEA)
    # Preserve the actual food EXACTLY as captured, pixel-for-pixel, outside mask.
    changed=(np.abs(cleaned.astype("int16")-img.astype("int16")).sum(axis=2)>0)
    assert not changed[:640,:900].any(), "Food or chef pixels modified unexpectedly"
    write(PHOTO,cleaned)
    print("Garbage removed and original foods preserved.")
    print("Source backup:",BACKUP.relative_to(ROOT))
    print("Site image:",PHOTO.name)
    print("Original sha256:",hashlib.sha256(BACKUP.read_bytes()).hexdigest())
    print("Cleaned sha256:",hashlib.sha256(PHOTO.read_bytes()).hexdigest())

if __name__=="__main__":
    main()
