import hashlib, re
from datetime import datetime, timedelta, date
from flask import Flask, jsonify, request, send_from_directory
from store import Store

app = Flask(__name__, static_folder="static", static_url_path="/static")
db = Store()

BANKS = [  # (id, название, цвет1, цвет2, акцент) — стилизация, без фирменных логотипов
 ("tbank","Т-Банк","#1c1c1e","#3a3a3c","#ffdd2d"),("sber","Сбербанк","#0b8f3c","#35c46a","#d8ffe4"),
 ("alfa","Альфа-Банк","#1a1a1a","#ef3124","#ffffff"),("ozon","Ozon Банк","#0a3cff","#2d9bff","#ffffff"),
 ("wb","WB Банк","#6d1fd1","#c026d3","#ffffff"),("vtb","ВТБ","#0a2aa8","#1f6bff","#ffffff"),
 ("gpb","Газпромбанк","#0b3c8a","#2b7de0","#ffffff"),("sovcom","Совкомбанк","#d4145a","#ff5c8a","#ffffff"),
 ("raif","Райффайзенбанк","#2b2b2b","#ffe600","#ffffff"),("rshb","Россельхозбанк","#0d6b3a","#9bcf2e","#ffffff"),
 ("pochta","Почта Банк","#1e3a8a","#e11d48","#ffffff"),("yandex","Яндекс Банк","#111111","#fc3f1d","#ffffff"),
 ("mts","МТС Банк","#c4121a","#ff5a5f","#ffffff"),("bspb","Банк Санкт-Петербург","#7a1230","#c0394f","#ffffff"),
 ("psb","Промсвязьбанк","#1b2a6b","#ff6a00","#ffffff"),("rosbank","Росбанк","#b0121b","#3b3b3b","#ffffff"),
 ("other","Другой банк","#2c3e50","#5d7b99","#ffffff")]
BANK_MAP = {b[0]: b for b in BANKS}

def err(msg, code=400): return jsonify({"error": msg}), code

def pseudo(name):
    """Третьи лица хранятся только как псевдоним (хеш с солью), без ФИО."""
    n = re.sub(r"\s+", " ", name.strip().lower())
    return hashlib.sha256((db.data["salt"] + n).encode()).hexdigest()[:6].upper()

def parse_ts(t): return datetime.strptime(t["date"] + " " + t["time"], "%Y-%m-%d %H:%M")

def card_stats(card, txs, d_from=None, d_to=None):
    inc = [t for t in txs if t["type"] == "in"]
    out = [t for t in txs if t["type"] == "out"]
    s_in, s_out = sum(t["amount"] for t in inc), sum(t["amount"] for t in out)
    first = {}
    for t in sorted(inc, key=parse_ts): first.setdefault(t["sender"], t["date"])
    return {"balance": round(card["initial"] + s_in - s_out, 2), "income": round(s_in, 2), "expense": round(s_out, 2),
            "turnover": round(s_in + s_out, 2), "n_in": len(inc), "n_out": len(out)}

def senders_report(txs, d_from=None, d_to=None):
    allinc = sorted([t for t in txs if t["type"] == "in"], key=parse_ts)
    first = {}
    for t in allinc: first.setdefault(t["sender"], t["date"])
    inc = [t for t in allinc if (not d_from or t["date"] >= d_from) and (not d_to or t["date"] <= d_to)]
    by = {}
    for t in inc: by.setdefault(t["sender"], []).append(t)
    rows = [{"alias": "Отправитель " + k, "count": len(v), "sum": round(sum(x["amount"] for x in v), 2),
             "last": max(x["date"] for x in v), "new": bool(d_from and first[k] >= d_from) if d_from else False,
             "history": [{"date": x["date"], "time": x["time"], "amount": x["amount"]} for x in v[-10:]]} for k, v in by.items()]
    rows.sort(key=lambda r: -r["sum"])
    amounts = [t["amount"] for t in inc]
    return {"total_ops": len(inc), "unique": len(by), "repeat": sum(1 for r in rows if r["count"] > 1),
            "new": sum(1 for r in rows if r["new"]), "sum": round(sum(amounts), 2),
            "avg": round(sum(amounts) / len(amounts), 2) if amounts else 0, "max": max(amounts) if amounts else 0, "rows": rows}

def risk(txs):
    """Прозрачная оценка необычности. Это НЕ вероятность блокировки и не гарантия безопасности."""
    today = date.today()
    w = lambda a, b: [t for t in txs if t["type"] == "in" and str(today - timedelta(days=a)) <= t["date"] <= str(today - timedelta(days=b))]
    cur, prev = w(6, 0), w(13, 7)
    factors, pts = [], 0
    def add(name, level, why):
        nonlocal pts; pts = max(pts, level); factors.append({"name": name, "level": level, "why": why})
    c, p = len(cur), len(prev)
    if p >= 3 and c >= 2 * p: add("Частота операций", 2, f"За 7 дней {c} поступлений против {p} за предыдущие 7 дней: рост более чем в 2 раза.")
    elif p >= 3 and c >= 1.5 * p: add("Частота операций", 1, f"За 7 дней {c} поступлений против {p} в предыдущие 7 дней: рост в 1,5 раза и более.")
    else: add("Частота операций", 0, f"Поступлений: {c} за 7 дней, {p} за предыдущие 7 дней. Резкого роста нет.")
    ac = sum(t["amount"] for t in cur) / c if c else 0
    ap = sum(t["amount"] for t in prev) / p if p else 0
    if p >= 3 and ap and ac >= 2 * ap: add("Средняя сумма", 2, f"Средняя сумма выросла с {ap:,.0f} до {ac:,.0f} руб. (более чем в 2 раза).".replace(",", " "))
    elif p >= 3 and ap and ac >= 1.5 * ap: add("Средняя сумма", 1, f"Средняя сумма выросла с {ap:,.0f} до {ac:,.0f} руб.".replace(",", " "))
    else: add("Средняя сумма", 0, "Существенного изменения средней суммы нет или данных мало.")
    seen_before = {t["sender"] for t in txs if t["type"] == "in" and t["date"] < str(today - timedelta(days=6))}
    new_s = {t["sender"] for t in cur} - seen_before
    share = len(new_s) / len({t["sender"] for t in cur}) if cur else 0
    if len(new_s) >= 5 and share >= 0.8: add("Новые отправители", 2, f"{len(new_s)} новых отправителей за 7 дней ({share:.0%} от всех).")
    elif len(new_s) >= 3 and share >= 0.6: add("Новые отправители", 1, f"{len(new_s)} новых отправителей за 7 дней ({share:.0%} от всех).")
    else: add("Новые отправители", 0, "Доля новых отправителей не выглядит необычной.")
    inc = [t for t in txs if t["type"] == "in"]
    nodoc = [t for t in inc if not t.get("doc") and not t.get("deal")]
    if inc and len(nodoc) / len(inc) > 0.5 and len(nodoc) >= 3: add("Документы и сделки", 2, f"{len(nodoc)} из {len(inc)} поступлений без привязки к сделке или документу.")
    elif nodoc: add("Документы и сделки", 1, f"{len(nodoc)} поступлений без привязки к сделке или документу. Рекомендуем дополнить учёт.")
    else: add("Документы и сделки", 0, "Все поступления связаны со сделкой или документом.")
    refunds = [t for t in txs if t.get("refund")]
    if refunds: add("Возвраты и спорные", 1, f"Отмечено возвратов или спорных платежей: {len(refunds)}.")
    keys = {}
    for t in inc: keys.setdefault((t["sender"], t["amount"], t["date"]), []).append(t)
    dup = sum(1 for v in keys.values() if len(v) > 1)
    if dup: add("Повторы", 1, f"Найдено групп одинаковых операций (тот же отправитель, сумма и день): {dup}. Проверьте, нет ли дублей.")
    level = ["НИЗКИЙ", "ПОВЫШЕННЫЙ", "ВЫСОКИЙ"][pts]
    return {"level": level, "code": pts, "factors": factors,
            "note": "Оценка показывает необычность данных учёта и качество документации. Это не вероятность блокировки и не гарантия безопасности. Решения принимает банк."}

def chart(txs, days=14):
    today = date.today(); res = []
    for i in range(days - 1, -1, -1):
        d = str(today - timedelta(days=i))
        res.append({"d": d[5:], "in": round(sum(t["amount"] for t in txs if t["date"] == d and t["type"] == "in"), 2),
                    "out": round(sum(t["amount"] for t in txs if t["date"] == d and t["type"] == "out"), 2)})
    return res

def find_card(cid): return next((c for c in db.data["cards"] if c["id"] == cid), None)
def card_txs(cid): return [t for t in db.data["tx"] if t["card"] == cid]

@app.route("/")
def index(): return send_from_directory("static", "index.html")

@app.get("/api/banks")
def banks(): return jsonify([{"id": b[0], "name": b[1], "c1": b[2], "c2": b[3], "ac": b[4]} for b in BANKS])

@app.get("/api/summary")
def summary():
    today, cards = date.today(), db.data["cards"]; txs = db.data["tx"]
    inc = lambda a: sum(t["amount"] for t in txs if t["type"] == "in" and t["date"] >= str(today - timedelta(days=a)))
    ts = str(today)
    cards_out = []
    for c in cards:
        r = risk(card_txs(c["id"]))
        cards_out.append({**c, **card_stats(c, card_txs(c["id"])), "risk": r["level"], "risk_code": r["code"]})
    return jsonify({"balance": round(sum(c["balance"] for c in cards_out), 2),
        "today_in": round(sum(t["amount"] for t in txs if t["type"] == "in" and t["date"] == ts), 2),
        "today_out": round(sum(t["amount"] for t in txs if t["type"] == "out" and t["date"] == ts), 2),
        "week_in": round(inc(6), 2), "month_in": round(inc(29), 2), "ops": len(txs),
        "senders": len({t["sender"] for t in txs if t["type"] == "in"}), "cards": len(cards),
        "review": sum(1 for c in cards_out if c["risk_code"] >= 1), "chart": chart(txs), "list": cards_out})

@app.post("/api/cards")
def add_card():
    j = request.get_json(silent=True) or {}
    bank = j.get("bank"); name = (j.get("bank_name") or "").strip()[:40]
    if bank not in BANK_MAP: return err("Выберите банк")
    if bank == "other" and not name: return err("Укажите название банка")
    last4 = str(j.get("last4", ""))
    if not re.fullmatch(r"\d{4}", last4): return err("Нужны ровно 4 последние цифры (без CVV, PIN и полного номера)")
    try: initial = float(j.get("initial") or 0)
    except ValueError: return err("Некорректный баланс")
    if j.get("system") not in ("Мир", "Visa", "Mastercard", "UnionPay"): return err("Выберите платёжную систему")
    if j.get("currency") not in ("RUB", "USD", "EUR"): return err("Выберите валюту")
    c = {"id": db.new_id(), "bank": bank, "bank_name": name or BANK_MAP[bank][1], "title": (j.get("title") or "").strip()[:40] or BANK_MAP[bank][1],
         "last4": last4, "system": j["system"], "initial": initial, "currency": j["currency"], "note": (j.get("note") or "")[:300]}
    with db.lock:
        db.data["cards"].append(c); db.log("card_add", c["title"] + " *" + last4); db.save()
    return jsonify(c), 201

@app.delete("/api/cards/<cid>")
def del_card(cid):
    with db.lock:
        c = find_card(cid)
        if not c: return err("Не найдено", 404)
        db.data["cards"].remove(c); db.data["tx"] = [t for t in db.data["tx"] if t["card"] != cid]
        db.log("card_delete", c["title"]); db.save()
    return jsonify({"ok": True})

@app.get("/api/cards/<cid>")
def card_detail(cid):
    c = find_card(cid)
    if not c: return err("Не найдено", 404)
    txs = card_txs(cid)
    d_from, d_to = request.args.get("from"), request.args.get("to")
    return jsonify({"card": c, "stats": card_stats(c, txs), "risk": risk(txs), "chart": chart(txs),
        "senders": senders_report(txs, d_from, d_to), "tx": sorted(txs, key=parse_ts, reverse=True)})

@app.post("/api/cards/<cid>/tx")
def add_tx(cid):
    c = find_card(cid)
    if not c: return err("Не найдено", 404)
    j = request.get_json(silent=True) or {}
    typ = j.get("type")
    if typ not in ("in", "out"): return err("Неверный тип операции")
    try: amount = round(float(j.get("amount")), 2)
    except (TypeError, ValueError): return err("Некорректная сумма")
    if amount <= 0 or amount > 1e9: return err("Сумма должна быть больше нуля")
    try: datetime.strptime(j.get("date", "") + " " + j.get("time", ""), "%Y-%m-%d %H:%M")
    except ValueError: return err("Некорректные дата или время")
    sender = (j.get("sender") or "").strip()
    if typ == "in" and not sender: return err("Укажите отправителя (хранится только как псевдоним)")
    op_id = (j.get("op_id") or "").strip()[:60]
    t = {"id": db.new_id(), "card": cid, "type": typ, "amount": amount, "date": j["date"], "time": j["time"],
         "sender": pseudo(sender) if typ == "in" else "", "sender_bank": (j.get("sender_bank") or "")[:40], "op_id": op_id,
         "comment": (j.get("comment") or "")[:300], "deal": (j.get("deal") or "")[:60], "doc": bool(j.get("doc")),
         "refund": bool(j.get("refund")), "fee": max(0, float(j.get("fee") or 0)) if str(j.get("fee") or "0").replace(".", "", 1).isdigit() else 0}
    with db.lock:
        for o in card_txs(cid):  # защита от повторного добавления
            if op_id and o["op_id"] == op_id: return err("Операция с таким идентификатором уже есть", 409)
            if not op_id and (o["type"], o["amount"], o["date"], o["time"], o["sender"]) == (typ, amount, t["date"], t["time"], t["sender"]):
                return err("Такая операция уже добавлена", 409)
        db.data["tx"].append(t); db.log("tx_add", f"{typ} {amount} {cid}"); db.save()
    return jsonify(t), 201

@app.delete("/api/tx/<tid>")
def del_tx(tid):
    with db.lock:
        t = next((x for x in db.data["tx"] if x["id"] == tid), None)
        if not t: return err("Не найдено", 404)
        db.data["tx"].remove(t); db.log("tx_delete", f"{t['type']} {t['amount']} {t['card']}"); db.save()
    return jsonify({"ok": True})

@app.get("/api/audit")
def audit(): return jsonify(db.data["audit"][-100:][::-1])

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
