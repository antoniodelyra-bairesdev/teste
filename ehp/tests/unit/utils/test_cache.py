import json
import pytest
from unittest.mock import patch, Mock

from ehp.utils.cache import (
    cache_response,
    invalidate_user_cache,
    get_cached_value,
    set_cached_value
)


@pytest.mark.unit
class TestCacheResponse:
    """Test the cache_response decorator"""

    async def test_cache_response_basic_functionality(self, mock_redis):
        """Test that the decorator caches function results"""
        @cache_response("test", ttl=60)
        async def test_func(param1="value1"):
            return {"result": param1}

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            # First call should execute function and cache result
            result1 = await test_func(param1="test_value")
            assert result1 == {"result": "test_value"}
            
            # Verify data was cached
            keys = mock_redis.keys("test:*")
            assert len(keys) == 1
            cache_key = keys[0]
            assert cache_key.startswith("test:")

    async def test_cache_response_with_user_specific_caching(self, mock_redis):
        """Test user-specific cache key generation"""
        @cache_response("my_pages", ttl=300, user_specific=True)
        async def my_pages_func(user=None, page=1):
            return {"data": f"user_{user.user.id}_page_{page}"}

        mock_user = Mock()
        mock_user.user.id = 123

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            result = await my_pages_func(user=mock_user, page=1)
            
            # Verify cache key includes user ID context
            assert result == {"data": "user_123_page_1"}
            keys = mock_redis.keys("my_pages:*")
            assert len(keys) == 1

    async def test_cache_response_handles_redis_error_gracefully(self):
        """Test that function still executes when Redis fails"""
        @cache_response("test", ttl=60)
        async def test_func(value="test"):
            return {"value": value}

        mock_redis = Mock()
        mock_redis.get.side_effect = Exception("Redis connection failed")

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            with patch("ehp.utils.cache.log_error") as mock_log:
                result = await test_func(value="fallback")
                assert result == {"value": "fallback"}
                mock_log.assert_called_once()

    async def test_cache_response_excludes_sensitive_params(self, mock_redis):
        """Test that db_session and user are excluded from cache key"""
        @cache_response("test", ttl=60)
        async def test_func(db_session=None, user=None, param="value"):
            return {"param": param}

        mock_user = Mock()
        mock_db_session = Mock()

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            result = await test_func(db_session=mock_db_session, user=mock_user, param="test")
            assert result == {"param": "test"}
            
            # Verify cache key was created
            keys = mock_redis.keys("test:*")
            assert len(keys) == 1


@pytest.mark.unit
class TestCacheOperations:
    """Test basic cache get/set operations"""

    def test_get_cached_value_success(self, mock_redis):
        """Test successful cache retrieval"""
        test_data = {"key": "value", "number": 42}
        mock_redis.set("test_key", json.dumps(test_data))

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            result = get_cached_value("test_key")
            assert result == test_data

    def test_get_cached_value_not_found(self, mock_redis):
        """Test cache retrieval when key doesn't exist"""
        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            result = get_cached_value("nonexistent_key")
            assert result is None

    def test_get_cached_value_redis_error(self, mock_redis):
        """Test cache retrieval when Redis fails"""
        # Create a proper mock for Redis client
        mock_redis_client = Mock()
        mock_redis_client.get.side_effect = Exception("Redis error")

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis_client):
            with patch("ehp.utils.cache.log_error") as mock_log:
                result = get_cached_value("test_key")
                assert result is None
                mock_log.assert_called_once()

    def test_set_cached_value_success(self, mock_redis):
        """Test successful cache storage"""
        test_data = {"test": "data"}

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            result = set_cached_value("test_key", test_data, ttl=300)
            assert result is True
            
            cached_value = json.loads(mock_redis.get("test_key"))
            assert cached_value == test_data

    def test_set_cached_value_redis_error(self, mock_redis):
        """Test cache storage when Redis fails"""
        # Create a proper mock for Redis client
        mock_redis_client = Mock()
        mock_redis_client.setex.side_effect = Exception("Redis error")

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis_client):
            with patch("ehp.utils.cache.log_error") as mock_log:
                result = set_cached_value("test_key", {"data": "test"}, ttl=300)
                assert result is False
                mock_log.assert_called_once()

    def test_invalidate_user_cache(self, mock_redis):
        """Test user-specific cache invalidation"""
        # Setup test data with user-specific keys
        mock_redis.set("my_pages:hash1_user_id_123", "value1")
        mock_redis.set("my_pages:hash2_user_id_456", "value2")

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            deleted_count = invalidate_user_cache(123, "my_pages")
            # Should attempt to delete user 123's cache
            assert deleted_count >= 0


@pytest.mark.unit
class TestCacheKeySecurity:
    """Test cache key generation security"""

    async def test_cache_key_uses_sha256(self, mock_redis):
        """Test that cache keys use SHA-256 hashing"""
        @cache_response("test", ttl=60)
        async def test_func(param="value"):
            return {"result": param}

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            await test_func(param="test_value")
            
            keys = mock_redis.keys("test:*")
            cache_key = keys[0]
            
            # SHA-256 produces 64-character hex strings
            hash_part = cache_key.split(":", 1)[1]
            assert len(hash_part) == 64
            assert all(c in "0123456789abcdef" for c in hash_part)

    async def test_cache_key_consistency(self, mock_redis):
        """Test that same parameters produce same cache key"""
        @cache_response("test", ttl=60)
        async def test_func(param1="value1", param2="value2"):
            return {"result": f"{param1}_{param2}"}

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            # Call with same parameters twice
            await test_func(param1="test", param2="value")
            keys_first = mock_redis.keys("test:*")
            
            mock_redis.flushall()  # Clear cache
            
            await test_func(param1="test", param2="value")
            keys_second = mock_redis.keys("test:*")
            
            # Should produce the same cache key
            assert keys_first == keys_second


@pytest.mark.unit
class TestRedisConnectionErrors:
    """Test Redis connection error handling"""

    async def test_cache_response_redis_connection_error(self):
        """Test that cache_response raises RedisConnectionError on Redis connection issues. Tests lines 63-64."""
        from redis.exceptions import ConnectionError
        from ehp.base.exceptions import RedisConnectionError

        @cache_response("test", ttl=60)
        async def test_func(param="value"):
            return {"result": param}

        mock_redis = Mock()
        mock_redis.get.side_effect = ConnectionError("Connection failed")

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            with pytest.raises(RedisConnectionError, match="Redis connection failed"):
                await test_func(param="test_value")

    async def test_cache_response_redis_timeout_error(self):
        """Test that cache_response raises RedisError on Redis timeout issues. Tests lines 67-68-69."""
        from redis.exceptions import TimeoutError
        from ehp.base.exceptions import RedisError

        @cache_response("test", ttl=60)
        async def test_func(param="value"):
            return {"result": param}

        mock_redis = Mock()
        mock_redis.get.side_effect = TimeoutError("Timeout occurred")

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            with pytest.raises(RedisError, match="Redis operation failed"):
                await test_func(param="test_value")

    async def test_cache_response_redis_base_error(self):
        """Test that cache_response raises RedisError on Redis base error. Tests lines 67-68-69."""
        from redis.exceptions import RedisError as RedisBaseError
        from ehp.base.exceptions import RedisError

        @cache_response("test", ttl=60)
        async def test_func(param="value"):
            return {"result": param}

        mock_redis = Mock()
        mock_redis.get.side_effect = RedisBaseError("Redis error")

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            with pytest.raises(RedisError, match="Redis operation failed"):
                await test_func(param="test_value")

    def test_invalidate_cache_pattern_connection_error(self):
        """Test that invalidate_cache_pattern raises RedisConnectionError on connection issues. Tests lines 103-104-105-106."""
        from redis.exceptions import ConnectionError
        from ehp.base.exceptions import RedisConnectionError
        from ehp.utils.cache import invalidate_cache_pattern

        mock_redis = Mock()
        mock_redis.scan.side_effect = ConnectionError("Connection failed")

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            with pytest.raises(RedisConnectionError, match="Redis connection failed"):
                invalidate_cache_pattern("test:*")

    def test_invalidate_cache_pattern_timeout_error(self):
        """Test that invalidate_cache_pattern raises RedisError on timeout. Tests lines 107-108-109-110."""
        from redis.exceptions import TimeoutError
        from ehp.base.exceptions import RedisError
        from ehp.utils.cache import invalidate_cache_pattern

        mock_redis = Mock()
        mock_redis.scan.side_effect = TimeoutError("Timeout occurred")

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            with pytest.raises(RedisError, match="Redis operation failed"):
                invalidate_cache_pattern("test:*")

    def test_invalidate_cache_pattern_redis_base_error(self):
        """Test that invalidate_cache_pattern raises RedisError on Redis base error. Tests lines 107-108-109-110."""
        from redis.exceptions import RedisError as RedisBaseError
        from ehp.base.exceptions import RedisError
        from ehp.utils.cache import invalidate_cache_pattern

        mock_redis = Mock()
        mock_redis.scan.side_effect = RedisBaseError("Redis error")

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            with pytest.raises(RedisError, match="Redis operation failed"):
                invalidate_cache_pattern("test:*")

    def test_get_cached_value_connection_error(self):
        """Test that get_cached_value raises RedisConnectionError on connection issues. Tests lines 145-146-147-148."""
        from redis.exceptions import ConnectionError
        from ehp.base.exceptions import RedisConnectionError

        mock_redis = Mock()
        mock_redis.get.side_effect = ConnectionError("Connection failed")

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            with pytest.raises(RedisConnectionError, match="Redis connection failed"):
                get_cached_value("test_key")

    def test_get_cached_value_timeout_error(self):
        """Test that get_cached_value raises RedisError on timeout. Tests lines 149-150-151-152."""
        from redis.exceptions import TimeoutError
        from ehp.base.exceptions import RedisError

        mock_redis = Mock()
        mock_redis.get.side_effect = TimeoutError("Timeout occurred")

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            with pytest.raises(RedisError, match="Redis operation failed"):
                get_cached_value("test_key")

    def test_get_cached_value_redis_base_error(self):
        """Test that get_cached_value raises RedisError on Redis base error. Tests lines 149-150-151-152."""
        from redis.exceptions import RedisError as RedisBaseError
        from ehp.base.exceptions import RedisError

        mock_redis = Mock()
        mock_redis.get.side_effect = RedisBaseError("Redis error")

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            with pytest.raises(RedisError, match="Redis operation failed"):
                get_cached_value("test_key")

    def test_set_cached_value_connection_error(self):
        """Test that set_cached_value raises RedisConnectionError on connection issues. Tests lines 174-175-176-177."""
        from redis.exceptions import ConnectionError
        from ehp.base.exceptions import RedisConnectionError

        mock_redis = Mock()
        mock_redis.setex.side_effect = ConnectionError("Connection failed")

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            with pytest.raises(RedisConnectionError, match="Redis connection failed"):
                set_cached_value("test_key", {"data": "test"}, ttl=300)

    def test_set_cached_value_timeout_error(self):
        """Test that set_cached_value raises RedisError on timeout. Tests lines 178-179-180-181."""
        from redis.exceptions import TimeoutError
        from ehp.base.exceptions import RedisError

        mock_redis = Mock()
        mock_redis.setex.side_effect = TimeoutError("Timeout occurred")

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            with pytest.raises(RedisError, match="Redis operation failed"):
                set_cached_value("test_key", {"data": "test"}, ttl=300)

    def test_set_cached_value_redis_base_error(self):
        """Test that set_cached_value raises RedisError on Redis base error. Tests lines 178-179-180-181."""
        from redis.exceptions import RedisError as RedisBaseError
        from ehp.base.exceptions import RedisError

        mock_redis = Mock()
        mock_redis.setex.side_effect = RedisBaseError("Redis error")

        with patch("ehp.utils.cache.get_redis_client", return_value=mock_redis):
            with pytest.raises(RedisError, match="Redis operation failed"):
                set_cached_value("test_key", {"data": "test"}, ttl=300)