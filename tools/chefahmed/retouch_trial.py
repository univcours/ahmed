#!/usr/bin/env python3
"""Stage a user-authorized clean background edit; preserve original menu photo."""
from PIL import Image,ImageOps,ImageDraw,ImageFont
from io import BytesIO
from urllib.request import urlopen,Request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"WhatsApp Image 2026-08-28 at 12.17.47 (2).jpeg"
URL="https://gcdn.picsart.com/editing-temp/9dad9771-9f25-45c8-bed4-4b1ad37d8095.webp"
OUT=ROOT/"social"/"audit"
OUT.mkdir(parents=True,exist_ok=True)
with urlopen(Request(URL,headers={"User-Agent":"ChefAhmed-Image-Retouch-QA/1.0"}),timeout=40) as r:
 data=r.read(12_000_000)
with Image.open(BytesIO(data)) as edited:
 edited.load();edited=ImageOps.exif_transpose(edited).convert("RGB")
 with Image.open(SRC) as original:
  orig=ImageOps.exif_transpose(original).convert("RGB")
  print("Original",orig.size,"edited",edited.size)
  if not (.70 <= edited.width/edited.height <= 1.1):
   raise RuntimeError("Output aspect ratio too different; refusing to stage")
  w,h=360,520
  canvas=Image.new("RGB",(w*2,h+48),(255,252,247))
  for i,im in enumerate((orig,edited)):
   thumb=ImageOps.contain(im,(w-20,h-18))
   canvas.paste(thumb,(i*w+(w-thumb.width)//2,(h-thumb.height)//2))
  d=ImageDraw.Draw(canvas)
  d.text((15,h+10),"BEFORE: original on scratched table",fill=(0,0,0))
  d.text((w+15,h+10),"AFTER: edited studio background",fill=(0,0,0))
  edited.save(OUT/"seafood-salad-bg-trial.jpg",quality=94,subsampling=0)
  canvas.save(OUT/"seafood-salad-before-after.jpg",quality=85)
print("Staged background cleanup for visual validation, no live menu photo modified.")
