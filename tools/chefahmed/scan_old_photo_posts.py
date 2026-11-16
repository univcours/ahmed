#!/usr/bin/env python3
"""Read-only inventory: map known old Chef Ahmed Facebook photo posts to menu entries.

No write operations; no page post content/token is stored. A future safe
replacement must verify post title and replacement image before removal.
"""
from pathlib import Path
import json,os,runpy,time
ROOT=Path(__file__).resolve().parents[2]
MENU=json.loads((ROOT/"menu.json").read_text(encoding="utf-8"))["items"]
SOCIAL=ROOT/"tools"/"chefahmed"/"optimize_hashtags.py"
helper=runpy.run_path(str(SOCIAL))
IDs=helper["OLD_POST_IDS"]
old_visible=[(name,x) for name,x in MENU.items() if not x.get("hidden") or name=="WhatsApp Image 2026-08-28 at 22.03.53.jpeg"]
assert len(IDs)==len(old_visible),(len(IDs),len(old_visible))
report=[]
secret=os.environ.get("CHEF_AHMED_PAGE_TOKEN","").strip()
if len(secret)<30: raise SystemExit("No Page token configured")
try: token=helper["page_token"](secret)
except Exception: raise SystemExit("Page token not authorized (no details exposed)")
for index,(oldid,(file,item)) in enumerate(zip(IDs,old_visible)):
    pid=helper["PAGE"]+"_"+oldid
    try:
        data=helper["call"](pid,token,{"fields":"id,message"})
        message=str(data.get("message",""))
        title=item.get("name_ar","")
        first=message[:200]
        matched=bool(title and title in first)
        status="matched" if matched else "title_mismatch"
    except Exception: status="unavailable";matched=False
    report.append({"index":index+1,"source_image":file,"title":item.get("name_ar",""),
                   "post_id":pid,"status":status,
                   "eligible_for_safe_replacement":matched})
    if index%10==9: print("Read-only verified",index+1,"of",len(IDs),flush=True)
    time.sleep(.13)
out=ROOT/"social"/"audit"/"original-facebook-posts.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({"page_id":helper["PAGE"],"items":report},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
from collections import Counter
print("Original photo posts verified:",dict(Counter(x["status"] for x in report)),"; no posts changed.")
