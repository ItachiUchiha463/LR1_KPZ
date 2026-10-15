from typing import List, Optional
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query
from db import runs_collection
from schemas import RunSummary, RunDetail
router = APIRouter(prefix='/api/runs', tags=['Історія прогонів'])

def _oid(mongo_id: str) -> ObjectId:
    try:
        return ObjectId(mongo_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail=f'Некоректний ObjectId: {mongo_id}')

@router.get('', response_model=List[RunSummary], summary='Список прогонів')
def list_runs(limit: int=Query(50, ge=1, le=500)):
    docs = runs_collection().find().sort('created_at', -1).limit(limit)
    summaries = []
    for d in docs:
        result = d.get('result', {})
        summaries.append({'_id': str(d['_id']), 'label': d.get('label', ''), 'created_at': d.get('created_at', ''), 'diagnoses': result.get('diagnoses', []), 'diagnoses_detail': result.get('diagnoses_detail', []), 'severity': result.get('severity'), 'has_conflicts': bool(result.get('conflicts'))})
    return summaries

@router.get('/{mongo_id}', response_model=RunDetail, summary='Деталі одного прогону')
def get_run(mongo_id: str):
    doc = runs_collection().find_one({'_id': _oid(mongo_id)})
    if not doc:
        raise HTTPException(status_code=404, detail='Прогін не знайдено')
    result = dict(doc.get('result', {}))
    result['label'] = doc.get('label', '')
    result['created_at'] = doc.get('created_at', '')
    result.setdefault('run_id', str(doc['_id']))
    return result
