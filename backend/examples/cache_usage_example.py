"""
Example usage of the caching layer (SemanticCache and ToolCache).

This example demonstrates how to use the semantic cache and tool cache
in the AI Agent System.
"""

import asyncio

from app.services.embedding_service import EmbeddingService
from app.services.semantic_cache import SemanticCache
from app.services.tool_cache import ToolCache


async def semantic_cache_example():
    """Example of using SemanticCache."""
    print("\n=== Semantic Cache Example ===\n")
    
    # Initialize services
    cache = SemanticCache()
    embedding_service = EmbeddingService()
    
    # Connect to cache backends
    await cache.connect()
    
    try:
        # Example prompt
        prompt = "How to create a NestJS controller with dependency injection?"
        
        # Generate embedding for the prompt
        print(f"Generating embedding for prompt: {prompt}")
        embedding = await embedding_service.embed_text(prompt)
        print(f"✓ Generated embedding with {len(embedding)} dimensions")
        
        # Check cache (should be miss on first run)
        print("\nChecking cache...")
        cached_response = await cache.get_with_embedding(prompt, embedding)
        
        if cached_response:
            print(f"✓ Cache HIT! Similarity: {cached_response.similarity_score:.4f}")
            print(f"  Response: {cached_response.response[:100]}...")
        else:
            print("✗ Cache MISS - would invoke LLM here")
            
            # Simulate LLM response
            response = """
            To create a NestJS controller with dependency injection:
            
            1. Use the @Controller() decorator
            2. Inject services via constructor
            3. Use @Injectable() on the service class
            
            Example:
            @Controller('users')
            export class UsersController {
              constructor(private usersService: UsersService) {}
            }
            """
            
            # Store in cache
            print("\nStoring response in cache...")
            success = await cache.set(prompt, response, embedding, ttl=3600)
            
            if success:
                print("✓ Response cached successfully")
            else:
                print("✗ Failed to cache response")
        
        # Try retrieving again (should be hit now)
        print("\nChecking cache again...")
        cached_response = await cache.get_with_embedding(prompt, embedding)
        
        if cached_response:
            print(f"✓ Cache HIT! Similarity: {cached_response.similarity_score:.4f}")
            print(f"  Response: {cached_response.response[:100]}...")
        
    finally:
        # Cleanup
        await cache.disconnect()
        print("\n✓ Disconnected from cache")


async def tool_cache_example():
    """Example of using ToolCache."""
    print("\n=== Tool Cache Example ===\n")
    
    # Initialize cache
    cache = ToolCache(default_ttl=300)  # 5 minutes
    
    # Connect to Redis
    await cache.connect()
    
    try:
        # Example tool call parameters
        tool_name = "search_framework_docs"
        params = {
            "query": "NestJS authentication guards",
            "frameworks": ["NestJS"],
            "top_k": 10
        }
        
        # Generate cache key
        cache_key = cache.generate_cache_key(tool_name, params)
        print(f"Generated cache key: {cache_key}")
        
        # Check cache (should be miss on first run)
        print("\nChecking tool cache...")
        cached_result = await cache.get(cache_key)
        
        if cached_result:
            print("✓ Cache HIT!")
            print(f"  Results: {len(cached_result)} items")
        else:
            print("✗ Cache MISS - would execute MCP tool here")
            
            # Simulate MCP tool result
            result = [
                {
                    "content": "Guards in NestJS are used to determine whether a request should be handled...",
                    "score": 0.92,
                    "framework": "NestJS",
                    "source": "https://docs.nestjs.com/guards"
                },
                {
                    "content": "Authentication guards can be implemented using the @UseGuards() decorator...",
                    "score": 0.88,
                    "framework": "NestJS",
                    "source": "https://docs.nestjs.com/security/authentication"
                }
            ]
            
            # Store in cache
            print("\nStoring tool result in cache...")
            success = await cache.set(cache_key, result, ttl=300)
            
            if success:
                print("✓ Tool result cached successfully")
            else:
                print("✗ Failed to cache tool result")
        
        # Try retrieving again (should be hit now)
        print("\nChecking tool cache again...")
        cached_result = await cache.get(cache_key)
        
        if cached_result:
            print("✓ Cache HIT!")
            print(f"  Results: {len(cached_result)} items")
            print(f"  First result score: {cached_result[0]['score']}")
        
        # Example using get_or_set convenience method
        print("\n--- Using get_or_set convenience method ---")
        
        async def fetch_docs():
            """Simulate expensive MCP tool call."""
            print("  Executing expensive MCP tool call...")
            await asyncio.sleep(0.1)  # Simulate network delay
            return [{"content": "Example doc", "score": 0.9}]
        
        result = await cache.get_or_set(
            "search_framework_docs",
            {"query": "React hooks", "top_k": 5},
            fetch_docs,
            ttl=300
        )
        
        print(f"✓ Got result: {len(result)} items")
        
    finally:
        # Cleanup
        await cache.disconnect()
        print("\n✓ Disconnected from cache")


async def main():
    """Run all examples."""
    print("=" * 60)
    print("Caching Layer Usage Examples")
    print("=" * 60)
    
    try:
        await tool_cache_example()
        # Note: semantic_cache_example requires vector database connection
        # Uncomment when vector database is available:
        # await semantic_cache_example()
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        print("  Make sure Redis is running: redis-server")


if __name__ == "__main__":
    asyncio.run(main())
