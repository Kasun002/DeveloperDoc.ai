"""
Example demonstrating cross-encoder re-ranking with vector search.

This example shows how to integrate the RerankingService with VectorSearchService
to improve documentation search relevance using cross-encoder re-ranking.
"""

import asyncio

from app.schemas.agent import DocumentationResult
from app.services.reranking_service import RerankingService
from app.services.vector_search_service import VectorSearchService


async def search_with_reranking_example():
    """
    Example: Search documentation with cross-encoder re-ranking.
    
    This demonstrates the two-stage retrieval process:
    1. Initial retrieval using vector similarity (fast, approximate)
    2. Re-ranking using cross-encoder (slower, more accurate)
    """
    # Initialize services
    vector_search = VectorSearchService()
    reranking_service = RerankingService()
    
    # Search query
    query = "How to create a REST API controller in NestJS"
    
    print(f"Query: {query}\n")
    
    # Stage 1: Initial retrieval with vector search
    print("Stage 1: Vector Search (Initial Retrieval)")
    print("-" * 50)
    
    initial_results = await vector_search.search_documentation(
        query=query,
        frameworks=["NestJS"],
        top_k=10,
        min_score=0.5
    )
    
    print(f"Found {len(initial_results)} initial results")
    for i, result in enumerate(initial_results[:3], 1):
        print(f"\n{i}. Score: {result.score:.4f}")
        print(f"   Framework: {result.framework}")
        print(f"   Content: {result.content[:100]}...")
    
    # Stage 2: Re-ranking with cross-encoder
    print("\n\nStage 2: Cross-Encoder Re-ranking")
    print("-" * 50)
    
    reranked_results = reranking_service.rerank_results(
        query=query,
        results=initial_results,
        top_k=5  # Return top 5 after re-ranking
    )
    
    print(f"Top {len(reranked_results)} results after re-ranking:")
    for i, result in enumerate(reranked_results, 1):
        print(f"\n{i}. Score: {result.score:.4f} (re-ranked)")
        print(f"   Framework: {result.framework}")
        print(f"   Content: {result.content[:100]}...")
        print(f"   Source: {result.source}")
    
    # Compare score changes
    print("\n\nScore Comparison (Before vs After Re-ranking)")
    print("-" * 50)
    
    # Create mapping of content to original scores
    original_scores = {r.content: r.score for r in initial_results}
    
    for result in reranked_results[:3]:
        original_score = original_scores.get(result.content, 0.0)
        score_change = result.score - original_score
        print(f"\nContent: {result.content[:60]}...")
        print(f"  Original Score: {original_score:.4f}")
        print(f"  Re-ranked Score: {result.score:.4f}")
        print(f"  Change: {score_change:+.4f}")


async def multi_framework_reranking_example():
    """
    Example: Search and re-rank across multiple frameworks.
    
    Demonstrates searching documentation from multiple frameworks
    and using re-ranking to find the most relevant results.
    """
    vector_search = VectorSearchService()
    reranking_service = RerankingService()
    
    query = "authentication middleware"
    frameworks = ["NestJS", "FastAPI", "Express.js"]
    
    print(f"Query: {query}")
    print(f"Frameworks: {', '.join(frameworks)}\n")
    
    # Search across multiple frameworks
    print("Searching across frameworks...")
    print("-" * 50)
    
    initial_results = await vector_search.search_documentation(
        query=query,
        frameworks=frameworks,
        top_k=15,
        min_score=0.5
    )
    
    print(f"Found {len(initial_results)} results across all frameworks")
    
    # Count results per framework
    framework_counts = {}
    for result in initial_results:
        framework_counts[result.framework] = framework_counts.get(result.framework, 0) + 1
    
    for framework, count in framework_counts.items():
        print(f"  {framework}: {count} results")
    
    # Re-rank all results
    print("\n\nRe-ranking results...")
    print("-" * 50)
    
    reranked_results = reranking_service.rerank_results(
        query=query,
        results=initial_results,
        top_k=5
    )
    
    print(f"\nTop {len(reranked_results)} results after re-ranking:")
    for i, result in enumerate(reranked_results, 1):
        print(f"\n{i}. {result.framework} - Score: {result.score:.4f}")
        print(f"   {result.content[:100]}...")


async def batch_reranking_example():
    """
    Example: Batch re-ranking for multiple queries.
    
    Demonstrates efficient batch processing when re-ranking
    results for multiple queries simultaneously.
    """
    vector_search = VectorSearchService()
    reranking_service = RerankingService()
    
    # Multiple queries
    queries = [
        "How to handle HTTP requests",
        "Database connection setup",
        "Authentication and authorization"
    ]
    
    print("Batch Re-ranking Example")
    print("=" * 50)
    
    # Search for each query
    all_results = []
    for query in queries:
        results = await vector_search.search_documentation(
            query=query,
            top_k=10,
            min_score=0.5
        )
        all_results.append(results)
        print(f"\nQuery: {query}")
        print(f"  Found {len(results)} initial results")
    
    # Batch re-rank
    print("\n\nBatch re-ranking all queries...")
    reranked_list = reranking_service.rerank_batch(
        queries=queries,
        results_list=all_results,
        top_k=3
    )
    
    # Display results
    print("\n\nTop 3 Results per Query (After Re-ranking)")
    print("=" * 50)
    
    for query, reranked in zip(queries, reranked_list):
        print(f"\n\nQuery: {query}")
        print("-" * 50)
        for i, result in enumerate(reranked, 1):
            print(f"\n{i}. Score: {result.score:.4f}")
            print(f"   Framework: {result.framework}")
            print(f"   {result.content[:80]}...")


def mock_search_results_example():
    """
    Example: Re-ranking with mock data (no database required).
    
    Useful for testing and development without database connection.
    """
    reranking_service = RerankingService()
    
    # Create mock documentation results
    mock_results = [
        DocumentationResult(
            content="Controllers are responsible for handling incoming requests and returning responses to the client. In NestJS, controllers are defined using the @Controller() decorator.",
            score=0.85,
            metadata={"section": "Controllers"},
            source="https://docs.nestjs.com/controllers",
            framework="NestJS"
        ),
        DocumentationResult(
            content="Middleware is a function which is called before the route handler. Middleware functions have access to the request and response objects.",
            score=0.80,
            metadata={"section": "Middleware"},
            source="https://docs.nestjs.com/middleware",
            framework="NestJS"
        ),
        DocumentationResult(
            content="Guards are used to determine whether a given request will be handled by the route handler or not, depending on certain conditions.",
            score=0.75,
            metadata={"section": "Guards"},
            source="https://docs.nestjs.com/guards",
            framework="NestJS"
        )
    ]
    
    query = "How to handle HTTP requests in NestJS"
    
    print("Mock Data Re-ranking Example")
    print("=" * 50)
    print(f"\nQuery: {query}\n")
    
    print("Original Results (Vector Search Scores):")
    print("-" * 50)
    for i, result in enumerate(mock_results, 1):
        print(f"\n{i}. Score: {result.score:.4f}")
        print(f"   {result.content[:80]}...")
    
    # Re-rank
    reranked = reranking_service.rerank_results(query, mock_results)
    
    print("\n\nRe-ranked Results (Cross-Encoder Scores):")
    print("-" * 50)
    for i, result in enumerate(reranked, 1):
        print(f"\n{i}. Score: {result.score:.4f}")
        print(f"   {result.content[:80]}...")


if __name__ == "__main__":
    print("Cross-Encoder Re-ranking Examples")
    print("=" * 70)
    print()
    
    # Run mock example (no database required)
    print("\n\n1. MOCK DATA EXAMPLE (No Database Required)")
    print("=" * 70)
    mock_search_results_example()
    
    # Uncomment to run database examples (requires database connection)
    # print("\n\n2. VECTOR SEARCH + RE-RANKING EXAMPLE")
    # print("=" * 70)
    # asyncio.run(search_with_reranking_example())
    
    # print("\n\n3. MULTI-FRAMEWORK RE-RANKING EXAMPLE")
    # print("=" * 70)
    # asyncio.run(multi_framework_reranking_example())
    
    # print("\n\n4. BATCH RE-RANKING EXAMPLE")
    # print("=" * 70)
    # asyncio.run(batch_reranking_example())
