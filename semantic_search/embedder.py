# semantic_search/embedder.py

import logging
import os
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)


def is_openrouter_available() -> bool:
    """Check if OpenRouter API key is available."""
    return bool(os.getenv("OPENROUTER_API_KEY"))


class OpenRouterEmbedder:
    """
    Embedder using OpenRouter API with Google's Gemini Embedding model.
    Requires OPENROUTER_API_KEY environment variable.
    """

    def __init__(self):
        """
        Initialize OpenRouter Embedder.

        Raises:
            ValueError: If OPENROUTER_API_KEY is not set
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
        self.model = "google/gemini-embedding-001"
        self.dimension = 3072

        logger.info(f"OpenRouter Embedder initialized with model: {self.model}")

    def encode_query(self, query: str, task: str = "search result") -> np.ndarray:
        """
        Encode a search query.

        Args:
            query: The search query text
            task: Task type for prompt template

        Returns:
            Numpy array of embeddings (3072 dimensions)
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
            Numpy array of embeddings (N x 3072 dimensions)
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
            query_embedding: Query embedding (3072,)
            document_embeddings: Document embeddings (N x 3072)

        Returns:
            Similarity scores (N,)
        """
        # Ensure query is 2D for matrix multiplication
        if len(query_embedding.shape) == 1:
            query_embedding = query_embedding.reshape(1, -1)

        # Compute cosine similarity (embeddings are already normalized)
        similarities = np.dot(document_embeddings, query_embedding.T).squeeze()

        return similarities
