import os, time, base64, requests
from datetime import datetime, timezone, timedelta

GITHUB_TOKEN   = os.environ["GITHUB_TOKEN"]
JBLANKED_TOKEN = os.environ["JBLANKED_TOKEN"]
GITHUB_USER    = "fmb787"
GITHUB_REPO    = "seed_fmb787_news"

# تحويل العملة لرقم
CUR_MAP = {
    "USD":1,"EUR":2,"GBP":3,"JPY":4,
    "CAD":5,"AUD":6,"NZD":7,"CHF":8
}

# تحويل التأثير لرقم
IMP_MAP = {"high":3,"medium":2,"low":1}

# قاعدة اتجاه الخبر: 1=positive, -1=negative, 0=unknown
DB = {
    "non-farm":1,"nonfarm":1,"cpi":1,"ppi":1,"gdp":1,
    "retail":1,"ism":1,"consumer":1,"adp":1,"jolts":1,
    "durable":1,"housing":1,"building":1,"existing home":1,
    "pce":1,"ifo":1,"pmi":1,"interest rate":1,
    "rate decision":1,"trade balance":1,
    "unemployment":-1,"jobless":-1,"claimant":-1,
}

def get_dir(name):
    low = name.lower()
    for k,v in DB.items():
        if k in low:
            return v
    return 0

def fetch():
    url  = "https://www.jblanked.com/news/api/forex-factory/calendar/week/"
    hdrs = {"Authorization":"Api-Key "+JBLANKED_TOKEN,"Content-Type":"application/json"}
    try:
        r = requests.get(url, headers=hdrs, timeout=15)
        print("status: "+str(r.status_code))
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                print(str(len(data))+" events")
                return data
    except Exception as e:
        print("error: "+str(e))
    return []

def parse_ts(ds):
    try:
        ds = ds.replace(".","-",2).strip()
        dt = datetime.strptime(ds, "%Y-%m-%d %H:%M:%S")
        return int(dt.replace(tzinfo=timezone.utc).timestamp())
    except:
        try:
            dt = datetime.strptime(ds[:10], "%Y-%m-%d")
            return int(dt.replace(tzinfo=timezone.utc).timestamp())
        except:
            return 0

def to_csv(rows):
    """
    Pine Seeds CSV — صيغة إلزامية:
    date,open,high,low,close,volume
    نستخدم الحقول هكذا:
    date  = تاريخ اليوم (مطلوب)
    open  = timestamp الخبر
    high  = كود العملة (1-8)
    low   = درجة التأثير (1-3)
    close = اتجاه الخبر (1, -1, 0)
    volume= رقم الخبر التسلسلي
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")
    lines = ["date,open,high,low,close,volume"]
    seen  = set()
    idx   = 1
    for ev in rows:
        try:
            name   = str(ev.get("Name","")).strip()
            cur    = str(ev.get("Currency","")).strip().upper()
            ds     = str(ev.get("Date","")).strip()
            impact = str(ev.get("Impact","Low")).strip().lower()

            if not name or not cur or not ds:
                continue

            ts  = parse_ts(ds)
            if ts == 0:
                continue

            cur_code = CUR_MAP.get(cur, 0)
            if cur_code == 0:
                continue

            imp_code = IMP_MAP.get(impact, 1)
            dir_code = get_dir(name)

            key = str(ts)+"_"+cur
            if key in seen:
                continue
            seen.add(key)

            # كل خبر = سطر واحد في CSV
            lines.append(today+","+str(ts)+","+str(cur_code)+","+str(imp_code)+","+str(dir_code)+","+str(idx))
            idx += 1
        except Exception as e:
            print("row error: "+str(e))
    return "\n".join(lines)

def to_names_csv(rows):
    """
    ملف ثانٍ يخزن أسماء الأخبار كأرقام
    لأن Pine Seeds لا يدعم النصوص
    نستخدم volume كـ index والاسم يُحفظ في ملف منفصل كـ mapping
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")
    lines = ["date,open,high,low,close,volume"]
    seen  = set()
    idx   = 1
    for ev in rows:
        try:
            name   = str(ev.get("Name","")).strip()
            cur    = str(ev.get("Currency","")).strip().upper()
            ds     = str(ev.get("Date","")).strip()
            actual = str(ev.get("Actual","")).strip()
            fore   = str(ev.get("Forecast","")).strip()
            prev   = str(ev.get("Previous","")).strip()

            if not name or not cur or not ds:
                continue

            ts = parse_ts(ds)
            if ts == 0:
                continue

            cur_code = CUR_MAP.get(cur, 0)
            if cur_code == 0:
                continue

            key = str(ts)+"_"+cur
            if key in seen:
                continue
            seen.add(key)

            # تحويل الأرقام — إذا فارغ نستخدم -9999 كـ placeholder
            try:
                act_val = float(actual) if actual and actual != "0.0" else -9999.0
            except:
                act_val = -9999.0
            try:
                fore_val = float(fore) if fore and fore != "0.0" else -9999.0
            except:
                fore_val = -9999.0

            # open=actual, high=forecast, low=prev_placeholder, close=idx, volume=ts
            lines.append(today+","+str(act_val)+","+str(fore_val)+",-9999,"+str(idx)+","+str(ts))
            idx += 1
        except Exception as e:
            print("row error2: "+str(e))
    return "\n".join(lines)

def push(content, filename):
    url  = "https://api.github.com/repos/"+GITHUB_USER+"/"+GITHUB_REPO+"/contents/"+filename
    hdrs = {"Authorization":"token "+GITHUB_TOKEN,"Accept":"application/vnd.github.v3+json"}
    sha  = None
    r    = requests.get(url, headers=hdrs, timeout=10)
    if r.status_code == 200:
        sha = r.json().get("sha")
    enc = base64.b64encode(content.encode()).decode()
    pay = {"message":"update "+datetime.utcnow().strftime("%H:%M:%S"),"content":enc}
    if sha:
        pay["sha"] = sha
    r = requests.put(url, headers=hdrs, json=pay, timeout=15)
    print(("OK" if r.status_code in(200,201) else "FAIL")+": "+filename)

def main():
    print("start "+datetime.utcnow().strftime("%H:%M:%S"))
    evs = fetch()
    if evs:
        push(to_csv(evs),       "EVENTS.CSV")
        push(to_names_csv(evs), "ACTUALS.CSV")
        push(str(int(time.time())), "last_update.txt")
        print("done - "+str(len(evs))+" events pushed")
    else:
        print("no data")

if __name__ == "__main__":
    main()
