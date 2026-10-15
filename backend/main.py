import os
import sys
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import config
from db import ensure_indexes
from routers import rules, facts, diagnoses, kb, health, diagnose, runs
app = FastAPI(title='Експертна система діагностики серверів — API бази знань', description='REST API для редактора бази знань (правила, факти, нейронні вузли) поверх MongoDB. Машина виводу читає цю ж базу знань окремим модулем inference_engine, тут вона використовується лише для статичної перевірки (/api/kb/validate).', version='2.0')
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=['*'], allow_headers=['*'])
app.include_router(health.router)
app.include_router(rules.router)
app.include_router(facts.router)
app.include_router(diagnoses.router)
app.include_router(kb.router)
app.include_router(diagnose.router)
app.include_router(runs.router)

@app.on_event('startup')
def on_startup():
    try:
        ensure_indexes()
    except Exception as exc:
        print(f'[startup] Не вдалося створити індекси MongoDB: {exc}')

@app.get('/', include_in_schema=False)
def root():
    return {'service': 'expert-system-kb-api', 'docs': '/docs', 'health': '/api/health'}
