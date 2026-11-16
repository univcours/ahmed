#!/usr/bin/env python3
"""Chef Ahmed authentic photo restoration, stage 2026-11.

Create non-destructive social/event-background versions of each menu photo:
* The exact original photo is never modified or deleted.
* Food subjects: original photographed dish pixels are preserved via an
  alpha mask; only surrounding floor/counter is changed to a clean, refined
  Moroccan banquet room, with an artificial drop shadow.
* Chef/human pictures: NEVER generate new faces or inpaint a person. Display
  the full original photograph as a framed image within the room.
* If segmentation is uncertain, prefer an unaltered framed photograph.
* Every referenced output must exist before menu.json is changed.
All transformed photos must be described as digitally retouched when posted.
"""
import io
import json
import os
from pathlib import Path
from urllib.request import urlopen, Request

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "social" / "enhanced"
MENU = ROOT / "menu.json"
BACKGROUND_URL = "https://gcdn.picsart.com/picsart-mcp/1e399729-140a-4e9e-aaee-e8ba3dd93905.png"
WIDTH = HEIGHT = 1200
CHEF_CATEGORY = "أجواء المطبخ"


def bg_image():
    req = Request(BACKGROUND_URL, headers={"User-Agent":"ChefAhmed-Photo-Restoration/2.0"})
    with urlopen(req, timeout=35) as response:
        body = response.read(12_000_000)
    with Image.open(io.BytesIO(body)) as file:
        file.load()
        background = ImageOps.exif_transpose(file).convert("RGB")
        if background.width < 1200 or background.height < 600:
            raise RuntimeError("Decor background below acceptable resolution")
        # Keep the center room and marble counter — no meal or human introduced.
        canvas = ImageOps.fit(background,(WIDTH,HEIGHT),
            method=Image.Resampling.LANCZOS,centering=(.5,.5))
    return canvas


def frame_original(original, background):
    """Place completely unaltered content inside a framed photo: no AI faces."""
    base = background.convert("RGBA")
    image = ImageOps.contain(original, (1040,1030), Image.Resampling.LANCZOS)
    w,h = image.size
    x=(WIDTH-w)//2
    y=(HEIGHT-h)//2 + 20
    shadow=Image.new("RGBA",(WIDTH,HEIGHT),(0,0,0,0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (x-15,y-15,x+w+15,y+h+15),radius=20,fill=(0,0,0,135))
    base=Image.alpha_composite(base,shadow.filter(ImageFilter.GaussianBlur(25)))
    d=ImageDraw.Draw(base)
    d.rounded_rectangle((x-11,y-11,x+w+11,y+h+11),radius=15,fill=(255,253,248,255))
    base.alpha_composite(image.convert("RGBA"),(x,y))
    return base.convert("RGB")


def food_original(original,background,session):
    iw,ih=original.size
    factor=min(1,1000/max(iw,ih))
    small=original.resize((max(1,int(iw*factor)),max(1,int(ih*factor))),
                          Image.Resampling.LANCZOS)
    mask_s=remove(small,session=session,only_mask=True)
    if not isinstance(mask_s,Image.Image):
        mask_s=Image.open(io.BytesIO(mask_s))
    a=np.asarray(mask_s.convert("L").resize((iw,ih),Image.Resampling.BILINEAR))
    coverage=float((a>110).mean())
    if coverage<.17 or coverage>.89:
        return frame_original(original,background),"framed_original_low_confidence",coverage
    # Lift the alpha border slightly to protect dish edges and shadows:
    alpha=(a>65).astype(np.uint8)*255
    minside=min(iw,ih)
    radius=max(2,round(minside*.003))
    kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*radius+1,2*radius+1))
    alpha=cv2.dilate(alpha,kernel,iterations=1)
    alpha=cv2.GaussianBlur(alpha,(0,0),max(1.2,minside*.0012))
    rgba=original.convert("RGBA")
    rgba.putalpha(Image.fromarray(alpha,"L"))
    # Crop no food: use the complete original dimensions, masked background only.
    bounds=rgba.getbbox()
    if bounds is None:
        return frame_original(original,background),"framed_original_empty_mask",coverage
    subject=rgba.crop(bounds)
    max_w,max_h=1080,1010
    scale=min(max_w/subject.width,max_h/subject.height,1.0)
    if scale<1: subject=subject.resize((max(1,round(subject.width*scale)),
                                       max(1,round(subject.height*scale))),
                                       Image.Resampling.LANCZOS)
    x=(WIDTH-subject.width)//2
    y=HEIGHT-subject.height-34
    out=background.convert("RGBA")
    shadow=Image.new("RGBA",(WIDTH,HEIGHT),(0,0,0,0))
    subject_alpha=subject.getchannel("A")
    dark=Image.new("RGBA",subject.size,(17,14,10,110))
    dark.putalpha(subject_alpha.point(lambda v:int(v*.37)))
    shadow.alpha_composite(dark,(x+13,y+19))
    out=Image.alpha_composite(out,shadow.filter(ImageFilter.GaussianBlur(24)))
    out.alpha_composite(subject,(x,y))
    return out.convert("RGB"),"dish_original_pixels_over_clean_decor",coverage


def main():
    data=json.loads(MENU.read_text(encoding="utf-8"))
    sources=[(p,v) for p,v in data["items"].items()
             if not v.get("hidden") and Path(p).suffix.lower() in (".jpg",".jpeg",".png",".webp")]
    if len(sources)<35: raise RuntimeError("Too few visible originals to process")
    for p,v in sources:
        if not (ROOT/p).is_file(): raise FileNotFoundError("Missing menu photo: "+p)
    OUT.mkdir(parents=True,exist_ok=True)
    background=bg_image()
    background.save(OUT/"moroccan-banquet-background.jpg",
                    "JPEG",quality=92,optimize=True,subsampling=0)
    session=new_session("u2net")
    entries=[]
    mapping={}
    for i,(name,item) in enumerate(sources,1):
        with Image.open(ROOT/name) as src:
            original=ImageOps.exif_transpose(src).convert("RGB")
        # Human/chef photos: retain entire actual image, never touch the face.
        if item.get("category")==CHEF_CATEGORY or "الشيف" in (item.get("name_ar") or ""):
            result=frame_original(original,background)
            method="framed_untouched_chef_photo"
            coverage=None
        else:
            try:
                result,method,coverage=food_original(original,background,session)
            except Exception as exc:
                print("SAFE FALLBACK on #"+str(i)+": "+type(exc).__name__,flush=True)
                result=frame_original(original,background)
                method="framed_original_segmentation_error"
                coverage=None
        rel="social/enhanced/chef-ahmed-%02d.jpg"%i
        output=ROOT/rel
        result.save(output,"JPEG",quality=90,optimize=True,subsampling=0)
        with Image.open(output) as checked:
            checked.verify()
        mapping[name]=rel
        entries.append({"id":i,"original":name,"enhanced":rel,
            "name_ar":item.get("name_ar"),"category":item.get("category"),
            "method":method,"mask_coverage":coverage,
            "chef_identity_retouched":False,"original_photo_preserved":True})
        print("PHOTO %02d/%02d %s — %s"%(i,len(sources),item.get("name_ar",""),method),flush=True)
    if len(mapping)!=len(sources):raise RuntimeError("Incomplete output")

    # Overview sheet for independent visual QA (does not modify originals).
    columns=5
    tile=220
    rows=(len(entries)+columns-1)//columns
    book=Image.new("RGB",(columns*tile,rows*(tile+42)),(250,247,240))
    drawer=ImageDraw.Draw(book)
    for k,entry in enumerate(entries):
        with Image.open(ROOT/entry["enhanced"]) as im:
            thumb=ImageOps.contain(im.convert("RGB"),(tile-12,tile-12))
        px=(k%columns)*tile+(tile-thumb.width)//2
        py=(k//columns)*(tile+42)+(tile-thumb.height)//2
        book.paste(thumb,(px,py))
        drawer.text(((k%columns)*tile+12,(k//columns)*(tile+42)+tile+5),
                    "%02d | %s"%(entry["id"],entry["method"].split("_")[0]),
                    fill=(65,42,30))
    book.save(OUT/"contact-sheet.jpg",quality=85,optimize=True)

    # Manifest first; menu links updated only after every source is safe & present.
    (OUT/"manifest.json").write_text(json.dumps({
        "version":2,"count":len(mapping),
        "background":"social/enhanced/moroccan-banquet-background.jpg",
        "background_type":"AI-generated empty banquet room (no food/no people)",
        "notes":"Composite images; each real food/chef photograph is kept as original source",
        "items":entries},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    data["cleaned_images"]=mapping
    tmp=MENU.with_suffix(".json.stage")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(tmp,MENU)
    print("SUCCESS: %d enhanced photos ready, source originals kept."%len(mapping),flush=True)

if __name__=="__main__":
    main()
