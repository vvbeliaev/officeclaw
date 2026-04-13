from src.knowledge.adapters.out.docling_normalizer import DoclingNormalizer
from src.knowledge.adapters.out.lightrag_store import LightRAGStore
from src.knowledge.app import KnowledgeApp
from src.shared.config import Settings


def build(settings: Settings) -> KnowledgeApp:
    store = LightRAGStore(settings)
    normalizer = DoclingNormalizer(settings.docling_url)
    return KnowledgeApp(store, normalizer)
