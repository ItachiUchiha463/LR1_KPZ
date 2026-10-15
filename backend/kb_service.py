import json
import os
import threading
from typing import Optional
import config
from db import rules_collection, facts_collection, diagnoses_collection
_cache: Optional[dict] = None
_lock = threading.Lock()

def invalidate_cache() -> None:
    global _cache
    with _lock:
        _cache = None

def load_kb_from_db() -> dict:
    facts = {}
    for doc in facts_collection().find():
        name = doc.get('name')
        if not name:
            continue
        spec = {k: v for k, v in doc.items() if k not in ('_id', 'name')}
        facts[name] = spec
    rules = []
    for doc in rules_collection().find().sort([('layer', 1), ('id', 1)]):
        doc.pop('_id', None)
        for cond in doc.get('conditions', []):
            for key in ('value', 'ref_fact', 'factor'):
                if key in cond and cond[key] is None:
                    del cond[key]
        rules.append(doc)
    diagnoses = {}
    for doc in diagnoses_collection().find():
        code = doc.get('code')
        if not code:
            continue
        diagnoses[code] = {k: v for k, v in doc.items() if k not in ('_id', 'code')}
        diagnoses[code]['code'] = code
    return {'facts': facts, 'rules': rules, 'diagnoses': diagnoses}

def get_kb(force_reload: bool=False) -> dict:
    global _cache
    with _lock:
        if _cache is None or force_reload:
            _cache = load_kb_from_db()
        return _cache

def load_kb_from_json() -> dict:
    with open(config.KB_JSON_PATH, encoding='utf-8') as f:
        return json.load(f)
