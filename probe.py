import re, urllib.request
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
html=urllib.request.urlopen(urllib.request.Request("https://www.apple.com/shop/buy-iphone/iphone-duo",headers={"User-Agent":UA,"Accept":"text/html"}),timeout=20).read().decode("utf-8","replace")
out=[]
for m in re.finditer(r'"partNumber":"(M[A-Z0-9]{4}LL/A)"', html):
    seg=html[m.end():m.end()+300]
    n=re.search(r'"name":"([^"]+)"', seg)
    out.append(f"{m.group(1)}={n.group(1) if n else '?'}")
print("::notice::" + " | ".join(dict.fromkeys(out)))
