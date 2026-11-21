"""Расчёт цепочки: RUB -> USDT -> GRAM -> продажа в Telegram Wallet (комиссия Wallet задаётся, по умолчанию 2%)."""
def _num(i, k, name, positive=False, default=None):
    v = i.get(k)
    if v in (None, ""):
        if default is not None: return default
        raise ValueError(f"Заполните поле: {name}")
    try: v = float(str(v).replace(",", "."))
    except ValueError: raise ValueError(f"Некорректное число: {name}")
    if v < 0 or (positive and v == 0) or v > 1e12: raise ValueError(f"Некорректное значение: {name}")
    return v

def calc(i):
    rub = _num(i, "rub_in", "потрачено, ₽", True); rate = _num(i, "usdt_rate", "цена покупки USDT", True)
    g_usdt = _num(i, "gram_usdt", "курс обмена GRAM", True); sell = _num(i, "sell_rate", "цена продажи GRAM", True)
    buy_fee = _num(i, "buy_fee", "комиссия покупки", default=0); ex_fee = _num(i, "ex_fee", "комиссия обмена", default=0)
    w_fee = _num(i, "wallet_fee", "комиссия Wallet", default=2); transfer = _num(i, "transfer_usdt", "сетевая комиссия", default=0); extra = _num(i, "extra_rub", "другие расходы", default=0)
    if max(buy_fee, ex_fee, w_fee) >= 100: raise ValueError("Комиссия должна быть меньше 100%")
    usdt = rub * (1 - buy_fee / 100) / rate
    usdt_after = usdt - transfer
    if usdt_after <= 0: raise ValueError("Сетевая комиссия больше купленной суммы USDT")
    gram = usdt_after * (1 - ex_fee / 100) / g_usdt
    gross = gram * sell; fee = gross * w_fee / 100; net = gross - fee
    cost = rub + extra; profit = net - cost
    return {"in": {"rub_in": rub, "usdt_rate": rate, "buy_fee": buy_fee, "transfer_usdt": transfer, "gram_usdt": g_usdt, "ex_fee": ex_fee, "sell_rate": sell, "wallet_fee": w_fee, "extra_rub": extra},
            "usdt": round(usdt, 4), "usdt_after": round(usdt_after, 4), "gram": round(gram, 4), "gross": round(gross, 2), "wallet_fee_rub": round(fee, 2),
            "net": round(net, 2), "cost": round(cost, 2), "profit": round(profit, 2), "profit_pct": round(profit / cost * 100, 2),
            "break_even": round(cost / (gram * (1 - w_fee / 100)), 2)}
