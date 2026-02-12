#!/usr/bin/env python3
"""
Verification script for AI Agent System setup.

This script checks that all required components are properly configured:
- PostgreSQL with pgvector extension
- Redis connection
- Environment variables
- Python dependencies
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_environment_variables():
    """Check that required environment variables are set."""
    print("\n=== Checking Environment Variables ===")
    
    required_vars = [
        "DATABASE_URL",
        "REDIS_URL",
        "OPENAI_API_KEY",
        "JWT_SECRET_KEY",
    ]
    
    optional_vars = [
        "SEMANTIC_CACHE_THRESHOLD",
        "TOOL_CACHE_TTL",
        "MAX_WORKFLOW_ITERATIONS",
        "EMBEDDING_MODEL",
    ]
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "KEY" in var or "PASSWORD" in var:
                display_value = "***" + value[-4:] if len(value) > 4 else "***"
            else:
                display_value = value
            print(f"✓ {var}: {display_value}")
        else:
            print(f"✗ {var}: NOT SET")
            missing_required.append(var)
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {value}")
        else:
            print(f"⚠ {var}: NOT SET (using default)")
            missing_optional.append(var)
    
    if missing_required:
        print(f"\n❌ Missing required variables: {', '.join(missing_required)}")
        return False
    
    if missing_optional:
        print(f"\n⚠️  Missing optional variables: {', '.join(missing_optional)}")
    
    print("\n✅ Environment variables check passed")
    return True


def check_postgresql():
    """Check PostgreSQL connection and pgvector extension."""
    print("\n=== Checking PostgreSQL ===")
    
    try:
        from sqlalchemy import create_engine, text
        from dotenv import load_dotenv
        
        load_dotenv()
        database_url = os.getenv("DATABASE_URL")
        vector_database_url = os.getenv("VECTOR_DATABASE_URL")
        
        if not database_url:
            print("❌ DATABASE_URL not set")
            return False
        
        # Check main database
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ PostgreSQL main database connection successful")
        
        engine.dispose()
        
        # Check vector database with pgvector
        if not vector_database_url:
            print("⚠ VECTOR_DATABASE_URL not set - skipping pgvector check")
            print("\n✅ PostgreSQL check passed (main database only)")
            return True
        
        vector_engine = create_engine(vector_database_url)
        
        with vector_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ PostgreSQL vector database connection successful")
            
            # Check pgvector extension
            result = conn.execute(
                text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'")
            )
            row = result.fetchone()
            
            if row:
                print(f"✓ pgvector extension installed (version {row[1]})")
            else:
                print("✗ pgvector extension NOT installed in vector database")
                print("  Run: CREATE EXTENSION vector; in the vector database")
                vector_engine.dispose()
                return False
            
            # Check if we can create a vector column (test)
            try:
                conn.execute(text("SELECT '[1,2,3]'::vector"))
                print("✓ Vector type working correctly")
            except Exception as e:
                print(f"✗ Vector type test failed: {e}")
                vector_engine.dispose()
                return False
        
        vector_engine.dispose()
        print("\n✅ PostgreSQL check passed")
        return True
        
    except ImportError as e:
        print(f"❌ Missing Python package: {e}")
        print("  Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        print("  Make sure PostgreSQL is running: docker-compose up -d")
        return False


def check_redis():
    """Check Redis connection."""
    print("\n=== Checking Redis ===")
    
    try:
        import redis
        from dotenv import load_dotenv
        
        load_dotenv()
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # Parse Redis URL
        client = redis.from_url(redis_url)
        
        # Test connection
        response = client.ping()
        if response:
            print("✓ Redis connection successful")
        else:
            print("✗ Redis ping failed")
            return False
        
        # Test set/get
        test_key = "ai_agent_setup_test"
        client.set(test_key, "test_value", ex=10)
        value = client.get(test_key)
        
        if value == b"test_value":
            print("✓ Redis set/get working correctly")
            client.delete(test_key)
        else:
            print("✗ Redis set/get test failed")
            return False
        
        # Get Redis info
        info = client.info()
        print(f"✓ Redis version: {info.get('redis_version', 'unknown')}")
        print(f"✓ Redis memory: {info.get('used_memory_human', 'unknown')}")
        
        client.close()
        print("\n✅ Redis check passed")
        return True
        
    except ImportError as e:
        print(f"❌ Missing Python package: {e}")
        print("  Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("  Make sure Redis is running: docker-compose up -d redis")
        return False


def check_python_dependencies():
    """Check that required Python packages are installed."""
    print("\n=== Checking Python Dependencies ===")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic",
        "redis",
        "openai",
        "pytest",
        "hypothesis",
    ]
    
    ai_agent_packages = [
        "langgraph",
        "langchain",
        "asyncpg",
        "sentence_transformers",
        "tenacity",
        "structlog",
    ]
    
    missing_required = []
    missing_ai_agent = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package}")
            missing_required.append(package)
    
    for package in ai_agent_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"⚠ {package} (AI Agent dependency)")
            missing_ai_agent.append(package)
    
    if missing_required:
        print(f"\n❌ Missing required packages: {', '.join(missing_required)}")
        print("  Run: pip install -r requirements.txt")
        return False
    
    if missing_ai_agent:
        print(f"\n⚠️  Missing AI Agent packages: {', '.join(missing_ai_agent)}")
        print("  These will be needed for AI Agent implementation")
        print("  Run: pip install -r requirements.txt")
    
    print("\n✅ Python dependencies check passed")
    return True


def check_docker_services():
    """Check if Docker services are running."""
    print("\n=== Checking Docker Services ===")
    
    try:
        import subprocess
        
        # Check if docker-compose is available
        result = subprocess.run(
            ["docker-compose", "--version"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("❌ docker-compose not found")
            print("  Install Docker Compose: https://docs.docker.com/compose/install/")
            return False
        
        print(f"✓ docker-compose: {result.stdout.strip()}")
        
        # Check running containers
        result = subprocess.run(
            ["docker-compose", "ps", "--services", "--filter", "status=running"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            running_services = result.stdout.strip().split("\n")
            running_services = [s for s in running_services if s]
            
            if "postgres" in running_services:
                print("✓ PostgreSQL container running")
            else:
                print("⚠ PostgreSQL container not running")
                print("  Start with: docker-compose up -d postgres")
            
            if "redis" in running_services:
                print("✓ Redis container running")
            else:
                print("⚠ Redis container not running")
                print("  Start with: docker-compose up -d redis")
            
            if running_services:
                print(f"\n✓ Running services: {', '.join(running_services)}")
            else:
                print("\n⚠ No services running")
                print("  Start services with: docker-compose up -d")
        
        print("\n✅ Docker services check passed")
        return True
        
    except FileNotFoundError:
        print("❌ docker-compose command not found")
        print("  Install Docker Compose: https://docs.docker.com/compose/install/")
        return False
    except Exception as e:
        print(f"⚠ Could not check Docker services: {e}")
        return True  # Don't fail if we can't check Docker


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("AI Agent System - Setup Verification")
    print("=" * 60)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    checks = [
        ("Environment Variables", check_environment_variables),
        ("Docker Services", check_docker_services),
        ("Python Dependencies", check_python_dependencies),
        ("PostgreSQL", check_postgresql),
        ("Redis", check_redis),
    ]
    
    results = {}
    
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n❌ {name} check failed with error: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All checks passed! Your environment is ready.")
        print("\nNext steps:")
        print("1. Review the design document: .kiro/specs/ai-agent/design.md")
        print("2. Start implementing Task 2: Core data models and schemas")
        print("3. Run the application: uvicorn app.main:app --reload")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\nQuick fixes:")
        print("- Start Docker services: docker-compose up -d")
        print("- Install dependencies: pip install -r requirements.txt")
        print("- Configure .env file with your API keys")
        return 1


if __name__ == "__main__":
    sys.exit(main())
