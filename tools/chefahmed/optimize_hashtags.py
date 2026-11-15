#!/usr/bin/env python3
"""Add context-relevant Facebook hashtags to Chef Ahmed's existing Page posts.

Uses GitHub encrypted CHEF_AHMED_PAGE_TOKEN only; scans first, then verifies
each in-place text update. Does not publish, delete or replace any photos.
"""
import argparse
import json
import os
import re
import sys
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

PAGE="1293206400544880"
API="https://graph.facebook.com/v27.0/"
MAX_POSTS=250
OLD_POST_IDS=["122129288991432953","122129289249432953","122129289339432953","122129289465432953","122129289549432953","122129289759432953","122129289903432953","122129289999432953","122129290107432953","122129290389432953","122129290491432953","122129290593432953","122129290755432953","122129290851432953","122129290953432953","122129291061432953","122129291145432953","122129291241432953","122129291445432953","122129291547432953","122129291679432953","122129291889432953","122129292033432953","122129292111432953","122129292225432953","122129292315432953","122129292477432953","122129292657432953","122129292789432953","122129292927432953","122129293059432953","122129293185432953","122129293293432953","122129293575432953","122129293665432953","122129293791432953","122129293965432953","122129294097432953","122129294211432953","122129294313432953"]
NEW_POST_IDS=["122129542761432953","122129545521432953","122129546931432953","122129547909432953","122129588127432953","122129588859432953","122129588949432953","122129589045432953"]
HASHTAGS_LINE=re.compile(r"^\s*(?:#[\w\u0600-\u06ff]+\s*)+$",re.UNICODE)

class FBError(Exception):
    pass

def call(path,token,fields=None,method="GET"):
    if not re.fullmatch(r"(?:me|me/accounts|\d+/posts|\d+_\d+)",path):
        raise ValueError("Resource not permitted: "+path[:20])
    args=dict(fields or {})
    url=API+path
    if method=="GET" and args: url+="?"+urlencode(args)
    payload=urlencode(args).encode() if method=="POST" else None
    req=Request(url,headers={
       "Authorization":"Bearer "+token,
       "Accept":"application/json",
       **({"Content-Type":"application/x-www-form-urlencoded"} if payload else {})
    },data=payload,method=method)
    try:
        with urlopen(req,timeout=35) as response: return json.load(response)
    except HTTPError as e:
        try: obj=json.load(e).get("error",{})
        except Exception: obj={}
        raise FBError("HTTP %s; Meta code %s, subcode %s"%(e.code,obj.get("code"),obj.get("error_subcode"))) from None

def page_token(secret):
    who=call("me",secret,{"fields":"id,name"})
    if str(who.get("id"))==PAGE:
        return secret
    listed=call("me/accounts",secret,{"fields":"id,name,access_token","limit":"100"}).get("data",[])
    for page in listed:
        if str(page.get("id"))==PAGE and page.get("access_token"):
            derived=page["access_token"]
            if str(call("me",derived,{"fields":"id"}).get("id"))==PAGE:
                return derived
    raise FBError("Token does not authorize Chef Ahmed Page")

def discover(token):
    result=[]
    cursor=None
    seen=set()
    # Do not follow arbitrary URLs or pagination links from Facebook.
    for _ in range(6):
        fields={"fields":"id,message","limit":"100"}
        if cursor: fields["after"]=cursor
        data=call(PAGE+"/posts",token,fields)
        rows=data.get("data",[])
        if not isinstance(rows,list): raise FBError("Malformed Page posts response")
        for row in rows:
            pid=str(row.get("id",""))
            if re.fullmatch(PAGE+r"_\d+",pid) and pid not in seen:
                result.append(pid);seen.add(pid)
        nxt=data.get("paging",{}).get("cursors",{}).get("after")
        if not data.get("paging",{}).get("next") or not nxt or nxt==cursor:
            break
        cursor=nxt
        if len(result)>=MAX_POSTS:
            raise FBError("Too many posts; batch exceeds safety limit")
    return result

def relevant_tags(message):
    m=message.casefold()
    b="#الشيف_أحمد"
    if re.search(r"burak|بوراك|بوراق",m):
        return [b,"#CZNBurak","#طنجة","#Chefs","#FoodLovers"]
    if re.search(r"كسكس|couscous|تفاية",m):
        return [b,"#كسكس_مغربي","#طبخ_مغربي","#Choumicha","#MoroccanFood"]
    if re.search(r"رفيسة|rfissa|تريد",m):
        return [b,"#رفيسة_مغربية","#طبخ_مغربي","#Choumicha","#MoroccanFood"]
    if re.search(r"مضهوص|مدهوص|medhoussa|madghoussa",m):
        return [b,"#المضهوصة_الغرباوية","#تراث_مغربي","#Choumicha","#MoroccanFood"]
    if re.search(r"طاكوس|tacos|بيتزا|pizza",m):
        return [b,"#Pizza","#Tacos","#FoodLovers","#ChefAhmed"]
    if re.search(r"بسطيل|pastilla|bastilla",m):
        return [b,"#بسطيلة","#مطبخ_مغربي","#طاولات_المناسبات","#MoroccanFood"]
    if re.search(r"بحر|سمك|حوت|قمرون|كروفيت|جمبري|كالامار|seafood|lobster",m):
        return [b,"#مأكولات_بحرية","#فواكه_البحر","#SeafoodLovers","#MoroccanFood"]
    if re.search(r"لحم|مشوي|برقوق|خروف|لوز",m):
        return [b,"#مطبخ_مغربي","#مناسبات_المغرب","#MoroccanFood","#FoodLovers"]
    if re.search(r"سلط|شلايض|مقبلات|كاناپي|canap",m):
        return [b,"#سلطات_مغربية","#طاولات_المناسبات","#FoodPresentation","#MoroccanFood"]
    if re.search(r"دجاج|كسبرة|حلو|ديسير|حلويات",m):
        return [b,"#وصفات_مغربية","#طبخ_مغربي","#Choumicha","#MoroccanFood"]
    return [b,"#أكلات_مغربية","#طاولات_المناسبات","#MoroccanFood","#ChefAhmed"]

def rewrite(message):
    # Only replace an existing trailing block of hashtags, preserving the
    # user's original caption, phone and links exactly.
    lines=message.rstrip().splitlines()
    while lines and HASHTAGS_LINE.fullmatch(lines[-1]):
        lines.pop()
    core="\n".join(lines).rstrip()
    if not core: return message
    suffix=" ".join(relevant_tags(core))
    return core+"\n\n"+suffix

def report(mode,source,total,actionable,updated,skipped,missing,error=None):
    lines=[
        "### Chef Ahmed — relevant Facebook hashtags",
        "- Mode: **%s**"%mode,
        "- Discovery: **%s**"%source,
        "- Existing Page posts checked: **%d**"%total,
        "- Posts needing hashtag improvements: **%d**"%actionable,
        "- Posts updated and verified: **%d**"%updated,
        "- Posts already optimized: **%d**"%skipped,
        "- Deleted/unreadable posts skipped: **%d**"%missing,
        "- Hashtags per post: **5**, selected by topic",
        "- Famous chef tags: **#CZNBurak only when mentioned**, **#Choumicha on traditional Moroccan recipes**",
        "- Images, post IDs, likes and comments: **untouched**",
        "- Status: **%s**"%(error or ("SCAN COMPLETE (no changes)" if mode=="scan" else "APPLY COMPLETE"))
    ]
    summary="\n".join(lines)+"\n"
    print(summary,flush=True)
    dest=os.getenv("GITHUB_STEP_SUMMARY")
    if dest:
        with open(dest,"a",encoding="utf-8") as file: file.write(summary)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=["scan","apply"],default="scan")
    mode=parser.parse_args().mode
    secret=os.getenv("CHEF_AHMED_PAGE_TOKEN","").strip()
    if len(secret)<30:
        report(mode,"not started",0,0,0,0,0,"BLOCKED: secret missing")
        return 2
    try:
        token=page_token(secret)
    except FBError as err:
        report(mode,"not started",0,0,0,0,0,"BLOCKED: "+str(err))
        return 2

    source="Page API"
    try:
        ids=discover(token)
    except FBError as err:
        source="verified allowlist (Page API unavailable: %s)"%str(err)
        ids=[PAGE+"_"+p for p in OLD_POST_IDS+NEW_POST_IDS]
    # Include known published photo posts to avoid Page feed omissions.
    known=[PAGE+"_"+p for p in OLD_POST_IDS+NEW_POST_IDS]
    ids=list(dict.fromkeys(ids+known))
    if len(ids)>MAX_POSTS: raise FBError("Safety limit exceeded")

    candidates=[]
    scanned=skipped=missing=0
    for pid in ids:
        try:
            data=call(pid,token,{"fields":"id,message"})
            if str(data.get("id"))!=pid:
                missing+=1;continue
            message=data.get("message","")
            if not isinstance(message,str) or not message.strip():
                skipped+=1;scanned+=1;continue
            after=rewrite(message)
            if message!=after: candidates.append((pid,message,after))
            else: skipped+=1
            scanned+=1
            time.sleep(0.08)
        except FBError:
            missing+=1
            continue
    print("Prepared %d changes from %d readable posts (unavailable: %d)."%(
        len(candidates),scanned,missing),flush=True)
    if mode=="scan":
        report(mode,source,scanned,len(candidates),0,skipped,missing)
        return 0
    done=0
    for idx,(pid,before,after) in enumerate(candidates,1):
        try:
            current=call(pid,token,{"fields":"message"})
            if current.get("message")!=before:
                report(mode,source,scanned,len(candidates),done,skipped,missing,
                       "STOPPED: post changed concurrently at #%d"%idx)
                return 5
            call(pid,token,{"message":after},method="POST")
            confirmed=call(pid,token,{"fields":"message"}).get("message")
            if confirmed!=after:
                report(mode,source,scanned,len(candidates),done,skipped,missing,
                       "STOPPED: post #%d was not verified after edit"%idx)
                return 5
            done+=1
            if done%5==0: print("Read-back verified: %d/%d"%(done,len(candidates)),flush=True)
            time.sleep(.3)
        except FBError as e:
            report(mode,source,scanned,len(candidates),done,skipped,missing,
                   "STOPPED: edit #%d failed: %s"%(idx,str(e)))
            return 5
    report(mode,source,scanned,len(candidates),done,skipped,missing)
    return 0

if __name__=="__main__":
    try: sys.exit(main())
    except Exception as e:
        print("STOPPED: unexpected "+type(e).__name__,file=sys.stderr)
        sys.exit(1)
