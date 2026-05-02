# semantic_search/embedder.py

import logging
import os
from typing import Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


# OpenRouter defaults (preserve backward compatibility)
DEFAULT_MODEL = "google/gemini-embedding-001"
DEFAULT_DIMENSION = 3072

# Local provider defaults — Ollama with nomic-embed-text out of the box.
# Override via LOCAL_EMBEDDING_BASE_URL / LOCAL_EMBEDDING_MODEL /
# LOCAL_EMBEDDING_DIMENSION when using a different server or model
# (e.g. llama.cpp's server, vLLM, LM Studio, or a different Ollama model
# such as bge-m3 — better for Turkish — at 1024 dimensions).
LOCAL_DEFAULT_BASE_URL = "http://localhost:11434/v1"
LOCAL_DEFAULT_MODEL = "nomic-embed-text"
LOCAL_DEFAULT_DIMENSION = 768


def is_openrouter_available() -> bool:
    """Check if OpenRouter API key is available."""
    return bool(os.getenv("OPENROUTER_API_KEY"))


def is_local_embedding_configured() -> bool:
    """Check if the user opted into a local embedding endpoint."""
    return os.getenv("EMBEDDING_PROVIDER", "").strip().lower() == "local"


def is_semantic_search_available() -> bool:
    """Returns True if any embedding provider is configured."""
    return is_local_embedding_configured() or is_openrouter_available()


def _coerce_dimension(value, env_name: str, default: int) -> int:
    """Parse a dimension value (int or str) with clear error messages."""
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as e:
        raise ValueError(
            f"{env_name} must be an integer, got {value!r}"
        ) from e
    if parsed <= 0:
        raise ValueError(f"Embedding dimension must be positive, got {parsed}")
    return parsed


class _BaseOpenAICompatibleEmbedder:
    """
    Shared encode/similarity logic for embedders backed by the OpenAI Python
    SDK. Subclasses configure ``client``, ``model``, ``dimension``, and
    optionally ``_extra_headers`` (e.g. OpenRouter ranking headers).
    """

    # Subclasses may override; sent on every embeddings.create call when set.
    _extra_headers: Dict[str, str] = {}

    # Set by subclasses
    client = None
    model: str = ""
    dimension: int = 0

    def encode_query(self, query: str, task: str = "search result") -> np.ndarray:
        """
        Encode a search query.

        Args:
            query: The search query text
            task: Task type for prompt template

        Returns:
            Numpy array of embeddings (``self.dimension`` elements).
        """
        text = f"task: {task} | query: {query}"

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float",
                extra_headers=self._extra_headers or None,
            )

            embedding = np.array(response.data[0].embedding, dtype=np.float32)

            # L2 normalize for cosine similarity
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            logger.debug(f"Encoded query: {query[:50]}... -> shape: {embedding.shape}")
            return embedding

        except Exception as e:
            logger.error(f"Failed to encode query: {e}")
            raise

    def encode_documents(self, documents: List[str], titles: Optional[List[str]] = None) -> np.ndarray:
        """
        Encode multiple documents with a batch API call.

        Args:
            documents: List of document texts
            titles: Optional list of document titles

        Returns:
            Numpy array of embeddings (N x ``self.dimension``).
        """
        if not documents:
            return np.array([])

        texts = []
        for i, doc in enumerate(documents):
            title = titles[i] if titles and i < len(titles) else "none"
            texts.append(f"title: {title} | text: {doc}")

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float",
                extra_headers=self._extra_headers or None,
            )

            embeddings = np.array(
                [d.embedding for d in sorted(response.data, key=lambda x: x.index)],
                dtype=np.float32,
            )

            # L2 normalize each embedding for cosine similarity
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / (norms + 1e-8)

            logger.info(f"Encoded {len(documents)} documents -> shape: {embeddings.shape}")
            return embeddings

        except Exception as e:
            logger.error(f"Failed to encode documents: {e}")
            raise

    def compute_similarity(self, query_embedding: np.ndarray, document_embeddings: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarity between query and documents.

        Args:
            query_embedding: Query embedding (``self.dimension``,)
            document_embeddings: Document embeddings (N x ``self.dimension``)

        Returns:
            Similarity scores (N,)
        """
        if len(query_embedding.shape) == 1:
            query_embedding = query_embedding.reshape(1, -1)

        # Embeddings are already L2-normalized.
        similarities = np.dot(document_embeddings, query_embedding.T).squeeze()
        return similarities


class OpenRouterEmbedder(_BaseOpenAICompatibleEmbedder):
    """
    Embedder using OpenRouter's embedding API.

    The model and dimension are configurable so users can pick any OpenRouter
    embedding model (e.g. when one becomes paid). Configuration precedence:
    explicit constructor args > environment variables > defaults.

    Environment variables:
        OPENROUTER_API_KEY (required): OpenRouter credential
        OPENROUTER_EMBEDDING_MODEL (optional): override the embedding model id
        OPENROUTER_EMBEDDING_DIMENSION (optional): override the vector size

    Defaults preserve backward compatibility: ``google/gemini-embedding-001``
    at 3072 dimensions.
    """

    _extra_headers = {
        "HTTP-Referer": "https://yargimcp.com",
        "X-Title": "Yargi MCP Server",
    }

    def __init__(self, model: Optional[str] = None, dimension: Optional[int] = None):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is not set")

        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package is required. Install with: pip install openai")

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model = model or os.getenv("OPENROUTER_EMBEDDING_MODEL") or DEFAULT_MODEL
        self.dimension = _coerce_dimension(
            dimension if dimension is not None else os.getenv("OPENROUTER_EMBEDDING_DIMENSION"),
            "OPENROUTER_EMBEDDING_DIMENSION",
            DEFAULT_DIMENSION,
        )

        logger.info(
            f"OpenRouter Embedder initialized with model: {self.model} "
            f"(dimension={self.dimension})"
        )


class LocalEmbedder(_BaseOpenAICompatibleEmbedder):
    """
    Embedder for a local OpenAI-compatible embedding server — Ollama,
    llama.cpp, vLLM, LM Studio, etc. Zero new Python dependencies; just
    point the existing OpenAI SDK at a local base URL.

    Environment variables:
        EMBEDDING_PROVIDER=local              (selects this provider)
        LOCAL_EMBEDDING_BASE_URL              (default: http://localhost:11434/v1)
        LOCAL_EMBEDDING_MODEL                 (default: nomic-embed-text)
        LOCAL_EMBEDDING_DIMENSION             (default: 768)
        LOCAL_EMBEDDING_API_KEY               (optional; ignored by most local servers)

    Setup (Ollama):
        $ ollama serve
        $ ollama pull nomic-embed-text          # or bge-m3 for better Turkish

    The dimension MUST match the model's actual output size (e.g. 768 for
    nomic-embed-text, 1024 for bge-m3, 1024 for mxbai-embed-large).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        dimension: Optional[int] = None,
        api_key: Optional[str] = None,
    ):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package is required. Install with: pip install openai")

        self.base_url = (
            base_url
            or os.getenv("LOCAL_EMBEDDING_BASE_URL")
            or LOCAL_DEFAULT_BASE_URL
        )
        # Most local servers don't validate the key — use a placeholder so
        # the OpenAI SDK doesn't error on the missing-key check.
        effective_key = (
            api_key
            or os.getenv("LOCAL_EMBEDDING_API_KEY")
            or "no-key-needed"
        )

        self.client = OpenAI(base_url=self.base_url, api_key=effective_key)
        self.model = model or os.getenv("LOCAL_EMBEDDING_MODEL") or LOCAL_DEFAULT_MODEL
        self.dimension = _coerce_dimension(
            dimension if dimension is not None else os.getenv("LOCAL_EMBEDDING_DIMENSION"),
            "LOCAL_EMBEDDING_DIMENSION",
            LOCAL_DEFAULT_DIMENSION,
        )

        logger.info(
            f"Local Embedder initialized: model={self.model} "
            f"base_url={self.base_url} dimension={self.dimension}"
        )


def get_embedder():
    """
    Factory that picks the embedder based on EMBEDDING_PROVIDER.

    - ``EMBEDDING_PROVIDER=local`` -> ``LocalEmbedder``
    - otherwise -> ``OpenRouterEmbedder`` (requires OPENROUTER_API_KEY)

    Raises:
        ValueError: If no provider is configured (neither local nor OpenRouter).
    """
    if is_local_embedding_configured():
        return LocalEmbedder()
    if is_openrouter_available():
        return OpenRouterEmbedder()
    raise ValueError(
        "No embedding provider configured. Set OPENROUTER_API_KEY for hosted "
        "embeddings, or EMBEDDING_PROVIDER=local (with LOCAL_EMBEDDING_* "
        "env vars) for a local OpenAI-compatible server like Ollama."
    )
