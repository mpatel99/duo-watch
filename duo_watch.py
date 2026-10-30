#!/usr/bin/env python3
"""
duo_watch.py - Watch Apple Store in-store pickup availability for iPhone Duo
near a ZIP code and send a push notification when stock appears.

Standard library only (Python 3.8+). Run:  python3 duo_watch.py
Notifications: ntfy.sh push (free phone app, no account) + desktop notification.
"""

import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

# ----------------------------------------------------------------------------
# CONFIG - edit these
# ----------------------------------------------------------------------------
ZIP_CODE = "07094"
MAX_DISTANCE_MILES = 30          # ignore stores farther than this
POLL_SECONDS = 180               # base interval; random jitter is added
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "milan-duo-watch-CHANGE-ME")  # subscribe to it in the ntfy app

# Only watch these (case-insensitive substring match on Apple's product title).
# Empty list = watch everything. Examples: ["256GB"], ["Night Sky"], ["512GB Star White"]
FILTERS = ["512GB"]

# Part numbers are auto-discovered from apple.com. If discovery fails, these are used.
# (US unlocked numbers from third-party listings - verify on apple.com if you rely on them.)
FALLBACK_PARTS = {
    "MK2E4LL/A": "iPhone Duo 256GB Night Sky",
    "MK2F4LL/A": "iPhone Duo 256GB Star White",
    "MK2J4LL/A": "iPhone Duo 512GB Night Sky",
    "MK2N4LL/A": "iPhone Duo 1TB Night Sky",
    "MK2T4LL/A": "iPhone Duo 2TB Night Sky",
}
# Add any you find yourself (e.g. from the URL when you pick a config on apple.com):
EXTRA_PARTS = {}

BUY_PAGE = "https://www.apple.com/shop/buy-iphone/iphone-duo"
FULFILLMENT_URL = "https://www.apple.com/shop/fulfillment-messages"
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".duo_watch_state.json")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
# ----------------------------------------------------------------------------


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def http_get(url, accept="application/json"):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": accept,
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": BUY_PAGE,
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def discover_parts():
    """Scrape US part numbers (xxxxxLL/A) from Apple's iPhone Duo buy page."""
    try:
        html = http_get(BUY_PAGE, accept="text/html")
    except Exception as e:
        log(f"Part discovery failed ({e}); using fallback list.")
        return {}
    parts = {}
    for m in re.finditer(r'"partNumber"\s*:\s*"(M[A-Z0-9]{4}LL/A)"', html):
        parts.setdefault(m.group(1), "")
    if not parts:  # looser match
        for p in set(re.findall(r'\b(M[A-Z0-9]{4}LL/A)\b', html)):
            parts.setdefault(p, "")
    log(f"Discovered {len(parts)} part numbers on apple.com.")
    return parts


def check(parts):
    """Return list of (store, distance, part, title, quote) that are available."""
    hits, plist = [], list(parts)
    # Apple accepts several parts per request; batch to be gentle.
    for i in range(0, len(plist), 8):
        batch = plist[i:i + 8]
        q = {"fae": "true", "pl": "true", "mts.0": "regular", "mts.1": "compact",
             "location": ZIP_CODE}
        for j, p in enumerate(batch):
            q[f"parts.{j}"] = p
        data = json.loads(http_get(FULFILLMENT_URL + "?" + urllib.parse.urlencode(q)))
        hits.extend(parse(data, parts))
        time.sleep(1.5)
    return hits


def parse(data, parts):
    hits = []
    stores = (data.get("body", {}).get("content", {})
              .get("pickupMessage", {}).get("stores", []))
    for s in stores:
        try:
            dist = float(s.get("storedistance") or s.get("storeDistanceVoText", "999").split()[0])
        except (ValueError, IndexError):
            dist = 999.0
        if dist > MAX_DISTANCE_MILES:
            continue
        for part, info in (s.get("partsAvailability") or {}).items():
            if info.get("pickupDisplay") != "available":
                continue
            title = (info.get("messageTypes", {}).get("regular", {})
                     .get("storePickupProductTitle")) or parts.get(part) or part
            if FILTERS and not any(f.lower() in title.lower() for f in FILTERS):
                continue
            hits.append((s.get("storeName", "?"), dist, part, title,
                         info.get("pickupSearchQuote", "")))
    return hits


def notify(title, body, url=None):
    log(f"NOTIFY: {title} | {body}")
    if NTFY_TOPIC:
        try:
            headers = {"Title": title, "Priority": "urgent", "Tags": "iphone"}
            if url:
                headers["Click"] = url
            req = urllib.request.Request(f"https://ntfy.sh/{NTFY_TOPIC}",
                                         data=body.encode(), headers=headers)
            urllib.request.urlopen(req, timeout=15).read()
        except Exception as e:
            log(f"ntfy failed: {e}")
    try:  # desktop notification, best effort
        if sys.platform == "darwin":
            subprocess.run(["osascript", "-e",
                            f'display notification {json.dumps(body)} with title {json.dumps(title)} sound name "Glass"'])
        elif sys.platform.startswith("linux"):
            subprocess.run(["notify-send", title, body])
        elif sys.platform == "win32":
            subprocess.run(["msg", "*", f"{title}: {body}"])
    except Exception:
        pass


def load_state():
    try:
        with open(STATE_FILE) as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_state(keys):
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(keys), f)


def main():
    parts = discover_parts() or dict(FALLBACK_PARTS)
    parts.update(EXTRA_PARTS)
    log(f"Watching {len(parts)} parts within {MAX_DISTANCE_MILES} mi of {ZIP_CODE}"
        + (f", filters={FILTERS}" if FILTERS else ""))
    if "--test-notify" in sys.argv:
        notify("Duo watch test", "Notifications are working.")
        return

    seen, backoff = load_state(), 0
    if "--once" in sys.argv:  # single check, for GitHub Actions / cron
        hits = check(parts)
        current = {f"{h[0]}|{h[2]}" for h in hits}
        new = [h for h in hits if f"{h[0]}|{h[2]}" not in seen]
        if new:
            lines = [f"{t} @ {st} ({d:.0f} mi) {q}".strip() for st, d, p, t, q in new]
            notify("iPhone Duo in stock near you", "\n".join(lines[:6]), BUY_PAGE)
        log(f"{len(hits)} available, {len(new)} new" if hits else "No stock nearby.")
        save_state(current)
        return
    while True:
        try:
            hits = check(parts)
            current = {f"{h[0]}|{h[2]}" for h in hits}
            new = [h for h in hits if f"{h[0]}|{h[2]}" not in seen]
            if new:
                lines = [f"{t} @ {st} ({d:.0f} mi) {q}".strip() for st, d, p, t, q in new]
                notify("iPhone Duo in stock near you", "\n".join(lines[:6]), BUY_PAGE)
            log(f"{len(hits)} available, {len(new)} new" if hits else "No stock nearby.")
            seen = current          # re-alert if it sells out and comes back
            save_state(seen)
            backoff = 0
        except urllib.error.HTTPError as e:
            backoff = min(backoff * 2 or 300, 3600)
            log(f"HTTP {e.code} from Apple (rate-limited?). Backing off {backoff}s.")
        except Exception as e:
            backoff = min(backoff * 2 or 120, 1800)
            log(f"Error: {e}. Retrying in {backoff}s.")
        time.sleep(backoff or POLL_SECONDS + random.randint(0, 60))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Stopped.")
