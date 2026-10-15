# -*- coding: utf-8 -*-
"""
Будує графічну модель інтерфейсу з ОДНОГО списку зв'язків:
  img/dialog_tree.png         - дерево діалогу (склад і вкладеність компонентів)
  img/dialog_transitions.png  - мережа переходів між екранами (ребра підписані подією)
  dialog_grid.md              - сітка переходів (матриця «звідки → куди»)
Запуск:  python build_dialog_tree.py   (потрібен Graphviz: команда dot)
"""
import os
import subprocess
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "img")

# id: (підпис, тип, група для сітки)
NODES = OrderedDict([
    ("S0", ("Головне вікно\\n(меню, рядок стану)", "shell", "Головне вікно")),
    ("M1", ("Меню «Система»", "menu", "Головне вікно")),
    ("M2", ("Меню «База знань»", "menu", "Головне вікно")),
    ("M3", ("Меню «Діагностика»", "menu", "Головне вікно")),
    ("M4", ("Меню «Довідка»", "menu", "Головне вікно")),
    ("P1", ("Сторінка\\n«Діагностика»", "page", "Діагностика")),
    ("P1a", ("Панель додавання\\nпоказника", "panel", "Діагностика")),
    ("P1b", ("Результат\\nдіагностики", "panel", "Діагностика")),
    ("P2", ("Сторінка\\n«Історія прогонів»", "page", "Історія прогонів")),
    ("P2a", ("Деталі прогону", "panel", "Історія прогонів")),
    ("P3", ("Сторінка «Редактор\\nбази знань»", "page", "Редактор")),
    ("P3a", ("Вкладка «Правила»", "panel", "Редактор")),
    ("P3b", ("Вкладка «Факти»", "panel", "Редактор")),
    ("P3c", ("Вкладка «Діагнози»", "panel", "Редактор")),
    ("P3d", ("Форма елемента\\n(правило / факт / діагноз)", "panel", "Редактор")),
    ("P3e", ("Результат перевірки\\nбази знань", "panel", "Редактор")),
    ("H", ("Сайт інструкції\\n(Docsify, нова вкладка)", "help", "Довідка")),
    ("D1", ("Діалог\\n«Про систему»", "dialog", "Про систему")),
    ("D2", ("Діалог підтвердження\\nвидалення", "dialog", "Підтвердження видалення")),
    ("C1", ("Контекстне меню\\nсписку (редактор)", "ctx", "Контекстне меню")),
    ("C2", ("Контекстне меню\\nпоказника", "ctx", "Контекстне меню")),
    ("C3", ("Контекстне меню\\nпрогону", "ctx", "Контекстне меню")),
])

EDGES = [
    ("S0", "P1", "старт програми"),
    ("S0", "M1", "клік по меню"), ("S0", "M2", "клік по меню"),
    ("S0", "M3", "клік по меню"), ("S0", "M4", "клік по меню"),
    ("S0", "H", "F1 · меню"),
    ("M1", "P1", "Ctrl+1"), ("M1", "P2", "Ctrl+2"), ("M1", "P3", "Ctrl+3"),
    ("M1", "S0", "Перевірити з'єднання"),
    ("M2", "P3a", "Правила"), ("M2", "P3b", "Факти"), ("M2", "P3c", "Діагнози"),
    ("M2", "P3e", "Перевірити базу знань"),
    ("M3", "P1", "Нова діагностика · Готові приклади"), ("M3", "P2", "Історія прогонів"),
    ("M4", "H", "Інструкція користувача · F1"),
    ("M4", "D1", "Про систему"),
    ("D1", "S0", "OK · Esc"),
    ("P1", "P1a", "+ Додати показник"), ("P1a", "P1", "Додати · Скасувати"),
    ("P1", "P1b", "Діагностувати"),
    ("P1", "C2", "права кнопка"), ("C2", "P1", "Видалити показник"),
    ("P1", "H", "F1 · «?»"),
    ("P2", "P2a", "клік по прогону"), ("P2", "C3", "права кнопка"),
    ("C3", "P2a", "Відкрити прогін"), ("P2", "H", "F1 · «?»"),
    ("P3", "P3a", "вкладка"), ("P3", "P3b", "вкладка"), ("P3", "P3c", "вкладка"),
    ("P3a", "P3d", "клік по правилу · + Створити"), ("P3b", "P3d", "клік по факту · + Створити"),
    ("P3c", "P3d", "клік по діагнозу · + Створити"),
    ("P3d", "D2", "Видалити"), ("D2", "P3", "Так · Ні"),
    ("P3a", "C1", "права кнопка"), ("P3b", "C1", "права кнопка"), ("P3c", "C1", "права кнопка"),
    ("C1", "P3d", "Відкрити"), ("C1", "D2", "Видалити…"), ("C1", "P3a", "Вимкнути / Увімкнути правило"),
    ("C1", "H", "Довідка про розділ"),
    ("P3", "P3e", "Перевірити базу знань"), ("P3", "H", "F1 · «?»"),
]

STYLE = {
    "shell": 'shape=box, style="filled,bold", fillcolor="#1f3a5f", fontcolor=white',
    "menu": 'shape=box, style=filled, fillcolor="#c7d8ef"',
    "page": 'shape=box, style="filled,rounded", fillcolor="#bfe3c8"',
    "panel": 'shape=box, style="filled,rounded", fillcolor="#e3f3e7"',
    "help": 'shape=box, style="filled,rounded", fillcolor="#d9cdf0"',
    "popup": 'shape=note, style=filled, fillcolor="#fff3b0"',
    "dialog": 'shape=box, style="filled", fillcolor="#f9d3a8"',
    "ctx": 'shape=box, style="filled,dashed", fillcolor="#e6e6e6"',
}


def render(name, dot_src):
    dot_path = os.path.join(IMG, name + ".dot")
    open(dot_path, "w", encoding="utf-8").write(dot_src)
    for fmt, extra in (("png", ["-Gdpi=110"]), ("pdf", [])):
        subprocess.run(["dot", "-T" + fmt, dot_path, "-o", os.path.join(IMG, f"{name}.{fmt}")] + extra, check=True)


def transitions():
    merged = OrderedDict()
    for s, d, lab in EDGES:
        merged.setdefault((s, d), []).append(lab)
    out = ['digraph T {', 'rankdir=LR; nodesep=0.35; ranksep=0.9; splines=true; overlap=false;',
           'node [fontname="DejaVu Sans", fontsize=10]; edge [fontname="DejaVu Sans", fontsize=8, color="#666666", arrowsize=0.6];']
    for nid, (label, kind, _) in NODES.items():
        out.append(f'"{nid}" [label="{label}", {STYLE[kind]}];')
    for (s, d), labs in merged.items():
        lab = "\\n".join(labs)  # у dot розрив рядка - це \n; підписи не починаємо зі слеша
        out.append('"%s" -> "%s" [label="%s"];' % (s, d, lab))
    out.append("}")
    render("dialog_transitions", "\n".join(out))
    return merged


def tree():
    menu_items = {
        "M1": ["Діагностика (Ctrl+1)", "Історія прогонів (Ctrl+2)", "Редактор бази знань (Ctrl+3)", "Перевірити з'єднання", "Оновити вікно (F5)"],
        "M2": ["Правила", "Факти", "Діагнози", "Перевірити базу знань"],
        "M3": ["Нова діагностика", "Готові приклади ▸", "Історія прогонів"],
        "M4": ["Інструкція користувача (F1)", "Про систему"],
    }
    out = ['digraph G {', 'rankdir=LR; nodesep=0.12; ranksep=0.5; splines=ortho;',
           'node [fontname="DejaVu Sans", fontsize=10, shape=box, style="filled,rounded", fillcolor="#f2f2ee"]; edge [arrowhead=none, color="#888888"];']
    def n(i, label, kind=None):
        st = STYLE.get(kind, "") if kind else ""
        out.append(f'"{i}" [label="{label}"{", " + st if st else ""}];')
    n("root", "Головне вікно", "shell")
    n("bar", "Рядок меню", "menu"); n("area", "Робоча область", "page"); n("dl", "Діалоги", "dialog"); n("sb", "Рядок стану")
    for c in ("bar", "area", "dl", "sb"):
        out.append(f'"root" -> "{c}";')
    for m in ("M1", "M2", "M3", "M4"):
        n(m, NODES[m][0].replace("Меню ", ""), "menu"); out.append(f'"bar" -> "{m}";')
        for k, it in enumerate(menu_items[m]):
            n(f"{m}i{k}", it); out.append(f'"{m}" -> "{m}i{k}";')
    n("Mex", "Усе в нормі · Витік памʼяті · Кілька проблем")
    out.append('"M3i1" -> "Mex";')
    for p, ch in (("P1", ["P1a", "P1b", "C2"]), ("P2", ["P2a", "C3"]), ("P3", ["P3a", "P3b", "P3c", "P3d", "P3e", "C1"])):
        n(p, NODES[p][0].replace("\\n", " "), "page"); out.append(f'"area" -> "{p}";')
        for c in ch:
            n(c, NODES[c][0].replace("\\n", " "), NODES[c][1]); out.append(f'"{p}" -> "{c}";')
    n("site", "Сайт інструкції (Docsify)", "help"); out.append('"root" -> "site";')
    n("Da", "Про систему", "dialog"); n("Dd", "Підтвердження видалення", "dialog")
    out.append('"dl" -> "Da"; "dl" -> "Dd";')
    out.append("}")
    render("dialog_tree", "\n".join(out))


def grid(merged):
    groups = list(OrderedDict.fromkeys(v[2] for v in NODES.values()))
    cell = {}
    for (s, d), labs in merged.items():
        gs, gd = NODES[s][2], NODES[d][2]
        cell.setdefault((gs, gd), [])
        for l in labs:
            if l not in cell[(gs, gd)]:
                cell[(gs, gd)].append(l)
    short = {g: g for g in groups}
    lines = ["| Звідки ↓ / Куди → | " + " | ".join(short[g] for g in groups) + " |",
             "|" + "---|" * (len(groups) + 1)]
    for gs in groups:
        row = [f"**{gs}**"]
        for gd in groups:
            row.append("; ".join(cell.get((gs, gd), [])) or "—")
        lines.append("| " + " | ".join(row) + " |")
    open(os.path.join(HERE, "dialog_grid.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return len(groups), sum(1 for v in cell.values() if v)


if __name__ == "__main__":
    os.makedirs(IMG, exist_ok=True)
    merged = transitions()
    tree()
    g, filled = grid(merged)
    print(f"вузлів: {len(NODES)}, зв'язків: {len(EDGES)} (унікальних пар: {len(merged)}); сітка {g}×{g}, заповнених клітинок: {filled}")
