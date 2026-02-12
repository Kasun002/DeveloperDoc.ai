"""
Vector search service for framework documentation using pgvector.

This module provides semantic search functionality for framework documentation
using pgvector with HNSW indexing. Supports cosine similarity search with
framework filtering.
"""

from typing import List, Optional

from app.core.vector_database import VectorDatabaseManager, vector_db_manager
from app.schemas.agent import DocumentationResult
from app.services.local_embedding_service import LocalEmbeddingService, get_local_embedding_service


class VectorSearchService:
    """
    Service for semantic search of framework documentation.
    
    This service provides vector similarity search using pgvector with HNSW
    indexing for fast O(log N) search performance. Supports framework filtering
    and configurable similarity thresholds.
    
    Attributes:
        db_manager: Vector database manager instance
        embedding_service: Embedding generation service instance
    """
    
    def __init__(
        self,
        db_manager: Optional[VectorDatabaseManager] = None,
        embedding_service: Optional[LocalEmbeddingService] = None
    ):
        """
        Initialize the Vector Search Service.
        
        Args:
            db_manager: Vector database manager. If None, uses global instance.
            embedding_service: Local embedding service. If None, creates new instance.
        """
        self.db_manager = db_manager or vector_db_manager
        self.embedding_service = embedding_service or get_local_embedding_service(
            model_name="all-MiniLM-L6-v2",
            dimension=384
        )
    
    async def search_documentation(
        self,
        query: str,
        frameworks: Optional[List[str]] = None,
        top_k: int = 10,
        min_score: float = 0.7
    ) -> List[DocumentationResult]:
        """
        Search framework documentation using semantic similarity.
        
        Performs vector similarity search using pgvector with HNSW indexing
        and cosine similarity. Results are filtered by minimum score and
        optionally by framework names.
        
        Args:
            query: Search query text
            frameworks: Optional list of framework names to filter by
                       (e.g., ["NestJS", "React", "FastAPI"])
            top_k: Maximum number of results to return (default: 10)
            min_score: Minimum similarity score threshold (0.0-1.0, default: 0.7)
            
        Returns:
            List[DocumentationResult]: List of documentation results with scores
            
        Raises:
            ValueError: If query is empty or parameters are invalid
            ConnectionError: If database connection fails
            
        Example:
            >>> service = VectorSearchService()
            >>> results = await service.search_documentation(
            ...     "How to create a controller in NestJS",
            ...     frameworks=["NestJS"],
            ...     top_k=5
            ... )
            >>> for result in results:
            ...     print(f"{result.framework}: {result.score}")
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        
        if not 0.0 <= min_score <= 1.0:
            raise ValueError("min_score must be between 0.0 and 1.0")
        
        # Generate query embedding
        query_embedding = await self.embedding_service.embed_query(query)
        
        # Build SQL query with framework filtering
        if frameworks:
            # Filter by specific frameworks
            framework_filter = "AND framework = ANY($3)"
            params = [query_embedding, top_k, frameworks]
        else:
            # No framework filter
            framework_filter = ""
            params = [query_embedding, top_k]
        
        # Vector search query using cosine similarity
        # Note: <=> is the cosine distance operator in pgvector
        # Cosine similarity = 1 - cosine distance
        sql_query = f"""
            SELECT 
                id,
                content,
                source,
                framework,
                section,
                version,
                metadata,
                1 - (embedding <=> $1::vector) AS similarity_score
            FROM framework_documentation
            WHERE 1=1
            {framework_filter}
            ORDER BY embedding <=> $1::vector
            LIMIT $2
        """
        
        # Execute search query
        rows = await self.db_manager.fetch(sql_query, *params)
        
        # Convert rows to DocumentationResult objects
        results = []
        for row in rows:
            score = float(row['similarity_score'])
            
            # Filter by minimum score
            if score < min_score:
                continue
            
            result = DocumentationResult(
                content=row['content'],
                score=score,
                metadata=row['metadata'] or {},
                source=row['source'],
                framework=row['framework']
            )
            
            # Add optional fields to metadata
            if row['section']:
                result.metadata['section'] = row['section']
            if row['version']:
                result.metadata['version'] = row['version']
            
            results.append(result)
        
        return results
    
    async def search_by_framework(
        self,
        query: str,
        framework: str,
        top_k: int = 10,
        min_score: float = 0.7
    ) -> List[DocumentationResult]:
        """
        Search documentation for a specific framework.
        
        Convenience method for searching within a single framework.
        
        Args:
            query: Search query text
            framework: Framework name (e.g., "NestJS", "React", "FastAPI")
            top_k: Maximum number of results to return (default: 10)
            min_score: Minimum similarity score threshold (0.0-1.0, default: 0.7)
            
        Returns:
            List[DocumentationResult]: List of documentation results with scores
            
        Raises:
            ValueError: If query or framework is empty
            ConnectionError: If database connection fails
        """
        if not framework or not framework.strip():
            raise ValueError("Framework cannot be empty")
        
        return await self.search_documentation(
            query=query,
            frameworks=[framework],
            top_k=top_k,
            min_score=min_score
        )
    
    async def search_multi_framework(
        self,
        query: str,
        frameworks: List[str],
        top_k_per_framework: int = 5,
        min_score: float = 0.7
    ) -> dict[str, List[DocumentationResult]]:
        """
        Search documentation across multiple frameworks separately.
        
        Returns results grouped by framework, useful for comparing
        documentation across different frameworks.
        
        Args:
            query: Search query text
            frameworks: List of framework names to search
            top_k_per_framework: Max results per framework (default: 5)
            min_score: Minimum similarity score threshold (0.0-1.0, default: 0.7)
            
        Returns:
            dict[str, List[DocumentationResult]]: Results grouped by framework
            
        Example:
            >>> results = await service.search_multi_framework(
            ...     "authentication",
            ...     frameworks=["NestJS", "FastAPI"],
            ...     top_k_per_framework=3
            ... )
            >>> print(results["NestJS"])
            >>> print(results["FastAPI"])
        """
        results_by_framework = {}
        
        for framework in frameworks:
            results = await self.search_by_framework(
                query=query,
                framework=framework,
                top_k=top_k_per_framework,
                min_score=min_score
            )
            results_by_framework[framework] = results
        
        return results_by_framework
    
    async def get_similar_documents(
        self,
        document_id: int,
        top_k: int = 5,
        same_framework_only: bool = True
    ) -> List[DocumentationResult]:
        """
        Find similar documents to a given document.
        
        Useful for finding related documentation or examples.
        
        Args:
            document_id: ID of the source document
            top_k: Maximum number of similar documents to return
            same_framework_only: Only return docs from same framework
            
        Returns:
            List[DocumentationResult]: List of similar documents
            
        Raises:
            ValueError: If document_id is invalid
            ConnectionError: If database connection fails
        """
        # Get the source document's embedding and framework
        source_query = """
            SELECT embedding, framework
            FROM framework_documentation
            WHERE id = $1
        """
        source_row = await self.db_manager.fetchrow(source_query, document_id)
        
        if not source_row:
            raise ValueError(f"Document with id {document_id} not found")
        
        source_embedding = source_row['embedding']
        source_framework = source_row['framework']
        
        # Build similarity search query
        if same_framework_only:
            framework_filter = "AND framework = $3"
            params = [source_embedding, document_id, source_framework, top_k]
        else:
            framework_filter = ""
            params = [source_embedding, document_id, top_k]
        
        similarity_query = f"""
            SELECT 
                id,
                content,
                source,
                framework,
                section,
                version,
                metadata,
                1 - (embedding <=> $1::vector) AS similarity_score
            FROM framework_documentation
            WHERE id != $2
            {framework_filter}
            ORDER BY embedding <=> $1::vector
            LIMIT ${len(params)}
        """
        
        rows = await self.db_manager.fetch(similarity_query, *params)
        
        # Convert to DocumentationResult objects
        results = []
        for row in rows:
            result = DocumentationResult(
                content=row['content'],
                score=float(row['similarity_score']),
                metadata=row['metadata'] or {},
                source=row['source'],
                framework=row['framework']
            )
            
            if row['section']:
                result.metadata['section'] = row['section']
            if row['version']:
                result.metadata['version'] = row['version']
            
            results.append(result)
        
        return results


# Global vector search service instance
vector_search_service = VectorSearchService()


async def get_vector_search_service() -> VectorSearchService:
    """
    Dependency injection function for FastAPI endpoints.
    
    Returns:
        VectorSearchService: Global vector search service instance
    """
    return vector_search_service
