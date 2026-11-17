#!/usr/bin/env python3
"""Publish cleaned originals as independent, reversible assets for Chef Ahmed.

For 15 visibly dirty floor/counter photographs: replace only the background
outside the subject with clean ivory. The FOOD pixels stay from original JPG.
For kitchen scene: safely crop ONLY the trash-containing far-right background
while keeping both photographed seafood trays and chef untouched.
Never delete the source originals or alter price/description/hidden status.
"""
from pathlib import Path
import json
import numpy as np
import cv2
from PIL import Image,ImageOps
from rembg import remove,new_session

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"social"/"cleaned"
MENU=ROOT/"menu.json"

SELECTED=[
 "WhatsApp Image 2026-08-28 at 12.17.47 (2).jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.47 (3).jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.47 (4).jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.47 (5).jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.48 (1).jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.48 (2).jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.48 (3).jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.48.jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.50 (2).jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.50 (5).jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.51 (1).jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.51 (3).jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.51.jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.50 (1).jpeg",
 "WhatsApp Image 2026-08-28 at 22.03.51.jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.47 (1).jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.49 (2).jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.50.jpeg",
]
KITCHEN="WhatsApp Image 2026-08-28 at 12.17.50 (3).jpeg"

def studio(width,height):
    # Ecru plaster surface with restrained directional brightness,
    # never fake flowers or food: only original dish is in foreground.
    yy,xx=np.mgrid[0:height,0:width]
    v=8*(xx/width-.5)+5*(yy/height-.5)
    rng=np.random.default_rng(707)
    grain=rng.normal(0,1.5,(height,width))
    arr=np.stack([244+v+grain,238+v+grain,229+v+grain],axis=2)
    return Image.fromarray(np.uint8(np.clip(arr,0,255)),"RGB")

def clean_dish(photo,session):
    w,h=photo.size
    factor=min(1,950/max(w,h))
    preview=photo.resize((round(w*factor),round(h*factor)),Image.Resampling.LANCZOS)
    mat=remove(preview,session=session,only_mask=True)
    mask=np.asarray(mat.convert("L").resize((w,h),Image.Resampling.BILINEAR))
    coverage=(mask>95).mean()
    if coverage<.16 or coverage>.90:
        raise ValueError("Unsafe subject segmentation coverage "+str(round(coverage,3)))
    radius=max(5,round(min(w,h)*.009))
    kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(radius*2+1,radius*2+1))
    solid=cv2.dilate((mask>95).astype(np.uint8)*255,kernel)
    feather=cv2.GaussianBlur(solid,(0,0),sigmaX=max(2,min(w,h)*.004))
    result=Image.composite(photo,studio(w,h),Image.fromarray(feather,"L"))
    return result,round(float(coverage),3)

def main():
    data=json.loads(MENU.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True,exist_ok=True)
    newmap=dict(data.get("cleaned_images",{}))
    session=new_session("u2net")
    checked=[]
    for i,name in enumerate(SELECTED,1):
        if name not in data["items"] or data["items"][name].get("hidden"):
            raise ValueError("Not a selected public original")
        original=ImageOps.exif_transpose(Image.open(ROOT/name)).convert("RGB")
        clean,coverage=clean_dish(original,session)
        fname=f"food-{i:02}.jpg"
        clean.save(OUT/fname,"JPEG",quality=94,subsampling=0,optimize=True)
        newmap[name]=f"social/cleaned/{fname}"
        data["items"][name]["cleaned_image"]=newmap[name]
        checked.append({"original":name,"clean":newmap[name],"mask_coverage":coverage,
                        "width":clean.width,"height":clean.height,
                        "original_untouched":True})
        print(f"Cleaned {i:02d}/{len(SELECTED)} original-food image; mask {coverage:.3f}",flush=True)
    with Image.open(ROOT/KITCHEN) as source:
        original=ImageOps.exif_transpose(source).convert("RGB")
        width,height=original.size
        if width<1300 or height<1000:
            raise ValueError("Kitchen photo was changed; refusing blind crop")
        # The black trash bins and hanging clutter occupy the far right.
        # Keep all photographed seafood plates (x<=1050) and the chef
        # exactly pixel-for-pixel, only cut the background x>1090.
        cropped=original.crop((0,0,1090,height))
        cropped.save(OUT/"kitchen-real-original-clean-framing.jpg","JPEG",
                     quality=95,subsampling=0,optimize=True)
        newmap[KITCHEN]="social/cleaned/kitchen-real-original-clean-framing.jpg"
        data["items"][KITCHEN]["cleaned_image"]=newmap[KITCHEN]
        checked.append({"original":KITCHEN,"clean":newmap[KITCHEN],
                        "operation":"frame out right-side trash with exact original food pixels",
                        "width":cropped.width,"height":cropped.height,
                        "original_untouched":True})
    data["cleaned_images"]=newmap
    # Atomic JSON write only after every file and QA has succeeded.
    temp=MENU.with_suffix(".json.tmp")
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    temp.replace(MENU)
    (OUT/"manifest.json").write_text(json.dumps(
        {"selected_count":len(SELECTED)+1,
         "mode":"original pixels preserved, dirty surroundings replaced; photo sources untouched",
         "images":checked},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("COMPLETE: cleaned",len(checked),"food/kitchen photos; originals unchanged.")
if __name__=="__main__":main()
