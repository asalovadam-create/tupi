"""Новости из открытых RSS-лент. Ничего не выдумывается: только то, что отдали источники, со ссылкой и датой."""
import re, time, html, threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

FEEDS = [("Банк России", "https://www.cbr.ru/rss/RssPress"),
         ("Коммерсантъ", "https://www.kommersant.ru/RSS/section-economics.xml"),
         ("РБК", "https://rssexport.rbc.ru/rbcnews/news/30/full.rss"),
         ("Ведомости", "https://www.vedomosti.ru/rss/news"),
         ("Banki.ru", "https://www.banki.ru/xml/news.rss"),
         ("Интерфакс", "https://www.interfax.ru/rss.asp"),
         ("Forklog", "https://forklog.com/feed")]
CATS = {"P2P": ["p2p", "п2п", "одноранг"],
        "Криптовалюты": ["крипт", "биткоин", "bitcoin", "usdt", "стейблкоин", "ethereum"],
        "Банки": ["банк"],
        "115-ФЗ": ["115-фз", "115 фз", "финмониторинг", "подозрительн", "блокировк"],
        "161-ФЗ": ["161-фз", "161 фз", "национальной платежной", "национальной платёжной"],
        "Банк России": ["банк россии", "банка россии", "центробанк", "цб рф", "ключевая ставка"],
        "Законодательство": ["законопроект", "госдум", "закон о", "федеральный закон"],
        "Биржи": ["бирж", "binance", "bybit", "okx"],
        "Платёжные системы": ["платежн", "платёжн", "сбп", "visa", "mastercard", "система «мир»"]}
HINTS = {"115-ФЗ": "Тема финансового мониторинга: проверьте, меняются ли требования банков к операциям и документам.",
         "161-ФЗ": "Касается правил национальной платёжной системы и переводов. Сверьтесь с первоисточником.",
         "P2P": "Может влиять на условия P2P-переводов. Оцените по первоисточнику.",
         "Банк России": "Решения и комментарии регулятора. Влияние зависит от ваших операций.",
         "Криптовалюты": "Может затрагивать работу с криптовалютой и биржами. Проверьте детали в источнике."}
MAX_AGE_DAYS, TTL = 45, 900
_c = {"t": 0, "items": [], "errors": []}; _lock = threading.Lock()

def _fetch(url):
    return urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0 P2PGuardian"}), timeout=8).read(2_000_000)

def _date(s):
    if not s: return None
    try: d = parsedate_to_datetime(s.strip())
    except Exception:
        try: d = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
        except Exception: return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

def _t(el, *names):
    for n in names:
        x = el.find(n)
        if x is not None and (x.text or "").strip(): return x.text.strip()
    return ""

def _parse(source, raw):
    root, out = ET.fromstring(raw), []
    A = "{http://www.w3.org/2005/Atom}"
    for it in list(root.iter("item")) + list(root.iter(A + "entry")):
        title = html.unescape(_t(it, "title", A + "title"))
        link = _t(it, "link") or (it.find(A + "link").get("href") if it.find(A + "link") is not None else "")
        body = _t(it, "description", A + "summary", "{http://purl.org/rss/1.0/modules/content/}encoded", A + "content")
        d = _date(_t(it, "pubDate", A + "published", A + "updated", "{http://purl.org/dc/elements/1.1/}date"))
        if not (title and link.startswith("http") and d): continue
        img = ""
        for e in list(it.iter("enclosure")) + list(it.iter("{http://search.yahoo.com/mrss/}content")):
            u = e.get("url") or ""
            if u.startswith("http") and ("image" in (e.get("type") or "image") or u.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))): img = u; break
        if not img:
            m = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)', body)
            img = m.group(1) if m else ""
        text = html.unescape(re.sub(r"<[^>]+>", " ", body)); text = re.sub(r"\s+", " ", text).strip()
        out.append({"title": title, "link": link, "date": d.isoformat(), "source": source, "summary": text[:260], "image": img})
    return out

def _categorize(i):
    blob = (i["title"] + " " + i["summary"]).lower()
    return [c for c, kw in CATS.items() if any(k in blob for k in kw)]

def refresh():
    items, errors, seen = [], [], set()
    def one(f):
        try: return f[0], _parse(f[0], _fetch(f[1])), None
        except Exception as e: return f[0], [], str(e)[:80]
    with ThreadPoolExecutor(len(FEEDS)) as ex: res = list(ex.map(one, FEEDS))
    limit = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    for src, its, e in res:
        if e: errors.append(src)
        for i in its:
            if i["link"] in seen or datetime.fromisoformat(i["date"]) < limit or datetime.fromisoformat(i["date"]) > datetime.now(timezone.utc) + timedelta(hours=1): continue
            i["cats"] = _categorize(i)
            if not i["cats"]: continue
            i["hint"] = next((HINTS[c] for c in i["cats"] if c in HINTS), "")
            seen.add(i["link"]); items.append(i)
    items.sort(key=lambda i: i["date"], reverse=True)
    return items, errors

def get_news():
    with _lock:
        if time.time() - _c["t"] > TTL:
            _c["items"], _c["errors"] = refresh(); _c["t"] = time.time()
        return _c["items"], _c["errors"]
