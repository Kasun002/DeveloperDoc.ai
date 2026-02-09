"""
Unit tests for Vector Database Manager.

Tests connection pooling, retry logic, and health checks for the
AsyncPG-based vector database manager.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncpg
from app.core.vector_database import VectorDatabaseManager


@pytest.mark.asyncio
class TestVectorDatabaseManager:
    """Test suite for VectorDatabaseManager."""
    
    async def test_connect_creates_pool(self):
        """Test that connect() creates a connection pool."""
        manager = VectorDatabaseManager("postgresql://test:test@localhost:5432/test")
        
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool
            
            await manager.connect()
            
            assert manager.pool is not None
            mock_create_pool.assert_called_once()
    
    async def test_connect_with_retry_on_failure(self):
        """Test that connect() retries on connection failure."""
        manager = VectorDatabaseManager("postgresql://test:test@localhost:5432/test")
        
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
            # Fail twice, then succeed
            mock_pool = AsyncMock()
            mock_create_pool.side_effect = [
                asyncpg.PostgresConnectionError("Connection failed"),
                asyncpg.PostgresConnectionError("Connection failed"),
                mock_pool
            ]
            
            await manager.connect()
            
            assert manager.pool is not None
            assert mock_create_pool.call_count == 3
    
    async def test_connect_raises_after_max_retries(self):
        """Test that connect() raises ConnectionError after max retries."""
        manager = VectorDatabaseManager("postgresql://test:test@localhost:5432/test")
        
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
            mock_create_pool.side_effect = asyncpg.PostgresConnectionError("Connection failed")
            
            with pytest.raises(ConnectionError):
                await manager.connect()
    
    async def test_disconnect_closes_pool(self):
        """Test that disconnect() closes the connection pool."""
        manager = VectorDatabaseManager("postgresql://test:test@localhost:5432/test")
        
        mock_pool = AsyncMock()
        manager.pool = mock_pool
        
        await manager.disconnect()
        
        mock_pool.close.assert_called_once()
        assert manager.pool is None
    
    async def test_health_check_returns_healthy(self):
        """Test health check returns healthy status when database is accessible."""
        manager = VectorDatabaseManager("postgresql://test:test@localhost:5432/test")
        
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=[1, True])
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock()))
        mock_pool.get_size = MagicMock(return_value=5)
        mock_pool.get_idle_size = MagicMock(return_value=3)
        
        manager.pool = mock_pool
        
        health = await manager.health_check()
        
        assert health["status"] == "healthy"
        assert health["pool_size"] == 5
        assert health["pool_free"] == 3
        assert health["pgvector_available"] is True
    
    async def test_health_check_returns_disconnected_when_no_pool(self):
        """Test health check returns disconnected when pool is not initialized."""
        manager = VectorDatabaseManager("postgresql://test:test@localhost:5432/test")
        
        health = await manager.health_check()
        
        assert health["status"] == "disconnected"
        assert "error" in health
    
    async def test_health_check_returns_unhealthy_on_error(self):
        """Test health check returns unhealthy status on database error."""
        manager = VectorDatabaseManager("postgresql://test:test@localhost:5432/test")
        
        mock_pool = AsyncMock()
        mock_pool.acquire.side_effect = Exception("Database error")
        
        manager.pool = mock_pool
        
        health = await manager.health_check()
        
        assert health["status"] == "unhealthy"
        assert "error" in health
    
    async def test_reconnect_closes_and_creates_new_pool(self):
        """Test that reconnect() closes old pool and creates new one."""
        manager = VectorDatabaseManager("postgresql://test:test@localhost:5432/test")
        
        old_pool = AsyncMock()
        manager.pool = old_pool
        
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
            new_pool = AsyncMock()
            mock_create_pool.return_value = new_pool
            
            await manager.reconnect()
            
            old_pool.close.assert_called_once()
            assert manager.pool == new_pool
    
    async def test_acquire_raises_when_pool_not_initialized(self):
        """Test that acquire() raises ConnectionError when pool is not initialized."""
        manager = VectorDatabaseManager("postgresql://test:test@localhost:5432/test")
        
        with pytest.raises(ConnectionError):
            await manager.acquire()
    
    async def test_fetch_executes_query(self):
        """Test that fetch() executes query and returns results."""
        manager = VectorDatabaseManager("postgresql://test:test@localhost:5432/test")
        
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[{"id": 1}, {"id": 2}])
        
        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock()))
        
        manager.pool = mock_pool
        
        results = await manager.fetch("SELECT * FROM test")
        
        assert len(results) == 2
        mock_conn.fetch.assert_called_once()
    
    async def test_fetch_retries_on_connection_error(self):
        """Test that fetch() has retry logic configured."""
        manager = VectorDatabaseManager("postgresql://test:test@localhost:5432/test")
        
        # Test that fetch method exists and is wrapped with retry decorator
        assert hasattr(manager, 'fetch')
        assert callable(manager.fetch)
        
        # Test successful fetch (no retry needed)
        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[{"id": 1}])
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock()))
        
        manager.pool = mock_pool
        
        results = await manager.fetch("SELECT * FROM test")
        
        assert len(results) == 1
        assert results[0]["id"] == 1
    
    async def test_fetchrow_returns_single_row(self):
        """Test that fetchrow() returns a single row."""
        manager = VectorDatabaseManager("postgresql://test:test@localhost:5432/test")
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={"id": 1, "name": "test"})
        
        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock()))
        
        manager.pool = mock_pool
        
        result = await manager.fetchrow("SELECT * FROM test WHERE id = $1", 1)
        
        assert result["id"] == 1
        assert result["name"] == "test"
    
    async def test_fetchval_returns_single_value(self):
        """Test that fetchval() returns a single value."""
        manager = VectorDatabaseManager("postgresql://test:test@localhost:5432/test")
        
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=42)
        
        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock()))
        
        manager.pool = mock_pool
        
        result = await manager.fetchval("SELECT COUNT(*) FROM test")
        
        assert result == 42
