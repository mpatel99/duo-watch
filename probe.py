import json, re, urllib.request, urllib.parse, urllib.error, http.cookiejar
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def get(url, accept="application/json", ref="https://www.apple.com/shop/buy-iphone/iphone-duo", xhr=False):
    h = {"User-Agent": UA, "Accept": accept, "Accept-Language": "en-US,en;q=0.9", "Referer": ref}
    if xhr: h.update({"X-Requested-With": "XMLHttpRequest", "Sec-Fetch-Site": "same-origin",
                      "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty"})
    try:
        with op.open(urllib.request.Request(url, headers=h), timeout=20) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
def summ(s, body, part):
    try:
        st = json.loads(body)["body"]["content"]["pickupMessage"].get("stores", [])
        return f"HTTP {s} JSON stores={len(st)} " + "; ".join(
            f"{x['storeName']}:{x['partsAvailability'].get(part,{}).get('pickupDisplay')}" for x in st[:4])
    except Exception:
        return f"HTTP {s} " + body[:80].replace("\n"," ")
F = "https://www.apple.com/shop/fulfillment-messages?fae=true&"
s, html = get("https://www.apple.com/shop/buy-iphone/iphone-duo", "text/html")
print(f"::notice::buypage {s}, cookies={len(jar)}")
P = "MK1E4LL/A"
q = urllib.parse.urlencode({"pl":"true","mts.0":"regular","mts.1":"compact","parts.0":P,"location":"07094"})
print("::notice::duo+cookies+xhr: " + summ(*get(F+q, xhr=True), P))
# control: an accessory that's normally stocked
s2, h2 = get("https://www.apple.com/shop/product/MX2D3AM/A/airtag", "text/html", ref="https://www.apple.com/shop")
cp = "MX532AM/A"
m = re.search(r'"partNumber":"(M[A-Z0-9]{4}(?:AM|LL|ZM)/A)"', h2)
if m: cp = m.group(1)
q2 = urllib.parse.urlencode({"pl":"true","mts.0":"regular","parts.0":cp,"location":"07094"})
print(f"::notice::control {cp} (page {s2}): " + summ(*get(F+q2, xhr=True, ref="https://www.apple.com/shop"), cp))
