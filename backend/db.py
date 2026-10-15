from typing import Optional
from pymongo import MongoClient, ASCENDING
from pymongo.server_api import ServerApi
import config
_client: Optional[MongoClient] = None

def get_client() -> MongoClient:
    global _client
    if _client is None:
        if config.MONGO_URI.startswith('mongodb+srv://'):
            _client = MongoClient(config.MONGO_URI, server_api=ServerApi('1'), serverSelectionTimeoutMS=8000)
        else:
            _client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client

def get_db():
    return get_client()[config.MONGO_DB]

def rules_collection():
    return get_db()['rules']

def facts_collection():
    return get_db()['facts']

def runs_collection():
    return get_db()['runs']

def diagnoses_collection():
    return get_db()['diagnoses']

def ensure_indexes() -> None:
    rules_collection().create_index([('id', ASCENDING)], unique=True)
    rules_collection().create_index([('branch', ASCENDING), ('layer', ASCENDING)])
    facts_collection().create_index([('name', ASCENDING)], unique=True)
    runs_collection().create_index([('created_at', ASCENDING)])
    diagnoses_collection().create_index([('code', ASCENDING)], unique=True)

def ping() -> tuple:
    try:
        get_client().admin.command('ping')
        return (True, f'Підключено до {config.MONGO_DB}')
    except Exception as exc:
        return (False, f'{type(exc).__name__}: {exc}')
