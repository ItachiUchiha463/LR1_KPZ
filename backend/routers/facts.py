from typing import List, Optional
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query
from pymongo.errors import DuplicateKeyError
import kb_service
from db import facts_collection
from schemas import FactSpec, FactOut
router = APIRouter(prefix='/api/facts', tags=['Факти'])

def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc['_id'] = str(doc['_id'])
    return doc

def _oid(mongo_id: str) -> ObjectId:
    try:
        return ObjectId(mongo_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail=f'Некоректний ObjectId: {mongo_id}')

@router.get('', response_model=List[FactOut], summary='Список фактів')
def list_facts(kind: Optional[str]=Query(None, description='raw / derived / neural'), search: Optional[str]=Query(None)):
    query: dict = {}
    if kind:
        query['kind'] = kind
    if search:
        query['$or'] = [{'name': {'$regex': search, '$options': 'i'}}, {'note': {'$regex': search, '$options': 'i'}}]
    docs = facts_collection().find(query).sort('name', 1)
    return [_serialize(d) for d in docs]

@router.post('', response_model=FactOut, status_code=201, summary='Створити факт')
def create_fact(fact: FactSpec):
    payload = fact.model_dump(exclude_none=True)
    try:
        result = facts_collection().insert_one(payload)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail=f"Факт '{fact.name}' уже існує. Редагуйте наявний замість створення нового.")
    kb_service.invalidate_cache()
    return _serialize(facts_collection().find_one({'_id': result.inserted_id}))

@router.put('/{mongo_id}', response_model=FactOut, summary='Оновити факт')
def update_fact(mongo_id: str, fact: FactSpec):
    oid = _oid(mongo_id)
    clash = facts_collection().find_one({'name': fact.name, '_id': {'$ne': oid}})
    if clash:
        raise HTTPException(status_code=409, detail=f"Інший факт уже має назву '{fact.name}'")
    full_dump = fact.model_dump()
    to_set = {k: v for k, v in full_dump.items() if v is not None}
    to_unset = {k: '' for k, v in full_dump.items() if v is None}
    update_ops = {'$set': to_set}
    if to_unset:
        update_ops['$unset'] = to_unset
    result = facts_collection().update_one({'_id': oid}, update_ops)
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail='Факт не знайдено')
    kb_service.invalidate_cache()
    return _serialize(facts_collection().find_one({'_id': oid}))

@router.delete('/{mongo_id}', status_code=204, summary='Видалити факт')
def delete_fact(mongo_id: str):
    result = facts_collection().delete_one({'_id': _oid(mongo_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Факт не знайдено')
    kb_service.invalidate_cache()
    return None
