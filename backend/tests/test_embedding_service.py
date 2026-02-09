"""
Unit tests for Embedding Service.

Tests embedding generation with OpenAI API, including error handling
and retry logic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from openai import RateLimitError, OpenAIError
from app.services.embedding_service import EmbeddingService


@pytest.mark.asyncio
class TestEmbeddingService:
    """Test suite for EmbeddingService."""
    
    async def test_embed_text_returns_embedding(self):
        """Test that embed_text() returns a valid embedding vector."""
        service = EmbeddingService(api_key="test-key")
        
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        
        with patch.object(service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            embedding = await service.embed_text("Hello world")
            
            assert len(embedding) == 1536
            assert all(isinstance(x, float) for x in embedding)
            mock_create.assert_called_once()
    
    async def test_embed_text_raises_on_empty_text(self):
        """Test that embed_text() raises ValueError for empty text."""
        service = EmbeddingService(api_key="test-key")
        
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await service.embed_text("")
        
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await service.embed_text("   ")
    
    async def test_embed_text_retries_on_rate_limit(self):
        """Test that embed_text() retries on rate limit error."""
        service = EmbeddingService(api_key="test-key")
        
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        
        # Create a mock response object for RateLimitError
        mock_error_response = MagicMock()
        mock_error_response.request = MagicMock()
        
        with patch.object(service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
            # Fail twice with rate limit, then succeed
            mock_create.side_effect = [
                RateLimitError("Rate limit exceeded", response=mock_error_response, body=None),
                RateLimitError("Rate limit exceeded", response=mock_error_response, body=None),
                mock_response
            ]
            
            embedding = await service.embed_text("Hello world")
            
            assert len(embedding) == 1536
            assert mock_create.call_count == 3
    
    async def test_embed_text_raises_after_max_retries(self):
        """Test that embed_text() raises error after max retries."""
        service = EmbeddingService(api_key="test-key")
        
        # Create a mock response object for RateLimitError
        mock_error_response = MagicMock()
        mock_error_response.request = MagicMock()
        
        with patch.object(service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = RateLimitError("Rate limit exceeded", response=mock_error_response, body=None)
            
            with pytest.raises(RateLimitError):
                await service.embed_text("Hello world")
            
            assert mock_create.call_count == 3
    
    async def test_embed_text_validates_dimension(self):
        """Test that embed_text() validates embedding dimension."""
        service = EmbeddingService(api_key="test-key")
        
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 512)]  # Wrong dimension
        
        with patch.object(service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            with pytest.raises(RuntimeError, match="Failed to generate embedding"):
                await service.embed_text("Hello world")
    
    async def test_embed_batch_returns_multiple_embeddings(self):
        """Test that embed_batch() returns embeddings for multiple texts."""
        service = EmbeddingService(api_key="test-key")
        
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
            MagicMock(embedding=[0.3] * 1536)
        ]
        
        with patch.object(service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            embeddings = await service.embed_batch(["Hello", "World", "Test"])
            
            assert len(embeddings) == 3
            assert all(len(emb) == 1536 for emb in embeddings if emb is not None)
    
    async def test_embed_batch_raises_on_empty_list(self):
        """Test that embed_batch() raises ValueError for empty list."""
        service = EmbeddingService(api_key="test-key")
        
        with pytest.raises(ValueError, match="Texts list cannot be empty"):
            await service.embed_batch([])
    
    async def test_embed_batch_handles_empty_strings(self):
        """Test that embed_batch() handles empty strings in the list."""
        service = EmbeddingService(api_key="test-key")
        
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536)
        ]
        
        with patch.object(service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            embeddings = await service.embed_batch(["Hello", "", "World"])
            
            assert len(embeddings) == 3
            assert embeddings[0] is not None
            assert embeddings[1] is None  # Empty string
            assert embeddings[2] is not None
    
    async def test_embed_batch_raises_on_all_empty_strings(self):
        """Test that embed_batch() raises ValueError when all texts are empty."""
        service = EmbeddingService(api_key="test-key")
        
        with pytest.raises(ValueError, match="All texts are empty"):
            await service.embed_batch(["", "  ", ""])
    
    async def test_embed_query_calls_embed_text(self):
        """Test that embed_query() is an alias for embed_text()."""
        service = EmbeddingService(api_key="test-key")
        
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        
        with patch.object(service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            embedding = await service.embed_query("search query")
            
            assert len(embedding) == 1536
            mock_create.assert_called_once()
    
    async def test_embed_document_calls_embed_text(self):
        """Test that embed_document() is an alias for embed_text()."""
        service = EmbeddingService(api_key="test-key")
        
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        
        with patch.object(service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            embedding = await service.embed_document("document text")
            
            assert len(embedding) == 1536
            mock_create.assert_called_once()
    
    async def test_embed_text_handles_openai_error(self):
        """Test that embed_text() retries on OpenAI errors."""
        service = EmbeddingService(api_key="test-key")
        
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        
        with patch.object(service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
            # Fail once with OpenAI error, then succeed
            mock_create.side_effect = [
                OpenAIError("API error"),
                mock_response
            ]
            
            embedding = await service.embed_text("Hello world")
            
            assert len(embedding) == 1536
            assert mock_create.call_count == 2
