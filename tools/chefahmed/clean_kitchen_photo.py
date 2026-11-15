#!/usr/bin/env python3
"""Clean photo framing by cropping the right-hand trash-bin area.

Uses the real original photograph; no pixel synthesis or changes to the
food or the chef. Original is preserved in social/originals.
"""
from pathlib import Path
import shutil
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
PHOTO=ROOT/"WhatsApp Image 2026-08-28 at 12.17.50 (3).jpeg"
BACKUP=ROOT/"social"/"originals"/"seafood-kitchen-before-trash-removal.jpeg"

def main():
    if not BACKUP.exists():
        BACKUP.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(PHOTO,BACKUP)
    image=cv2.imdecode(np.fromfile(str(BACKUP),np.uint8),cv2.IMREAD_COLOR)
    if image is None or image.shape[:2]!=(960,1280):
        raise RuntimeError("Unexpected original photo; refuse replacement")
    # Right-hand black bin begins at x~923; crop at 916 to keep
    # the chef and authentic platters but remove the rubbish entirely.
    cropped=image[:,:916].copy()
    ok,buf=cv2.imencode(".jpg",cropped,[cv2.IMWRITE_JPEG_QUALITY,96])
    if not ok: raise RuntimeError("JPEG error")
    buf.tofile(str(PHOTO))
    print("Website photo updated: real seafood and chef retained, trash bin excluded.")
    print("Source:",BACKUP.relative_to(ROOT))
    print("Output:",PHOTO.name,"size",cropped.shape[1],cropped.shape[0])
if __name__=="__main__":
    main()
