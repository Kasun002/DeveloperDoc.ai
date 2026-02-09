"""
Unit tests for the cross-encoder reranking service.

Tests the RerankingService class functionality including:
- Basic re-ranking of documentation results
- Batch processing
- Score normalization
- Error handling
"""

import pytest

from app.schemas.agent import DocumentationResult
from app.services.reranking_service import RerankingService


class TestRerankingService:
    """Test suite for RerankingService."""
    
    @pytest.fixture
    def reranking_service(self):
        """Create a RerankingService instance for testing."""
        return RerankingService()
    
    @pytest.fixture
    def sample_results(self):
        """Create sample documentation results for testing."""
        return [
            DocumentationResult(
                content="NestJS controllers handle incoming requests and return responses to the client.",
                score=0.85,
                metadata={"section": "Controllers", "version": "10.x"},
                source="https://docs.nestjs.com/controllers",
                framework="NestJS"
            ),
            DocumentationResult(
                content="React hooks allow you to use state and other React features without writing a class.",
                score=0.80,
                metadata={"section": "Hooks", "version": "18.x"},
                source="https://react.dev/reference/react",
                framework="React"
            ),
            DocumentationResult(
                content="FastAPI is a modern, fast web framework for building APIs with Python.",
                score=0.75,
                metadata={"section": "Introduction", "version": "0.100"},
                source="https://fastapi.tiangolo.com/",
                framework="FastAPI"
            )
        ]
    
    def test_rerank_results_basic(self, reranking_service, sample_results):
        """Test basic re-ranking functionality."""
        query = "How to create a controller in NestJS"
        
        reranked = reranking_service.rerank_results(query, sample_results)
        
        # Verify all results are returned
        assert len(reranked) == len(sample_results)
        
        # Verify results are DocumentationResult instances
        for result in reranked:
            assert isinstance(result, DocumentationResult)
        
        # Verify scores are in valid range [0, 1]
        for result in reranked:
            assert 0.0 <= result.score <= 1.0
        
        # Verify results are sorted by score (descending)
        scores = [result.score for result in reranked]
        assert scores == sorted(scores, reverse=True)
        
        # Verify NestJS result should rank higher for NestJS query
        # (This is a heuristic test - cross-encoder should rank relevant docs higher)
        nestjs_result = next(r for r in reranked if r.framework == "NestJS")
        assert nestjs_result.score > 0.5  # Should have decent relevance
    
    def test_rerank_results_with_top_k(self, reranking_service, sample_results):
        """Test re-ranking with top_k limit."""
        query = "web framework"
        top_k = 2
        
        reranked = reranking_service.rerank_results(query, sample_results, top_k=top_k)
        
        # Verify only top_k results are returned
        assert len(reranked) == top_k
        
        # Verify results are sorted by score
        scores = [result.score for result in reranked]
        assert scores == sorted(scores, reverse=True)
    
    def test_rerank_results_empty_query(self, reranking_service, sample_results):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            reranking_service.rerank_results("", sample_results)
        
        with pytest.raises(ValueError, match="Query cannot be empty"):
            reranking_service.rerank_results("   ", sample_results)
    
    def test_rerank_results_empty_results(self, reranking_service):
        """Test that empty results list raises ValueError."""
        with pytest.raises(ValueError, match="Results list cannot be empty"):
            reranking_service.rerank_results("test query", [])
    
    def test_rerank_results_preserves_metadata(self, reranking_service, sample_results):
        """Test that re-ranking preserves result metadata."""
        query = "documentation"
        
        reranked = reranking_service.rerank_results(query, sample_results)
        
        # Verify all metadata is preserved
        for original, reranked_result in zip(sample_results, reranked):
            # Find matching result by content
            matching = next(r for r in reranked if r.content == original.content)
            assert matching.metadata == original.metadata
            assert matching.source == original.source
            assert matching.framework == original.framework
    
    def test_rerank_results_scores_differ_from_original(self, reranking_service, sample_results):
        """Test that cross-encoder produces different scores than original."""
        query = "controller pattern"
        
        # Store original scores
        original_scores = {r.content: r.score for r in sample_results}
        
        reranked = reranking_service.rerank_results(query, sample_results)
        
        # At least some scores should differ (cross-encoder re-scoring)
        scores_changed = False
        for result in reranked:
            if abs(result.score - original_scores[result.content]) > 0.01:
                scores_changed = True
                break
        
        assert scores_changed, "Cross-encoder should produce different scores"
    
    def test_rerank_batch(self, reranking_service, sample_results):
        """Test batch re-ranking of multiple queries."""
        queries = [
            "NestJS controllers",
            "React hooks",
            "FastAPI framework"
        ]
        results_list = [sample_results, sample_results, sample_results]
        
        reranked_list = reranking_service.rerank_batch(queries, results_list, top_k=2)
        
        # Verify correct number of result sets
        assert len(reranked_list) == len(queries)
        
        # Verify each result set has top_k results
        for reranked in reranked_list:
            assert len(reranked) == 2
            
            # Verify sorted by score
            scores = [r.score for r in reranked]
            assert scores == sorted(scores, reverse=True)
    
    def test_rerank_batch_mismatched_lengths(self, reranking_service, sample_results):
        """Test that mismatched queries and results raise ValueError."""
        queries = ["query1", "query2"]
        results_list = [sample_results]  # Only one result set
        
        with pytest.raises(ValueError, match="must have same length"):
            reranking_service.rerank_batch(queries, results_list)
    
    def test_rerank_batch_with_empty_results(self, reranking_service, sample_results):
        """Test batch re-ranking handles empty result sets."""
        queries = ["query1", "query2"]
        results_list = [sample_results, []]  # Second set is empty
        
        reranked_list = reranking_service.rerank_batch(queries, results_list)
        
        assert len(reranked_list) == 2
        assert len(reranked_list[0]) > 0  # First set has results
        assert len(reranked_list[1]) == 0  # Second set is empty
    
    def test_get_model_info(self, reranking_service):
        """Test getting model information."""
        info = reranking_service.get_model_info()
        
        assert "model_name" in info
        assert "batch_size" in info
        assert "model_type" in info
        
        assert info["model_name"] == "cross-encoder/ms-marco-MiniLM-L-6-v2"
        assert info["batch_size"] == 32
        assert info["model_type"] == "cross-encoder"
    
    def test_rerank_results_single_result(self, reranking_service):
        """Test re-ranking with a single result."""
        query = "test query"
        single_result = [
            DocumentationResult(
                content="Test content",
                score=0.8,
                metadata={},
                source="test.com",
                framework="Test"
            )
        ]
        
        reranked = reranking_service.rerank_results(query, single_result)
        
        assert len(reranked) == 1
        assert 0.0 <= reranked[0].score <= 1.0
    
    def test_rerank_results_score_normalization(self, reranking_service, sample_results):
        """Test that scores are properly normalized to [0, 1] range."""
        query = "framework documentation"
        
        reranked = reranking_service.rerank_results(query, sample_results)
        
        # All scores should be in [0, 1] range
        for result in reranked:
            assert 0.0 <= result.score <= 1.0, \
                f"Score {result.score} is outside [0, 1] range"
