from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query
import kb_service
from db import runs_collection
from inference_engine.engine import InferenceEngine
from schemas import DiagnoseRequest, DiagnoseResponse, RunSummary, RunDetail
router = APIRouter(prefix='/api', tags=['Діагностика'])

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

@router.post('/diagnose', response_model=DiagnoseResponse, summary='Запустити діагностику')
def diagnose(req: DiagnoseRequest):
    kb = kb_service.get_kb()
    engine = InferenceEngine(kb)
    result = engine.run(req.facts)
    payload = result.to_dict()
    if not req.include_trace:
        payload['trace'] = []
    run_id = None
    if req.save_run:
        doc = {'label': req.label or '(без підпису)', 'created_at': _now_iso(), 'input_facts': req.facts, 'result': payload}
        inserted = runs_collection().insert_one(doc)
        run_id = str(inserted.inserted_id)
    payload['run_id'] = run_id
    return payload

@router.get('/diagnose/explain', summary='Пояснити ланцюжок для факту з уже готового результату')
def explain_from_facts(target_fact: str=Query('діагноз')):
    kb = kb_service.get_kb()
    facts_producing = [r['id'] for r in kb['rules'] if any((c['fact'] == target_fact for c in r.get('conclusions', [])))]
    return {'target_fact': target_fact, 'rules_that_can_produce_it': facts_producing, 'note': "Повний ланцюжок конкретного прогону дивіться в полі 'trace' відповіді POST /api/diagnose"}
