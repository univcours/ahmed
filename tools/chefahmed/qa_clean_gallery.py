#!/usr/bin/env python3
"""Make a clean photobook thumbnail of the verified edited Chef Ahmed gallery."""
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
import json, math
ROOT=Path(__file__).resolve().parents[2]
data=json.loads((ROOT/"menu.json").read_text(encoding="utf-8"))
items=data["items"]; photos=data.get("cleaned_images",{})
assert len(photos)>=16,"Expected 16 checked retouches"
w,h=250,290
columns=4
grid=Image.new("RGB",(w*columns,h*math.ceil(len(photos)/columns)),(246,241,231))
d=ImageDraw.Draw(grid)
for i,(source,rel) in enumerate(photos.items()):
    p=ROOT/rel
    if not p.is_file():raise RuntimeError("Missing processed image "+rel)
    with Image.open(p) as file:
        img=ImageOps.exif_transpose(file).convert("RGB")
        tile=ImageOps.contain(img,(w-18,h-48))
        x=i%columns*w+(w-tile.width)//2
        y=i//columns*h+(h-44-tile.height)//2
        grid.paste(tile,(x,y))
    d.text((i%columns*w+10,(i//columns)*h+h-31),f"{i+1:02} | {img.width}x{img.height}",fill=(38,35,28))
    d.rectangle((i%columns*w,i//columns*h,(i%columns+1)*w-1,(i//columns+1)*h-1),
                outline=(213,199,172),width=1)
output=ROOT/"social"/"cleaned"/"preview-sheet.jpg"
grid.save(output,quality=86,optimize=True)
print("Verified and previewed",len(photos),"cleaned photos; no missing assets.")
