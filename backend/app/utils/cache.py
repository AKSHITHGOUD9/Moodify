"""Cache management utilities"""

import time
from typing import Dict, Any, Optional
from functools import lru_cache

class CacheManager:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = 3600  # 1 hour default TTL
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        
        cache_data = self._cache[key]
        if time.time() - cache_data['timestamp'] > self._ttl:
            del self._cache[key]
            return None
        
        return cache_data['data']
    
    def set(self, key: str, data: Any, ttl: int = None) -> None:
        self._cache[key] = {
            'data': data,
            'timestamp': time.time(),
            'ttl': ttl or self._ttl
        }
    
    def clear(self, key: str = None) -> None:
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()

user_profile_cache = CacheManager()
album_covers_cache = CacheManager()
