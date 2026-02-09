"""
Unit tests for Vector Search Service.

Tests semantic search functionality using pgvector with framework filtering.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.vector_search_service import VectorSearchService
from app.schemas.agent import DocumentationResult


@pytest.mark.asyncio
class TestVectorSearchService:
    """Test suite for VectorSearchService."""
    
    async def test_search_documentation_returns_results(self):
        """Test that search_documentation() returns search results."""
        mock_db_manager = AsyncMock()
        mock_embedding_service = AsyncMock()
        
        service = VectorSearchService(
            db_manager=mock_db_manager,
            embedding_service=mock_embedding_service
        )
        
        # Mock embedding generation
        mock_embedding_service.embed_query = AsyncMock(return_value=[0.1] * 1536)
        
        # Mock database results
        mock_rows = [
            {
                'id': 1,
                'content': 'NestJS controller documentation',
                'source': 'https://docs.nestjs.com/controllers',
                'framework': 'NestJS',
                'section': 'Controllers',
                'version': '10.x',
                'metadata': {'category': 'basics'},
                'similarity_score': 0.92
            },
            {
                'id': 2,
                'content': 'NestJS routing documentation',
                'source': 'https://docs.nestjs.com/routing',
                'framework': 'NestJS',
                'section': 'Routing',
                'version': '10.x',
                'metadata': {},
                'similarity_score': 0.85
            }
        ]
        mock_db_manager.fetch = AsyncMock(return_value=mock_rows)
        
        results = await service.search_documentation(
            query="How to create a controller",
            frameworks=["NestJS"],
            top_k=5
        )
        
        assert len(results) == 2
        assert all(isinstance(r, DocumentationResult) for r in results)
        assert results[0].framework == "NestJS"
        assert results[0].score == 0.92
        assert results[1].score == 0.85
    
    async def test_search_documentation_filters_by_min_score(self):
        """Test that search_documentation() filters results by minimum score."""
        mock_db_manager = AsyncMock()
        mock_embedding_service = AsyncMock()
        
        service = VectorSearchService(
            db_manager=mock_db_manager,
            embedding_service=mock_embedding_service
        )
        
        mock_embedding_service.embed_query = AsyncMock(return_value=[0.1] * 1536)
        
        mock_rows = [
            {
                'id': 1,
                'content': 'High relevance doc',
                'source': 'https://example.com/1',
                'framework': 'NestJS',
                'section': None,
                'version': None,
                'metadata': {},
                'similarity_score': 0.92
            },
            {
                'id': 2,
                'content': 'Low relevance doc',
                'source': 'https://example.com/2',
                'framework': 'NestJS',
                'section': None,
                'version': None,
                'metadata': {},
                'similarity_score': 0.65
            }
        ]
        mock_db_manager.fetch = AsyncMock(return_value=mock_rows)
        
        results = await service.search_documentation(
            query="test query",
            min_score=0.7
        )
        
        # Only the high relevance doc should be returned
        assert len(results) == 1
        assert results[0].score == 0.92
    
    async def test_search_documentation_raises_on_empty_query(self):
        """Test that search_documentation() raises ValueError for empty query."""
        service = VectorSearchService()
        
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await service.search_documentation("")
        
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await service.search_documentation("   ")
    
    async def test_search_documentation_validates_parameters(self):
        """Test that search_documentation() validates parameters."""
        service = VectorSearchService()
        
        with pytest.raises(ValueError, match="top_k must be positive"):
            await service.search_documentation("test", top_k=0)
        
        with pytest.raises(ValueError, match="top_k must be positive"):
            await service.search_documentation("test", top_k=-1)
        
        with pytest.raises(ValueError, match="min_score must be between"):
            await service.search_documentation("test", min_score=1.5)
        
        with pytest.raises(ValueError, match="min_score must be between"):
            await service.search_documentation("test", min_score=-0.1)
    
    async def test_search_by_framework_filters_single_framework(self):
        """Test that search_by_framework() searches within a single framework."""
        mock_db_manager = AsyncMock()
        mock_embedding_service = AsyncMock()
        
        service = VectorSearchService(
            db_manager=mock_db_manager,
            embedding_service=mock_embedding_service
        )
        
        mock_embedding_service.embed_query = AsyncMock(return_value=[0.1] * 1536)
        
        mock_rows = [
            {
                'id': 1,
                'content': 'React hooks documentation',
                'source': 'https://react.dev/hooks',
                'framework': 'React',
                'section': 'Hooks',
                'version': '18.2',
                'metadata': {},
                'similarity_score': 0.88
            }
        ]
        mock_db_manager.fetch = AsyncMock(return_value=mock_rows)
        
        results = await service.search_by_framework(
            query="How to use hooks",
            framework="React"
        )
        
        assert len(results) == 1
        assert results[0].framework == "React"
    
    async def test_search_by_framework_raises_on_empty_framework(self):
        """Test that search_by_framework() raises ValueError for empty framework."""
        service = VectorSearchService()
        
        with pytest.raises(ValueError, match="Framework cannot be empty"):
            await service.search_by_framework("test", framework="")
    
    async def test_search_multi_framework_returns_grouped_results(self):
        """Test that search_multi_framework() returns results grouped by framework."""
        mock_db_manager = AsyncMock()
        mock_embedding_service = AsyncMock()
        
        service = VectorSearchService(
            db_manager=mock_db_manager,
            embedding_service=mock_embedding_service
        )
        
        mock_embedding_service.embed_query = AsyncMock(return_value=[0.1] * 1536)
        
        # Mock different results for different frameworks
        def mock_fetch_side_effect(query, *args):
            if 'NestJS' in str(args):
                return [
                    {
                        'id': 1,
                        'content': 'NestJS doc',
                        'source': 'https://nestjs.com',
                        'framework': 'NestJS',
                        'section': None,
                        'version': None,
                        'metadata': {},
                        'similarity_score': 0.9
                    }
                ]
            elif 'React' in str(args):
                return [
                    {
                        'id': 2,
                        'content': 'React doc',
                        'source': 'https://react.dev',
                        'framework': 'React',
                        'section': None,
                        'version': None,
                        'metadata': {},
                        'similarity_score': 0.85
                    }
                ]
            return []
        
        mock_db_manager.fetch = AsyncMock(side_effect=mock_fetch_side_effect)
        
        results = await service.search_multi_framework(
            query="authentication",
            frameworks=["NestJS", "React"],
            top_k_per_framework=3
        )
        
        assert "NestJS" in results
        assert "React" in results
        assert len(results["NestJS"]) == 1
        assert len(results["React"]) == 1
    
    async def test_get_similar_documents_returns_similar_docs(self):
        """Test that get_similar_documents() finds similar documents."""
        mock_db_manager = AsyncMock()
        mock_embedding_service = AsyncMock()
        
        service = VectorSearchService(
            db_manager=mock_db_manager,
            embedding_service=mock_embedding_service
        )
        
        # Mock source document fetch
        source_row = {
            'embedding': [0.1] * 1536,
            'framework': 'NestJS'
        }
        
        # Mock similar documents
        similar_rows = [
            {
                'id': 2,
                'content': 'Similar doc 1',
                'source': 'https://example.com/2',
                'framework': 'NestJS',
                'section': 'Controllers',
                'version': '10.x',
                'metadata': {},
                'similarity_score': 0.95
            },
            {
                'id': 3,
                'content': 'Similar doc 2',
                'source': 'https://example.com/3',
                'framework': 'NestJS',
                'section': 'Routing',
                'version': '10.x',
                'metadata': {},
                'similarity_score': 0.88
            }
        ]
        
        mock_db_manager.fetchrow = AsyncMock(return_value=source_row)
        mock_db_manager.fetch = AsyncMock(return_value=similar_rows)
        
        results = await service.get_similar_documents(
            document_id=1,
            top_k=5,
            same_framework_only=True
        )
        
        assert len(results) == 2
        assert all(r.framework == "NestJS" for r in results)
        assert results[0].score == 0.95
        assert results[1].score == 0.88
    
    async def test_get_similar_documents_raises_on_invalid_id(self):
        """Test that get_similar_documents() raises ValueError for invalid document ID."""
        mock_db_manager = AsyncMock()
        mock_embedding_service = AsyncMock()
        
        service = VectorSearchService(
            db_manager=mock_db_manager,
            embedding_service=mock_embedding_service
        )
        
        mock_db_manager.fetchrow = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError, match="Document with id .* not found"):
            await service.get_similar_documents(document_id=999)
    
    async def test_search_documentation_without_framework_filter(self):
        """Test that search_documentation() works without framework filter."""
        mock_db_manager = AsyncMock()
        mock_embedding_service = AsyncMock()
        
        service = VectorSearchService(
            db_manager=mock_db_manager,
            embedding_service=mock_embedding_service
        )
        
        mock_embedding_service.embed_query = AsyncMock(return_value=[0.1] * 1536)
        
        mock_rows = [
            {
                'id': 1,
                'content': 'NestJS doc',
                'source': 'https://nestjs.com',
                'framework': 'NestJS',
                'section': None,
                'version': None,
                'metadata': {},
                'similarity_score': 0.9
            },
            {
                'id': 2,
                'content': 'React doc',
                'source': 'https://react.dev',
                'framework': 'React',
                'section': None,
                'version': None,
                'metadata': {},
                'similarity_score': 0.85
            }
        ]
        mock_db_manager.fetch = AsyncMock(return_value=mock_rows)
        
        results = await service.search_documentation(
            query="authentication",
            frameworks=None,  # No framework filter
            top_k=10
        )
        
        assert len(results) == 2
        assert results[0].framework == "NestJS"
        assert results[1].framework == "React"
