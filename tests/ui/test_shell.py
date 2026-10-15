"""UI-тест у справжньому Chromium (Playwright). Скриншоти зберігає в docs/pr2/img/."""
import sys, json
import os, subprocess, time
from pathlib import Path
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from playwright.sync_api import sync_playwright
BASE = Path(ROOT).as_uri() + "/"
IMG = os.path.join(ROOT, "docs", "pr2", "img") + os.sep
R = []
def check(name, ok, extra=""):
    R.append((name, bool(ok)))
    print(("  [OK]  " if ok else "  [FAIL]"), name, extra if not ok else "")

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1360, "height": 820})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

    pg.goto(BASE + "app.html"); pg.wait_for_timeout(1200)
    check("оболонка: 4 пункти головного меню", pg.locator(".mtitle").count() == 4)
    check("оболонка: за замовчуванням відкрита «Діагностика»", "diagnose.html" in pg.locator("#view").get_attribute("src"))
    check("статус: індикатор бекенда зелений", "ok" in (pg.locator("#dot").get_attribute("class") or ""))
    check("статус: контекст «Діагностика»", pg.locator("#sb-ctx").inner_text() == "Діагностика", pg.locator("#sb-ctx").inner_text())

    def menu(title): return pg.locator(".menu", has=pg.locator(".mtitle", has_text=title))
    # --- меню й підказки
    pg.locator(".mtitle", has_text="База знань").click()
    check("меню відкривається кліком", menu("База знань").get_attribute("class").find("open") >= 0)
    menu("База знань").locator(".mi", has_text="Факти").hover(); pg.wait_for_timeout(150)
    check("підказка в рядку стану при наведенні", "Факти" in pg.locator("#sb-hint").inner_text(), pg.locator("#sb-hint").inner_text())
    pg.locator(".mtitle", has_text="Діагностика").hover(); pg.wait_for_timeout(150)
    check("наведення перемикає відкрите меню", "open" in (menu("Діагностика").get_attribute("class") or ""))
    menu("Діагностика").locator(".mi", has_text="Готові приклади").hover(); pg.wait_for_timeout(150)
    pg.screenshot(path=IMG + "menu-submenu.png")
    check("підменю (2-й рівень) видиме", menu("Діагностика").locator(".sub").is_visible())
    menu("Діагностика").locator(".sub .mi", has_text="Кілька проблем").click(); pg.wait_for_timeout(600)
    fr = pg.frame_locator("#view")
    n = fr.locator(".fact-row").count()
    check("приклад «Кілька проблем» підставив показники", n >= 10, f"n={n}")
    fr.locator("button.primary").click(); pg.wait_for_timeout(900)
    cards = fr.locator(".diag-card").count()
    check("діагностика через оболонку: 4 картки діагнозів", cards == 4, f"cards={cards}")
    check("контекст після результату «Діагностика › Результат»", pg.locator("#sb-ctx").inner_text() == "Діагностика › Результат", pg.locator("#sb-ctx").inner_text())
    pg.screenshot(path=IMG + "shell-diagnose.png")

    # --- контекстне меню показника
    fr.locator(".fact-row").first.click(button="right"); pg.wait_for_timeout(200)
    check("контекстне меню показника відкрилось", fr.locator(".ctx").count() == 1)
    pg.screenshot(path=IMG + "ctx-fact.png")
    n0 = fr.locator(".fact-row").count()
    fr.locator(".ctx div", has_text="Видалити показник").click(); pg.wait_for_timeout(200)
    check("«Видалити показник» з контекстного меню працює", fr.locator(".fact-row").count() == n0 - 1)

    # --- F1 з вкладеної сторінки (та сама дія, що й пункт меню «Інструкція користувача»)
    fr.locator("body").press("F1"); pg.wait_for_timeout(500)
    check("F1 доходить до дії «Інструкція користувача» (підказка про запуск сайту)",
          "serve_manual.py" in pg.locator("#sb-hint").inner_text(), pg.locator("#sb-hint").inner_text())

    # --- редактор через меню і гарячі клавіші
    pg.keyboard.press("Control+3"); pg.wait_for_timeout(1200)
    check("Ctrl+3 відкриває редактор", "editor.html" in pg.locator("#view").get_attribute("src"))
    check("контекст «Редактор › Правила»", pg.locator("#sb-ctx").inner_text() == "Редактор › Правила", pg.locator("#sb-ctx").inner_text())
    pg.locator(".mtitle", has_text="База знань").click()
    menu("База знань").locator(".mi", has_text="Діагнози").click(); pg.wait_for_timeout(700)
    check("меню «База знань › Діагнози» перемикає вкладку", fr.locator("#tabDiagnoses.active").count() == 1)
    check("контекст «Редактор › Діагнози»", pg.locator("#sb-ctx").inner_text() == "Редактор › Діагнози", pg.locator("#sb-ctx").inner_text())
    pg.locator(".mtitle", has_text="База знань").click()
    menu("База знань").locator(".mi", has_text="Правила").click(); pg.wait_for_timeout(500)
    fr.locator("#list .item").nth(2).click(); pg.wait_for_timeout(500)
    pg.screenshot(path=IMG + "shell-editor-rule.png")
    fr.locator("#list .item").nth(2).click(button="right"); pg.wait_for_timeout(250)
    items = fr.locator(".ctx div").all_inner_texts()
    check("контекстне меню правила: Відкрити/Вимкнути/Видалити/Довідка", len(items) == 4 and any("Вимкнути" in x for x in items), str(items))
    pg.screenshot(path=IMG + "ctx-rule.png")
    fr.locator(".ctx div", has_text="Вимкнути правило").click(); pg.wait_for_timeout(700)
    en = json.loads(pg.evaluate("fetch('http://localhost:8000/api/rules').then(r=>r.text())"))
    check("«Вимкнути правило» реально змінило дані (enabled=false)", any(r.get("enabled") is False for r in en))
    fr.locator("#list .item").nth(2).click(button="right"); pg.wait_for_timeout(250)
    fr.locator(".ctx div", has_text="Увімкнути правило").click(); pg.wait_for_timeout(500)
    # --- перевірка бази з меню
    pg.locator(".mtitle", has_text="База знань").click()
    menu("База знань").locator(".mi", has_text="Перевірити базу знань").click(); pg.wait_for_timeout(1000)
    check("меню «Перевірити базу знань» запускає перевірку", "total_problems" in fr.locator("#validateResult").inner_text() or fr.locator("#validateResult").inner_text().strip() != "")

    # --- історія
    pg.keyboard.press("Control+2"); pg.wait_for_timeout(1200)
    check("Ctrl+2 відкриває історію прогонів", "logs.html" in pg.locator("#view").get_attribute("src"))
    check("історія показує збережені прогони", fr.locator(".run-row").count() >= 3, f"{fr.locator('.run-row').count()}")
    fr.locator(".run-row").first.click(); pg.wait_for_timeout(500)
    pg.screenshot(path=IMG + "shell-logs.png")
    fr.locator(".run-row").first.click(button="right"); pg.wait_for_timeout(200)
    check("контекстне меню прогону відкрилось", fr.locator(".ctx").count() == 1)
    fr.locator("body").press("Escape")

    # --- Про систему
    pg.locator(".mtitle", has_text="Довідка").click()
    menu("Довідка").locator(".mi", has_text="Про систему").click(); pg.wait_for_timeout(700)
    check("діалог «Про систему» показує склад бази", "113" in pg.locator("#about-body").inner_text(), pg.locator("#about-body").inner_text()[:120])
    pg.screenshot(path=IMG + "dialog-about.png")
    pg.click("#about-ok"); pg.wait_for_timeout(200)
    check("діалог закривається кнопкою OK", "open" not in (pg.locator("#overlay").get_attribute("class") or ""))
    pg.locator(".mtitle", has_text="Система").click()
    menu("Система").locator(".mi", has_text="Перевірити з'єднання").click(); pg.wait_for_timeout(600)
    check("«Перевірити з'єднання» пише результат у рядок стану", "З'єднання" in pg.locator("#sb-hint").inner_text(), pg.locator("#sb-hint").inner_text())

    # --- «Інструкція користувача» (сайт Docsify)
    pg.locator(".mtitle", has_text="Довідка").click()
    check("меню «Довідка» має пункт «Інструкція користувача»", menu("Довідка").locator(".mi", has_text="Інструкція користувача").count() == 1)
    menu("Довідка").locator(".mi", has_text="Інструкція користувача").click(); pg.wait_for_timeout(900)
    check("сайт інструкції не запущено → підказка, як його запустити", "serve_manual.py" in pg.locator("#sb-hint").inner_text(), pg.locator("#sb-hint").inner_text())
    srv = subprocess.Popen([sys.executable, os.path.join(ROOT, "help", "serve_manual.py"), "--no-browser"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    try:
        pg.locator(".mtitle", has_text="Довідка").click()
        with pg.context.expect_page() as pi:
            menu("Довідка").locator(".mi", has_text="Інструкція користувача").click()
        newp = pi.value
        check("сайт інструкції запущено → відкривається нова вкладка на localhost:3000", newp.url.rstrip("/") == "http://localhost:3000", newp.url)
        newp.close()
    finally:
        srv.terminate()

    # --- автономний режим сторінки (без оболонки)
    pg2 = b.new_page(viewport={"width": 1200, "height": 760})
    e2 = []; pg2.on("pageerror", lambda e: e2.append(str(e)))
    pg2.goto(BASE + "diagnose.html"); pg2.wait_for_timeout(1000)
    check("автономна diagnose.html працює без оболонки", pg2.locator(".fact-row").count() >= 3 and not e2, str(e2))
    b.close()

    real_errs = [e for e in errors if "ERR_FILE_NOT_FOUND" not in e and "Failed to load resource" not in e]
    check("немає помилок JS у консолі", not real_errs, str(real_errs[:3]))
ok = sum(1 for _, v in R if v)
print(f"\nПІДСУМОК: {ok}/{len(R)}")
sys.exit(0 if ok == len(R) else 1)
