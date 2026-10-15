from fastapi import APIRouter
import kb_service
from inference_engine.engine import InferenceEngine
router = APIRouter(prefix='/api/kb', tags=['База знань'])

@router.get('/validate', summary='Статична перевірка бази знань')
def validate_kb():
    kb = kb_service.get_kb()
    engine = InferenceEngine(kb)
    return engine.validate_knowledge_base()

@router.post('/reload', summary='Скинути кеш бази знань')
def reload_kb():
    kb_service.invalidate_cache()
    kb = kb_service.get_kb(force_reload=True)
    return {'reloaded': True, 'rules': len(kb['rules']), 'facts': len(kb['facts'])}
