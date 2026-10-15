import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB = os.environ.get('MONGO_DB', 'expert_system')
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_JSON_PATH = os.path.join(PROJECT_ROOT, 'data', 'knowledge_base.json')
