from src.knowledge.adapters.out.lightrag_store import LightRAGStore
from src.knowledge.app import KnowledgeApp
from src.shared.config import Settings


def build(settings: Settings) -> KnowledgeApp:
    store = LightRAGStore(settings)
    return KnowledgeApp(store)
