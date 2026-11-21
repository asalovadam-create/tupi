"""Курсы: доллар по данным ЦБ РФ, GRAM (бывш. TON) по CoinGecko. Источник и дата показываются в интерфейсе."""
import os, json, time, threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

GRAM_ID = os.environ.get("GRAM_COINGECKO_ID", "the-open-network")
_c, _lock = {}, threading.Lock()

def _get(url): return urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0 P2PGuardian"}), timeout=8).read(2_000_000)

def _json(url): return json.loads(_get(url))

def _cached(key, ttl, fn):
    with _lock: e = _c.get(key)
    if e and time.time() - e[0] < ttl: return e[1]
    try: v = fn()
    except Exception as ex: v = {"error": "Источник недоступен", "detail": [str(ex)[:80]]}
    if "error" in v: return e[1] if e else v  # неудачу не кэшируем
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

def _hourly(newest_first):
    c = newest_first[::-1]
    return c[::6], ((c[-1] / c[0] - 1) * 100 if len(c) > 100 and c[0] else None)

def _cg():
    d = {cur: _json(f"https://api.coingecko.com/api/v3/coins/markets?vs_currency={cur}&ids={GRAM_ID}&price_change_percentage=24h,7d&sparkline=true")[0] for cur in ("usd", "rub")}
    x = d["rub"]
    return {"usd": d["usd"]["current_price"], "rub": x["current_price"], "ch24": x.get("price_change_percentage_24h_in_currency"),
            "ch7d": x.get("price_change_percentage_7d_in_currency"), "series": (x.get("sparkline_in_7d") or {}).get("price", [])[::6]}

def _binance():
    base = "https://data-api.binance.vision/api/v3"
    t = _json(base + "/ticker/24hr?symbol=GRAMUSDT"); series, ch7 = [], None
    try: series, ch7 = _hourly([float(k[4]) for k in reversed(_json(base + "/klines?symbol=GRAMUSDT&interval=1h&limit=169"))])
    except Exception: pass
    return {"usd": float(t["lastPrice"]), "ch24": float(t["priceChangePercent"]), "ch7d": ch7, "series": series}

def _okx():
    t = _json("https://www.okx.com/api/v5/market/ticker?instId=GRAM-USDT")
    if t.get("code") != "0" or not t.get("data"): raise ValueError(t.get("msg") or "нет данных")
    x = t["data"][0]; last, o24 = float(x["last"]), float(x["open24h"]); series, ch7 = [], None
    try: series, ch7 = _hourly([float(k[4]) for k in _json("https://www.okx.com/api/v5/market/candles?instId=GRAM-USDT&bar=1H&limit=169")["data"]])
    except Exception: pass
    return {"usd": last, "ch24": (last / o24 - 1) * 100 if o24 else None, "ch7d": ch7, "series": series}

def _bybit():
    x = _json("https://api.bybit.com/v5/market/tickers?category=spot&symbol=GRAMUSDT")["result"]["list"][0]
    return {"usd": float(x["lastPrice"]), "ch24": float(x["price24hPcnt"]) * 100, "ch7d": None, "series": []}

PROVIDERS = [("CoinGecko", _cg), ("Binance", _binance), ("OKX", _okx), ("Bybit", _bybit)]

def _gram(usd_rub):
    """Пробуем все источники одновременно и берём первый рабочий по порядку приоритета."""
    with ThreadPoolExecutor(len(PROVIDERS)) as ex: futs = [(n, ex.submit(f)) for n, f in PROVIDERS]
    detail = []
    for n, fu in futs:
        try: r = fu.result()
        except Exception as e: detail.append(f"{n}: {str(e)[:60]}"); continue
        r["source"] = n
        if "rub" not in r:
            if not usd_rub: detail.append(f"{n}: нет курса ЦБ для пересчёта в рубли"); continue
            r["rub"], r["rub_calc"] = r["usd"] * usd_rub, True
        return r
    return {"error": "Курс GRAM не получен", "detail": detail}

def get_usd(now): return _cached("usd", 1800, lambda: _usd(now))
def get_gram(usd_rub=None): return _cached("gram", 120, lambda: _gram(usd_rub))

def get_rates():
    now = datetime.now(timezone(timedelta(hours=3))).replace(tzinfo=None)  # даты по Москве
    u = get_usd(now)
    return {"usd": u, "gram": get_gram((u.get("today") or {}).get("value"))}
