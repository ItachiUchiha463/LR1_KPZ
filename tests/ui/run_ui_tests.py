"""
Запуск усіх UI-тестів: піднімає тестовий бекенд, проганяє test_manual.py і test_shell.py, зупиняє бекенд.

Потрібно:  pip install playwright  і  playwright install chromium
Запуск:    python tests/ui/run_ui_tests.py
Увага: порт 8000 має бути вільним (зупиніть справжній uvicorn).
"""
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
server = subprocess.Popen([sys.executable, os.path.join(HERE, "mock_api.py")])
rc = 0
try:
    for _ in range(60):
        try:
            urllib.request.urlopen("http://localhost:8000/api/health", timeout=1)
            break
        except Exception:
            time.sleep(0.25)
    for name in ("test_manual.py", "test_shell.py"):
        print("=" * 60, "\n", name, "\n" + "=" * 60)
        rc |= subprocess.call([sys.executable, os.path.join(HERE, name)])
finally:
    server.terminate()
sys.exit(rc)
