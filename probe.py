import json, urllib.request, urllib.parse, urllib.error, re
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
BASE = "https://www.apple.com/shop/fulfillment-messages"
P = "MK1E4LL/A"

def get(url, accept="application/json"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept,
        "Referer": "https://www.apple.com/shop/buy-iphone/iphone-duo"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")

# what does the buy page say about part numbers / pickup URL?
s, html = get("https://www.apple.com/shop/buy-iphone/iphone-duo", "text/html")
print(f"::notice::buypage {s}; fulfillment refs: {sorted(set(re.findall(r'fulfillment[-A-Za-z/]*', html)))[:8]}")
for m in re.finditer(r'.{60}MK1E4LL/A.{120}', html):
    print("::notice::ctx " + m.group(0).replace("\n", " ")[:180]); break
print("::notice::cppart " + str(sorted(set(re.findall(r'cppart[^&"]{0,40}', html)))[:6]))

variants = {
 "A_min": {"parts.0": P, "location": "07094"},
 "B_pl": {"pl": "true", "mts.0": "regular", "parts.0": P, "location": "07094"},
 "C_unlocked": {"pl": "true", "mts.0": "regular", "parts.0": P, "location": "07094", "cppart": "UNLOCKED/US"},
 "D_option": {"pl": "true", "mts.0": "regular", "parts.0": P, "option.0": "", "location": "07094", "searchNearby": "true"},
 "E_mt": {"little": "false", "mt": "regular", "parts.0": P, "location": "07094", "searchNearby": "true"},
 "F_fae": {"fae": "true", "pl": "true", "mts.0": "regular", "mts.1": "compact", "parts.0": P, "location": "07094"},
}
for name, q in variants.items():
    s, body = get(BASE + "?" + urllib.parse.urlencode(q))
    info = body[:140].replace("\n", " ")
    try:
        j = json.loads(body)
        st = j["body"]["content"]["pickupMessage"].get("stores", [])
        info = f"JSON stores={len(st)} first={st[0]['storeName'] if st else None} " \
               f"avail={st[0]['partsAvailability'].get(P,{}).get('pickupDisplay') if st else None}"
    except Exception as e:
        pass
    print(f"::notice::{name}: HTTP {s} {info}")
