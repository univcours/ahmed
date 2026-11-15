#!/usr/bin/env python3
"""Install approved cover and attempt official Meta Page cover update. No feed posts."""
import os, sys, re, io, json, urllib.request, urllib.parse, urllib.error
from pathlib import Path
from PIL import Image, ImageOps

PAGE="1293206400544880"
GRAPH="https://graph.facebook.com/v27.0/"
IMAGE="https://gcdn.picsart.com/picsart-mcp/cdd08aa5-8627-43c6-8a58-7c272d7f14d9.jpeg"
ROOT=Path(__file__).resolve().parents[2]
COVER=ROOT/"social"/"chef-ahmed-facebook-cover.jpg"
REPORT=ROOT/"social"/"cover-update-status.json"

def note(status,detail,photo_id=None):
    result={"status":status,"detail":detail,"page_id":PAGE,"cover_image":"social/chef-ahmed-facebook-cover.jpg","photo_id":photo_id}
    REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    msg="### Chef Ahmed Page cover\n- Status: "+status+"\n- "+detail+"\n- New photo id: "+str(photo_id or "none")+"\n"
    print(msg,flush=True)
    summary=os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf-8") as f: f.write(msg)

def api(path,token,fields=None,method="GET"):
    if path not in ("me","me/accounts",PAGE,PAGE+"/photos"):
        raise ValueError("Unauthorized Graph endpoint")
    url=GRAPH+path
    params=dict(fields or {})
    data=None
    if method=="GET":
        if params: url+="?"+urllib.parse.urlencode(params)
    elif method=="POST": data=urllib.parse.urlencode(params).encode()
    else: raise ValueError("Wrong method")
    headers={"Authorization":"Bearer "+token,"Accept":"application/json"}
    if data is not None:headers["Content-Type"]="application/x-www-form-urlencoded"
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers,data=data,method=method),timeout=45) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try: err=json.load(e).get("error",{})
        except Exception:err={}
        raise RuntimeError("Graph HTTP %s; Meta code %s, subcode %s"%(e.code,err.get("code"),err.get("error_subcode"))) from None

def get_page_token(token):
    identity=api("me",token,{"fields":"id,name"})
    if str(identity.get("id"))==PAGE: return token
    for item in api("me/accounts",token,{"fields":"id,access_token","limit":"100"}).get("data",[]):
        if str(item.get("id"))==PAGE and item.get("access_token"):
            candidate=item["access_token"]
            if str(api("me",candidate,{"fields":"id"}).get("id"))==PAGE:
                return candidate
    raise RuntimeError("Current token cannot access target Page")

def main():
    # Host exact artwork on the user's site even if Meta refuses cover modification.
    req=urllib.request.Request(IMAGE,headers={"User-Agent":"ChefAhmed-Cover-Installer/1.0"})
    with urllib.request.urlopen(req,timeout=40) as r:
        image_bytes=r.read(6000000)
    with Image.open(io.BytesIO(image_bytes)) as raw:
        raw.load()
        im=ImageOps.exif_transpose(raw).convert("RGB")
        if im.size!=(1640,624):raise RuntimeError("Cover image is not 1640x624")
        COVER.parent.mkdir(parents=True,exist_ok=True)
        im.save(COVER,"JPEG",quality=95,subsampling=0,optimize=True)
    secret=os.environ.get("CHEF_AHMED_PAGE_TOKEN","").strip()
    if len(secret)<30:
        note("BLOCKED","Token secret is missing; the artwork was saved for manual cover setup")
        return 0
    try:
        token=get_page_token(secret)
        old=api(PAGE,token,{"fields":"id,cover"})
        if str(old.get("id"))!=PAGE:raise RuntimeError("Incorrect Page ID")
        print("Verified Page. Existing cover ID: "+str(old.get("cover",{}).get("id")),flush=True)
        photo=api(PAGE+"/photos",token,{"url":IMAGE,"published":"false","no_story":"true"},method="POST")
        pid=str(photo.get("id",""))
        if not re.fullmatch(r"\d+",pid):raise RuntimeError("Unpublished image upload returned no photo ID")
        result=api(PAGE,token,{"cover":pid},method="POST")
        if result.get("success") is not True:raise RuntimeError("Meta did not confirm cover update")
        confirm=api(PAGE,token,{"fields":"cover"})
        if str(confirm.get("cover",{}).get("id"))!=pid:
            raise RuntimeError("Cover was not verified by read-back")
        note("COVER UPDATED","Meta accepted cover update and confirmed new cover via read-back",pid)
    except Exception as exc:
        note("COVER NOT UPDATED",str(exc))
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as exc:
        print("Failed to save cover asset: "+type(exc).__name__,file=sys.stderr)
        sys.exit(1)
