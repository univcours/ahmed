#!/usr/bin/env python3
"""Improve the visibly pixelated portraits in the public Chef Ahmed gallery.

The uploaded Canva thumbnails were 160x200 and 200x133, not full-resolution
sources. Restore detail from those low-res public thumbnails with an open
source FSRCNN super-resolution model, without generating different food/faces.
The AI originals should replace these enhanced copies if uploaded later.
"""
from pathlib import Path
from urllib.request import Request, urlopen
from PIL import Image, ImageFilter, ImageOps
import json
import numpy as np
import cv2

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/"social"/"cleaned"
MODEL=ROOT/"tools"/"chefahmed"/"FSRCNN_x4.pb"
URI="https://raw.githubusercontent.com/Saafke/FSRCNN_Tensorflow/master/models/FSRCNN_x4.pb"
PHOTOS=[
    ("chef-ahmed-moroccan-feast.jpg","chef-ahmed-moroccan-feast-sharp.webp",(160,200)),
    ("chef-ahmed-wedding-service.jpg","chef-ahmed-wedding-service-sharp.webp",(200,133)),
]

def download_model():
    if MODEL.is_file() and MODEL.stat().st_size>10000: return
    import time
    for attempt in range(3):
        try:
            data=urlopen(Request(URI,headers={"User-Agent":"ChefAhmed-Publisher/1.0"}),timeout=35).read()
            if len(data)<10000:raise RuntimeError("Model too small")
            MODEL.write_bytes(data)
            return
        except Exception:
            if attempt==2:raise
            time.sleep(3)

def main():
    download_model()
    sr=cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel(str(MODEL))
    sr.setModel("fsrcnn",4)
    menu_path=ROOT/"menu.json"
    menu=json.loads(menu_path.read_text(encoding="utf-8"))
    for source,output,thumb_size in PHOTOS:
        path=DEST/source
        image=ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        # Existing JPEGs had been scaled up from tiny Canva previews. Recover
        # their actual information size before neural super-resolution.
        original_preview=image.resize(thumb_size,Image.Resampling.LANCZOS)
        array=cv2.cvtColor(np.asarray(original_preview),cv2.COLOR_RGB2BGR)
        result=sr.upsample(array)
        restored=Image.fromarray(cv2.cvtColor(result,cv2.COLOR_BGR2RGB))
        restored=restored.filter(ImageFilter.UnsharpMask(radius=1.15,percent=82,threshold=3))
        output_path=DEST/output
        restored.save(output_path,format="WEBP",quality=94,method=6)
        print(output_path,restored.size,output_path.stat().st_size,flush=True)
    old=menu["items"]["WhatsApp Image 2026-08-28 at 22.03.51 (2).jpeg"]
    old["public_image"]="social/cleaned/chef-ahmed-moroccan-feast-sharp.webp"
    old["cleaned_image"]=old["public_image"]
    if "social/cleaned/chef-ahmed-wedding-service.jpg" not in menu["items"]:
        raise RuntimeError("Cannot find wedding image entry; refusing accidental catalog change")
    # Keep the product key for backwards-compatible category and sharing URLs.
    wedding=menu["items"]["social/cleaned/chef-ahmed-wedding-service.jpg"]
    wedding["public_image"]="social/cleaned/chef-ahmed-wedding-service-sharp.webp"
    menu_path.write_text(json.dumps(menu,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
