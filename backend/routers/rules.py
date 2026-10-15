from typing import List, Optional
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query
from pymongo.errors import DuplicateKeyError
import kb_service
from db import rules_collection
from schemas import RuleBase, RuleOut
router = APIRouter(prefix='/api/rules', tags=['Правила'])

def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc['_id'] = str(doc['_id'])
    return doc

def _oid(mongo_id: str) -> ObjectId:
    try:
        return ObjectId(mongo_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail=f'Некоректний ObjectId: {mongo_id}')

@router.get('', response_model=List[RuleOut], summary='Список правил')
def list_rules(branch: Optional[str]=Query(None, description='Фільтр за гілкою'), layer: Optional[int]=Query(None, description='Фільтр за шаром'), search: Optional[str]=Query(None, description='Пошук у id / тексті / примітці'), enabled_only: bool=Query(False, description='Лише увімкнені правила')):
    query: dict = {}
    if branch:
        query['branch'] = branch
    if layer is not None:
        query['layer'] = layer
    if enabled_only:
        query['enabled'] = True
    if search:
        query['$or'] = [{'id': {'$regex': search, '$options': 'i'}}, {'text': {'$regex': search, '$options': 'i'}}, {'note': {'$regex': search, '$options': 'i'}}]
    docs = rules_collection().find(query).sort([('layer', 1), ('id', 1)])
    return [_serialize(d) for d in docs]

@router.post('', response_model=RuleOut, status_code=201, summary='Створити правило')
def create_rule(rule: RuleBase):
    payload = rule.model_dump(exclude_none=True)
    try:
        result = rules_collection().insert_one(payload)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail=f"Правило з id '{rule.id}' уже існує. Оберіть інший id.")
    kb_service.invalidate_cache()
    return _serialize(rules_collection().find_one({'_id': result.inserted_id}))

@router.get('/{mongo_id}', response_model=RuleOut, summary='Одне правило')
def get_rule(mongo_id: str):
    doc = rules_collection().find_one({'_id': _oid(mongo_id)})
    if not doc:
        raise HTTPException(status_code=404, detail='Правило не знайдено')
    return _serialize(doc)

@router.put('/{mongo_id}', response_model=RuleOut, summary='Оновити правило')
def update_rule(mongo_id: str, rule: RuleBase):
    oid = _oid(mongo_id)
    payload = rule.model_dump(exclude_none=True)
    clash = rules_collection().find_one({'id': rule.id, '_id': {'$ne': oid}})
    if clash:
        raise HTTPException(status_code=409, detail=f"Інше правило вже використовує id '{rule.id}'")
    result = rules_collection().update_one({'_id': oid}, {'$set': payload})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail='Правило не знайдено')
    kb_service.invalidate_cache()
    return _serialize(rules_collection().find_one({'_id': oid}))

@router.delete('/{mongo_id}', status_code=204, summary='Видалити правило')
def delete_rule(mongo_id: str):
    result = rules_collection().delete_one({'_id': _oid(mongo_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Правило не знайдено')
    kb_service.invalidate_cache()
    return None

@router.post('/{mongo_id}/toggle', response_model=RuleOut, summary='Увімкнути / вимкнути правило')
def toggle_rule(mongo_id: str):
    oid = _oid(mongo_id)
    doc = rules_collection().find_one({'_id': oid})
    if not doc:
        raise HTTPException(status_code=404, detail='Правило не знайдено')
    new_state = not doc.get('enabled', True)
    rules_collection().update_one({'_id': oid}, {'$set': {'enabled': new_state}})
    kb_service.invalidate_cache()
    return _serialize(rules_collection().find_one({'_id': oid}))
