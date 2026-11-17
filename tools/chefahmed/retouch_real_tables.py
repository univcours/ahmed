#!/usr/bin/env python3
"""Precise dirt retouch on the original photographed worktable (NOT background removal).

Never crop or reposition a dish; NEVER composite a new table/floor, recolor food,
or replace the scene. Only manually approved off-plate stain zones are eligible.
Keep output dimensions exactly unchanged; preserve ALL off-mask pixels byte-identical.
Outputs use lossless PNG to preserve the original photographed food pixel values.

Run from repository root:
    python tools/chefahmed/retouch_real_tables.py        # preview only
    python tools/chefahmed/retouch_real_tables.py --publish  # map reviewed photos
"""
from pathlib import Path
import argparse
import json

import cv2
import numpy as np
from PIL import Image, ImageOps, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "social" / "retouched-tables"
MENU = ROOT / "menu.json"

# Coordinates are fractions (x / width, y / height), visually reviewed against
# the corresponding SOURCE photo. All polygons are strictly outside the whole
# photographed serving dish, including rim and garnishes.
# We target dark isolated dirt/grime only, never re-texture the entire table.
REGIONS = {
    "WhatsApp Image 2026-08-28 at 12.17.48 (3).jpeg": [
        [(0,0), (.31,0),(.27,.10),(.14,.19),(0,.20)],
        [(.87,0),(1,0),(1,.38),(.92,.36),(.92,.20)],
        [(.94,.30),(1,.25),(1,.98),(.95,.89)],
        [(0,.68),(.09,.70),(.14,.85),(.23,1),(0,1)],
        [(.82,1),(1,1),(1,.81),(.93,.85),(.92,.96)]
    ],
    "WhatsApp Image 2026-08-28 at 12.17.47 (5).jpeg": [
        [(.89,.13),(1,.13),(1,.75),(.95,.74),(.93,.61),(.91,.39)],
        [(0,.81),(.09,.82),(.15,.94),(.19,1),(0,1)]
    ],
    "WhatsApp Image 2026-08-28 at 12.17.47 (4).jpeg": [
        [(.91,.09),(1,.09),(1,.26),(.94,.24)],
        [(0,.88),(.12,.91),(.18,1),(0,1)]
    ],
    "WhatsApp Image 2026-08-28 at 12.17.50 (2).jpeg": [
        [(0,0),(.23,0),(.15,.09),(.08,.19),(0,.35)],
        [(.87,0),(1,0),(1,.27),(.95,.19)],
        [(0,.78),(.11,.85),(.22,1),(0,1)],
    ],
}

# Do not erase actual grout/patterns, tray shadows, or table material; mask
# only unusually dark, low-saturation grime pixels inside manually defined
# regions. The source table remains in place everywhere outside tiny masks.
VALUE_LIMIT = {
    "WhatsApp Image 2026-08-28 at 12.17.48 (3).jpeg": 85,
    "WhatsApp Image 2026-08-28 at 12.17.47 (5).jpeg": 96,
    "WhatsApp Image 2026-08-28 at 12.17.47 (4).jpeg": 88,
    "WhatsApp Image 2026-08-28 at 12.17.50 (2).jpeg": 75,
}

def make_mask(rgb, filename):
    h,w=rgb.shape[:2]
    roi=np.zeros((h,w),np.uint8)
    for polygon in REGIONS[filename]:
        pts=np.array([(round(x*(w-1)),round(y*(h-1))) for x,y in polygon], np.int32)
        cv2.fillPoly(roi, [pts], 255)
    # avoid geometry along polygon limits or nearby plate rim
    roi=cv2.erode(roi,np.ones((9,9),np.uint8),iterations=1)
    hsv=cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    dark=(hsv[:,:,2]<VALUE_LIMIT[filename]) & (hsv[:,:,1]<115)
    # Resolve only small grime islands, never whole table areas.
    candidate=(dark & (roi>0)).astype(np.uint8)
    n,labels,stats,_=cv2.connectedComponentsWithStats(candidate,8)
    mask=np.zeros((h,w),np.uint8)
    max_component=int(h*w*.009)
    for i in range(1,n):
        area=int(stats[i,cv2.CC_STAT_AREA])
        if 4<=area<=max_component:
            mask[labels==i]=255
    # Slightly cover smear edges, but never cross the approved off-food area.
    mask=cv2.dilate(mask,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(7,7)))
    mask=cv2.bitwise_and(mask,roi)
    return mask, roi

def clean_one(source_path, destination):
    src=ImageOps.exif_transpose(Image.open(source_path)).convert("RGB")
    rgb=np.asarray(src).copy()
    mask,_=make_mask(rgb,source_path.name)
    filled=cv2.inpaint(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR),mask,3,cv2.INPAINT_TELEA)
    out=cv2.cvtColor(filled,cv2.COLOR_BGR2RGB)
    # Guaranteed 100% original food and table pixels outside explicitly
    # designated stains, regardless of algorithm or metadata.
    if not np.array_equal(out[mask==0],rgb[mask==0]):
        raise RuntimeError("Original pixels outside dirt mask were changed!")
    changed=int(np.count_nonzero(mask))
    pct=changed/mask.size
    if pct>.09:
        raise RuntimeError(f"Unsafe broad change region: {pct:.1%}")
    destination.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(out).save(destination,"PNG",optimize=True)
    return src, Image.fromarray(out), changed, pct

def contact_sheet(rows, out):
    w=1100;cw=550;ch=400
    canvas=Image.new("RGB",(w,ch*len(rows)),(242,241,236))
    draw=ImageDraw.Draw(canvas)
    for k,(name,original,cleaned,_,pct) in enumerate(rows):
        for side,im in enumerate([original,cleaned]):
            thumb=ImageOps.contain(im,(cw-30,ch-75),Image.Resampling.LANCZOS)
            x=side*cw+(cw-thumb.width)//2;y=k*ch+(ch-75-thumb.height)//2
            canvas.paste(thumb,(x,y))
        draw.text((16,k*ch+ch-55),f"{k+1}. ORIGINAL",fill=(25,40,35))
        draw.text((cw+16,k*ch+ch-55),f"SPOT CLEAN: {pct:.2%} of pixels | ORIGINAL TABLE",fill=(25,40,35))
        draw.text((16,k*ch+ch-30),name,fill=(65,65,65))
    canvas.save(out,"JPEG",quality=89,optimize=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--publish",action="store_true")
    args=parser.parse_args()
    data=json.loads(MENU.read_text(encoding="utf-8"))
    rows=[]
    for name in REGIONS:
        if name not in data["items"]:raise KeyError("Original item missing: "+name)
        source=ROOT/name
        if not source.is_file():raise FileNotFoundError(source)
        target=OUT/(source.stem.replace("WhatsApp Image 2026-08-28 at ","").replace(" ","_").replace("(","").replace(")","")+".png")
        old,new,count,pct=clean_one(source,target)
        print(f"{name}: small dirt-pixel cleanup {count} pixels ({pct:.2%}); no crop; real plate and table.",flush=True)
        rows.append((name,old,new,count,pct))
        if args.publish:
            data["items"][name]["cleaned_image"]=str(target.relative_to(ROOT))
    OUT.mkdir(parents=True,exist_ok=True)
    contact_sheet(rows,OUT/"full-plates-original-tables-preview.jpg")
    (OUT/"audit.json").write_text(json.dumps({
        "intent":"Keep the ENTIRE real serving plate and original photographed table; retouch tiny dirt marks only",
        "source_originals_unchanged":True,
        "items":[{"name":name,"retouched":str((OUT/(Path(name).stem.replace("WhatsApp Image 2026-08-28 at ","").replace(" ","_").replace("(","").replace(")","")+".png")).relative_to(ROOT)),
                  "masked_pixels":count,"masked_share":round(pct,6)} for name,_,_,count,pct in rows]
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if args.publish:
        MENU.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("DONE",len(rows),"full-photo localized edits. Menu update:",args.publish)
if __name__=="__main__": main()
