"""Тестовий бекенд для UI-тестів: ті самі ендпоінти /api/*, дані в пам'яті, справжня машина виводу.
Запускається автоматично з run_ui_tests.py. Перед запуском зупиніть справжній uvicorn на порту 8000."""
import json, os, sys, uuid, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from inference_engine.engine import InferenceEngine

KB = json.load(open(os.path.join(ROOT, "data", "knowledge_base.json"), encoding="utf-8"))
def oid(): return uuid.uuid4().hex[:24]

FACT_KEYS = ["name","kind","type","aggregation","unit","values","note","default"]
facts = []
for name, spec in KB["facts"].items():
    d = {k: None for k in FACT_KEYS}; d.update(spec); d["name"] = name; d["_id"] = oid(); facts.append(d)
def norm_cond(c):
    return {"fact": c.get("fact"), "op": c.get("op", "=="), "value": c.get("value"),
            "ref_fact": c.get("ref_fact"), "factor": c.get("factor")}
rules = []
for r in KB["rules"]:
    d = dict(r); d["conditions"] = [norm_cond(c) for c in r["conditions"]]; d["_id"] = oid(); rules.append(d)
diagnoses = []
for code, s in KB["diagnoses"].items():
    diagnoses.append({"code": code, "name": s["name"], "criticality": s["criticality"],
                      "description": s.get("description", ""), "recommendation": s.get("recommendation", ""), "_id": oid()})
runs = []
COLL = {"rules": (rules, "id"), "facts": (facts, "name"), "diagnoses": (diagnoses, "code")}

def build_kb():
    f = {x["name"]: {k: v for k, v in x.items() if k not in ("_id", "name") and v is not None} for x in facts}
    rl = []
    for r in rules:
        rr = {k: v for k, v in r.items() if k != "_id"}
        rr["conditions"] = [{k: v for k, v in c.items() if v is not None} for c in r["conditions"]]
        rl.append(rr)
    dg = {x["code"]: {k: v for k, v in x.items() if k != "_id"} for x in diagnoses}
    return {"facts": f, "rules": rl, "diagnoses": dg}

def do_diagnose(req):
    result = InferenceEngine(build_kb()).run(req["facts"]); payload = result.to_dict()
    if not req.get("include_trace", True): payload["trace"] = []
    run_id = None
    if req.get("save_run"):
        run_id = oid()
        runs.append({"_id": run_id, "label": req.get("label") or "(без підпису)",
                     "created_at": datetime.now(timezone.utc).isoformat(), "result": dict(payload)})
    payload["run_id"] = run_id
    return payload

EX = {
 "нормальна робота": {"доступна_памʼять_%": 55, "кількість_swap_операцій": 0, "тренд_використання_RAM": "стабільний", "температура_CPU": 52},
 "agent: витік памʼяті": {"доступна_памʼять_%": 6, "кількість_swap_операцій": 500, "тренд_використання_RAM": "монотонно_зростає", "тривалість_симптому_хв": 45, "критичність_сервісу": 5},
 "agent: кілька проблем": {"доступна_памʼять_%": 8, "кількість_swap_операцій": 400, "тренд_використання_RAM": "монотонно_зростає", "заповненість_диска_%": 93, "IOPS_поточні": 200, "IOPS_базова_лінія": 1000, "тренд_росту_файлів": "швидкий", "наявність_блокувань_deadlocks": True, "кількість_deadlocks_10хв": 7, "тренд_черги_транзакцій": "монотонно_зростає", "тривалість_симптому_хв": 30, "критичність_сервісу": 4},
}
t0 = datetime.now(timezone.utc) - timedelta(minutes=9)
for i, (label, facts_in) in enumerate(EX.items()):
    do_diagnose({"facts": facts_in, "save_run": True, "label": label})
    runs[-1]["created_at"] = (t0 + timedelta(minutes=i * 3)).isoformat()

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, obj=None):
        body = b"" if obj is None else json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        for k, v in (("Access-Control-Allow-Origin", "*"), ("Access-Control-Allow-Headers", "*"),
                     ("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")):
            self.send_header(k, v)
        if obj is not None: self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.end_headers()
        if body: self.wfile.write(body)
    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")
    def do_OPTIONS(self): self._send(200)
    def do_GET(self): self.route("GET")
    def do_POST(self): self.route("POST")
    def do_PUT(self): self.route("PUT")
    def do_DELETE(self): self.route("DELETE")
    def route(self, m):
        p = [x for x in urlparse(self.path).path.split("/") if x]
        try:
            if p[:2] == ["api", "health"]:
                return self._send(200, {"api": True, "mongo_connected": True, "mongo_message": "Підключено до expert_system (mock)", "rules_in_db": len(rules)})
            if p[:2] == ["api", "diagnose"] and m == "POST":
                return self._send(200, do_diagnose(self._body()))
            if p[:2] == ["api", "kb"] and p[2:3] == ["validate"]:
                return self._send(200, InferenceEngine(build_kb()).validate_knowledge_base())
            if p[:2] == ["api", "runs"]:
                if len(p) == 2:
                    out = []
                    for d in sorted(runs, key=lambda x: x["created_at"], reverse=True):
                        r = d["result"]
                        out.append({"_id": d["_id"], "label": d["label"], "created_at": d["created_at"],
                                    "diagnoses": r.get("diagnoses", []), "diagnoses_detail": r.get("diagnoses_detail", []),
                                    "severity": r.get("severity"), "has_conflicts": bool(r.get("conflicts"))})
                    return self._send(200, out)
                d = next((x for x in runs if x["_id"] == p[2]), None)
                if not d: return self._send(404, {"detail": "Прогін не знайдено"})
                r = dict(d["result"]); r.update(label=d["label"], created_at=d["created_at"], run_id=d["_id"])
                return self._send(200, r)
            if len(p) >= 2 and p[0] == "api" and p[1] in COLL:
                lst, key = COLL[p[1]]
                if len(p) == 2 and m == "GET": return self._send(200, lst)
                if len(p) == 2 and m == "POST":
                    b = self._body()
                    if any(x[key] == b.get(key) for x in lst):
                        return self._send(409, {"detail": f"«{b.get(key)}» уже існує"})
                    b["_id"] = oid(); lst.append(b); return self._send(201, b)
                item = next((x for x in lst if x["_id"] == p[2]), None)
                if not item: return self._send(404, {"detail": "Не знайдено"})
                if len(p) == 4 and p[3] == "toggle":
                    item["enabled"] = not item.get("enabled", True); return self._send(200, item)
                if m == "PUT":
                    b = self._body(); b["_id"] = item["_id"]; item.clear(); item.update(b); return self._send(200, item)
                if m == "DELETE":
                    lst.remove(item); return self._send(204)
            self._send(404, {"detail": "Немає такого ендпоінта"})
        except Exception as e:
            self._send(500, {"detail": str(e)})

ThreadingHTTPServer(("127.0.0.1", 8000), H).serve_forever()
