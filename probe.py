import json, urllib.request, urllib.parse, urllib.error, re
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
def get(url, accept="application/json"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept,
        "Referer": "https://www.apple.com/shop/buy-iphone/iphone-duo"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
s, html = get("https://www.apple.com/shop/buy-iphone/iphone-duo", "text/html")
for key in ["fulfillmentMessageUrl", "fulfillmentMessageUrlAbsolute", "fulfillmentBootstrap"]:
    for m in re.finditer(key + r'.{0,260}', html):
        print("::notice::" + m.group(0).replace("\n"," ")[:260]); break
names = dict(re.findall(r'"partNumber":"(M[A-Z0-9]{4}LL/A)"[^}]*?"name":"([^"]+)"', html))
names.update({p:n for n,p in re.findall(r'"name":"(iPhone Duo[^"]+)"[^{}]*?"partNumber":"(M[A-Z0-9]{4}LL/A)"', html)})
print("::notice::names " + json.dumps(names))
