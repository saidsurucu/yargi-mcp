# semantic_search/embedder.py

import logging
import os
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)


DEFAULT_MODEL = "google/gemini-embedding-001"
DEFAULT_DIMENSION = 3072


def is_openrouter_available() -> bool:
    """Check if OpenRouter API key is available."""
    return bool(os.getenv("OPENROUTER_API_KEY"))


class OpenRouterEmbedder:
    """
    Embedder using OpenRouter's embedding API.

    The model and dimension are configurable so users can pick any OpenRouter
    embedding model (e.g. when one becomes paid or when a different model fits
    the budget better). Configuration precedence: explicit constructor args >
    environment variables > defaults.

    Environment variables:
        OPENROUTER_API_KEY (required): OpenRouter credential
        OPENROUTER_EMBEDDING_MODEL (optional): override the embedding model id
        OPENROUTER_EMBEDDING_DIMENSION (optional): override the vector size

    Defaults preserve backward compatibility: ``google/gemini-embedding-001``
    at 3072 dimensions.
    """

    def __init__(self, model: Optional[str] = None, dimension: Optional[int] = None):
        """
        Initialize OpenRouter Embedder.

        Args:
            model: OpenRouter embedding model id. Falls back to
                OPENROUTER_EMBEDDING_MODEL env var, then DEFAULT_MODEL.
            dimension: Output vector size. Falls back to
                OPENROUTER_EMBEDDING_DIMENSION env var, then DEFAULT_DIMENSION.
                Must match the chosen model's actual output size — the vector
                store and similarity math rely on it.

        Raises:
            ValueError: If OPENROUTER_API_KEY is not set or dimension is invalid
            ImportError: If openai package is not installed
        """
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

        dim_value = dimension if dimension is not None else os.getenv("OPENROUTER_EMBEDDING_DIMENSION")
        if dim_value is None:
            self.dimension = DEFAULT_DIMENSION
        else:
            try:
                self.dimension = int(dim_value)
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"OPENROUTER_EMBEDDING_DIMENSION must be an integer, got {dim_value!r}"
                ) from e
            if self.dimension <= 0:
                raise ValueError(f"Embedding dimension must be positive, got {self.dimension}")

        logger.info(
            f"OpenRouter Embedder initialized with model: {self.model} "
            f"(dimension={self.dimension})"
        )

    def encode_query(self, query: str, task: str = "search result") -> np.ndarray:
        """
        Encode a search query.

        Args:
            query: The search query text
            task: Task type for prompt template

        Returns:
            Numpy array of embeddings (``self.dimension`` elements).
        """
        # Apply query prompt template
        text = f"task: {task} | query: {query}"

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float",
                extra_headers={
                    "HTTP-Referer": "https://yargimcp.com",
                    "X-Title": "Yargi MCP Server",
                }
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
        Encode multiple documents with batch API call.

        Args:
            documents: List of document texts
            titles: Optional list of document titles

        Returns:
            Numpy array of embeddings (N x ``self.dimension``).
        """
        if not documents:
            return np.array([])

        # Apply document prompt template
        texts = []
        for i, doc in enumerate(documents):
            title = titles[i] if titles and i < len(titles) else "none"
            text = f"title: {title} | text: {doc}"
            texts.append(text)

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float",
                extra_headers={
                    "HTTP-Referer": "https://yargimcp.com",
                    "X-Title": "Yargi MCP Server",
                }
            )

            # Extract embeddings in order
            embeddings = np.array(
                [d.embedding for d in sorted(response.data, key=lambda x: x.index)],
                dtype=np.float32
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
        # Ensure query is 2D for matrix multiplication
        if len(query_embedding.shape) == 1:
            query_embedding = query_embedding.reshape(1, -1)

        # Compute cosine similarity (embeddings are already normalized)
        similarities = np.dot(document_embeddings, query_embedding.T).squeeze()

        return similarities
