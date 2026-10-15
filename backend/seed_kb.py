import json
import os
import sys
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
import config
from db import rules_collection, facts_collection, diagnoses_collection, ensure_indexes

def seed(force: bool=False) -> None:
    with open(config.KB_JSON_PATH, encoding='utf-8') as f:
        kb = json.load(f)
    rc, fc, dc = (rules_collection(), facts_collection(), diagnoses_collection())
    existing = rc.count_documents({})
    if existing > 0 and (not force):
        answer = input(f'У колекції rules вже є {existing} документів. Очистити facts/rules/diagnoses й перезаписати? (y/n): ')
        if answer.lower() != 'y':
            print('Скасовано.')
            return
    rc.delete_many({})
    fc.delete_many({})
    dc.delete_many({})
    fact_docs = [{'name': name, **spec} for name, spec in kb['facts'].items()]
    diagnosis_docs = [{'code': code, **spec} for code, spec in kb.get('diagnoses', {}).items()]
    if fact_docs:
        fc.insert_many(fact_docs)
    if kb['rules']:
        rc.insert_many(kb['rules'])
    if diagnosis_docs:
        dc.insert_many(diagnosis_docs)
    ensure_indexes()
    print(f'Імпортовано: {len(fact_docs)} фактів, {len(kb['rules'])} правил, {len(diagnosis_docs)} діагнозів у довіднику.')
    print(f'База даних: {config.MONGO_DB}')
if __name__ == '__main__':
    force = '--force' in sys.argv
    seed(force=force)
