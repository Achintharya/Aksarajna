import time
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from src.utils.config_manager import config_manager
from src.utils.logger import logger

class Cache:
    """
    Simple cache implementation with TTL support.
    Can be extended to use Redis or other caching solutions in the future.
    """
    
    def __init__(self):
        """Initialize the cache."""
        self.config = config_manager
        self.enabled = self.config.get('cache.enabled', True)
        self.ttl = self.config.get('cache.ttl', 3600)  # Default TTL: 1 hour
        self.cache_dir = Path('./cache')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"Cache initialized (enabled: {self.enabled}, TTL: {self.ttl}s)")
    
    def _get_cache_path(self, key: str) -> Path:
        """Get the cache file path for a key."""
        # Use a simple hash function to avoid file name issues
        hashed_key = str(hash(key) % 10000000)
        return self.cache_dir / f"{hashed_key}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key (str): The cache key.
            
        Returns:
            The cached value, or None if not found or expired.
        """
        if not self.enabled:
            return None
        
        # Check memory cache first
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if entry['expires'] > time.time():
                logger.debug(f"Cache hit (memory): {key}")
                return entry['value']
            else:
                # Expired, remove from memory cache
                del self.memory_cache[key]
        
        # Check file cache
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    entry = json.load(f)
                
                if entry['expires'] > time.time():
                    # Add to memory cache for faster access next time
                    self.memory_cache[key] = entry
                    logger.debug(f"Cache hit (file): {key}")
                    return entry['value']
                else:
                    # Expired, remove the file
                    os.remove(cache_path)
            except (json.JSONDecodeError, KeyError, OSError) as e:
                logger.warning(f"Error reading cache file for key {key}: {e}")
        
        logger.debug(f"Cache miss: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key (str): The cache key.
            value (Any): The value to cache.
            ttl (int, optional): Time-to-live in seconds. If None, use the default TTL.
        """
        if not self.enabled:
            return
        
        ttl = ttl or self.ttl
        expires = time.time() + ttl
        
        entry = {
            'value': value,
            'expires': expires
        }
        
        # Store in memory cache
        self.memory_cache[key] = entry
        
        # Store in file cache
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, 'w') as f:
                json.dump(entry, f)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
        except OSError as e:
            logger.warning(f"Error writing cache file for key {key}: {e}")
    
    def delete(self, key: str) -> None:
        """
        Delete a value from the cache.
        
        Args:
            key (str): The cache key.
        """
        if not self.enabled:
            return
        
        # Remove from memory cache
        if key in self.memory_cache:
            del self.memory_cache[key]
        
        # Remove from file cache
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                os.remove(cache_path)
                logger.debug(f"Cache deleted: {key}")
            except OSError as e:
                logger.warning(f"Error deleting cache file for key {key}: {e}")
    
    def clear(self) -> None:
        """Clear the entire cache."""
        if not self.enabled:
            return
        
        # Clear memory cache
        self.memory_cache.clear()
        
        # Clear file cache
        try:
            for cache_file in self.cache_dir.glob('*.json'):
                os.remove(cache_file)
            logger.info("Cache cleared")
        except OSError as e:
            logger.warning(f"Error clearing cache: {e}")
    
    def cleanup(self) -> None:
        """Remove expired entries from the cache."""
        if not self.enabled:
            return
        
        # Clean memory cache
        now = time.time()
        expired_keys = [k for k, v in self.memory_cache.items() if v['expires'] <= now]
        for key in expired_keys:
            del self.memory_cache[key]
        
        # Clean file cache
        try:
            for cache_file in self.cache_dir.glob('*.json'):
                try:
                    with open(cache_file, 'r') as f:
                        entry = json.load(f)
                    
                    if entry['expires'] <= now:
                        os.remove(cache_file)
                except (json.JSONDecodeError, KeyError, OSError):
                    # If there's any error, just remove the file
                    try:
                        os.remove(cache_file)
                    except OSError:
                        pass
            
            logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")
        except OSError as e:
            logger.warning(f"Error during cache cleanup: {e}")

# Create a singleton instance
cache = Cache()
