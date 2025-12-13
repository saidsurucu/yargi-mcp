# semantic_search/embedder.py

import logging
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import torch

logger = logging.getLogger(__name__)

class EmbeddingGemma:
    """
    Wrapper for Google's EmbeddingGemma model.
    Handles query and document encoding with proper prompt templates.
    """
    
    def __init__(self, model_name: str = "google/embeddinggemma-300m", device: Optional[str] = None):
        """
        Initialize EmbeddingGemma model.
        
        Args:
            model_name: HuggingFace model name
            device: Device to run model on ('cuda', 'cpu', or None for auto)
        """
        self.model_name = model_name
        
        # Auto-detect device if not specified
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
            
        logger.info(f"Initializing EmbeddingGemma on device: {self.device}")
        
        try:
            # Load model with float32 precision (EmbeddingGemma doesn't support float16)
            self.model = SentenceTransformer(model_name, device=self.device)
            self.model.eval()  # Set to evaluation mode
            
            # Set precision to float32 or bfloat16
            if self.device == 'cuda' and torch.cuda.is_bf16_supported():
                logger.info("Using bfloat16 precision for CUDA")
                self.dtype = torch.bfloat16
            else:
                logger.info("Using float32 precision")
                self.dtype = torch.float32
                
            logger.info(f"Successfully loaded model: {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to load EmbeddingGemma model: {e}")
            raise
    
    def encode_query(self, query: str, task: str = "search result") -> np.ndarray:
        """
        Encode a search query with appropriate prompt template.
        
        Args:
            query: The search query text
            task: Task type for prompt template (search result, question answering, etc.)
            
        Returns:
            Numpy array of embeddings (768 dimensions)
        """
        # Apply query prompt template
        prompted_query = f"task: {task} | query: {query}"
        
        try:
            with torch.no_grad():
                # Encode with model
                embeddings = self.model.encode(
                    prompted_query,
                    convert_to_numpy=True,
                    normalize_embeddings=True,  # L2 normalization for cosine similarity
                    show_progress_bar=False
                )
            
            logger.debug(f"Encoded query: {query[:50]}... -> shape: {embeddings.shape}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to encode query: {e}")
            raise
    
    def encode_documents(self, documents: List[str], titles: Optional[List[str]] = None) -> np.ndarray:
        """
        Encode multiple documents with appropriate prompt template.
        
        Args:
            documents: List of document texts
            titles: Optional list of document titles
            
        Returns:
            Numpy array of embeddings (N x 768 dimensions)
        """
        if not documents:
            return np.array([])
        
        # Apply document prompt template
        prompted_docs = []
        for i, doc in enumerate(documents):
            title = titles[i] if titles and i < len(titles) else "none"
            prompted_doc = f"title: {title} | text: {doc}"
            prompted_docs.append(prompted_doc)
        
        try:
            with torch.no_grad():
                # Batch encode documents
                embeddings = self.model.encode(
                    prompted_docs,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=len(documents) > 10,
                    batch_size=8  # Adjust based on memory
                )
            
            logger.info(f"Encoded {len(documents)} documents -> shape: {embeddings.shape}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to encode documents: {e}")
            raise
    
    def reduce_dimensions(self, embeddings: np.ndarray, target_dim: int = 512) -> np.ndarray:
        """
        Reduce embedding dimensions using Matryoshka Representation Learning.
        
        Args:
            embeddings: Original embeddings (N x 768)
            target_dim: Target dimension (512, 256, or 128)
            
        Returns:
            Reduced embeddings (N x target_dim)
        """
        if target_dim not in [512, 256, 128]:
            raise ValueError(f"Target dimension must be 512, 256, or 128, got {target_dim}")
        
        if len(embeddings.shape) == 1:
            # Single embedding
            reduced = embeddings[:target_dim]
            # Re-normalize after truncation
            norm = np.linalg.norm(reduced)
            if norm > 0:
                reduced = reduced / norm
        else:
            # Multiple embeddings
            reduced = embeddings[:, :target_dim]
            # Re-normalize each embedding
            norms = np.linalg.norm(reduced, axis=1, keepdims=True)
            reduced = reduced / (norms + 1e-8)  # Avoid division by zero
        
        logger.debug(f"Reduced dimensions: {embeddings.shape} -> {reduced.shape}")
        return reduced
    
    def compute_similarity(self, query_embedding: np.ndarray, document_embeddings: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarity between query and documents.
        
        Args:
            query_embedding: Query embedding (768,)
            document_embeddings: Document embeddings (N x 768)
            
        Returns:
            Similarity scores (N,)
        """
        # Ensure query is 2D for matrix multiplication
        if len(query_embedding.shape) == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Compute cosine similarity (embeddings are already normalized)
        similarities = np.dot(document_embeddings, query_embedding.T).squeeze()
        
        return similarities