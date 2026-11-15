#!/usr/bin/env python3
"""Correct Chef Ahmed post phone numbers safely via a GitHub Actions secret.
No photos, new posts, deletion, Page metadata, or token logging.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PAGE_ID="1293206400544880"
PHONE="0689199142"
GRAPH="https://graph.facebook.com/v27.0/"
POSTS=["122129288991432953","122129289249432953","122129289339432953","122129289465432953","122129289549432953","122129289759432953","122129289903432953","122129289999432953","122129290107432953","122129290389432953","122129290491432953","122129290593432953","122129290755432953","122129290851432953","122129290953432953","122129291061432953","122129291145432953","122129291241432953","122129291445432953","122129291547432953","122129291679432953","122129291889432953","122129292033432953","122129292111432953","122129292225432953","122129292315432953","122129292477432953","122129292657432953","122129292789432953","122129292927432953","122129293059432953","122129293185432953","122129293293432953","122129293575432953","122129293665432953","122129293791432953","122129293965432953","122129294097432953","122129294211432953","122129294313432953"]
OLD=re.compile(r"(?<!\d)\+212[ \t-]*689[ \t-]*199142(?!\d)")
INLINE=re.compile(r"(📞[ \t]*(?:للاستفسار(?:[ \t]+والطلبات)?|للطلب(?:[ \t]+والاستفسار)?|للاتصال)[ \t]*:)[ \t]*0689199142")

class FBError(Exception):
    pass

def api(path, token, *, method="GET", params=None):
    if not re.fullmatch(r"(?:me|me/accounts|\d+_\d+)",path):
        raise ValueError("Unexpected resource")
    url=GRAPH+path
    headers={"Authorization":"Bearer "+token,"Accept":"application/json"}
    data=None
    if method=="GET":
        if params:
            url+="?"+urllib.parse.urlencode(params)
    elif method=="POST":
        data=urllib.parse.urlencode(params or {}).encode()
        headers["Content-Type"]="application/x-www-form-urlencoded"
    else:
        raise ValueError("Only GET and POST are permitted")
    req=urllib.request.Request(url,headers=headers,method=method,data=data)
    try:
        with urllib.request.urlopen(req,timeout=25) as resp:
            result=json.load(resp)
        if "error" in result:
            e=result["error"]
            raise FBError("Graph code "+str(e.get("code"))+" subcode "+str(e.get("error_subcode")))
        return result
    except urllib.error.HTTPError as exc:
        try:
            e=json.load(exc).get("error",{})
        except Exception:
            e={}
        raise FBError("HTTP "+str(exc.code)+" Graph code "+str(e.get("code"))+" subcode "+str(e.get("error_subcode"))) from None

def normalize(message):
    changed=OLD.sub(PHONE,message)
    return INLINE.sub(lambda m:m.group(1)+"\n"+PHONE,changed)

def report(mode,seen,needed,changed,skipped,error=None):
    lines=[
        "### Chef Ahmed — existing Facebook post phone repair",
        "- Mode: "+mode,
        "- Expected Page ID: "+PAGE_ID,
        "- Posts inspected: "+str(seen)+"/40",
        "- Posts needing modification: "+str(needed),
        "- Posts edited and read-back verified: "+str(changed),
        "- No change necessary: "+str(skipped),
        "- Photo deletions/uploads/new posts: NONE",
        "- Phone: 0689199142",
        "- Result: "+(error if error else ("SCAN ONLY" if mode=="scan" else "APPLY COMPLETE"))
    ]
    msg="\n".join(lines)+"\n"
    print(msg,flush=True)
    summary=os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf-8") as f:
            f.write(msg)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=["scan","apply"],default="scan")
    args=p.parse_args()
    token=os.getenv("CHEF_AHMED_PAGE_TOKEN","").strip()
    if len(token)<30:
        report(args.mode,0,0,0,0,"BLOCKED: GitHub encrypted secret missing")
        return 2
    if len(POSTS)!=40 or len(set(POSTS))!=40:
        report(args.mode,0,0,0,0,"BLOCKED: invalid post allowlist")
        return 2
    try:
        identity=api("me",token,params={"fields":"id,name"})
        if str(identity.get("id")) != PAGE_ID:
            # The supplied encrypted secret can also be an authorized user token.
            # Derive the Chef Ahmed Page token in runner memory only; never print/store it.
            pages=api("me/accounts",token,params={"fields":"id,name,access_token","limit":"100"}).get("data",[])
            selected=next((p for p in pages if str(p.get("id")) == PAGE_ID),None)
            if not selected or not isinstance(selected.get("access_token"),str):
                report(args.mode,0,0,0,0,"BLOCKED: User Token has no authorized Chef Ahmed Page access; choose Page Token in Graph API Explorer")
                return 3
            token=selected["access_token"]
            page_identity=api("me",token,params={"fields":"id,name"})
            if str(page_identity.get("id")) != PAGE_ID:
                report(args.mode,0,0,0,0,"BLOCKED: derived Page Token identity mismatch")
                return 3
            print("Verified Chef Ahmed Page Token derived securely from authorized user token.",flush=True)
        else:
            print("Verified Chef Ahmed Page Token.",flush=True)
    except FBError as e:
        report(args.mode,0,0,0,0,"BLOCKED: Facebook Page authorization: "+str(e))
        return 3

    changes=[]
    skipped=0
    for i,suffix in enumerate(POSTS,1):
        post=PAGE_ID+"_"+suffix
        try:
            obj=api(post,token,params={"fields":"id,message"})
            if str(obj.get("id"))!=post or not isinstance(obj.get("message"),str):
                report(args.mode,i-1,len(changes),0,skipped,"BLOCKED: unexpected post payload at position "+str(i))
                return 4
            before=obj["message"]
            after=normalize(before)
            if after==before:
                skipped+=1
            else:
                changes.append((post,before,after))
            time.sleep(.15)
        except FBError as e:
            report(args.mode,i-1,len(changes),0,skipped,"BLOCKED: post read failure #"+str(i)+" "+str(e))
            return 4

    if args.mode=="scan":
        report(args.mode,40,len(changes),0,skipped)
        return 0

    done=0
    for i,(post,before,after) in enumerate(changes,1):
        try:
            latest=api(post,token,params={"fields":"message"})
            if latest.get("message")!=before:
                report(args.mode,40,len(changes),done,skipped,"BLOCKED: concurrent change, post #"+str(i))
                return 5
            api(post,token,method="POST",params={"message":after})
            check=api(post,token,params={"fields":"message"})
            if check.get("message")!=after:
                report(args.mode,40,len(changes),done,skipped,"BLOCKED: read-back mismatch after edit #"+str(i))
                return 5
            done+=1
            print("Verified edit "+str(done)+"/"+str(len(changes)),flush=True)
            time.sleep(.5)
        except FBError as e:
            report(args.mode,40,len(changes),done,skipped,"BLOCKED: edit rejected #"+str(i)+" "+str(e))
            return 5
    report(args.mode,40,len(changes),done,skipped)
    return 0

if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("BLOCKED: unexpected "+type(e).__name__,file=sys.stderr)
        sys.exit(1)
