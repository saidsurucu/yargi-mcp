# semantic_search/__init__.py

from .embedder import (
    OpenRouterEmbedder,
    LocalEmbedder,
    get_embedder,
    is_openrouter_available,
    is_local_embedding_configured,
    is_semantic_search_available,
)
from .vector_store import VectorStore
from .processor import DocumentProcessor

__all__ = [
    'OpenRouterEmbedder',
    'LocalEmbedder',
    'get_embedder',
    'is_openrouter_available',
    'is_local_embedding_configured',
    'is_semantic_search_available',
    'VectorStore',
    'DocumentProcessor',
]
