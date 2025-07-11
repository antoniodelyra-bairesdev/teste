import json
import hashlib
from functools import wraps
from typing import Any, Callable, Optional

from ehp.base.redis_storage import get_redis_client
from ehp.utils.base import log_error


def cache_response(key_prefix: str, ttl: int = 300, user_specific: bool = True):
    """
    Cache decorator for endpoint responses using Redis.
    
    Args:
        key_prefix: Prefix for the cache key
        ttl: Time to live in seconds (default: 5 minutes)
        user_specific: Whether to include user ID in cache key
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                redis_client = get_redis_client()
                
                # Create cache key from function parameters
                cache_params = {k: v for k, v in kwargs.items() if k not in ['db_session', 'user']}
                
                # Add user ID to cache key if user_specific is True
                if user_specific and 'user' in kwargs:
                    cache_params['user_id'] = kwargs['user'].user.id
                
                # Create a secure hash of the parameters for the cache key
                # Using SHA-256 instead of MD5 for better security
                params_str = json.dumps(cache_params, sort_keys=True, default=str)
                params_hash = hashlib.sha256(params_str.encode('utf-8')).hexdigest()
                cache_key = f"{key_prefix}:{params_hash}"
                
                # Try to get cached response
                cached = redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                
                # Serialize result for caching
                if hasattr(result, 'model_dump'):
                    # Pydantic model
                    serialized_result = result.model_dump()
                elif hasattr(result, 'dict'):
                    # Legacy Pydantic model
                    serialized_result = result.dict()
                else:
                    # Assume it's already serializable
                    serialized_result = result
                
                redis_client.setex(cache_key, ttl, json.dumps(serialized_result, default=str))
                return result
                
            except Exception as e:
                log_error(f"Cache error in {func.__name__}: {e}")
                # If caching fails, still execute the function
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern: str) -> int:
    """
    Invalidate cache entries matching a pattern using SCAN.
    
    Args:
        pattern: Redis key pattern (e.g., "my_pages:*")
    
    Returns:
        Number of keys deleted
    """
    deleted_count = 0
    try:
        redis_client = get_redis_client()
        
        # Use SCAN to iterate keys safely without blocking the server
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match=pattern, count=1000)
            if keys:
                deleted_count += redis_client.delete(*keys)
            if cursor == 0:
                break
        
        return deleted_count
    except Exception as e:
        log_error(f"Cache invalidation error for pattern {pattern}: {e}")
        return 0


def invalidate_user_cache(user_id: int, cache_prefix: str) -> int:
    """
    Invalidate all cache entries for a specific user.
    
    Args:
        user_id: User ID
        cache_prefix: Cache key prefix (e.g., "my_pages")
    
    Returns:
        Number of keys deleted
    """
    pattern = f"{cache_prefix}:*user_id*{user_id}*"
    return invalidate_cache_pattern(pattern)


def get_cached_value(key: str) -> Optional[Any]:
    """
    Get a cached value by key.
    
    Args:
        key: Cache key
    
    Returns:
        Cached value or None if not found
    """
    try:
        redis_client = get_redis_client()
        cached = redis_client.get(key)
        return json.loads(cached) if cached else None
    except Exception as e:
        log_error(f"Cache retrieval error for key {key}: {e}")
        return None


def set_cached_value(key: str, value: Any, ttl: int = 300) -> bool:
    """
    Set a cached value with TTL.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds
    
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client = get_redis_client()
        redis_client.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as e:
        log_error(f"Cache set error for key {key}: {e}")
        return False
