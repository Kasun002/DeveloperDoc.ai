"""
Documentation Search Agent for semantic framework documentation retrieval.

This module implements the Documentation Search Agent that performs semantic
search across framework documentation using pgvector, applies cross-encoder
re-ranking, and implements self-correction for low-confidence results.
"""

import logging
from typing import List, Optional

from app.schemas.agent import DocumentationResult
from app.services.embedding_service import EmbeddingService, embedding_service
from app.services.reranking_service import RerankingService, reranking_service
from app.services.tool_cache import ToolCache, tool_cache
from app.services.vector_search_service import VectorSearchService, vector_search_service

logger = logging.getLogger(__name__)


class DocumentationSearchAgent:
    """
    Agent for semantic documentation search with self-correction.
    
    This agent performs semantic retrieval of framework documentation using
    pgvector with HNSW indexing, applies cross-encoder re-ranking to improve
    relevance, and implements self-correction when initial results have low
    confidence scores.
    
    Attributes:
        vector_search_service: Service for vector similarity search
        reranking_service: Service for cross-encoder re-ranking
        embedding_service: Service for generating embeddings
        self_correction_threshold: Score threshold below which self-correction triggers
    """
    
    def __init__(
        self,
        vector_search_service: Optional[VectorSearchService] = None,
        reranking_service: Optional[RerankingService] = None,
        embedding_service: Optional[EmbeddingService] = None,
        tool_cache: Optional[ToolCache] = None,
        self_correction_threshold: float = 0.7
    ):
        """
        Initialize the Documentation Search Agent.
        
        Args:
            vector_search_service: Vector search service instance
            reranking_service: Re-ranking service instance
            embedding_service: Embedding service instance
            tool_cache: Tool cache instance for caching search results
            self_correction_threshold: Threshold for triggering self-correction (default: 0.7)
        """
        self.vector_search_service = vector_search_service or vector_search_service
        self.reranking_service = reranking_service or reranking_service
        self.embedding_service = embedding_service or embedding_service
        self.tool_cache = tool_cache or tool_cache
        self.self_correction_threshold = self_correction_threshold
    
    async def search_docs(
        self,
        query: str,
        frameworks: Optional[List[str]] = None,
        top_k: int = 10,
        min_score: float = 0.7
    ) -> List[DocumentationResult]:
        """
        Search framework documentation with re-ranking and self-correction.
        
        Performs semantic search using pgvector, applies cross-encoder re-ranking
        to improve relevance, and triggers self-correction if the maximum score
        is below the threshold. Uses tool-level caching to avoid redundant searches.
        
        Args:
            query: Search query text
            frameworks: Optional list of framework names to filter by
            top_k: Maximum number of results to return (default: 10)
            min_score: Minimum similarity score threshold (default: 0.7)
            
        Returns:
            List[DocumentationResult]: Re-ranked documentation results with scores
            
        Raises:
            ValueError: If query is empty or parameters are invalid
            ConnectionError: If database connection fails
            
        Example:
            >>> agent = DocumentationSearchAgent()
            >>> results = await agent.search_docs(
            ...     "How to create a controller in NestJS",
            ...     frameworks=["NestJS"],
            ...     top_k=5
            ... )
            >>> for result in results:
            ...     print(f"{result.framework}: {result.score}")
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        logger.info(
            f"Documentation search started",
            extra={
                "query": query,
                "frameworks": frameworks,
                "top_k": top_k,
                "min_score": min_score
            }
        )
        
        # Generate cache key from query and parameters
        cache_params = {
            "query": query,
            "frameworks": frameworks,
            "top_k": top_k,
            "min_score": min_score
        }
        
        # Try to get from cache first
        try:
            cache_key = self.tool_cache.generate_cache_key(
                "search_framework_docs",
                cache_params
            )
            cached_result = await self.tool_cache.get(cache_key)
            
            if cached_result is not None:
                logger.info(
                    f"Cache hit for documentation search",
                    extra={
                        "query": query,
                        "cache_key": cache_key
                    }
                )
                # Convert cached dicts back to DocumentationResult objects
                return [
                    DocumentationResult(**result_dict)
                    for result_dict in cached_result
                ]
        except Exception as e:
            # Cache errors should not break the search
            logger.warning(
                f"Cache lookup failed, proceeding without cache",
                extra={"error": str(e)},
                exc_info=True
            )
        
        # Cache miss - perform search
        logger.info(
            f"Cache miss, performing documentation search",
            extra={"query": query}
        )
        
        # Step 1: Perform initial vector search
        initial_results = await self.vector_search_service.search_documentation(
            query=query,
            frameworks=frameworks,
            top_k=top_k * 2,  # Retrieve more for re-ranking
            min_score=min_score
        )
        
        if not initial_results:
            logger.info("No results found for query", extra={"query": query})
            return []
        
        logger.info(
            f"Initial vector search returned {len(initial_results)} results",
            extra={
                "query": query,
                "result_count": len(initial_results),
                "max_score": max(r.score for r in initial_results) if initial_results else 0
            }
        )
        
        # Step 2: Apply cross-encoder re-ranking
        reranked_results = self.reranking_service.rerank_results(
            query=query,
            results=initial_results,
            top_k=top_k
        )
        
        logger.info(
            f"Re-ranking complete",
            extra={
                "query": query,
                "reranked_count": len(reranked_results),
                "max_score_after_rerank": max(r.score for r in reranked_results) if reranked_results else 0
            }
        )
        
        # Step 3: Check if self-correction is needed
        max_score = max(r.score for r in reranked_results) if reranked_results else 0
        
        if max_score < self.self_correction_threshold:
            logger.info(
                f"Self-correction triggered due to low confidence",
                extra={
                    "query": query,
                    "max_score": max_score,
                    "threshold": self.self_correction_threshold
                }
            )
            
            # Attempt self-correction
            corrected_results = await self.self_correct(query, reranked_results)
            
            # Use corrected results if they're better
            corrected_max_score = max(r.score for r in corrected_results) if corrected_results else 0
            if corrected_max_score > max_score:
                logger.info(
                    f"Self-correction improved results",
                    extra={
                        "query": query,
                        "original_max_score": max_score,
                        "corrected_max_score": corrected_max_score
                    }
                )
                final_results = corrected_results
            else:
                logger.info(
                    f"Self-correction did not improve results, using original",
                    extra={
                        "query": query,
                        "original_max_score": max_score,
                        "corrected_max_score": corrected_max_score
                    }
                )
                final_results = reranked_results
        else:
            final_results = reranked_results
        
        # Cache the results (convert to dicts for JSON serialization)
        try:
            result_dicts = [
                {
                    "content": r.content,
                    "score": r.score,
                    "metadata": r.metadata,
                    "source": r.source,
                    "framework": r.framework
                }
                for r in final_results
            ]
            await self.tool_cache.set(cache_key, result_dicts, ttl=300)  # 5 minutes TTL
            logger.info(
                f"Results cached",
                extra={
                    "query": query,
                    "cache_key": cache_key,
                    "result_count": len(final_results)
                }
            )
        except Exception as e:
            # Cache errors should not break the search
            logger.warning(
                f"Failed to cache results",
                extra={"error": str(e)},
                exc_info=True
            )
        
        return final_results
    
    async def self_correct(
        self,
        query: str,
        initial_results: List[DocumentationResult]
    ) -> List[DocumentationResult]:
        """
        Refine query and re-search when initial results have low confidence.
        
        Implements self-correction by analyzing the initial results and refining
        the query to improve relevance. Uses a simple strategy of extracting
        key terms from the query and expanding it.
        
        Args:
            query: Original search query
            initial_results: Initial search results with low confidence
            
        Returns:
            List[DocumentationResult]: Improved search results
            
        Example:
            >>> agent = DocumentationSearchAgent()
            >>> initial_results = [...]  # Low confidence results
            >>> improved = await agent.self_correct("controller", initial_results)
        """
        logger.info(
            f"Self-correction started",
            extra={
                "original_query": query,
                "initial_result_count": len(initial_results)
            }
        )
        
        # Strategy 1: Expand query with framework-specific terms
        # If frameworks are mentioned in initial results, add them to query
        frameworks_in_results = set()
        if initial_results:
            for result in initial_results[:3]:  # Check top 3 results
                frameworks_in_results.add(result.framework)
        
        # Create refined query
        refined_query = query
        if frameworks_in_results:
            # Add framework context to query
            framework_context = " ".join(frameworks_in_results)
            refined_query = f"{query} {framework_context}"
            
            logger.info(
                f"Query refined with framework context",
                extra={
                    "original_query": query,
                    "refined_query": refined_query,
                    "frameworks": list(frameworks_in_results)
                }
            )
        else:
            # Strategy 2: Add generic programming terms
            refined_query = f"{query} example code documentation"
            
            logger.info(
                f"Query refined with generic terms",
                extra={
                    "original_query": query,
                    "refined_query": refined_query
                }
            )
        
        # Perform new search with refined query
        try:
            # Search with lower min_score to get more candidates
            corrected_results = await self.vector_search_service.search_documentation(
                query=refined_query,
                frameworks=list(frameworks_in_results) if frameworks_in_results else None,
                top_k=20,  # Get more results for re-ranking
                min_score=0.5  # Lower threshold for self-correction
            )
            
            if not corrected_results:
                logger.info(
                    f"Self-correction found no results",
                    extra={"refined_query": refined_query}
                )
                return initial_results
            
            # Re-rank the corrected results
            reranked_corrected = self.reranking_service.rerank_results(
                query=query,  # Use original query for re-ranking
                results=corrected_results,
                top_k=10
            )
            
            logger.info(
                f"Self-correction complete",
                extra={
                    "refined_query": refined_query,
                    "result_count": len(reranked_corrected),
                    "max_score": max(r.score for r in reranked_corrected) if reranked_corrected else 0
                }
            )
            
            return reranked_corrected
            
        except Exception as e:
            logger.error(
                f"Self-correction failed",
                extra={
                    "error": str(e),
                    "refined_query": refined_query
                },
                exc_info=True
            )
            # Return original results if self-correction fails
            return initial_results
    
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a query using text-embedding-3-small.
        
        This is a convenience method that delegates to the embedding service.
        
        Args:
            query: Query text to embed
            
        Returns:
            List[float]: 1536-dimensional embedding vector
            
        Raises:
            ValueError: If query is empty
            ConnectionError: If OpenAI API call fails
            
        Example:
            >>> agent = DocumentationSearchAgent()
            >>> embedding = await agent.embed_query("NestJS controller")
            >>> len(embedding)
            1536
        """
        return await self.embedding_service.embed_query(query)
    
    def get_agent_info(self) -> dict:
        """
        Get information about the agent configuration.
        
        Returns:
            dict: Agent configuration including thresholds and service info
        """
        return {
            "agent_type": "documentation_search",
            "self_correction_threshold": self.self_correction_threshold,
            "vector_search_service": "VectorSearchService",
            "reranking_service": self.reranking_service.get_model_info(),
            "embedding_service": "EmbeddingService (text-embedding-3-small)"
        }


# Global documentation search agent instance
documentation_search_agent = DocumentationSearchAgent()


async def get_documentation_search_agent() -> DocumentationSearchAgent:
    """
    Dependency injection function for FastAPI endpoints.
    
    Returns:
        DocumentationSearchAgent: Global documentation search agent instance
    """
    return documentation_search_agent
