# semantic_search/__init__.py

from .embedder import OpenRouterEmbedder, is_openrouter_available
from .vector_store import VectorStore
from .processor import DocumentProcessor

__all__ = ['OpenRouterEmbedder', 'is_openrouter_available', 'VectorStore', 'DocumentProcessor']
