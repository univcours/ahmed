#!/usr/bin/env python3
"""Make a contact sheet of only Chef Ahmed's original menu pictures.
Generated contact sheets are stored outside the menu allowlist.
"""
import json, pathlib, math, re
from PIL import Image,ImageOps,ImageDraw,ImageFont
ROOT=pathlib.Path(__file__).resolve().parents[2]
manifest=json.loads((ROOT/"menu.json").read_text(encoding="utf-8"))["items"]
files=[(k,v) for k,v in manifest.items() if not v.get("hidden") and pathlib.Path(k).is_file() is False]
# Filenames are relative to repository root, not the runner CWD.
files=[(k,v) for k,v in manifest.items() if not v.get("hidden") and (ROOT/k).is_file()]
columns=5
w,h=240,205
sheet=Image.new("RGB",(w*columns,h*math.ceil(len(files)/columns)),(250,248,243))
d=ImageDraw.Draw(sheet)
report=[]
for i,(name,item) in enumerate(files):
    with Image.open(ROOT/name) as raw:
        rgb=ImageOps.exif_transpose(raw).convert("RGB")
        W,H=rgb.size
        img=ImageOps.contain(rgb,(230,165),method=Image.Resampling.LANCZOS)
        x=(i%columns)*w+(w-img.width)//2
        y=(i//columns)*h+(168-img.height)//2
        sheet.paste(img,(x,y))
        d.text(((i%columns)*w+9,(i//columns)*h+174),f"{i+1:02d} | {W}x{H}",fill=(25,20,20))
        d.rectangle(((i%columns)*w,(i//columns)*h,(i%columns+1)*w-1,(i//columns+1)*h-1),outline=(215,208,200),width=1)
        report.append({"index":i+1,"file":name,"name_ar":item.get("name_ar"),"width":W,"height":H,
                       "ratio":round(W/H,3)})
out=ROOT/"social"/"audit"
out.mkdir(parents=True,exist_ok=True)
sheet.save(out/"menu-contact-sheet.jpg",quality=84,optimize=True)
(out/"menu-sizes.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Created original photo audit for",len(report),"visible menu items.")
