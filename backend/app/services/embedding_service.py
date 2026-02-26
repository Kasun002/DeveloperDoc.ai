"""
Embedding generation service using OpenAI API.

This module provides embedding generation functionality for the AI Agent System
using OpenAI's text-embedding-3-small model. Includes error handling, rate limiting,
and retry logic.
"""

import asyncio
import logging
from typing import List, Optional

from app.core.config import settings
from openai import AsyncOpenAI, OpenAIError, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random_exponential,
)

logger = logging.getLogger(__name__)

# Maximum number of texts sent to OpenAI in a single embed_batch call.
# Keeping this small avoids hitting per-minute token rate limits.
_BATCH_CHUNK_SIZE = 20


class EmbeddingService:
    """
    Service for generating text embeddings using OpenAI API.
    
    This service provides methods to generate embeddings for text using the
    text-embedding-3-small model (1536 dimensions). Includes automatic retry
    logic for transient failures and rate limiting.
    
    Attributes:
        client: AsyncOpenAI client instance
        model: Embedding model name
        dimension: Embedding dimension size
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        dimension: int = settings.embedding_dimension
    ):
        """
        Initialize the Embedding Service.
        
        Args:
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY from settings.
            model: Embedding model name (default: text-embedding-3-small)
            dimension: Embedding dimension (default: 1536)
        """
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self.model = model
        self.dimension = dimension
    
    @retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(4),
        # For rate-limit errors use a randomized exponential back-off starting
        # at 10 s and capping at 90 s.  OpenAI rate-limit windows are typically
        # 60 s, so waiting at least that long before retrying is important.
        wait=wait_random_exponential(multiplier=2, min=10, max=90),
        reraise=True,
    )
    @retry(
        retry=retry_if_exception_type(OpenAIError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.
        
        Generates a 1536-dimensional embedding vector using OpenAI's
        text-embedding-3-small model. Includes automatic retry logic
        for rate limiting and transient errors.
        
        Args:
            text: Text to embed (max ~8000 tokens)
            
        Returns:
            List[float]: Embedding vector (1536 dimensions)
            
        Raises:
            ValueError: If text is empty or None
            OpenAIError: If API call fails after all retries
            
        Example:
            >>> service = EmbeddingService()
            >>> embedding = await service.embed_text("Hello world")
            >>> len(embedding)
            1536
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            
            # Extract embedding from response
            embedding = response.data[0].embedding
            
            # Verify dimension
            if len(embedding) != self.dimension:
                raise ValueError(
                    f"Expected embedding dimension {self.dimension}, "
                    f"got {len(embedding)}"
                )
            
            return embedding
            
        except RateLimitError as e:
            # Rate limit error - will be retried by tenacity
            raise
        except OpenAIError as e:
            # Other OpenAI errors - will be retried by tenacity
            raise
        except Exception as e:
            # Unexpected errors
            raise RuntimeError(f"Failed to generate embedding: {str(e)}")
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a single API call.
        
        More efficient than calling embed_text multiple times. Includes
        automatic retry logic for rate limiting and transient errors.
        
        Args:
            texts: List of texts to embed (max ~8000 tokens per text)
            
        Returns:
            List[List[float]]: List of embedding vectors
            
        Raises:
            ValueError: If texts list is empty or contains empty strings
            OpenAIError: If API call fails after all retries
            
        Example:
            >>> service = EmbeddingService()
            >>> embeddings = await service.embed_batch(["Hello", "World"])
            >>> len(embeddings)
            2
            >>> len(embeddings[0])
            1536
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        # Filter out empty texts and track original indices
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)

        if not valid_texts:
            raise ValueError("All texts are empty")

        # Process in chunks to stay within OpenAI per-request limits and
        # reduce the chance of hitting per-minute token rate limits.
        all_embeddings: List[List[float]] = []
        for chunk_start in range(0, len(valid_texts), _BATCH_CHUNK_SIZE):
            chunk = valid_texts[chunk_start: chunk_start + _BATCH_CHUNK_SIZE]
            chunk_embeddings = await self._embed_batch_chunk(chunk)
            all_embeddings.extend(chunk_embeddings)
            if chunk_start + _BATCH_CHUNK_SIZE < len(valid_texts):
                # Brief pause between chunks to reduce rate-limit pressure.
                await asyncio.sleep(0.5)

        # Reconstruct the full-length result list (None slots for empty inputs)
        result: List[Optional[List[float]]] = [None] * len(texts)
        for i, embedding in zip(valid_indices, all_embeddings):
            result[i] = embedding

        return result

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(4),
        wait=wait_random_exponential(multiplier=2, min=10, max=90),
        reraise=True,
    )
    @retry(
        retry=retry_if_exception_type(OpenAIError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _embed_batch_chunk(self, texts: List[str]) -> List[List[float]]:
        """Send a single chunk of texts to OpenAI and return their embeddings."""
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float",
            )

            embeddings = [item.embedding for item in response.data]

            for embedding in embeddings:
                if len(embedding) != self.dimension:
                    raise ValueError(
                        f"Expected embedding dimension {self.dimension}, "
                        f"got {len(embedding)}"
                    )

            return embeddings

        except RateLimitError:
            logger.warning(
                "openai_rate_limit_hit",
                service="embedding_service",
                chunk_size=len(texts),
                action="retrying with exponential back-off",
            )
            raise
        except OpenAIError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to generate embeddings: {str(e)}")
    
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        
        Alias for embed_text() with semantic naming for search use cases.
        
        Args:
            query: Search query text
            
        Returns:
            List[float]: Query embedding vector (1536 dimensions)
            
        Raises:
            ValueError: If query is empty or None
            OpenAIError: If API call fails after all retries
        """
        return await self.embed_text(query)
    
    async def embed_document(self, document: str) -> List[float]:
        """
        Generate embedding for a document.
        
        Alias for embed_text() with semantic naming for document indexing.
        
        Args:
            document: Document text
            
        Returns:
            List[float]: Document embedding vector (1536 dimensions)
            
        Raises:
            ValueError: If document is empty or None
            OpenAIError: If API call fails after all retries
        """
        return await self.embed_text(document)


# Global embedding service instance
embedding_service = EmbeddingService()


async def get_embedding_service() -> EmbeddingService:
    """
    Dependency injection function for FastAPI endpoints.
    
    Returns:
        EmbeddingService: Global embedding service instance
    """
    return embedding_service
