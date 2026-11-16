#!/usr/bin/env python3
"""Append the French Google Play link to exact RivoScan posts only.
Never changes Chef Ahmed posts, photos, or page settings.
"""
import os,sys,json,re,urllib.parse,urllib.request,urllib.error
PAGE="1409928902211743"
IDS=[
"1409928902211743_122102944047548805",
"1409928902211743_122102955783548805",
"1409928902211743_122102956017548805",
"1409928902211743_122102956125548805",
]
URL="https://play.google.com/store/apps/details?id=com.ribhlab.rivoscan&hl=fr"
ENDPOINT="https://graph.facebook.com/v27.0/"
def api(path,token,params=None,method="GET"):
    if path not in ["me","me/accounts",PAGE]+IDS:raise ValueError("Endpoint outside allowed RivoScan post list")
    data=urllib.parse.urlencode(params or {}).encode("utf-8")
    request=urllib.request.Request(ENDPOINT+path+(("?"+data.decode()) if method=="GET" else ""),data=data if method=="POST" else None,headers={"Authorization":"Bearer "+token,"Accept":"application/json"},method=method)
    try:
        with urllib.request.urlopen(request,timeout=35) as resp: return json.load(resp)
    except urllib.error.HTTPError as err:
        try:payload=json.load(err).get("error",{})
        except Exception:payload={}
        raise RuntimeError("Graph HTTP "+str(err.code)+"; Meta error "+str(payload.get("code"))+"; subcode "+str(payload.get("error_subcode"))) from None

def page_token(secret):
    me=api("me",secret,{"fields":"id"})
    if str(me.get("id"))==PAGE:return secret
    pages=api("me/accounts",secret,{"fields":"id,access_token","limit":"100"}).get("data",[])
    for p in pages:
        if str(p.get("id"))==PAGE and p.get("access_token"):
            t=p["access_token"]
            if str(api("me",t,{"fields":"id"}).get("id"))==PAGE:return t
    raise RuntimeError("No authorization for the RivoScan page through this token")

def main():
    secret=os.environ.get("CHEF_AHMED_PAGE_TOKEN","").strip()
    if not secret:
        print("RIVOSCAN_FRENCH_LINKS_NOT_UPDATED: no GitHub secret available")
        return 2
    try:token=page_token(secret)
    except Exception as e:
        print("RIVOSCAN_FRENCH_LINKS_NOT_UPDATED: "+str(e))
        return 3
    done=0; skipped=0
    for i,post_id in enumerate(IDS,1):
        try:
            p=api(post_id,token,{"fields":"id,message"})
            if p.get("id")!=post_id or not isinstance(p.get("message"),str):
                raise RuntimeError("Unexpected post identity or missing message")
            msg=p["message"]
            if URL in msg or "hl=fr" in msg:
                print("SKIP_POST_ALREADY_LINKED",i); skipped+=1; continue
            # Preserve entire existing caption; only add the user-requested FR URL.
            new=msg.rstrip()+"\n\n🇫🇷 Google Play (français) :\n"+URL
            result=api(post_id,token,{"message":new},method="POST")
            if result.get("success") is not True:raise RuntimeError("Meta did not confirm edit")
            check=api(post_id,token,{"fields":"id,message"})
            if check.get("message")!=new:raise RuntimeError("Read-back did not match")
            done+=1;print("RIVOSCAN_POST_UPDATED_AND_VERIFIED",i)
        except Exception as e:
            print("RIVOSCAN_FRENCH_LINKS_STOPPED_AT",i,str(e))
            return 4
    print("RIVOSCAN_FRENCH_LINKS_DONE: updated",done,"alreadyLinked",skipped)
    return 0
if __name__=="__main__":sys.exit(main())
