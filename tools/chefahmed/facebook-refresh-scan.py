#!/usr/bin/env python3
"""Read-only Facebook authorization and Page post verification.
Never prints any token or raw response. No edits, deletes, or publishing.
"""
import json,os,sys,urllib.request,urllib.parse,urllib.error
PAGE="1293206400544880"
GRAPH="https://graph.facebook.com/v27.0/"
TOKEN=os.getenv("CHEF_AHMED_PAGE_TOKEN","").strip()
def read(path,secret,fields):
    url=GRAPH+path+"?"+urllib.parse.urlencode(fields)
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+secret,"Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=25) as h:return json.load(h)
    except urllib.error.HTTPError as e:
        try: raw=json.load(e).get("error",{})
        except: raw={}
        raise RuntimeError("Meta HTTP %d, code %s, subcode %s"%(e.code,raw.get("code"),raw.get("error_subcode")))
def run():
    if len(TOKEN)<30:
        print("BLOCKED: missing CHEF_AHMED_PAGE_TOKEN GitHub Actions Secret");return 2
    try:
        me=read("me",TOKEN,{"fields":"id"})
        token=TOKEN
        if str(me.get("id"))!=PAGE:
            pages=read("me/accounts",TOKEN,{"fields":"id,name,access_token","limit":100}).get("data",[])
            selected=next((p for p in pages if str(p.get("id"))==PAGE),None)
            if not selected or not selected.get("access_token"):
                print("BLOCKED: token cannot manage the Chef Ahmed Page");return 3
            token=selected["access_token"]
            if str(read("me",token,{"fields":"id"}).get("id"))!=PAGE:
                print("BLOCKED: derived token has wrong Page identity");return 3
        obj=read(PAGE+"_122129293965432953",token,{"fields":"id,message"})
        if str(obj.get("id"))!=PAGE+"_122129293965432953":
            print("BLOCKED: old post mismatch");return 4
        print("PASS: authenticated Chef Ahmed Page and verified original post. READ ONLY.")
        return 0
    except Exception as e:
        print("BLOCKED:",str(e).replace(TOKEN,"[REDACTED]"))
        return 5
if __name__=="__main__":
    sys.exit(run())
