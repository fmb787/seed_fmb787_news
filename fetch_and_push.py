import os, time, base64, requests
from datetime import datetime, timezone

GITHUB_TOKEN    = os.environ["GITHUB_TOKEN"]
GITHUB_USER     = "fmb787"
GITHUB_REPO     = "fmb-news-seeds"
TE_CALENDAR_URL = "https://api.tradingeconomics.com/calendar?c=guest:guest&importance=2"

IMPORTANCE_MAP = {1:"low", 2:"medium", 3:"high"}

NEWS_DIRECTION = {
    "non-farm":       ("positive","اذا الفعلي اعلى=دولار يرتفع / اذا الفعلي اقل=دولار ينخفض"),
    "nonfarm":        ("positive","اذا الفعلي اعلى=دولار يرتفع / اذا الفعلي اقل=دولار ينخفض"),
    "cpi":            ("positive","اذا الفعلي اعلى=دولار يرتفع / اذا الفعلي اقل=دولار ينخفض"),
    "ppi":            ("positive","اذا الفعلي اعلى=دولار يرتفع / اذا الفعلي اقل=دولار ينخفض"),
    "gdp":            ("positive","اذا الفعلي اعلى=عملة ترتفع / اذا الفعلي اقل=عملة تنخفض"),
    "retail sales":   ("positive","اذا الفعلي اعلى=عملة ترتفع / اذا الفعلي اقل=عملة تنخفض"),
    "ism services":   ("positive","اذا الفعلي اعلى=دولار يرتفع / اذا الفعلي اقل=دولار ينخفض"),
    "ism manufactur": ("positive","اذا الفعلي اعلى=دولار يرتفع / اذا الفعلي اقل=دولار ينخفض"),
    "consumer conf":  ("positive","اذا الفعلي اعلى=دولار يرتفع / اذا الفعلي اقل=دولار ينخفض"),
    "adp":            ("positive","اذا الفعلي اعلى=دولار يرتفع / اذا الفعلي اقل=دولار ينخفض"),
    "jolts":          ("positive","اذا الفعلي اعلى=دولار يرتفع / اذا الفعلي اقل=دولار ينخفض"),
    "unemployment":   ("negative","اذا الفعلي اعلى=دولار ينخفض / اذا الفعلي اقل=دولار يرتفع"),
    "jobless claims": ("negative","اذا الفعلي اعلى=دولار ينخفض / اذا الفعلي اقل=دولار يرتفع"),
    "claimant":       ("negative","اذا الفعلي اعلى=عملة تنخفض / اذا الفعلي اقل=عملة ترتفع"),
    "interest rate":  ("positive","اذا الفعلي اعلى=عملة ترتفع / اذا الفعلي اقل=عملة تنخفض"),
    "rate decision":  ("positive","اذا الفعلي اعلى=عملة ترتفع / اذا الفعلي اقل=عملة تنخفض"),
    "trade balance":  ("positive","اذا الفعلي اعلى=عملة ترتفع / اذا الفعلي اقل=عملة تنخفض"),
    "pmi":            ("positive","اذا الفعلي اعلى=عملة ترتفع / اذا الفعلي اقل=عملة تنخفض"),
    "ifo":            ("positive","اذا الفعلي اعلى=يورو يرتفع / اذا الفعلي اقل=يورو ينخفض"),
    "durable goods":  ("positive","اذا الفعلي اعلى=دولار يرتفع / اذا الفعلي اقل=دولار ينخفض"),
    "existing home":  ("positive","اذا الفعلي اعلى=دولار يرتفع / اذا الفعلي اقل=دولار ينخفض"),
    "housing":        ("positive","اذا الفعلي اعلى=دولار يرتفع / اذا الفعلي اقل=دولار ينخفض"),
    "building":       ("positive","اذا الفعلي اعلى=دولار يرتفع / اذا الفعلي اقل=دولار ينخفض"),
}

def get_direction(name):
    low = name.lower()
    for k,(d,h) in NEWS_DIRECTION.items():
        if k in low:
            return d, h
    return "unknown","راقب حركة السعر بعد الصدور"

def fetch():
    try:
        r = requests.get(TE_CALENDAR_URL, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"TE error: {e}")
    return []

def to_pine(events):
    lines = []
    seen  = set()
    for ev in events:
        try:
            name   = str(ev.get("Event","")).strip().replace("|","")
            cur    = str(ev.get("Currency","")).strip()
            ds     = str(ev.get("Date","")).strip().replace("Z","").replace("T"," ")
            if "." in ds: ds = ds[:ds.index(".")]
            imp    = int(ev.get("Importance",1))
            actual = str(ev.get("Actual","")).strip().replace("|","")
            fore   = str(ev.get("Forecast","")).strip().replace("|","")
            prev   = str(ev.get("Previous","")).strip().replace("|","")
            if not name or not cur or not ds: continue
            dt = datetime.strptime(ds,"%Y-%m-%d %H:%M:%S")
            ts = int(dt.replace(tzinfo=timezone.utc).timestamp())
            key = f"{name}_{ts}_{cur}"
            if key in seen: continue
            seen.add(key)
            d,h = get_direction(name)
            h   = h.replace("|","_")
            lines.append(f"{name}|{ts}|{cur}|{IMPORTANCE_MAP.get(imp,'low')}|{d}|{h}|{actual}|{fore}|{prev}")
        except:
            continue
    return "\n".join(lines)

def push(content,
