#!/usr/bin/env python3
"""Generate zero-crop square versions of Chef Ahmed's already-published art.

Original posters' title, dishes, mini-cards and telephone remain visible.
No Face/food/text re-generation; no publication is performed here.
"""
from pathlib import Path
from io import BytesIO
import json
import urllib.request
from PIL import Image,ImageOps,ImageDraw

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"social"/"facebook-safe"
PAGE="1293206400544880"
POSTS=[
    ("couscous","0e102b47-8b14-40e5-93b3-51109eda3ca7.jpeg","122129588859432953"),
    ("rfissa","1e1d25e5-abc4-4a4a-9924-27984a35f88e.jpeg","122129588949432953"),
    ("medhoussa","8805984c-cfa4-4499-ac39-51776549e5ec.jpeg","122129589045432953"),
    ("burak-tangier","d6edc916-9e06-4468-86b2-e4a1b53b6a51.png","122129588127432953")
]
def read(url):
    req=urllib.request.Request(url,headers={"User-Agent":"ChefAhmed-Square-Preview-Restoration/1.0"})
    with urllib.request.urlopen(req,timeout=60) as r:
        contents=r.read(12_000_000)
    with Image.open(BytesIO(contents)) as im:
        im.load()
        return ImageOps.exif_transpose(im).convert("RGB")
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for name,filename,post in POSTS:
        im=read("https://gcdn.picsart.com/picsart-mcp/"+filename)
        w,h=im.size
        side=max(w,h)
        bg=Image.new("RGB",(side,side),(54,16,24))
        x=(side-w)//2
        y=(side-h)//2
        bg.paste(im,(x,y))
        d=ImageDraw.Draw(bg)
        if x>12:
            d.line((x-7,0,x-7,side),fill=(195,153,78),width=4)
            d.line((x+w+7,0,x+w+7,side),fill=(195,153,78),width=4)
        if y>12:
            d.line((0,y-7,side,y-7),fill=(195,153,78),width=4)
            d.line((0,y+h+7,side,y+h+7),fill=(195,153,78),width=4)
        path=OUT/(name+".jpg")
        bg.save(path,"JPEG",quality=92,subsampling=0,optimize=True)
        manifest.append({"name":name,"post_id":PAGE+"_"+post,
                        "original_size":[w,h],
                        "facebook_safe_size":[side,side],
                        "safe_image":"social/facebook-safe/"+name+".jpg",
                        "original_post_media_replaced":False})
    (OUT/"index.json").write_text(json.dumps({"items":manifest,
        "note":"These are non-cropped replacements for future/new Facebook posts only. Existing photo media cannot be overwritten with this tool."},
        ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Generated",len(manifest),"complete square Facebook designs; no posts modified.")
if __name__=="__main__":
    main()
