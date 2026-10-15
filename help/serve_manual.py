# -*- coding: utf-8 -*-
"""
Локальний сервер для сайту інструкції (Docsify).

Docsify читає .md-файли по HTTP, тому відкрити help/src/index.html подвійним
кліком (file://) не вийде. Для завантаження самого Docsify потрібен інтернет
(бібліотека підключається з CDN).

Запуск:  python help/serve_manual.py [--port 3000] [--no-browser]
Сайт:    http://localhost:3000
"""
import argparse
import functools
import http.server
import os
import sys
import webbrowser

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")


class Handler(http.server.SimpleHTTPRequestHandler):
    # явні типи з UTF-8: у Windows реєстр інколи віддає .js як text/plain, а .md як невідомий тип
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".md": "text/markdown; charset=utf-8", ".html": "text/html; charset=utf-8",
                      ".js": "application/javascript; charset=utf-8", ".css": "text/css; charset=utf-8"}


def main():
    ap = argparse.ArgumentParser(description="Сервер сайту інструкції (Docsify)")
    ap.add_argument("--port", type=int, default=3000)
    ap.add_argument("--no-browser", action="store_true", help="не відкривати браузер автоматично")
    args = ap.parse_args()
    handler = functools.partial(Handler, directory=SRC)
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    except OSError as e:
        print(f"Не вдалося зайняти порт {args.port}: {e}\nСпробуйте інший: python help/serve_manual.py --port 3001")
        return 1
    url = f"http://localhost:{args.port}"
    print(f"Інструкція: {url}\nЗупинити: Ctrl+C")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nЗупинено.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
