"""Курсы: доллар по данным ЦБ РФ, GRAM (бывш. TON) по CoinGecko. Источник и дата показываются в интерфейсе."""
import os, json, time, threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

GRAM_ID = os.environ.get("GRAM_COINGECKO_ID", "the-open-network")
_c, _lock = {}, threading.Lock()

def _get(url): return urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0 P2PGuardian"}), timeout=8).read(2_000_000)

def _cached(key, ttl, fn):
    with _lock: e = _c.get(key)
    if e and time.time() - e[0] < ttl: return e[1]
    try: v = fn()
    except Exception: return e[1] if e else {"error": "Источник недоступен"}
    with _lock: _c[key] = (time.time(), v)
    return v

def _usd(now):
    url = f"https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={now - timedelta(days=24):%d/%m/%Y}&date_req2={now + timedelta(days=3):%d/%m/%Y}&VAL_NM_RQ=R01235"
    rec = sorted((datetime.strptime(r.get("Date"), "%d.%m.%Y").date(), round(float(r.findtext("Value").replace(",", ".")) / float(r.findtext("Nominal", "1").replace(",", ".")), 4)) for r in ET.fromstring(_get(url)).iter("Record"))
    if not rec: raise ValueError("пусто")
    today = now.date()
    at = lambda d: next(({"date": f"{x[0]:%d.%m.%Y}", "value": x[1]} for x in reversed(rec) if x[0] <= d), {"date": f"{rec[0][0]:%d.%m.%Y}", "value": rec[0][1]})
    t, y, w = at(today), at(today - timedelta(days=1)), at(today - timedelta(days=7))
    nxt = next(({"date": f"{x[0]:%d.%m.%Y}", "value": x[1]} for x in rec if x[0] > today), None)
    pct = lambda a, b: round((a - b) / b * 100, 2) if b else 0
    return {"today": t, "yesterday": y, "week": w, "next": nxt, "chg_day": round(t["value"] - y["value"], 4), "chg_day_pct": pct(t["value"], y["value"]),
            "chg_week": round(t["value"] - w["value"], 4), "chg_week_pct": pct(t["value"], w["value"]), "series": [x[1] for x in rec if x[0] <= today][-14:],
            "note": "Официальный курс ЦБ РФ: меняется раз в рабочий день, внутри дня не обновляется."}

def _gram():
    d = {cur: json.loads(_get(f"https://api.coingecko.com/api/v3/coins/markets?vs_currency={cur}&ids={GRAM_ID}&price_change_percentage=24h,7d&sparkline=true"))[0] for cur in ("usd", "rub")}
    r = d["rub"]
    return {"usd": d["usd"]["current_price"], "rub": r["current_price"], "ch24": r.get("price_change_percentage_24h_in_currency"),
            "ch7d": r.get("price_change_percentage_7d_in_currency"), "series": (r.get("sparkline_in_7d") or {}).get("price", [])[::6], "updated": r.get("last_updated")}

def get_usd(now): return _cached("usd", 1800, lambda: _usd(now))
def get_gram(): return _cached("gram", 120, _gram)

def get_rates():
    now = datetime.now(timezone(timedelta(hours=3))).replace(tzinfo=None)  # даты по Москве
    with ThreadPoolExecutor(2) as ex:
        u, g = ex.submit(get_usd, now), ex.submit(get_gram)
        return {"usd": u.result(), "gram": g.result()}
