#!/usr/bin/env python3
"""AI-assisted non-destructive studio backgrounds for original catering photos.
Trial only: outputs not applied to menu until visual review.
Removes scratched / cluttered table beyond original dish silhouette, while
compositing the ORIGINAL plate/food pixels over a spotless linen surface.
"""
from pathlib import Path
import io,random
import numpy as np
import cv2
from PIL import Image,ImageOps,ImageDraw,ImageFont
from rembg import remove,new_session

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"social"/"audit"/"bg-trial"
FILES=[
 "WhatsApp Image 2026-08-28 at 12.17.47 (2).jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.47 (3).jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.47 (4).jpeg",
 "WhatsApp Image 2026-08-28 at 12.17.48 (2).jpeg",
]
MAX_INPUT_DIM=950

def ivory(width,height):
  # Muted warm ecru plaster / marble. Subtle tone and film grain.
  yy,xx=np.mgrid[0:height,0:width]
  v=8*(xx/width-.5) + 5*(yy/height-.5)
  rng=np.random.default_rng(707)
  grain=rng.normal(0,1.5,(height,width))
  base=np.stack([244+v+grain,238+v+grain,229+v+grain],axis=2)
  return Image.fromarray(np.uint8(np.clip(base,0,255)),"RGB")

def process(image,session):
  width,height=image.size
  factor=min(1,MAX_INPUT_DIM/max(width,height))
  work=image.resize((round(width*factor),round(height*factor)),Image.Resampling.LANCZOS)
  rem=remove(work,session=session,only_mask=True)
  mask=np.asarray(rem.convert("L").resize((width,height),Image.Resampling.BILINEAR))
  # Preserve original plate and food contours; generous dilation prevents
  # erasing leafy garnishes, prawns and decorative edges.
  radius=max(5,round(min(width,height)*.009))
  kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(radius*2+1,radius*2+1))
  solid=(mask>95).astype(np.uint8)*255
  solid=cv2.dilate(solid,kernel,iterations=1)
  blur=cv2.GaussianBlur(solid,(0,0),sigmaX=max(2,min(width,height)*.004))
  alpha=Image.fromarray(blur,"L")
  bg=ivory(width,height)
  return Image.composite(image,bg,alpha),mask

def main():
  OUT.mkdir(parents=True,exist_ok=True)
  session=new_session("u2net")
  sheet=Image.new("RGB",(960,4*430),(255,252,247))
  draw=ImageDraw.Draw(sheet)
  for i,name in enumerate(FILES):
    src=ImageOps.exif_transpose(Image.open(ROOT/name)).convert("RGB")
    clean,mask=process(src,session)
    output=OUT/(f"test-{i+1:02}.jpg")
    clean.save(output,"JPEG",quality=94,optimize=True)
    for j,im in enumerate((src,clean)):
      thumb=ImageOps.contain(im,(465,400))
      x=j*480+(480-thumb.width)//2
      y=i*430+((400-thumb.height)//2)
      sheet.paste(thumb,(x,y))
    draw.text((10,i*430+405),f"{i+1}. ORIGINAL",fill=(25,25,25))
    draw.text((490,i*430+405),f"{i+1}. STUDIO CLEANUP",fill=(25,25,25))
    print("Processed",name,src.size,"mask coverage",round((mask>95).mean(),3),flush=True)
  sheet.save(OUT/"before-after-contact.jpg",quality=86,optimize=True)
  print("Stage complete. No live menu images replaced.")
if __name__=="__main__":main()
