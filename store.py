"""Слой хранения. Сейчас JSON-файл; позже заменить класс на PostgreSQL, API остаётся прежним."""
import json, os, threading, uuid, time

class Store:
    def __init__(self, path="data.json"):
        self.path, self.lock = path, threading.RLock()
        self.data = {"cards": [], "tx": [], "audit": [], "salt": uuid.uuid4().hex}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.data.update(json.load(f))
        self.save()

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def log(self, action, details=""):
        self.data["audit"].append({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "a": action, "d": details})
        self.data["audit"] = self.data["audit"][-1000:]

    def new_id(self):
        return uuid.uuid4().hex[:10]
