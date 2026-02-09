"""
Cross-encoder re-ranking service for documentation search results.

This module provides re-ranking functionality using a cross-encoder model
to improve the relevance of documentation search results. Uses the
cross-encoder/ms-marco-MiniLM-L-6-v2 model for efficient re-ranking.
"""

from typing import List, Optional

from sentence_transformers import CrossEncoder

from app.schemas.agent import DocumentationResult


class RerankingService:
    """
    Service for re-ranking documentation search results using cross-encoder.
    
    This service uses a cross-encoder model to re-score documentation results
    based on their relevance to the query. Cross-encoders provide more accurate
    relevance scores than bi-encoders (used for initial retrieval) by jointly
    encoding the query and document.
    
    Attributes:
        model: CrossEncoder model instance
        model_name: Name of the cross-encoder model
        batch_size: Batch size for processing multiple results
    """
    
    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        batch_size: int = 32
    ):
        """
        Initialize the Reranking Service.
        
        Args:
            model_name: Cross-encoder model name (default: cross-encoder/ms-marco-MiniLM-L-6-v2)
            batch_size: Batch size for processing (default: 32)
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.model = CrossEncoder(model_name)
    
    def rerank_results(
        self,
        query: str,
        results: List[DocumentationResult],
        top_k: Optional[int] = None
    ) -> List[DocumentationResult]:
        """
        Re-rank documentation results using cross-encoder model.
        
        Takes initial search results and re-scores them using a cross-encoder
        model for improved relevance. The cross-encoder jointly encodes the
        query and each document to produce more accurate relevance scores.
        
        Args:
            query: Original search query
            results: List of initial documentation results from vector search
            top_k: Optional limit on number of results to return after re-ranking.
                   If None, returns all results with updated scores.
            
        Returns:
            List[DocumentationResult]: Re-ranked results with updated scores,
                                       sorted by relevance (highest first)
            
        Raises:
            ValueError: If query is empty or results list is empty
            
        Example:
            >>> service = RerankingService()
            >>> initial_results = [...]  # From vector search
            >>> reranked = service.rerank_results(
            ...     "How to create a controller in NestJS",
            ...     initial_results,
            ...     top_k=5
            ... )
            >>> for result in reranked:
            ...     print(f"{result.framework}: {result.score}")
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        if not results:
            raise ValueError("Results list cannot be empty")
        
        # Prepare query-document pairs for cross-encoder
        # Format: [(query, doc1), (query, doc2), ...]
        query_doc_pairs = [(query, result.content) for result in results]
        
        # Get cross-encoder scores in batches for efficiency
        cross_encoder_scores = self.model.predict(
            query_doc_pairs,
            batch_size=self.batch_size,
            show_progress_bar=False
        )
        
        # Update results with new scores
        # Cross-encoder scores are typically in range [-10, 10]
        # Normalize to [0, 1] using sigmoid-like transformation
        reranked_results = []
        for result, score in zip(results, cross_encoder_scores):
            # Create a new result with updated score
            # Normalize score to [0, 1] range using sigmoid
            normalized_score = 1 / (1 + pow(2.71828, -float(score)))
            
            reranked_result = DocumentationResult(
                content=result.content,
                score=normalized_score,
                metadata=result.metadata,
                source=result.source,
                framework=result.framework
            )
            reranked_results.append(reranked_result)
        
        # Sort by score (descending)
        reranked_results.sort(key=lambda x: x.score, reverse=True)
        
        # Apply top_k limit if specified
        if top_k is not None and top_k > 0:
            reranked_results = reranked_results[:top_k]
        
        return reranked_results
    
    def rerank_batch(
        self,
        queries: List[str],
        results_list: List[List[DocumentationResult]],
        top_k: Optional[int] = None
    ) -> List[List[DocumentationResult]]:
        """
        Re-rank multiple sets of documentation results in batch.
        
        More efficient than calling rerank_results multiple times when
        processing multiple queries.
        
        Args:
            queries: List of search queries
            results_list: List of result lists, one per query
            top_k: Optional limit on results per query
            
        Returns:
            List[List[DocumentationResult]]: Re-ranked results for each query
            
        Raises:
            ValueError: If queries and results_list have different lengths
            
        Example:
            >>> service = RerankingService()
            >>> queries = ["query1", "query2"]
            >>> results = [[results1], [results2]]
            >>> reranked = service.rerank_batch(queries, results, top_k=5)
        """
        if len(queries) != len(results_list):
            raise ValueError("Queries and results_list must have same length")
        
        # Process each query-results pair
        reranked_list = []
        for query, results in zip(queries, results_list):
            if results:  # Only rerank if there are results
                reranked = self.rerank_results(query, results, top_k)
            else:
                reranked = []
            reranked_list.append(reranked)
        
        return reranked_list
    
    def get_model_info(self) -> dict:
        """
        Get information about the loaded cross-encoder model.
        
        Returns:
            dict: Model information including name and batch size
        """
        return {
            "model_name": self.model_name,
            "batch_size": self.batch_size,
            "model_type": "cross-encoder"
        }


# Global reranking service instance
reranking_service = RerankingService()


def get_reranking_service() -> RerankingService:
    """
    Dependency injection function for FastAPI endpoints.
    
    Returns:
        RerankingService: Global reranking service instance
    """
    return reranking_service
