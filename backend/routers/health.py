import os
from collections import Counter
from fastapi import APIRouter
import config
import db
from db import rules_collection, facts_collection
from schemas import HealthOut, StatsOut
router = APIRouter(prefix='/api', tags=['Стан системи'])

@router.get('/health', response_model=HealthOut, summary="Перевірка з'єднання")
def health():
    ok, message = db.ping()
    rules_count = None
    if ok:
        try:
            rules_count = rules_collection().count_documents({})
        except Exception:
            rules_count = None
    return {'api': True, 'mongo_connected': ok, 'mongo_message': message, 'rules_in_db': rules_count}

@router.get('/stats', response_model=StatsOut, summary='Статистика бази знань')
def stats():
    rules = list(rules_collection().find({}, {'branch': 1, 'layer': 1, 'enabled': 1}))
    by_branch = Counter((r.get('branch', '?') for r in rules))
    by_layer = Counter((str(r.get('layer', '?')) for r in rules))
    disabled = sum((1 for r in rules if not r.get('enabled', True)))
    return {'rule_count': len(rules), 'fact_count': facts_collection().count_documents({}), 'branches': sorted(by_branch.keys()), 'rules_per_branch': dict(by_branch), 'rules_per_layer': dict(by_layer), 'disabled_rules': disabled}
