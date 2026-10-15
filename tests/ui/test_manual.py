"""
Перевірки сайту інструкції (Docsify): вміст 6 файлів-тем статично (без мережі,
без браузера - CDN у пісочниці недоступний), і те, що serve_manual.py реально
віддає їх правильно (сервер піднімається насправжки, це перевіряється по HTTP).
"""
import os
import re
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "help", "src")
FILES = ["start.md", "diagnostics.md", "knowledge-base.md", "logs.md", "howto.md", "reference.md"]
R = []


def check(name, ok, extra=""):
    R.append((name, bool(ok)))
    print(("  [OK]  " if ok else "  [FAIL]"), name, "" if ok else extra)


# ---------- 1. статичний вміст: кожен файл сам по собі ----------
for fn in FILES:
    path = os.path.join(SRC, fn)
    check(f"{fn}: файл існує", os.path.exists(path))
    if not os.path.exists(path):
        continue
    text = open(path, encoding="utf-8").read()
    check(f"{fn}: починається із заголовку # (немає блоку атрибутів)", text.startswith("# "), text[:60])
    check(f"{fn}: немає типів посилань popup/window/macro (Docsify їх не розуміє)",
          not re.search(r'"(popup|window|macro)"', text))
    check(f"{fn}: немає посилань-макросів app:", "](app:" not in text)
    for label, target in re.findall(r'\[([^\]]*)\]\(([^)\s]+)\)', text):
        if target.startswith("http"):
            continue
        if target.endswith(".md") and target not in FILES:
            check(f"{fn}: посилання «{label}» веде на наявний файл", False, f"-> {target}")
        if target.startswith("img/") and not os.path.exists(os.path.join(SRC, target)):
            check(f"{fn}: посилання на зображення {target} існує", False)
    for img in re.findall(r'!\[[^\]]*\]\(([^)\s]+)\)', text):
        check(f"{fn}: файл зображення {img} є на диску", os.path.exists(os.path.join(SRC, img)))

# ---------- 2. зміст відповідає рівно шести файлам ----------
sidebar = open(os.path.join(SRC, "_sidebar.md"), encoding="utf-8").read()
sidebar_targets = re.findall(r"\]\(([^)]+)\)", sidebar)
check("_sidebar.md містить рівно 6 пунктів, що збігаються з файлами",
      sorted(sidebar_targets) == sorted(FILES), str(sidebar_targets))

# ---------- 3. у теках немає забутих старих файлів тем ----------
stray = [f for f in os.listdir(SRC) if f.endswith(".md") and f not in FILES and f != "_sidebar.md"]
check("у help/src/ немає зайвих файлів тем", not stray, str(stray))

# ---------- 4. index.html узгоджений з новою структурою ----------
idx = open(os.path.join(SRC, "index.html"), encoding="utf-8").read()
check("index.html: домашня сторінка - start.md", 'homepage: "start.md"' in idx)
check("index.html: немає посилання на видалений файл intro.md", "intro.md" not in idx)
check("index.html: підключає Docsify і плагін пошуку", "docsify@4" in idx and "search.min.js" in idx)

# ---------- 5. сервер реально піднімається й віддає файли правильно ----------
PORT = 3111
srv = subprocess.Popen([sys.executable, os.path.join(ROOT, "help", "serve_manual.py"), "--port", str(PORT), "--no-browser"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(40):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1)
            break
        except Exception:
            time.sleep(0.25)

    def get(path):
        r = urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=3)
        return r.status, r.headers.get("Content-Type", ""), r.read()

    s, ct, body = get("/")
    check("сервер віддає index.html з кореня, підключає Docsify", s == 200 and b"docsify" in body)
    s, ct, body = get("/_sidebar.md")
    check("зміст _sidebar.md віддається в UTF-8", s == 200 and "utf-8" in ct.lower(), ct)
    s, ct, body = get("/start.md")
    check("тема start.md віддається і читається українською",
          s == 200 and "Запуск системи".encode("utf-8") in body)
    s, ct, body = get("/img/shell-diagnose.png")
    check("зображення віддаються з правильним типом", s == 200 and ct == "image/png", ct)
finally:
    srv.terminate()

ok = sum(1 for _, v in R if v)
print(f"\nПІДСУМОК сайту інструкції: {ok}/{len(R)}")
sys.exit(0 if ok == len(R) else 1)
