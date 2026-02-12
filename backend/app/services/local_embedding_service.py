"""
Local embedding generation service using sentence-transformers.

This module provides embedding generation functionality using free, local models
that don't require API keys or have quota limits. Perfect for development and
when OpenAI quota is exceeded.

Models used:
- all-MiniLM-L6-v2: Fast, 384 dimensions, good quality
- Alternative: all-mpnet-base-v2: Slower, 768 dimensions, better quality
"""

from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer


class LocalEmbeddingService:
    """
    Service for generating text embeddings using local sentence-transformers models.
    
    This service provides methods to generate embeddings without API calls,
    using models that run locally. No API keys or quotas required.
    
    Attributes:
        model: SentenceTransformer model instance
        dimension: Embedding dimension size
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        dimension: Optional[int] = None
    ):
        """
        Initialize the Local Embedding Service.
        
        Args:
            model_name: Model name from sentence-transformers
                Options:
                - "all-MiniLM-L6-v2" (384 dim, fast, recommended)
                - "all-mpnet-base-v2" (768 dim, slower, better quality)
            dimension: Target embedding dimension (will pad/truncate if needed)
        """
        print(f"Loading local embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        
        # Get actual dimension from model
        actual_dim = self.model.get_sentence_embedding_dimension()
        self.dimension = dimension or actual_dim
        self.actual_dimension = actual_dim
        
        print(f"✓ Model loaded: {model_name} ({actual_dim} dimensions)")
        if dimension and dimension != actual_dim:
            print(f"  Will adjust to {dimension} dimensions")
    
    def _adjust_dimension(self, embedding: np.ndarray) -> List[float]:
        """Adjust embedding dimension to match target."""
        if len(embedding) == self.dimension:
            return embedding.tolist()
        elif len(embedding) < self.dimension:
            # Pad with zeros
            padded = np.pad(embedding, (0, self.dimension - len(embedding)))
            return padded.tolist()
        else:
            # Truncate
            return embedding[:self.dimension].tolist()
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.
        
        Args:
            text: Text to embed
            
        Returns:
            List[float]: Embedding vector
            
        Raises:
            ValueError: If text is empty or None
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        try:
            # Generate embedding (synchronous, but fast)
            embedding = self.model.encode(text, convert_to_numpy=True)
            
            # Adjust dimension if needed
            return self._adjust_dimension(embedding)
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate embedding: {str(e)}")
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List[List[float]]: List of embedding vectors
            
        Raises:
            ValueError: If texts list is empty
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")
        
        # Filter out empty texts and track indices
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)
        
        if not valid_texts:
            raise ValueError("All texts are empty")
        
        try:
            # Generate embeddings in batch (much faster)
            embeddings = self.model.encode(
                valid_texts,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            # Adjust dimensions
            adjusted_embeddings = [
                self._adjust_dimension(emb) for emb in embeddings
            ]
            
            # Reconstruct full list with None for empty texts
            result = [None] * len(texts)
            for i, embedding in zip(valid_indices, adjusted_embeddings):
                result[i] = embedding
            
            return result
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate embeddings: {str(e)}")
    
    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a search query."""
        return await self.embed_text(query)
    
    async def embed_document(self, document: str) -> List[float]:
        """Generate embedding for a document."""
        return await self.embed_text(document)


# Global local embedding service instance
local_embedding_service = None


def get_local_embedding_service(
    model_name: str = "all-MiniLM-L6-v2",
    dimension: int = 384
) -> LocalEmbeddingService:
    """
    Get or create global local embedding service instance.
    
    Args:
        model_name: Model name (default: all-MiniLM-L6-v2)
        dimension: Target dimension (default: 384)
        
    Returns:
        LocalEmbeddingService: Global instance
    """
    global local_embedding_service
    if local_embedding_service is None:
        local_embedding_service = LocalEmbeddingService(
            model_name=model_name,
            dimension=dimension
        )
    return local_embedding_service
