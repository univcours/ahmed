#!/usr/bin/env python3
"""Clean real table/floor debris and add a small flower bouquet WITHOUT changing food.

Real photographs and their tables stay in position. Each old source photo is
immutable. Only localized, manually reviewed off-dish polygons may be inpainted.
Bouquet is placed in a protected empty counter space of the kitchen-wide shot.
Never use background-removal/scene generation, never crop or recolor a platter.
"""
from __future__ import annotations
import json
import math
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFilter
from retouch_real_tables import REGIONS, VALUE_LIMIT

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "social" / "cleaned"
MENU = ROOT / "menu.json"
KITCHEN = "WhatsApp Image 2026-08-28 at 12.17.50 (3).jpeg"
OUT_PREFIX = "original-table-decor-"

# The photo has two real seafood platters on a central granite workbench.
# These few polygons cover ONLY empty floor/counter regions. The bucket and
# other large objects are left alone rather than synthesizing fake tile.
KITCHEN_DIRT_AREAS = [
    [(0.82, 0.66), (0.998, 0.66), (0.998, 0.86), (0.86, 0.85)],
    [(0.00, 0.37), (0.20, 0.37), (0.19, 0.45), (0.00, 0.48)],
]
# Hard exclusion for the TWO complete seafood trays and for the chef/person.
KITCHEN_PROTECTED = [
    (0.12, 0.51, 0.76, 1.00),  # all serving food, trays, garnishes and rim
    (0.275, 0.195, 0.54, 0.66), # chef and body
]
BOUQUET_BOX = (0.054, 0.24, 0.205, 0.48)  # on an EMPTY original left-side counter


def polygons_mask(shape: tuple[int,int], polygons) -> np.ndarray:
    h, w = shape
    mask = np.zeros((h, w), np.uint8)
    for coords in polygons:
        pts = np.array([(round(x*(w-1)),round(y*(h-1))) for x,y in coords],np.int32)
        cv2.fillPoly(mask,[pts],255)
    return mask


def protected_kitchen(shape: tuple[int,int]) -> np.ndarray:
    h, w = shape
    protected = np.zeros((h,w), np.uint8)
    for x0,y0,x1,y1 in KITCHEN_PROTECTED:
        x0=int(round(x0*w)); y0=int(round(y0*h))
        x1=int(round(x1*w)); y1=int(round(y1*h))
        protected[y0:y1, x0:x1] = 255
    return protected


def crumbs_mask(rgb: np.ndarray, region: np.ndarray, max_fraction=.0020) -> np.ndarray:
    """Find tiny warm-colored, high-contrast food crumbs on an approved surface."""
    hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
    hue, sat, val=cv2.split(hsv)
    warm = (((hue>=4)&(hue<=32)) | ((hue>=170)&(hue<=179))) & (sat>60) & (val>55)
    local=cv2.GaussianBlur(rgb.astype(np.float32),(0,0),sigmaX=6)
    # An isolated food crumb differs from its immediate floor/counter.
    diff=np.max(np.abs(rgb.astype(np.float32)-local),axis=2)
    raw=(warm & (diff>17) & (region>0)).astype(np.uint8)
    count,labels,stats,_=cv2.connectedComponentsWithStats(raw,connectivity=8)
    mask=np.zeros(region.shape,np.uint8)
    limit=int(region.size*max_fraction)
    for i in range(1,count):
        area=int(stats[i,cv2.CC_STAT_AREA])
        if 5<=area<=limit:
            mask[labels==i]=255
    mask=cv2.dilate(mask,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5)))
    return cv2.bitwise_and(mask,region)


def get_clean_mask(rgb: np.ndarray, filename: str):
    h,w=rgb.shape[:2]
    if filename==KITCHEN:
        roi=polygons_mask((h,w),KITCHEN_DIRT_AREAS)
        roi=cv2.erode(roi,np.ones((11,11),np.uint8))
        protection=protected_kitchen((h,w))
        roi[protection>0]=0
        stains=crumbs_mask(rgb,roi,max_fraction=.0007)
        hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
        dark=((hsv[:,:,2]<76) & (hsv[:,:,1]<65) & (roi>0)).astype(np.uint8)
        # Only small dark marks; no wholesale erasure of the patterned tile.
        n,labels,stats,_=cv2.connectedComponentsWithStats(dark,8)
        for k in range(1,n):
            if 6<=stats[k,cv2.CC_STAT_AREA]<=int(h*w*.0005):
                stains[labels==k]=255
        stains=cv2.bitwise_and(stains,roi)
        stains[protection>0]=0
        return stains,roi,protection
    if filename not in REGIONS:
        raise KeyError("No safe source-photo surface boundaries: "+filename)
    roi=polygons_mask((h,w),REGIONS[filename])
    roi=cv2.erode(roi,np.ones((11,11),np.uint8))
    protect=(roi==0).astype(np.uint8)*255
    hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
    value=hsv[:,:,2];sat=hsv[:,:,1]
    threshold=VALUE_LIMIT[filename]
    raw=(value<threshold) & (sat<115) & (roi>0)
    comps,lbl,stats,_=cv2.connectedComponentsWithStats(raw.astype(np.uint8),8)
    grime=np.zeros((h,w),np.uint8)
    max_area=int(h*w*(.060 if "12.17.48 (3)" in filename else .009))
    for k in range(1,comps):
        area=int(stats[k,cv2.CC_STAT_AREA])
        if 4<=area<=max_area:
            grime[lbl==k]=255
    grime=cv2.dilate(grime,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(7,7)))
    crumbs=crumbs_mask(rgb,roi)
    mask=cv2.bitwise_or(grime,crumbs)
    mask=cv2.bitwise_and(mask,roi)
    # Preserve full serving platter plus a margin from every edge.
    mask[protect>0]=0
    return mask,roi,protect


def soft_oval(canvas, rect, color, blur=0):
    layer=Image.new("RGBA",canvas.size,(0,0,0,0))
    ImageDraw.Draw(layer).ellipse(rect, fill=color)
    if blur:
        layer=layer.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(layer)


def leaf(canvas, cx, cy, rx, ry, tilt, color):
    w,h=canvas.size
    layer=Image.new("RGBA",(w,h),(0,0,0,0))
    d=ImageDraw.Draw(layer)
    d.ellipse((int(cx-rx),int(cy-ry),int(cx+rx),int(cy+ry)),fill=color)
    layer=layer.rotate(tilt,Image.Resampling.BICUBIC,center=(int(cx),int(cy)))
    canvas.alpha_composite(layer)


def rose(canvas, cx, cy, radius, hue, seed):
    rng=random.Random(seed)
    r=radius
    soft_oval(canvas,(cx-r*1.09,cy-r*.90,cx+r*1.10,cy+r*.98),(0,0,0,33),blur=5)
    for layer in range(3):
        n=7-layer
        ring_radius=r*(.61-.17*layer)
        petal_radius=r*(.46-.08*layer)
        for k in range(n):
            angle=2*math.pi*k/n+layer*.34
            px=cx+math.cos(angle)*ring_radius
            py=cy+math.sin(angle)*ring_radius*.73
            delta=rng.randint(-17,16)
            rgb=tuple(max(0,min(255,c+delta-7*layer)) for c in hue)
            leaf(canvas,int(px),int(py),
                 int(petal_radius*.90),int(petal_radius*1.22),
                 int(-angle*180/math.pi),(rgb[0],rgb[1],rgb[2],249))
    soft_oval(canvas,(cx-r*.18,cy-r*.16,cx+r*.18,cy+r*.17),
              (max(0,hue[0]-31),max(0,hue[1]-34),max(0,hue[2]-28),255),blur=1)
    soft_oval(canvas,(cx-r*.11,cy-r*.12,cx+r*.08,cy+r*.06),(255,222,185,105),blur=2)


def floral_bouquet(size: tuple[int,int]) -> Image.Image:
    """Small, self-contained floral decor: no outside licensed photo required."""
    rng=random.Random(137)
    w,h=520,590
    canvas=Image.new("RGBA",(w,h),(0,0,0,0))
    draw=ImageDraw.Draw(canvas)
    # Gentle contact shadow and natural stems under slightly transparent glass.
    soft_oval(canvas,(175,529,355,565),(12,28,26,67),blur=17)
    stems=[(236,188),(310,166),(182,197),(349,237),(132,244),
           (275,102),(201,120),(354,137)]
    for px,py in stems:
        draw.line([(260,512),(260+(px-260)*.34,340),(px,py)],
                  fill=(61,101,73,218),width=rng.randint(5,8),joint="curve")
    # Eucalyptus and leaves extending to the bouquet sides.
    for j in range(23):
        angle=2*math.pi*j/23
        cx=int(258+math.cos(angle)*rng.randint(98,171))
        cy=int(205+math.sin(angle)*rng.randint(63,127))
        tilt=rng.randint(-79,79)
        shade=(rng.randint(76,116),rng.randint(110,155),rng.randint(79,117),238)
        leaf(canvas,cx,cy,rng.randint(15,24),rng.randint(25,39),tilt,shade)
        draw.line([(cx-7,cy+15),(cx+9,cy-12)],fill=(181,201,154,111),width=2)
    # Roses never touch a photographed food tray: restricted to decor rectangle.
    roses=[
        (188,206,65,(241,177,147),101),
        (309,190,69,(236,194,166),102),
        (270,119,57,(247,236,215),103),
        (376,255,52,(232,162,149),104),
        (128,256,50,(245,210,177),105),
    ]
    for vals in roses: rose(canvas,*vals)
    # Little creamy gypsophila buds among the roses.
    for j in range(45):
        x=rng.randint(91,411)
        y=rng.randint(86,289)
        if abs(x-260)<45 and 146<y<248: continue
        rad=rng.randint(3,7)
        soft_oval(canvas,(x-rad,y-rad,x+rad,y+rad),(244,244,226,236),blur=1)
    # Transparent thick glass flower vase. Draw behind reflective highlights.
    glass=Image.new("RGBA",(w,h),(0,0,0,0))
    d=ImageDraw.Draw(glass)
    d.polygon([(206,343),(325,343),(348,525),(185,525)],
              fill=(187,221,210,84))
    d.polygon([(206,425),(328,425),(338,520),(196,520)],
              fill=(130,189,182,78))
    d.line([(208,346),(193,515),(214,526)],fill=(233,253,250,215),width=8)
    d.line([(321,346),(339,514),(321,526)],fill=(236,253,251,192),width=7)
    d.arc((194,328,336,356),180,360,fill=(241,253,245,231),width=7)
    d.arc((192,510,345,541),0,180,fill=(151,197,187,192),width=6)
    d.line([(235,364),(214,407)],fill=(248,253,245,179),width=8)
    d.line([(301,433),(315,489)],fill=(245,255,253,105),width=6)
    canvas.alpha_composite(glass)
    # Final tiny natural softening to avoid graphic hard edges in a photo.
    canvas=canvas.filter(ImageFilter.GaussianBlur(.65))
    return canvas.resize(size,Image.Resampling.LANCZOS)


def add_bouquet(rgb: np.ndarray):
    h,w=rgb.shape[:2]
    x0,y0,x1,y1=BOUQUET_BOX
    x0=int(round(x0*w));x1=int(round(x1*w))
    y0=int(round(y0*h));y1=int(round(y1*h))
    flowers=floral_bouquet((x1-x0,y1-y0))
    rgba=Image.fromarray(rgb,"RGB").convert("RGBA")
    overlay=Image.new("RGBA",rgba.size,(0,0,0,0))
    overlay.alpha_composite(flowers,(x0,y0))
    rgba=Image.alpha_composite(rgba,overlay)
    output=np.asarray(rgba.convert("RGB"))
    # Exact guarantee: no bouquet pixel near chef or seafood platter.
    changed=np.any(output!=rgb,axis=2)
    allowed=np.zeros((h,w),np.uint8)
    allowed[y0:y1,x0:x1]=255
    if np.any(changed & (allowed==0)):
        raise RuntimeError("Bouquet overflow")
    if np.any(changed & (protected_kitchen((h,w))>0)):
        raise RuntimeError("Bouquet touched chef or real plated food")
    return output,changed,(x0,y0,x1,y1)


def main():
    source=json.loads(MENU.read_text(encoding="utf-8"))
    selected=list(REGIONS)+[KITCHEN]
    OUT.mkdir(parents=True,exist_ok=True)
    audit=[]
    for name in selected:
        if name not in source["items"] or not (ROOT/name).is_file():
            raise RuntimeError("Original image missing from Chef Ahmed catalog: "+name)
        original=np.asarray(ImageOps.exif_transpose(Image.open(ROOT/name)).convert("RGB"))
        h,w=original.shape[:2]
        mask,roi,protect=get_clean_mask(original,name)
        if float((mask>0).mean())>.085:
            raise RuntimeError("Unsafe dirt mask coverage: "+name)
        clean_bgr=cv2.inpaint(cv2.cvtColor(original,cv2.COLOR_RGB2BGR),
                             mask,4,cv2.INPAINT_TELEA)
        result=cv2.cvtColor(clean_bgr,cv2.COLOR_BGR2RGB)
        dirt_changed=np.any(result!=original,axis=2)
        if np.any(dirt_changed & (mask==0)):
            raise RuntimeError("Modified pixels outside approved dirt masks: "+name)
        bouquet_box=None
        if name==KITCHEN:
            result,flowers_changed,bouquet_box=add_bouquet(result)
        else:
            flowers_changed=np.zeros((h,w),dtype=bool)
        changed=np.any(result!=original,axis=2)
        if np.any(changed & (protect>0)):
            raise RuntimeError("REAL food or person altered in "+name)
        if changed.mean()>.105:
            raise RuntimeError("Too much of original photo altered: "+name)
        if np.array_equal(result,original):
            print("SKIP (no safe changes):",name,flush=True)
            continue
        destination=OUT/(OUT_PREFIX+name.replace("WhatsApp Image 2026-08-28 at ","")
                           .replace(" ","_").replace("(","").replace(")","")
                           .replace(".jpeg","")+".png")
        Image.fromarray(result).save(destination,"PNG",optimize=True)
        source["items"][name]["cleaned_image"]=str(destination.relative_to(ROOT))
        audit.append({"original":name,"output":str(destination.relative_to(ROOT)),
                      "width":w,"height":h,"dish_and_source_table_unchanged_outside_masks":True,
                      "dirt_pixels":int(dirt_changed.sum()),
                      "bouquet_pixels":int(flowers_changed.sum()),
                      "bouquet_box":list(bouquet_box) if bouquet_box else None,
                      "total_edited_pct":round(100*changed.mean(),4)})
        print(name,"cleaned/decorated",round(100*changed.mean(),3),"%",flush=True)
    if len(audit)!=5:
        raise RuntimeError("Expected 5 safely edited original photos, got "+str(len(audit)))
    (OUT/"real-floor-and-flower-audit.json").write_text(
        json.dumps({"source_originals_preserved":True,
                    "no_crop_or_new_background":True,"items":audit},
                   ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Update catalog ONLY after all images are saved and geometry has been verified.
    MENU.write_text(json.dumps(source,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("SUCCESS:",len(audit),"real source photos, no changed original dishes.",flush=True)

if __name__=="__main__":
    main()
