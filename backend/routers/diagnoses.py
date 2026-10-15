from typing import List
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query
from pymongo.errors import DuplicateKeyError
import kb_service
from db import diagnoses_collection
from schemas import DiagnosisSpec, DiagnosisOut
router = APIRouter(prefix='/api/diagnoses', tags=['Діагнози'])

def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc['_id'] = str(doc['_id'])
    return doc

def _oid(mongo_id: str) -> ObjectId:
    try:
        return ObjectId(mongo_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail=f'Некоректний ObjectId: {mongo_id}')

@router.get('', response_model=List[DiagnosisOut], summary='Список діагнозів')
def list_diagnoses(search: str=Query(None)):
    query: dict = {}
    if search:
        query['$or'] = [{'code': {'$regex': search, '$options': 'i'}}, {'name': {'$regex': search, '$options': 'i'}}]
    docs = diagnoses_collection().find(query).sort('name', 1)
    return [_serialize(d) for d in docs]

@router.post('', response_model=DiagnosisOut, status_code=201, summary='Створити діагноз')
def create_diagnosis(d: DiagnosisSpec):
    payload = d.model_dump()
    try:
        result = diagnoses_collection().insert_one(payload)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail=f"Діагноз з кодом '{d.code}' уже існує. Редагуй наявний.")
    kb_service.invalidate_cache()
    return _serialize(diagnoses_collection().find_one({'_id': result.inserted_id}))

@router.put('/{mongo_id}', response_model=DiagnosisOut, summary='Оновити діагноз')
def update_diagnosis(mongo_id: str, d: DiagnosisSpec):
    oid = _oid(mongo_id)
    clash = diagnoses_collection().find_one({'code': d.code, '_id': {'$ne': oid}})
    if clash:
        raise HTTPException(status_code=409, detail=f"Інший діагноз уже має код '{d.code}'")
    result = diagnoses_collection().update_one({'_id': oid}, {'$set': d.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail='Діагноз не знайдено')
    kb_service.invalidate_cache()
    return _serialize(diagnoses_collection().find_one({'_id': oid}))

@router.delete('/{mongo_id}', status_code=204, summary='Видалити діагноз')
def delete_diagnosis(mongo_id: str):
    result = diagnoses_collection().delete_one({'_id': _oid(mongo_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Діагноз не знайдено')
    kb_service.invalidate_cache()
    return None
